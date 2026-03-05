import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.platform.organizations.models import Organization


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/login/", "/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1", ".localhost", "testserver"],
)


@pytest.mark.django_db
@override_settings(**COMMON)
def test_superuser_can_access_admin_without_tenant(client):
    User = get_user_model()
    su = User.objects.create_superuser(email="su@example.com", password="pass12345")
    Organization.objects.create(name="Acme", slug="acme")

    client.force_login(su)
    resp = client.get("/admin/", HTTP_HOST="localhost")
    assert resp.status_code == 200
