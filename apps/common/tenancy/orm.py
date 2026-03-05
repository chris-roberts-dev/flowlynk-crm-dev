from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.tenancy.context import TenantNotResolvedError, get_current_org_id


class TenantQuerySet(models.QuerySet):
    def for_org_id(self, org_id: int):
        return self.filter(organization_id=org_id)


class TenantManager(models.Manager):
    """
    Default manager for tenant-scoped models.
    Fail-closed unless a tenant is resolved, unless .unscoped() is used explicitly.
    """

    def get_queryset(self):
        qs = TenantQuerySet(self.model, using=self._db)

        # Allow explicit escape hatch
        if getattr(self, "_unscoped", False):
            return qs

        org_id = get_current_org_id()
        if org_id is None:
            if getattr(settings, "TENANT_STRICT_ORM", True):
                raise TenantNotResolvedError(
                    f"Tenant not resolved for tenant-scoped model {self.model.__name__}. "
                    "Use .unscoped() explicitly only for platform-level operations."
                )
            return qs.none()

        return qs.filter(organization_id=org_id)

    def unscoped(self):
        mgr = self.__class__()
        mgr.model = self.model
        mgr._db = self._db
        mgr._hints = self._hints
        mgr._unscoped = True  # type: ignore[attr-defined]
        return mgr

    def for_org_id(self, org_id: int):
        return self.unscoped().filter(organization_id=org_id)
