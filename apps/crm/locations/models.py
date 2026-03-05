from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.mixins.models import TenantModel


class Region(TenantModel):
    """
    Tenant-owned region (top of the location hierarchy).
    """

    code = models.CharField(
        max_length=50,
        help_text="Unique region identifier. Recommended format: 'R-<ABBR>' (e.g., 'R-TENN', 'R-MO'). Must be unique within the organization.",
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-friendly region name. Example: 'Tennessee Region'.",
    )
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_region_org_code"
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "code"]),
        ]
        ordering = ["organization_id", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Market(TenantModel):
    """
    Tenant-owned market within a region.
    """

    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="markets")
    code = models.CharField(
        max_length=64,
        help_text="Unique market identifier within the region. Recommended format: 'M-<AREA>' (e.g., 'M-MID-TN', 'M-STL-MO').",
    )
    name = models.CharField(
        max_length=120,
        help_text="Human-friendly market name. Example: 'Middle Tennessee' or 'St. Louis County'.",
    )
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_market_org_code"
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "region"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "code"]),
        ]
        ordering = ["organization_id", "name"]

    def clean(self):
        # Prevent cross-org FK linkage (absolute isolation).
        if (
            self.region_id
            and self.organization_id
            and self.region.organization_id != self.organization_id
        ):
            raise ValidationError("Market.organization must match region.organization.")

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ServiceAreaType(models.TextChoices):
    RADIUS = "radius", "Radius Miles"


class Location(TenantModel):
    """
    Tenant-owned location within a market.

    NOTE: This used to be flat. It is now Market-scoped.
    """

    market = models.ForeignKey(
        Market, on_delete=models.PROTECT, related_name="locations"
    )
    code = models.CharField(
        max_length=120,
        help_text="Unique location identifier within the market. Recommended format: 'L-<MARKET>-###' (e.g., 'L-MID-TN-001').",
    )
    name = models.CharField(
        max_length=160,
        help_text="Location label used in admin and scheduling. Usually the primary city/area served (e.g., 'Cookeville', 'St. Louis').",
    )
    is_active = models.BooleanField(default=True)
    service_area = models.CharField(
        max_length=120,
        choices=ServiceAreaType.choices,
        default=ServiceAreaType.RADIUS,
        help_text="How this location defines its service coverage. Currently supported: 'Radius Miles'.",
    )
    service_miles = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Service radius in miles from the center point. Example: 60.",
    )
    service_lat = models.DecimalField(
        null=True,
        blank=True,
        max_digits=9,
        decimal_places=6,
        help_text="Center latitude for the service area (decimal degrees). Example: 36.14560.",
    )
    service_long = models.DecimalField(
        null=True,
        blank=True,
        max_digits=9,
        decimal_places=6,
        help_text="Center longitude for the service area (decimal degrees). Example: -85.47249.",
    )
    address1 = models.CharField(
        max_length=200,
        blank=True,
        help_text="Street address line 1 for this location (internal/admin use). Example: '1027 Maple Ave'.",
    )
    address2 = models.CharField(
        max_length=200,
        blank=True,
        help_text="Street address line 2 (suite/unit). Leave blank if not applicable.",
    )
    city = models.CharField(
        max_length=120,
        blank=True,
        help_text="City for this location address. Example: 'Nashville'.",
    )
    state = models.CharField(
        max_length=80,
        blank=True,
        help_text="State/Province code (2-letter US state recommended). Example: 'TN'.",
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="ZIP/Postal code. Example: '38506'.",
    )
    phone = models.CharField(
        max_length=32,
        blank=True,
        help_text="Primary contact phone for this location. Example: '931-319-1538'.",
    )
    email = models.EmailField(
        max_length=120,
        blank=True,
        help_text="Primary contact email for this location (used for notifications/quotes). Example: 'hello@mypipelinehero.com'.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional internal notes for operations (crew pickup notes, special instructions, etc.).",
    )

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_location_org_code"
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "market"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "code"]),
        ]
        ordering = ["organization_id", "name"]

    def clean(self):
        if (
            self.market_id
            and self.organization_id
            and self.market.organization_id != self.organization_id
        ):
            raise ValidationError(
                "Location.organization must match market.organization."
            )

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
