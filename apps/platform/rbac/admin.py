from __future__ import annotations

from django.contrib import admin, messages
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import path

from apps.common.admin.rbac import RBACPermissionAdminMixin
from apps.common.admin.tenant import TenantAdminMixin
from webcrm.admin import admin_site

from .bootstrap import ensure_role_templates_for_org
from .defaults import ROLE_TEMPLATES
from .models import (
    Capability,
    MembershipCapabilityGrant,
    MembershipRole,
    Role,
    RoleCapability,
)


@admin.register(Capability, site=admin_site)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "description")
    ordering = ("code",)

    # Capabilities are global; platform superusers only.
    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_authenticated and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.is_superuser


class RoleCapabilityInline(admin.TabularInline):
    model = RoleCapability
    extra = 0
    autocomplete_fields = ("capability",)


@admin.register(Role, site=admin_site)
class RoleAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
    """
    Tenant admin UX:
    - In tenant mode, provide a button to seed/update org roles from platform templates.
    - Idempotent: safe to click multiple times.
    """

    required_capabilities = {
        "view": "rbac.manage",
        "add": "rbac.manage",
        "change": "rbac.manage",
        "delete": "rbac.manage",
    }

    change_list_template = "admin/rbac/role/change_list.html"

    list_display = (
        "name",
        "code",
        "organization",
        "is_system",
        "is_active",
        "created_at",
    )
    list_filter = ("organization", "is_system", "is_active")
    search_fields = ("name", "code")
    ordering = ("code",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [RoleCapabilityInline]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "apply-templates/",
                self.admin_site.admin_view(self.apply_templates_view),
                name="rbac_role_apply_templates",
            ),
        ]
        return custom + urls

    def apply_templates_view(self, request: HttpRequest):
        """
        Seed/update all ROLE_TEMPLATES for the active org.
        Tenant required (handled by TenantAdminMixin); RBAC enforced (RBACPermissionAdminMixin).
        """
        org = getattr(request, "organization", None)
        if org is None:
            messages.error(request, "No active tenant organization.")
            return redirect("admin:rbac_role_changelist")

        res = ensure_role_templates_for_org(
            organization=org, template_codes=list(ROLE_TEMPLATES.keys())
        )
        messages.success(
            request,
            "Default roles applied. "
            f"created_roles={res.created_roles}, updated_roles={res.updated_roles}, "
            f"role_capabilities={res.created_role_capabilities}",
        )
        return redirect("admin:rbac_role_changelist")


@admin.register(MembershipRole, site=admin_site)
class MembershipRoleAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
    required_capabilities = {
        "view": "rbac.assign",
        "add": "rbac.assign",
        "change": "rbac.assign",
        "delete": "rbac.assign",
    }

    list_display = ("membership", "role", "organization", "created_at")
    list_filter = ("organization",)
    search_fields = ("membership__user__email", "role__code", "role__name")
    autocomplete_fields = ("membership", "role")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MembershipCapabilityGrant, site=admin_site)
class MembershipCapabilityGrantAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
    required_capabilities = {
        "view": "rbac.assign",
        "add": "rbac.assign",
        "change": "rbac.assign",
        "delete": "rbac.assign",
    }

    list_display = ("membership", "capability", "allowed", "organization", "created_at")
    list_filter = ("organization", "allowed")
    search_fields = ("membership__user__email", "capability__code")
    autocomplete_fields = ("membership", "capability")
    readonly_fields = ("created_at", "updated_at")
