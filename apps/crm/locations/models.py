from __future__ import annotations

from django.db import models

from apps.common.mixins.models import TenantModel


class Location(TenantModel):
    """
    Minimal tenant-owned model to prove tenant ORM + admin scoping.
    Later we’ll expand into Region -> Market -> Location.
    """

    code = models.CharField(
        max_length=50, help_text="Org-scoped code used for imports/integrations."
    )
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_location_org_code"
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "code"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
