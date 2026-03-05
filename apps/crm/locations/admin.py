from __future__ import annotations

from django.contrib import admin

from apps.common.admin.rbac import RBACPermissionAdminMixin
from apps.common.admin.tenant import TenantAdminMixin
from webcrm.admin import admin_site

from .models import Location, Market, Region


class LocationInline(admin.TabularInline):
    model = Location
    extra = 0
    fields = ("name", "code", "is_active")
    show_change_link = True


class MarketInline(admin.TabularInline):
    model = Market
    extra = 0
    fields = ("name", "code", "is_active")
    show_change_link = True


@admin.register(Region, site=admin_site)
class RegionAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
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
    inlines = [MarketInline]


@admin.register(Market, site=admin_site)
class MarketAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
    required_capabilities = {
        "view": "locations.manage",
        "add": "locations.manage",
        "change": "locations.manage",
        "delete": "locations.manage",
    }

    list_display = ("name", "code", "region", "organization", "is_active", "created_at")
    list_filter = ("organization", "region", "is_active")
    search_fields = (
        "name",
        "code",
        "region__name",
        "organization__name",
        "organization__slug",
    )
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("region",)
    inlines = [LocationInline]


@admin.register(Location, site=admin_site)
class LocationAdmin(RBACPermissionAdminMixin, TenantAdminMixin):
    required_capabilities = {
        "view": "locations.manage",
        "add": "locations.manage",
        "change": "locations.manage",
        "delete": "locations.manage",
    }

    list_display = ("name", "code", "market", "organization", "is_active", "created_at")
    list_filter = ("organization", "market", "is_active")
    search_fields = (
        "name",
        "code",
        "market__name",
        "market__region__name",
        "organization__name",
        "organization__slug",
    )
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("market",)
