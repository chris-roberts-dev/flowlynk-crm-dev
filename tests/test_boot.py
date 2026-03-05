import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_django_system_check_passes():
    # Equivalent to: python manage.py check
    call_command("check")
