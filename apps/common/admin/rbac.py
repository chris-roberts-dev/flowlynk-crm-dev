from __future__ import annotations

from typing import Optional

from django.http import HttpRequest

from apps.platform.rbac.service import has_capability


class RBACPermissionAdminMixin:
    """
    Admin permission enforcement via RBAC capability codes.

    This is *in addition* to Django admin's built-in checks:
      - user.is_staff
      - Django model permissions

    If required capability is missing -> deny (return False) -> admin returns 403.
    """

    # Override per ModelAdmin, e.g.:
    # required_capabilities = {"view": "locations.manage", "add": "...", "change": "...", "delete": "..."}
    required_capabilities: dict[str, str] = {}

    def _cap_code_for(self, action: str) -> Optional[str]:
        return self.required_capabilities.get(action)

    def _rbac_allows(self, request: HttpRequest, action: str) -> bool:
        code = self._cap_code_for(action)
        if not code:
            return True  # no RBAC requirement for this action
        org = getattr(request, "organization", None)

        # Platform superuser is allowed globally (service handles it).
        if org is None:
            # tenant mode required for tenant-scoped access; platform mode should only be for superusers.
            return bool(request.user.is_authenticated and request.user.is_superuser)

        return has_capability(
            user=request.user, organization=org, capability_code=code
        ).allowed

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        base = super().has_view_permission(request, obj)  # type: ignore[misc]
        return bool(base and self._rbac_allows(request, "view"))

    def has_add_permission(self, request: HttpRequest) -> bool:
        base = super().has_add_permission(request)  # type: ignore[misc]
        return bool(base and self._rbac_allows(request, "add"))

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        base = super().has_change_permission(request, obj)  # type: ignore[misc]
        return bool(base and self._rbac_allows(request, "change"))

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        base = super().has_delete_permission(request, obj)  # type: ignore[misc]
        return bool(base and self._rbac_allows(request, "delete"))
