from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("locations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Region",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=50,
                        help_text="Unique region identifier. Recommended format: 'R-<ABBR>' (e.g., 'R-TENN', 'R-MO'). Must be unique within the organization.",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=200,
                        help_text="Human-friendly region name. Example: 'Tennessee Region'.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(editable=False)),
                ("updated_at", models.DateTimeField()),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={"ordering": ["organization_id", "name"]},
        ),
        migrations.CreateModel(
            name="Market",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=64,
                        help_text="Unique market identifier within the region. Recommended format: 'M-<AREA>' (e.g., 'M-MID-TN', 'M-STL-MO').",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=120,
                        help_text="Human-friendly market name. Example: 'Middle Tennessee' or 'St. Louis County'.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(editable=False)),
                ("updated_at", models.DateTimeField()),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="organizations.organization",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="markets",
                        to="locations.region",
                    ),
                ),
            ],
            options={"ordering": ["organization_id", "name"]},
        ),
        # ---- Constraints / Indexes (Region) ----
        migrations.AddConstraint(
            model_name="region",
            constraint=models.UniqueConstraint(
                fields=("organization", "code"), name="uniq_region_org_code"
            ),
        ),
        migrations.AddIndex(
            model_name="region",
            index=models.Index(
                fields=["organization", "is_active"], name="region_org_active_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="region",
            index=models.Index(
                fields=["organization", "code"], name="region_org_code_idx"
            ),
        ),
        # ---- Constraints / Indexes (Market) ----
        migrations.AddConstraint(
            model_name="market",
            constraint=models.UniqueConstraint(
                fields=("organization", "code"), name="uniq_market_org_code"
            ),
        ),
        migrations.AddIndex(
            model_name="market",
            index=models.Index(
                fields=["organization", "region"], name="market_org_region_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="market",
            index=models.Index(
                fields=["organization", "is_active"], name="market_org_active_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="market",
            index=models.Index(
                fields=["organization", "code"], name="market_org_code_idx"
            ),
        ),
        # ---- Location changes ----
        # Add market FK as NULLABLE first so existing rows don't break.
        migrations.AddField(
            model_name="location",
            name="market",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="locations",
                to="locations.market",
            ),
        ),
        # New Location fields (nullable/blank-friendly; service_area has default)
        migrations.AddField(
            model_name="location",
            name="service_area",
            field=models.CharField(
                max_length=120,
                choices=[("radius", "Radius Miles")],
                default="radius",
                help_text="How this location defines its service coverage. Currently supported: 'Radius Miles'.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="service_miles",
            field=models.PositiveSmallIntegerField(
                null=True,
                blank=True,
                help_text="Service radius in miles from the center point. Example: 60.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="service_lat",
            field=models.DecimalField(
                null=True,
                blank=True,
                max_digits=9,
                decimal_places=6,
                help_text="Center latitude for the service area (decimal degrees). Example: 36.14560.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="service_long",
            field=models.DecimalField(
                null=True,
                blank=True,
                max_digits=9,
                decimal_places=6,
                help_text="Center longitude for the service area (decimal degrees). Example: -85.47249.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="address1",
            field=models.CharField(
                max_length=200,
                blank=True,
                help_text="Street address line 1 for this location (internal/admin use). Example: '1027 Maple Ave'.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="address2",
            field=models.CharField(
                max_length=200,
                blank=True,
                help_text="Street address line 2 (suite/unit). Leave blank if not applicable.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="city",
            field=models.CharField(
                max_length=120,
                blank=True,
                help_text="City for this location address. Example: 'Nashville'.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="state",
            field=models.CharField(
                max_length=80,
                blank=True,
                help_text="State/Province code (2-letter US state recommended). Example: 'TN'.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="postal_code",
            field=models.CharField(
                max_length=20,
                blank=True,
                help_text="ZIP/Postal code. Example: '38506'.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="phone",
            field=models.CharField(
                max_length=32,
                blank=True,
                help_text="Primary contact phone for this location. Example: '931-319-1538'.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="email",
            field=models.EmailField(
                max_length=120,
                blank=True,
                help_text="Primary contact email for this location (used for notifications/quotes). Example: 'hello@mypipelinehero.com'.",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Optional internal notes for operations (crew pickup notes, special instructions, etc.).",
            ),
        ),
        # NOTE:
        # We intentionally do NOT add Location constraints/indexes here because your
        # initial migration already created uniq_location_org_code (and likely indexes).
    ]
