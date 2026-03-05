import pytest
from django.test import override_settings

from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization


COMMON_OVERRIDES = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1", ".localhost"],
)


@pytest.mark.django_db
@override_settings(**COMMON_OVERRIDES)
def test_tenant_entrypoint_sets_session_and_redirects_to_admin(client):
    Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )

    resp = client.get("/t/acme/admin/", HTTP_HOST="localhost", follow=False)
    assert resp.status_code == 302
    assert resp["Location"] == "/admin/"

    session = client.session
    assert session["active_org_slug"] == "acme"
    assert isinstance(session["active_org_id"], int)


@pytest.mark.django_db
@override_settings(**COMMON_OVERRIDES)
def test_resolves_tenant_from_subdomain(client):
    Organization.objects.create(
        name="Acme", slug="acme", status=Organization.Status.ACTIVE
    )

    resp = client.get("/app/", HTTP_HOST="acme.localhost")
    assert resp.status_code == 200
    assert b"Acme" in resp.content
    assert b"acme" in resp.content


@pytest.mark.django_db
@override_settings(**COMMON_OVERRIDES)
def test_resolves_tenant_from_explicit_login_path(client):
    """
    Middleware resolves tenant from /login/<org_slug>/.
    Tenant login view renders only when pending email refers to an active user with membership.
    """
    org = Organization.objects.create(
        name="Bravo Co", slug="bravo", status=Organization.Status.ACTIVE
    )

    user = User.objects.create_user(email="someone@example.com", password="pass12345")
    user.is_active = True
    user.save(update_fields=["is_active"])
    Membership.objects.create(
        user=user, organization=org, status=Membership.Status.ACTIVE
    )

    session = client.session
    session["pending_login_email"] = "someone@example.com"
    session.save()

    resp = client.get("/login/bravo/", HTTP_HOST="localhost")
    assert resp.status_code == 200
    assert b"Bravo Co" in resp.content
    assert b"someone@example.com" in resp.content


@pytest.mark.django_db
@override_settings(**COMMON_OVERRIDES)
def test_denies_tenant_route_if_unresolved(client):
    resp = client.get("/app/", HTTP_HOST="localhost")
    assert resp.status_code == 404


@pytest.mark.django_db
@override_settings(**COMMON_OVERRIDES)
def test_rejects_nested_subdomain_patterns(client):
    Organization.objects.create(
        name="Alpha", slug="alpha", status=Organization.Status.ACTIVE
    )

    resp = client.get("/app/", HTTP_HOST="alpha.dev.localhost")
    assert resp.status_code == 404
