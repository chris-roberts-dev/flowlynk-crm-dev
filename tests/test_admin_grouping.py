import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.platform.organizations.models import Organization


COMMON = dict(
    TENANT_BASE_DOMAIN="localhost",
    TENANT_REQUIRED_PATH_PREFIXES=["/admin/", "/app/"],
    TENANT_EXEMPT_PATH_PREFIXES=["/admin/logout/"],
    ALLOWED_HOSTS=["localhost", "127.0.0.1", ".localhost"],
)


@pytest.mark.django_db
@override_settings(**COMMON)
def test_admin_index_shows_only_platform_and_crm_groups(client):
    User = get_user_model()
    admin_user = User.objects.create_superuser(
        email="admin@example.com", password="pass12345"
    )
    client.force_login(admin_user)

    Organization.objects.create(name="Acme", slug="acme")

    resp = client.get("/admin/", HTTP_HOST="acme.localhost")
    assert resp.status_code == 200

    content = resp.content.decode("utf-8")

    assert "Platform" in content
    assert "CRM" in content

    # User model should appear (under Accounts app grouped into Platform)
    assert ">Users<" in content


@pytest.mark.django_db
@override_settings(**COMMON)
def test_user_model_is_grouped_under_platform(client):
    User = get_user_model()
    admin_user = User.objects.create_superuser(
        email="admin2@example.com", password="pass12345"
    )
    client.force_login(admin_user)

    Organization.objects.create(name="Acme", slug="acme")

    resp = client.get("/admin/", HTTP_HOST="acme.localhost")
    assert resp.status_code == 200

    grouped = resp.context["grouped_app_list"]
    assert "Platform" in grouped
    assert "CRM" in grouped

    platform_labels = {a["app_label"] for a in grouped["Platform"]}
    assert "accounts" in platform_labels
