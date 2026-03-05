import pytest
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import override_settings

from apps.crm.locations.models import Location
from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization
from apps.platform.rbac.models import Capability, MembershipRole, Role, RoleCapability


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1", ".localhost"],
)


def grant_django_model_perms(
    user, app_label: str, model: str, perms: list[str]
) -> None:
    """
    perms: e.g. ["view", "add", "change", "delete"]
    """
    codenames = [f"{p}_{model}" for p in perms]
    qs = Permission.objects.filter(
        content_type__app_label=app_label, codename__in=codenames
    )
    user.user_permissions.add(*qs)
    user.save()


def attach_role_with_capability(
    org: Organization, membership: Membership, cap_code: str
) -> None:
    role = Role.objects.unscoped().create(
        organization=org,
        code="tmp",
        name="Temp",
        description="",
        is_system=False,
        is_active=True,
    )
    cap = Capability.objects.get(code=cap_code)
    RoleCapability.objects.unscoped().create(
        organization=org, role=role, capability=cap
    )
    MembershipRole.objects.unscoped().create(
        organization=org, membership=membership, role=role
    )


@pytest.mark.django_db
@override_settings(**COMMON)
def test_admin_denies_without_rbac_capability_even_with_django_perms(client):
    call_command("seed_capabilities")

    org = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    user = User.objects.create_user(
        email="staff@example.com", password="pass12345", is_staff=True
    )
    user.is_active = True
    user.save(update_fields=["is_active"])

    membership = Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    # Django perms granted (admin would normally allow)
    grant_django_model_perms(
        user, app_label="locations", model="location", perms=["view"]
    )

    client.force_login(user)

    # Should be denied because RBAC required capability is missing
    resp = client.get("/admin/locations/location/", HTTP_HOST="org1.localhost")
    assert resp.status_code == 403


@pytest.mark.django_db
@override_settings(**COMMON)
def test_admin_allows_with_rbac_capability_and_django_perms(client):
    call_command("seed_capabilities")

    org = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    user = User.objects.create_user(
        email="staff2@example.com", password="pass12345", is_staff=True
    )
    user.is_active = True
    user.save(update_fields=["is_active"])

    membership = Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    # Django perms granted
    grant_django_model_perms(
        user, app_label="locations", model="location", perms=["view"]
    )

    # RBAC capability via role
    attach_role_with_capability(org, membership, "locations.manage")

    # Seed a record to view
    Location.objects.unscoped().create(organization=org, code="A", name="Loc A")

    client.force_login(user)

    resp = client.get("/admin/locations/location/", HTTP_HOST="org1.localhost")
    assert resp.status_code == 200
    assert b"Loc A" in resp.content
