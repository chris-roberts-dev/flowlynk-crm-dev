import pytest
from django.test import override_settings
from django.utils import timezone

from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1", ".localhost"],
)


@pytest.mark.django_db
@override_settings(**COMMON)
def test_tenant_login_redirects_to_same_host_admin_and_sets_session(client):
    org = Organization.objects.create(
        name="Acme",
        slug="acme",
        status=Organization.Status.ACTIVE,
    )
    user = User.objects.create_user(
        email="u@acme.com", password="pass12345", is_active=True
    )
    Membership.objects.create(
        user=user,
        organization=org,
        status=Membership.Status.ACTIVE,
        last_login_at=timezone.now(),
    )

    # Email discovery step stores pending email in session
    session = client.session
    session["pending_login_email"] = "u@acme.com"
    session.save()

    # In the path-based approach, login happens on the root host
    resp = client.post(
        "/login/acme/",
        data={"password": "pass12345"},
        HTTP_HOST="localhost:8000",
        follow=False,
    )
    assert resp.status_code == 302
    assert resp["Location"] == "/admin/"

    # Tenant affinity is persisted
    session = client.session
    assert session["active_org_slug"] == "acme"
    assert session["active_org_id"] == org.id
