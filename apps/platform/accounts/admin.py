from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth import get_user_model

from webcrm.admin import admin_site

from apps.platform.accounts.models import Membership
from apps.platform.rbac.bootstrap import (
    ensure_owner_assigned,
    ensure_staff_and_admin_perms_for_models,
)


User = get_user_model()

TENANT_ADMIN_APP_LABELS = ["locations", "rbac", "accounts"]


@admin.register(User, site=admin_site)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "is_staff", "is_superuser", "created_at")
    search_fields = ("email",)
    list_filter = ("is_active", "is_staff", "is_superuser")
    ordering = ("email",)


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


@admin.register(Membership, site=admin_site)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "status", "last_login_at", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("user__email", "organization__name", "organization__slug")
    actions = [make_org_owner]
