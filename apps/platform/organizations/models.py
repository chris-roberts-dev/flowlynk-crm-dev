from __future__ import annotations

from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils import timezone


slug_validator = RegexValidator(
    regex=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    message="Slug must be lowercase alphanumeric and hyphens, 1-63 chars, cannot start/end with hyphen.",
)


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=200)
    slug = models.CharField(
        max_length=63,
        unique=True,
        validators=[MinLengthValidator(1), slug_validator],
        help_text="Tenant slug used for subdomain resolution. Example: acme -> acme.app.com",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["slug"], name="uniq_organization_slug"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"
