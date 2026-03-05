from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0003_backfill_location_market"),
    ]

    operations = [
        migrations.AlterField(
            model_name="location",
            name="market",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="locations",
                to="locations.market",
            ),
        ),
    ]
