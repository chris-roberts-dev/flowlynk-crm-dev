from django.contrib import admin

from webcrm.admin import admin_site

from .models import Organization


@admin.register(Organization, site=admin_site)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("status",)
    ordering = ("slug",)
    readonly_fields = ("created_at", "updated_at")
