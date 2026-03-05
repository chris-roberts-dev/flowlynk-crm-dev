import json

import pytest
from django.core.management import call_command

from apps.platform.organizations.models import Organization
from apps.platform.rbac.defaults import CAPABILITIES
from apps.platform.rbac.models import Capability, Role, RoleCapability


@pytest.mark.django_db
def test_seed_capabilities_is_idempotent():
    assert Capability.objects.count() == 0
    call_command("seed_capabilities")
    assert Capability.objects.count() == len(CAPABILITIES)
    call_command("seed_capabilities")
    assert Capability.objects.count() == len(CAPABILITIES)


@pytest.mark.django_db
def test_import_roles_dry_run_does_not_write(tmp_path):
    call_command("seed_capabilities")
    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )

    payload = {
        "roles": [
            {
                "code": "manager",
                "name": "Manager",
                "description": "Ops manager",
                "is_system": True,
                "is_active": True,
                "capabilities": ["locations.manage", "leads.view"],
            }
        ]
    }
    f = tmp_path / "roles.json"
    f.write_text(json.dumps(payload), encoding="utf-8")

    call_command("import_roles", org="acme", file=str(f), dry_run=True)

    assert Role.objects.unscoped().filter(organization_id=org.id).count() == 0
    assert RoleCapability.objects.unscoped().filter(organization_id=org.id).count() == 0


@pytest.mark.django_db
def test_import_roles_upserts_and_sets_role_capabilities(tmp_path):
    call_command("seed_capabilities")
    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )

    payload = {
        "roles": [
            {
                "code": "manager",
                "name": "Manager",
                "description": "Ops manager",
                "is_system": True,
                "is_active": True,
                "capabilities": ["locations.manage", "leads.view"],
            },
            {
                "code": "staff",
                "name": "Staff",
                "description": "",
                "is_system": False,
                "is_active": True,
                "capabilities": ["leads.view"],
            },
        ]
    }
    f = tmp_path / "roles.json"
    f.write_text(json.dumps(payload), encoding="utf-8")

    call_command("import_roles", org="acme", file=str(f))

    manager = Role.objects.unscoped().get(organization_id=org.id, code="manager")
    caps = set(
        RoleCapability.objects.unscoped()
        .filter(organization_id=org.id, role_id=manager.id)
        .select_related("capability")
        .values_list("capability__code", flat=True)
    )
    assert caps == {"locations.manage", "leads.view"}

    # Upsert update + replace mappings
    payload2 = {
        "roles": [
            {
                "code": "manager",
                "name": "Manager v2",
                "description": "Updated",
                "is_system": True,
                "is_active": True,
                "capabilities": ["quotes.view"],
            }
        ]
    }
    f.write_text(json.dumps(payload2), encoding="utf-8")
    call_command("import_roles", org="acme", file=str(f))

    manager.refresh_from_db()
    assert manager.name == "Manager v2"
    caps2 = set(
        RoleCapability.objects.unscoped()
        .filter(organization_id=org.id, role_id=manager.id)
        .select_related("capability")
        .values_list("capability__code", flat=True)
    )
    assert caps2 == {"quotes.view"}
