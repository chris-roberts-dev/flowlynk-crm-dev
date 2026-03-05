import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.platform.accounts.models import Membership
from apps.platform.organizations.models import Organization
from apps.platform.rbac.bootstrap import ensure_owner_assigned
from apps.platform.rbac.defaults import ROLE_TEMPLATES
from apps.platform.rbac.models import Role, RoleCapability


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1"],
)


@pytest.mark.django_db
@override_settings(**COMMON)
def test_apply_default_roles_button_seeds_roles_for_active_org(client):
    User = get_user_model()

    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )
    user = User.objects.create_user(
        email="admin@acme.com", password="pass12345", is_staff=True, is_active=True
    )
    membership = Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    # Give this membership the owner role so it has rbac.manage (and can access RoleAdmin)
    ensure_owner_assigned(organization=org, membership_id=membership.id)

    client.force_login(user)

    session = client.session
    session["active_org_id"] = org.id
    session["active_org_slug"] = org.slug
    session.save()

    resp = client.get(
        "/admin/rbac/role/apply-templates/", HTTP_HOST="localhost", follow=False
    )
    assert resp.status_code == 302  # redirect back to changelist

    # All templates should exist for this org
    for code in ROLE_TEMPLATES.keys():
        assert (
            Role.objects.unscoped().filter(organization_id=org.id, code=code).exists()
        )

    # And at least one RoleCapability exists for the org
    assert RoleCapability.objects.unscoped().filter(organization_id=org.id).exists()


@pytest.mark.django_db
@override_settings(**COMMON)
def test_apply_default_roles_is_idempotent(client):
    User = get_user_model()

    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )
    user = User.objects.create_user(
        email="admin@acme.com", password="pass12345", is_staff=True, is_active=True
    )
    membership = Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )
    ensure_owner_assigned(organization=org, membership_id=membership.id)

    client.force_login(user)
    session = client.session
    session["active_org_id"] = org.id
    session["active_org_slug"] = org.slug
    session.save()

    client.get("/admin/rbac/role/apply-templates/", HTTP_HOST="localhost")
    client.get("/admin/rbac/role/apply-templates/", HTTP_HOST="localhost")

    assert Role.objects.unscoped().filter(organization_id=org.id).count() == len(
        ROLE_TEMPLATES
    )
