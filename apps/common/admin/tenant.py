from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.platform.organizations.models import Organization


class TenantAdminMixin(admin.ModelAdmin):
    """
    Tenant-safe admin with an explicit Platform Mode for superusers.

    Tenant Mode (default):
      - requires request.organization
      - queryset filtered to that org
      - organization field hidden & forced on save

    Platform Mode (superuser, no request.organization):
      - queryset is unscoped (all orgs)
      - organization field is visible and required
      - no automatic org forcing (but we still validate org is set)
    """

    def is_platform_mode(self, request: HttpRequest) -> bool:
        org = getattr(request, "organization", None)
        return (
            org is None and request.user.is_authenticated and request.user.is_superuser
        )

    def get_organization(self, request: HttpRequest) -> Organization:
        org = getattr(request, "organization", None)
        if org is None:
            raise PermissionError(
                "Tenant organization not resolved for tenant-mode admin request."
            )
        return org

    def _base_queryset(self):
        """
        Some tenant models use a custom manager/queryset with `.unscoped()`,
        while others (like Membership) may use the default Manager.

        Always return a queryset that can be safely filtered.
        """
        mgr = self.model._default_manager
        if hasattr(mgr, "unscoped") and callable(getattr(mgr, "unscoped")):
            return mgr.unscoped().all()
        return mgr.all()

    def get_exclude(self, request: HttpRequest, obj=None):
        # Hide org in tenant-mode; show in platform-mode
        base_exclude = {"created_by", "updated_by"}
        if self.is_platform_mode(request):
            return tuple(base_exclude)
        return tuple(base_exclude | {"organization"})

    def get_queryset(self, request: HttpRequest):
        qs = self._base_queryset()

        if self.is_platform_mode(request):
            return qs

        org = self.get_organization(request)

        # TenantAdminMixin is intended for tenant-owned models.
        # Filter if the model has organization_id, otherwise deny-by-default.
        if hasattr(self.model, "organization_id"):
            return qs.filter(organization_id=org.id)

        return qs.none()

    def save_model(self, request: HttpRequest, obj, form, change):
        if not self.is_platform_mode(request):
            org = self.get_organization(request)
            if hasattr(obj, "organization_id"):
                obj.organization_id = org.id  # force org in tenant mode
        else:
            # Platform mode: require org explicitly set (for tenant-owned models)
            if (
                hasattr(obj, "organization_id")
                and getattr(obj, "organization_id", None) is None
            ):
                raise ValueError("organization must be set in platform mode.")

        # Audit fields
        if not change and hasattr(obj, "created_by_id"):
            obj.created_by = request.user if request.user.is_authenticated else None
        if hasattr(obj, "updated_by_id"):
            obj.updated_by = request.user if request.user.is_authenticated else None

        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request: HttpRequest, **kwargs):
        # In platform mode we do NOT tenant-filter FK choices.
        if self.is_platform_mode(request):
            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        org = getattr(request, "organization", None)
        if org and "queryset" in kwargs and kwargs["queryset"] is not None:
            qs = kwargs["queryset"]
            if hasattr(qs.model, "organization_id"):
                kwargs["queryset"] = qs.filter(organization_id=org.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
