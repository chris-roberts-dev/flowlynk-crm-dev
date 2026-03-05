import io

import pytest
from django.core.management import call_command

from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization
from apps.platform.rbac.models import MembershipRole, Role


@pytest.mark.django_db
def test_bootstrap_org_admin_grants_staff_and_permissions_and_owner_role():
    out = io.StringIO()
    call_command(
        "bootstrap_org_admin",
        org_slug="acme",
        org_name="Acme Co",
        email="admin@acme.com",
        password="pass12345",
        stdout=out,
    )

    output = out.getvalue()
    assert "/t/acme/admin/" in output

    org = Organization.objects.get(slug="acme")
    user = User.objects.get(email="admin@acme.com")
    membership = Membership.objects.get(user=user, organization=org)

    assert user.is_active is True
    assert user.is_staff is True
    assert membership.status == Membership.Status.ACTIVE

    owner_role = Role.objects.unscoped().get(organization_id=org.id, code="owner")
    assert (
        MembershipRole.objects.unscoped()
        .filter(
            organization_id=org.id, membership_id=membership.id, role_id=owner_role.id
        )
        .exists()
    )

    # Ensure admin has at least baseline permissions so apps appear.
    assert user.user_permissions.filter(
        content_type__app_label="locations", codename="view_location"
    ).exists()


@pytest.mark.django_db
def test_bootstrap_org_admin_is_idempotent():
    call_command(
        "bootstrap_org_admin",
        org_slug="acme",
        org_name="Acme Co",
        email="admin@acme.com",
        password="pass12345",
    )
    call_command(
        "bootstrap_org_admin",
        org_slug="acme",
        org_name="Acme Co",
        email="admin@acme.com",
        password="pass12345",
    )

    org = Organization.objects.get(slug="acme")
    user = User.objects.get(email="admin@acme.com")

    assert Organization.objects.filter(slug="acme").count() == 1
    assert User.objects.filter(email="admin@acme.com").count() == 1
    assert Membership.objects.filter(user=user, organization=org).count() == 1

    owner_role = Role.objects.unscoped().get(organization_id=org.id, code="owner")
    assert (
        MembershipRole.objects.unscoped()
        .filter(organization_id=org.id, membership__user=user, role_id=owner_role.id)
        .count()
        == 1
    )


@pytest.mark.django_db
def test_bootstrap_org_admin_dry_run_makes_no_changes():
    out = io.StringIO()
    call_command(
        "bootstrap_org_admin",
        org_slug="dryco",
        org_name="Dry Co",
        email="dry@dryco.com",
        password="pass12345",
        dry_run=True,
        stdout=out,
    )

    output = out.getvalue()
    assert "Dry-run" in output
    assert "/t/dryco/admin/" in output

    assert Organization.objects.filter(slug="dryco").count() == 0
    assert User.objects.filter(email="dry@dryco.com").count() == 0
    assert Membership.objects.count() == 0
