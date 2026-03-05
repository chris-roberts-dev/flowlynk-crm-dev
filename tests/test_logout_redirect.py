import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_platform_logout_redirects_to_landing(client):
    User = get_user_model()
    user = User.objects.create_user(email="logout@example.com", password="pass12345")
    client.force_login(user)

    resp = client.post("/logout/")
    assert resp.status_code == 302
    assert resp["Location"] == "/"


@pytest.mark.django_db
def test_admin_logout_redirects_to_landing(client):
    User = get_user_model()
    user = User.objects.create_superuser(
        email="adminlogout@example.com", password="pass12345"
    )
    client.force_login(user)

    resp = client.post("/admin/logout/")
    assert resp.status_code == 302
    assert resp["Location"] == "/"
