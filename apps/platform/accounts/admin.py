from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.http import HttpRequest

from webcrm.admin import admin_site

from apps.common.admin.rbac import RBACPermissionAdminMixin
from apps.common.admin.tenant import TenantAdminMixin
from apps.platform.accounts.models import Membership
from apps.platform.rbac.bootstrap import (
    ensure_owner_assigned,
    ensure_staff_and_admin_perms_for_models,
)
from apps.platform.rbac.models import MembershipRole

User = get_user_model()

TENANT_ADMIN_APP_LABELS = ["locations", "rbac", "accounts"]


class TenantUserCreationForm(forms.ModelForm):
    """
    Tenant-mode: create a global User and set password.
    Membership is created in UserAdmin.save_model based on request.organization.
    """

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "is_active")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Email is required.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError({"password2": "Passwords do not match."})
        if p1:
            validate_password(p1)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            obj.set_password(password)
        if commit:
            obj.save()
        return obj


class TenantUserChangeForm(forms.ModelForm):
    """
    Tenant-mode: edit global user basics; optional password reset.
    """

    new_password1 = forms.CharField(
        label="New password",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        help_text="Leave blank to keep the current password.",
    )
    new_password2 = forms.CharField(
        label="New password confirmation",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "is_active")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Email is required.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 or p2:
            if not p1 or not p2:
                raise ValidationError(
                    "Both password fields are required to reset password."
                )
            if p1 != p2:
                raise ValidationError({"new_password2": "Passwords do not match."})
            validate_password(p1)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        p1 = self.cleaned_data.get("new_password1")
        if p1:
            obj.set_password(p1)
        if commit:
            obj.save()
        return obj


class TenantBoundUserAdminMixin(admin.ModelAdmin):
    """
    Tenant-safe queryset behavior for the global User model.

    - Platform Mode (superuser with no request.organization): see all users.
    - Tenant Mode: only users that have a Membership in request.organization.
    """

    def is_platform_mode(self, request: HttpRequest) -> bool:
        org = getattr(request, "organization", None)
        return (
            org is None and request.user.is_authenticated and request.user.is_superuser
        )

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)

        if self.is_platform_mode(request):
            return qs

        org = getattr(request, "organization", None)
        if org is None:
            # Deny-by-default: without a resolved tenant, do not expose global users
            return qs.none()

        membership_qs = Membership.objects.filter(
            user_id=OuterRef("pk"),
            organization_id=org.id,
        )
        return qs.annotate(_has_membership=Exists(membership_qs)).filter(
            _has_membership=True
        )


@admin.register(User, site=admin_site)
class UserAdmin(TenantBoundUserAdminMixin):
    list_display = (
        "email",
        "full_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    search_fields = ("email", "full_name")
    list_filter = ("is_active", "is_staff", "is_superuser")
    ordering = ("email",)

    # Tenant-mode forms
    add_form = TenantUserCreationForm
    form = TenantUserChangeForm

    def get_form(self, request: HttpRequest, obj=None, change=False, **kwargs):
        """
        Use tenant-safe forms in tenant mode; default ModelAdmin behavior in platform mode.
        """
        if self.is_platform_mode(request):
            return super().get_form(request, obj=obj, change=change, **kwargs)

        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        else:
            defaults["form"] = self.form
        defaults.update(kwargs)
        return super().get_form(request, obj=obj, change=change, **defaults)

    def get_fieldsets(self, request: HttpRequest, obj=None):
        """
        Tenant mode: keep it tight and safe (no groups/perms/superuser toggles).
        Platform mode: fall back to default.
        """
        if self.is_platform_mode(request):
            return super().get_fieldsets(request, obj=obj)

        if obj is None:
            return (
                (
                    None,
                    {
                        "fields": (
                            "email",
                            "full_name",
                            "is_active",
                            "password1",
                            "password2",
                        )
                    },
                ),
            )

        return (
            (None, {"fields": ("email", "full_name", "is_active")}),
            ("Password reset", {"fields": ("new_password1", "new_password2")}),
        )

    def save_model(self, request: HttpRequest, obj, form, change):
        """
        Tenant mode invariants:
          - force is_staff=True (admin-first MVP)
          - force is_superuser=False
          - ensure Membership(user, active org) exists + ACTIVE
        """
        if not self.is_platform_mode(request):
            org = getattr(request, "organization", None)
            if org is None:
                raise PermissionError(
                    "Tenant organization not resolved for user admin request."
                )

            obj.is_superuser = False
            obj.is_staff = True

            super().save_model(request, obj, form, change)

            membership, created = Membership.objects.get_or_create(
                user=obj,
                organization=org,
                defaults={"status": Membership.Status.ACTIVE},
            )
            if not created and membership.status != Membership.Status.ACTIVE:
                membership.status = Membership.Status.ACTIVE
                membership.save(update_fields=["status"])
            return

        super().save_model(request, obj, form, change)


@admin.action(description="Make Org Owner (RBAC)")
def make_org_owner(modeladmin, request, queryset):
    changed = 0
    perms_added_total = 0
    staff_enabled_count = 0

    for m in queryset.select_related("organization", "user"):
        res = ensure_owner_assigned(organization=m.organization, membership_id=m.id)
        changed += res.assigned_membership_roles

        staff_enabled, perms_added = ensure_staff_and_admin_perms_for_models(
            user=m.user, app_labels=TENANT_ADMIN_APP_LABELS
        )
        perms_added_total += perms_added
        if staff_enabled:
            staff_enabled_count += 1

    messages.success(
        request,
        f"Owner role ensured. New owner assignments: {changed}. "
        f"Staff enabled for {staff_enabled_count} user(s). "
        f"Django perms added: {perms_added_total}.",
    )


class MembershipRoleInline(admin.TabularInline):
    """
    Inline role assignments on Membership.
    Organization is forced from the parent Membership/request.organization.
    """

    model = MembershipRole
    extra = 0
    autocomplete_fields = ("role",)
    fields = ("role",)
    # keep tenant invariants tight
    can_delete = True


@admin.register(Membership, site=admin_site)
class MembershipAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
    """
    Tenant-mode Membership screen.

    - Shows Memberships for the active org (via TenantAdminMixin).
    - Allows role assignment via inline.
    - RBAC-gated: requires rbac.assign to view/add/change/delete in tenant admin.
      (Platform superuser bypasses via RBACPermissionAdminMixin behavior.)
    """

    required_capabilities = {
        "view": "rbac.assign",
        "add": "rbac.assign",
        "change": "rbac.assign",
        "delete": "rbac.assign",
    }

    list_display = ("user", "organization", "status", "last_login_at", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("user__email", "organization__name", "organization__slug")
    actions = [make_org_owner]
    inlines = [MembershipRoleInline]

    @transaction.atomic
    def save_formset(self, request, form, formset, change):
        """
        Force tenant invariants for inline MembershipRole rows.

        - membership FK must be this Membership
        - organization must match request.organization (tenant mode) / membership.organization
        """
        parent_membership: Membership = form.instance
        org = getattr(request, "organization", None) or parent_membership.organization

        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, MembershipRole):
                obj.membership = parent_membership
                obj.organization = org
            obj.save()

        formset.save_m2m()

        # handle deletions
        for obj in formset.deleted_objects:
            obj.delete()
