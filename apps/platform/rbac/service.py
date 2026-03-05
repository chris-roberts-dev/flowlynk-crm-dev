from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied

from apps.platform.accounts.models import Membership
from apps.platform.organizations.models import Organization

from .models import MembershipCapabilityGrant, MembershipRole, RoleCapability


@dataclass(frozen=True)
class AuthzResult:
    allowed: bool
    reason: str | None = None


def has_capability(
    *, user, organization: Organization, capability_code: str
) -> AuthzResult:
    """
    Server-side enforcement.
    - Superuser: allowed (platform privilege)
    - Otherwise: must have active membership; then role capabilities + membership grants apply.
    Deny-by-default.
    """
    if user.is_authenticated and user.is_superuser:
        return AuthzResult(True, "platform_superuser")

    if not user.is_authenticated:
        return AuthzResult(False, "not_authenticated")

    membership = Membership.objects.filter(
        user_id=user.id,
        organization_id=organization.id,
        status=Membership.Status.ACTIVE,
    ).first()

    if not membership:
        return AuthzResult(False, "no_active_membership")

    # Explicit grants/denials first (highest priority)
    grant = (
        MembershipCapabilityGrant.objects.unscoped()
        .filter(
            organization_id=organization.id,
            membership_id=membership.id,
            capability__code=capability_code,
        )
        .select_related("capability")
        .first()
    )
    if grant:
        return AuthzResult(
            grant.allowed,
            "membership_grant_allow" if grant.allowed else "membership_grant_deny",
        )

    # Role-based
    role_ids = (
        MembershipRole.objects.unscoped()
        .filter(
            organization_id=organization.id,
            membership_id=membership.id,
        )
        .values_list("role_id", flat=True)
    )

    if not role_ids:
        return AuthzResult(False, "no_roles")

    has = (
        RoleCapability.objects.unscoped()
        .filter(
            organization_id=organization.id,
            role_id__in=list(role_ids),
            capability__code=capability_code,
        )
        .exists()
    )

    return AuthzResult(bool(has), "role_capability" if has else "missing_capability")


def require_capability(
    *, user, organization: Organization, capability_code: str
) -> None:
    res = has_capability(
        user=user, organization=organization, capability_code=capability_code
    )
    if not res.allowed:
        raise PermissionDenied(f"Missing capability: {capability_code} ({res.reason})")
