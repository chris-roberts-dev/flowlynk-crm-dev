from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.platform.organizations.models import Organization

from .defaults import CAPABILITIES, ROLE_TEMPLATES
from .models import Capability, MembershipRole, Role, RoleCapability


@dataclass(frozen=True)
class BootstrapResult:
    created_capabilities: int = 0
    created_roles: int = 0
    updated_roles: int = 0
    created_role_capabilities: int = 0
    assigned_membership_roles: int = 0
    granted_django_permissions: int = 0
    staff_enabled: bool = False


def ensure_capabilities_seeded() -> int:
    """
    Idempotently ensure global Capability rows exist for CAPABILITIES defaults.
    Returns number created.
    """
    existing = set(Capability.objects.values_list("code", flat=True))
    to_create = []
    for code, desc in CAPABILITIES.items():
        if code not in existing:
            to_create.append(Capability(code=code, description=desc, is_active=True))
    if to_create:
        Capability.objects.bulk_create(to_create, batch_size=200)
    return len(to_create)


@transaction.atomic
def ensure_role_template_for_org(
    *, organization: Organization, template_code: str
) -> BootstrapResult:
    """
    Ensure a role defined in ROLE_TEMPLATES exists for the org and has exactly
    the template's capabilities (replace mapping deterministically).
    """
    if template_code not in ROLE_TEMPLATES:
        raise ValueError(f"Unknown role template: {template_code}")

    created_caps = ensure_capabilities_seeded()

    tmpl = ROLE_TEMPLATES[template_code]
    cap_codes: list[str] = list(tmpl.get("capabilities", []))

    cap_map = {c.code: c for c in Capability.objects.filter(code__in=cap_codes)}
    missing = sorted(set(cap_codes) - set(cap_map.keys()))
    if missing:
        raise ValueError(f"Missing capabilities in DB (seed first?): {missing}")

    role, created = Role.objects.unscoped().update_or_create(
        organization_id=organization.id,
        code=template_code,
        defaults={
            "name": tmpl["name"],
            "description": tmpl.get("description", ""),
            "is_system": bool(tmpl.get("is_system", True)),
            "is_active": bool(tmpl.get("is_active", True)),
        },
    )

    # Replace mappings safely/deterministically
    RoleCapability.objects.unscoped().filter(
        organization_id=organization.id, role_id=role.id
    ).delete()
    rows = [
        RoleCapability(
            organization_id=organization.id,
            role_id=role.id,
            capability_id=cap_map[code].id,
        )
        for code in set(cap_codes)
    ]
    if rows:
        RoleCapability.objects.unscoped().bulk_create(rows, batch_size=200)

    return BootstrapResult(
        created_capabilities=created_caps,
        created_roles=1 if created else 0,
        updated_roles=0 if created else 1,
        created_role_capabilities=len(rows),
    )


@transaction.atomic
def ensure_role_templates_for_org(
    *, organization: Organization, template_codes: list[str] | None = None
) -> BootstrapResult:
    """
    Ensure multiple ROLE_TEMPLATES exist for the org (idempotent).
    If template_codes is None, applies all templates.
    """
    codes = template_codes or list(ROLE_TEMPLATES.keys())

    created_caps_total = 0
    created_roles_total = 0
    updated_roles_total = 0
    created_role_caps_total = 0

    # Seed once up-front for speed (still safe to call again inside template creation)
    created_caps_total += ensure_capabilities_seeded()

    for code in codes:
        res = ensure_role_template_for_org(
            organization=organization, template_code=code
        )
        created_caps_total += res.created_capabilities
        created_roles_total += res.created_roles
        updated_roles_total += res.updated_roles
        created_role_caps_total += res.created_role_capabilities

    return BootstrapResult(
        created_capabilities=created_caps_total,
        created_roles=created_roles_total,
        updated_roles=updated_roles_total,
        created_role_capabilities=created_role_caps_total,
    )


@transaction.atomic
def assign_role_to_membership(
    *, organization: Organization, membership_id: int, role_code: str
) -> int:
    """
    Idempotently assign a role to a membership.
    Returns 1 if created, 0 if already existed.
    """
    role = (
        Role.objects.unscoped()
        .filter(organization_id=organization.id, code=role_code)
        .first()
    )
    if not role:
        raise ValueError(f"Role not found for org={organization.slug}: {role_code}")

    _, created = MembershipRole.objects.unscoped().get_or_create(
        organization_id=organization.id,
        membership_id=membership_id,
        role_id=role.id,
    )
    return 1 if created else 0


@transaction.atomic
def ensure_staff_and_admin_perms_for_models(
    *, user, models: list[type]
) -> tuple[bool, int]:
    """
    Ensure user can see apps/models in Django Admin:
    - Sets is_staff=True if needed
    - Grants ALL Django permissions for the provided model list (idempotent)

    This avoids relying on app_label strings (which may not match ContentType labels).
    """
    staff_enabled = False
    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        staff_enabled = True

    cts = [ContentType.objects.get_for_model(m) for m in models]
    perms_qs = Permission.objects.filter(content_type__in=cts)

    before = set(user.user_permissions.values_list("id", flat=True))
    to_add = [p for p in perms_qs if p.id not in before]
    if to_add:
        user.user_permissions.add(*to_add)

    return staff_enabled, len(to_add)


@transaction.atomic
def ensure_owner_assigned(
    *, organization: Organization, membership_id: int
) -> BootstrapResult:
    """
    Ensure the org has an 'owner' role template and the membership has that role.
    (RBAC only; does not touch Django admin perms.)
    """
    res = ensure_role_template_for_org(organization=organization, template_code="owner")
    assigned = assign_role_to_membership(
        organization=organization, membership_id=membership_id, role_code="owner"
    )
    return BootstrapResult(
        created_capabilities=res.created_capabilities,
        created_roles=res.created_roles,
        updated_roles=res.updated_roles,
        created_role_capabilities=res.created_role_capabilities,
        assigned_membership_roles=assigned,
    )
