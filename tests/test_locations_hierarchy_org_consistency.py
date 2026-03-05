import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.contrib.auth import get_user_model

from apps.platform.organizations.models import Organization
from apps.platform.accounts.models import Membership
from apps.platform.rbac.models import Capability, Role, RoleCapability, MembershipRole

from apps.crm.locations.models import Region, Market, Location
from apps.crm.locations.service import create_region, create_market, create_location


COMMON = dict(
    ROOT_DOMAIN="localhost",
)


@pytest.mark.django_db
@override_settings(**COMMON)
def test_market_and_location_reject_cross_org_fk():
    org1 = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    org2 = Organization.objects.create(
        name="Org 2", slug="org2", status=Organization.Status.ACTIVE
    )

    r1 = Region.objects.create(organization=org1, code="R-TENN", name="Tennessee")
    r2 = Region.objects.create(organization=org2, code="R-MO", name="Missouri")

    # Market cannot point to Region in another org
    bad_market = Market(organization=org1, region=r2, code="M-MID-TN", name="Bad")
    with pytest.raises(ValidationError):
        bad_market.full_clean()

    good_market = Market.objects.create(
        organization=org1, region=r1, code="M-MID-TN", name="Middle TN"
    )

    # Location cannot point to Market in another org
    bad_loc = Location(organization=org2, market=good_market, code="L-1", name="Bad")
    with pytest.raises(ValidationError):
        bad_loc.full_clean()


@pytest.mark.django_db
@override_settings(**COMMON)
def test_locations_service_requires_locations_manage_capability():
    User = get_user_model()

    org = Organization.objects.create(
        name="Org", slug="org", status=Organization.Status.ACTIVE
    )
    user = User.objects.create_user(
        email="u@example.com", password="pass12345", is_active=True, is_staff=True
    )

    # Active membership but NO roles/capability
    Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    with pytest.raises(Exception):
        create_region(user=user, organization=org, code="R-TENN", name="Tennessee")

    # Now grant locations.manage capability through a role
    cap = Capability.objects.create(
        code="locations.manage", description="Manage locations", is_active=True
    )
    role = Role.objects.create(
        organization=org, code="owner", name="Owner", is_system=True, is_active=True
    )
    RoleCapability.objects.create(organization=org, role=role, capability=cap)

    mship = Membership.objects.get(user=user, organization=org)
    MembershipRole.objects.create(organization=org, membership=mship, role=role)

    region = create_region(user=user, organization=org, code="R-TENN", name="Tennessee")
    market = create_market(
        user=user, organization=org, region=region, code="M-MID-TN", name="Middle TN"
    )
    loc = create_location(
        user=user,
        organization=org,
        market=market,
        code="L-MID-TN-001",
        name="Cookeville",
    )

    # service_area default should be present
    assert loc.service_area == "radius"
    assert loc.market_id == market.id
