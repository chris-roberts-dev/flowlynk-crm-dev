import pytest

from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization
from apps.platform.rbac.models import MembershipRole, Role, RoleCapability
from apps.platform.rbac.service import has_capability
from django.core.management import call_command


@pytest.mark.django_db
def test_has_capability_via_role():
    call_command("seed_capabilities")

    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )
    user = User.objects.create_user(
        email="u@example.com", password="pass12345", is_active=True
    )
    membership = Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    role = Role.objects.unscoped().create(
        organization=org,
        code="staff",
        name="Staff",
        description="",
        is_system=False,
        is_active=True,
    )

    # Attach capability
    RoleCapability.objects.unscoped().create(
        organization=org,
        role=role,
        capability_id=1,  # we'll replace with lookup below
    )
    # safer: lookup capability id
    from apps.platform.rbac.models import Capability

    cap = Capability.objects.get(code="leads.view")
    RoleCapability.objects.unscoped().filter(role=role).update(capability=cap)

    MembershipRole.objects.unscoped().create(
        organization=org, membership=membership, role=role
    )

    res = has_capability(user=user, organization=org, capability_code="leads.view")
    assert res.allowed is True


@pytest.mark.django_db
def test_superuser_has_all_capabilities():
    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )
    su = User.objects.create_superuser(email="su@example.com", password="pass12345")
    res = has_capability(user=su, organization=org, capability_code="anything.at.all")
    assert res.allowed is True
