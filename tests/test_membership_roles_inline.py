import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.platform.organizations.models import Organization
from apps.platform.accounts.models import Membership
from apps.platform.rbac.models import Capability, Role, RoleCapability, MembershipRole

COMMON = {
    "ROOT_DOMAIN": "localhost",
}


@pytest.mark.django_db
@override_settings(**COMMON)
def test_membership_change_allows_role_assignment_inline_scoped_to_org(client):
    User = get_user_model()

    org = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )

    # Create capability required by MembershipAdmin
    cap = Capability.objects.create(
        code="rbac.assign", description="Assign roles", is_active=True
    )

    # Create a role in org and bind capability
    role = Role.objects.create(
        organization=org,
        code="owner",
        name="Owner",
        description="Owner role",
        is_system=True,
        is_active=True,
    )
    RoleCapability.objects.create(organization=org, role=role, capability=cap)

    # Tenant admin user
    tenant_admin = User.objects.create_user(
        email="ta@example.com", password="pass12345", is_staff=True, is_active=True
    )
    admin_membership = Membership.objects.create(
        user=tenant_admin, organization=org, status=Membership.Status.ACTIVE
    )
    # Grant tenant admin the capability via role
    MembershipRole.objects.create(
        organization=org, membership=admin_membership, role=role
    )

    # Target user to assign roles to
    u1 = User.objects.create_user(
        email="u1@example.com", password="pass12345", is_active=True
    )
    m1 = Membership.objects.create(
        user=u1, organization=org, status=Membership.Status.ACTIVE
    )

    client.force_login(tenant_admin)

    # Resolve tenant via session (path-based tenancy)
    session = client.session
    session["active_org_id"] = org.id
    session["active_org_slug"] = org.slug
    session.save()

    # Load change page (sanity)
    resp = client.get(
        f"/admin/accounts/membership/{m1.id}/change/", HTTP_HOST="localhost"
    )
    assert resp.status_code == 200

    # Post inline role assignment on MembershipRoleInline
    post_data = {
        "user": str(u1.id),
        "status": Membership.Status.ACTIVE,
        "last_login_at_0": "",
        "last_login_at_1": "",
        # inline formset prefix uses related_name "membership_roles"
        "membership_roles-TOTAL_FORMS": "1",
        "membership_roles-INITIAL_FORMS": "0",
        "membership_roles-MIN_NUM_FORMS": "0",
        "membership_roles-MAX_NUM_FORMS": "1000",
        "membership_roles-0-id": "",
        "membership_roles-0-role": str(role.id),
        "_save": "Save",
    }

    resp = client.post(
        f"/admin/accounts/membership/{m1.id}/change/",
        data=post_data,
        HTTP_HOST="localhost",
        follow=False,
    )
    assert resp.status_code == 302

    # Ensure role assignment created and is org-scoped
    assert MembershipRole.objects.filter(
        organization=org, membership=m1, role=role
    ).exists()
