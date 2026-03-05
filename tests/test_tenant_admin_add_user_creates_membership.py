import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from apps.platform.accounts.models import Membership
from apps.platform.organizations.models import Organization


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1"],
)


@pytest.mark.django_db
@override_settings(**COMMON)
def test_tenant_admin_add_user_creates_membership(client):
    User = get_user_model()

    org1 = Organization.objects.create(
        name="Org 1", slug="org1", status=Organization.Status.ACTIVE
    )
    org2 = Organization.objects.create(
        name="Org 2", slug="org2", status=Organization.Status.ACTIVE
    )

    tenant_admin = User.objects.create_user(
        email="ta@example.com",
        password="pass12345",
        is_staff=True,
        is_active=True,
    )
    Membership.objects.create(
        user=tenant_admin, organization=org1, status=Membership.Status.ACTIVE
    )

    # Minimal Django admin perms to access /admin/accounts/user/add/
    ct = ContentType.objects.get_for_model(User)
    perms = Permission.objects.filter(
        content_type=ct,
        codename__in=["add_user", "view_user", "change_user"],
    )
    tenant_admin.user_permissions.add(*perms)

    client.force_login(tenant_admin)

    # Resolve tenant via session fallback (path-based tenancy uses active_org_id)
    session = client.session
    session["active_org_id"] = org1.id
    session["active_org_slug"] = org1.slug
    session.save()

    resp = client.post(
        "/admin/accounts/user/add/",
        data={
            "email": "newguy@example.com",
            "full_name": "New Guy",
            "is_active": "on",
            "password1": "Passw0rd!Passw0rd!",
            "password2": "Passw0rd!Passw0rd!",
        },
        HTTP_HOST="localhost",
        follow=False,
    )

    # Django admin redirects to the change page after successful add
    assert resp.status_code in (302, 303)

    new_user = User.objects.get(email="newguy@example.com")
    assert new_user.is_staff is True
    assert new_user.is_superuser is False

    assert Membership.objects.filter(
        user=new_user, organization=org1, status=Membership.Status.ACTIVE
    ).exists()
    assert not Membership.objects.filter(user=new_user, organization=org2).exists()
