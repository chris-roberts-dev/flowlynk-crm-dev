import pytest

from apps.common.tenancy.context import TenantNotResolvedError, org_context
from apps.crm.locations.models import Location
from apps.platform.organizations.models import Organization


@pytest.mark.django_db
def test_tenant_queryset_filters_by_current_org():
    org1 = Organization.objects.create(name="Org 1", slug="org1")
    org2 = Organization.objects.create(name="Org 2", slug="org2")

    Location.objects.unscoped().create(organization=org1, code="A", name="Loc A")
    Location.objects.unscoped().create(organization=org2, code="B", name="Loc B")

    with org_context(org1.id):
        rows = list(Location.objects.all())
        assert len(rows) == 1
        assert rows[0].organization_id == org1.id
        assert rows[0].code == "A"

    with org_context(org2.id):
        rows = list(Location.objects.all())
        assert len(rows) == 1
        assert rows[0].organization_id == org2.id
        assert rows[0].code == "B"


@pytest.mark.django_db
def test_tenant_queryset_raises_when_tenant_missing(settings):
    settings.TENANT_STRICT_ORM = True
    Organization.objects.create(name="Org 1", slug="org1")
    with org_context(None):
        with pytest.raises(TenantNotResolvedError):
            list(Location.objects.all())
