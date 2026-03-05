from django.contrib import admin

from apps.common.admin.rbac import RBACPermissionAdminMixin
from apps.common.admin.tenant import TenantAdminMixin
from webcrm.admin import admin_site

from .models import Location


@admin.register(Location, site=admin_site)
class LocationAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
    required_capabilities = {
        "view": "locations.manage",
        "add": "locations.manage",
        "change": "locations.manage",
        "delete": "locations.manage",
    }

    list_display = ("name", "code", "organization", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "code", "organization__name", "organization__slug")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
