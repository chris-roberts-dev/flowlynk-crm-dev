from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.tenancy.orm import TenantManager
from apps.platform.organizations.models import Organization


class TenantModel(models.Model):
    """
    Pattern A: direct organization FK on every tenant-owned table.
    Includes minimal audit fields and common indexes.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="%(class)ss"
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)ss",
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)ss",
    )

    objects = TenantManager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["organization", "updated_at"]),
        ]
