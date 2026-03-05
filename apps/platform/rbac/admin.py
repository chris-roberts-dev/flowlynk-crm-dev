from __future__ import annotations

from django.contrib import admin

from apps.common.admin.rbac import RBACPermissionAdminMixin
from apps.common.admin.tenant import TenantAdminMixin
from webcrm.admin import admin_site

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
    required_capabilities = {
        "view": "rbac.manage",
        "add": "rbac.manage",
        "change": "rbac.manage",
        "delete": "rbac.manage",
    }

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
