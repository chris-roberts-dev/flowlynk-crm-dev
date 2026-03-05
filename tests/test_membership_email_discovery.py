import pytest
from django.test import override_settings

from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1", ".localhost"],
)


def make_active_user(email: str, password: str = "pass12345") -> User:
    user = User.objects.create_user(email=email, password=password)
    user.is_active = True
    user.save(update_fields=["is_active"])
    return user


@pytest.mark.django_db
@override_settings(**COMMON)
def test_email_discovery_single_membership_redirects_to_tenant_login(client):
    user = make_active_user("u@example.com")
    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )
    Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    # Sanity: match the view's filters
    assert (
        Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            organization__status=Organization.Status.ACTIVE,
        ).count()
        == 1
    )

    resp = client.post(
        "/login/", data={"email": "u@example.com"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 302
    assert resp["Location"].endswith("/login/acme/")
    assert client.session.get("pending_login_email") == "u@example.com"


@pytest.mark.django_db
@override_settings(**COMMON)
def test_email_discovery_multiple_memberships_shows_picker(client):
    user = make_active_user("u2@example.com")

    org1 = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )
    org2 = Organization.objects.create(
        name="Bravo", slug="bravo", status=Organization.Status.ACTIVE
    )

    Membership.objects.create(
        user=user, organization=org1, status=Membership.Status.ACTIVE
    )
    Membership.objects.create(
        user=user, organization=org2, status=Membership.Status.ACTIVE
    )

    # Sanity: match the view's filters EXACTLY
    qs = Membership.objects.filter(
        user=user,
        status=Membership.Status.ACTIVE,
        organization__status=Organization.Status.ACTIVE,
    )
    assert qs.count() == 2

    resp = client.post(
        "/login/", data={"email": "u2@example.com"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 200

    # Picker view renders org_choices into context
    assert "org_choices" in resp.context
    org_choices = resp.context["org_choices"]
    assert isinstance(org_choices, list)
    assert {o["slug"] for o in org_choices} == {"acme", "bravo"}

    # Pending email stored for password-only step
    assert client.session.get("pending_login_email") == "u2@example.com"


@pytest.mark.django_db
@override_settings(**COMMON)
def test_tenant_login_requires_membership(client):
    make_active_user("u3@example.com")
    Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )

    session = client.session
    session["pending_login_email"] = "u3@example.com"
    session.save()

    resp = client.get("/login/acme/", HTTP_HOST="localhost")
    assert resp.status_code == 302
    assert resp["Location"].endswith("/login/")


@pytest.mark.django_db
@override_settings(**COMMON)
def test_tenant_login_success_sets_session_and_redirects(client):
    user = make_active_user("u4@example.com")
    org = Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )
    Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    session = client.session
    session["pending_login_email"] = "u4@example.com"
    session.save()

    resp = client.post(
        "/login/acme/", data={"password": "pass12345"}, HTTP_HOST="localhost"
    )
    assert resp.status_code == 302
    assert resp["Location"].endswith("/admin/")
    assert client.session["active_org_id"] == org.id
    assert client.session["active_org_slug"] == "acme"
    assert client.session.get("pending_login_email") is None


@pytest.mark.django_db
@override_settings(**COMMON)
def test_not_you_clears_pending_email(client):
    session = client.session
    session["pending_login_email"] = "u@example.com"
    session.save()

    resp = client.post("/login/clear/", HTTP_HOST="localhost")
    assert resp.status_code == 302
    assert resp["Location"].endswith("/login/")
    assert "pending_login_email" not in client.session
