from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.platform.organizations.models import Organization
from apps.platform.rbac.service import require_capability

from .models import Location, Market, Region


@dataclass(frozen=True)
class LocationTreeIds:
    region_id: int | None = None
    market_id: int | None = None
    location_id: int | None = None


@transaction.atomic
def create_region(
    *, user, organization: Organization, code: str, name: str, is_active: bool = True
) -> Region:
    require_capability(
        user=user, organization=organization, capability_code="locations.manage"
    )
    obj = Region.objects.create(
        organization=organization,
        code=code,
        name=name,
        is_active=is_active,
    )
    obj.full_clean()
    obj.save()
    return obj


@transaction.atomic
def create_market(
    *,
    user,
    organization: Organization,
    region: Region,
    code: str,
    name: str,
    is_active: bool = True,
) -> Market:
    require_capability(
        user=user, organization=organization, capability_code="locations.manage"
    )
    obj = Market.objects.create(
        organization=organization,
        region=region,
        code=code,
        name=name,
        is_active=is_active,
    )
    obj.full_clean()
    obj.save()
    return obj


@transaction.atomic
def create_location(
    *,
    user,
    organization: Organization,
    market: Market,
    code: str,
    name: str,
    is_active: bool = True,
) -> Location:
    require_capability(
        user=user, organization=organization, capability_code="locations.manage"
    )
    obj = Location.objects.create(
        organization=organization,
        market=market,
        code=code,
        name=name,
        is_active=is_active,
    )
    obj.full_clean()
    obj.save()
    return obj
