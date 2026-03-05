import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings

from apps.platform.accounts.models import Membership
from apps.platform.organizations.models import Organization


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1"],
)


def grant_user_admin_view_perms(user):
    """
    Minimal perms required to access /admin/accounts/user/ changelist.
    """
    perm = Permission.objects.get(codename="view_user")
    user.user_permissions.add(perm)
    user.save()


@pytest.mark.django_db
@override_settings(**COMMON)
def test_tenant_admin_user_changelist_is_scoped_by_membership(client):
    User = get_user_model()

    org1 = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    org2 = Organization.objects.create(
        name="Org 2", slug="org2", status=Organization.Status.ACTIVE
    )

    # Tenant admin user (staff) belongs only to org1
    tenant_admin = User.objects.create_user(
        email="ta@example.com",
        password="pass12345",
        is_staff=True,
        is_active=True,
    )
    grant_user_admin_view_perms(tenant_admin)

    Membership.objects.create(
        user=tenant_admin, organization=org1, status=Membership.Status.ACTIVE
    )

    u1 = User.objects.create_user(
        email="u1@example.com", password="pass12345", is_active=True
    )
    u2 = User.objects.create_user(
        email="u2@example.com", password="pass12345", is_active=True
    )

    Membership.objects.create(
        user=u1, organization=org1, status=Membership.Status.ACTIVE
    )
    Membership.objects.create(
        user=u2, organization=org2, status=Membership.Status.ACTIVE
    )

    client.force_login(tenant_admin)

    # Resolve tenant via session (path-based tenancy)
    session = client.session
    session["active_org_id"] = org1.id
    session["active_org_slug"] = org1.slug
    session.save()

    resp = client.get("/admin/accounts/user/", HTTP_HOST="localhost")
    assert resp.status_code == 200

    content = resp.content
    assert b"ta@example.com" in content
    assert b"u1@example.com" in content
    assert b"u2@example.com" not in content


@pytest.mark.django_db
@override_settings(**COMMON)
def test_platform_superuser_sees_all_users(client):
    User = get_user_model()

    org1 = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    org2 = Organization.objects.create(
        name="Org 2", slug="org2", status=Organization.Status.ACTIVE
    )

    su = User.objects.create_superuser(email="su@example.com", password="pass12345")

    u1 = User.objects.create_user(
        email="u1@example.com", password="pass12345", is_active=True
    )
    u2 = User.objects.create_user(
        email="u2@example.com", password="pass12345", is_active=True
    )

    Membership.objects.create(
        user=u1, organization=org1, status=Membership.Status.ACTIVE
    )
    Membership.objects.create(
        user=u2, organization=org2, status=Membership.Status.ACTIVE
    )

    client.force_login(su)

    resp = client.get("/admin/accounts/user/", HTTP_HOST="localhost")
    assert resp.status_code == 200

    content = resp.content
    assert b"su@example.com" in content
    assert b"u1@example.com" in content
    assert b"u2@example.com" in content
