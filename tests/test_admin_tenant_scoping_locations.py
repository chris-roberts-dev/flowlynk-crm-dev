import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import override_settings

from apps.crm.locations.models import Location
from apps.platform.accounts.models import Membership
from apps.platform.organizations.models import Organization
from apps.platform.rbac.models import Capability, MembershipRole, Role, RoleCapability


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1", ".localhost"],
)


def grant_location_perms(
    user, *, add: bool = False, change: bool = False, view: bool = False
):
    codenames = []
    if view:
        codenames.append("view_location")
    if add:
        codenames.append("add_location")
    if change:
        codenames.append("change_location")

    perms = Permission.objects.filter(
        content_type__app_label="locations", codename__in=codenames
    )
    user.user_permissions.add(*perms)
    user.save()


def grant_rbac_locations_manage(*, org: Organization, membership: Membership):
    """
    Our LocationAdmin now requires RBAC capability 'locations.manage'.
    We attach a temp role with that capability to the membership.
    """
    call_command("seed_capabilities")
    cap = Capability.objects.get(code="locations.manage")

    role = Role.objects.unscoped().create(
        organization=org,
        code="tmp_locations_manage",
        name="Temp Locations Manage",
        description="Test role for locations.manage",
        is_system=False,
        is_active=True,
    )
    RoleCapability.objects.unscoped().create(
        organization=org, role=role, capability=cap
    )
    MembershipRole.objects.unscoped().create(
        organization=org, membership=membership, role=role
    )


@pytest.mark.django_db
@override_settings(**COMMON)
def test_admin_changelist_is_tenant_filtered(client):
    User = get_user_model()
    user = User.objects.create_user(
        email="staff@example.com", password="pass12345", is_staff=True
    )
    user.is_active = True
    user.save(update_fields=["is_active"])

    # Django admin needs view permission
    grant_location_perms(user, view=True)

    org1 = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    org2 = Organization.objects.create(
        name="Org 2", slug="org2", status=Organization.Status.ACTIVE
    )

    membership = Membership.objects.create(
        user=user, organization=org1, status=Membership.Status.ACTIVE
    )

    # RBAC requirement for LocationAdmin
    grant_rbac_locations_manage(org=org1, membership=membership)

    # Create data in both orgs (unscoped to bypass strict ORM)
    Location.objects.unscoped().create(organization=org1, code="A", name="Loc A")
    Location.objects.unscoped().create(organization=org2, code="B", name="Loc B")

    client.force_login(user)

    resp = client.get("/admin/locations/location/", HTTP_HOST="org1.localhost")
    assert resp.status_code == 200
    content = resp.content.decode("utf-8")
    assert "Loc A" in content
    assert "Loc B" not in content


@pytest.mark.django_db
@override_settings(**COMMON)
def test_admin_save_forces_organization_and_sets_audit_fields(client):
    User = get_user_model()
    user = User.objects.create_user(
        email="staff2@example.com", password="pass12345", is_staff=True
    )
    user.is_active = True
    user.save(update_fields=["is_active"])

    # Django admin needs add permission to create via admin
    grant_location_perms(user, add=True, view=True)

    org1 = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    membership = Membership.objects.create(
        user=user, organization=org1, status=Membership.Status.ACTIVE
    )

    # RBAC requirement for LocationAdmin
    grant_rbac_locations_manage(org=org1, membership=membership)

    client.force_login(user)

    resp = client.post(
        "/admin/locations/location/add/",
        data={"code": "X", "name": "Created Via Admin", "is_active": "on"},
        HTTP_HOST="org1.localhost",
        follow=False,
    )
    # Django admin redirects back to changelist on success
    assert resp.status_code == 302

    loc = Location.objects.unscoped().get(code="X")
    assert loc.organization_id == org1.id
    assert loc.created_by_id == user.id
    assert loc.updated_by_id == user.id
