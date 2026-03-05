from __future__ import annotations

from django.db import migrations
from django.utils import timezone


def backfill_default_region_market(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Region = apps.get_model("locations", "Region")
    Market = apps.get_model("locations", "Market")
    Location = apps.get_model("locations", "Location")

    now = timezone.now()

    for org in Organization.objects.all():
        region, _ = Region.objects.get_or_create(
            organization_id=org.id,
            code="R-DEFAULT",
            defaults={
                "name": "Default Region",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )

        market, _ = Market.objects.get_or_create(
            organization_id=org.id,
            code="M-DEFAULT",
            defaults={
                "name": "Default Market",
                "is_active": True,
                "region_id": region.id,
                "created_at": now,
                "updated_at": now,
            },
        )

        Location.objects.filter(
            organization_id=org.id,
            market__isnull=True,
        ).update(market_id=market.id)


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0002_region_market_and_locations_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_default_region_market, migrations.RunPython.noop),
    ]
