from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.mixins.models import TenantModel
from apps.platform.accounts.models import Membership


class Capability(models.Model):
    """
    Global catalog of stable capability codes.
    Not tenant-scoped.
    """

    code = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class Role(TenantModel):
    """
    Tenant-scoped role definition.
    """

    code = models.CharField(
        max_length=80, help_text="Org-scoped stable code (used by imports)."
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_role_org_code"
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "code"]),
        ]
        ordering = ["organization_id", "code"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class RoleCapability(TenantModel):
    """
    Explicit mapping: Role -> Capability (tenant-scoped record to allow per-org role evolution).
    """

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_capabilities"
    )
    capability = models.ForeignKey(
        Capability, on_delete=models.CASCADE, related_name="role_capabilities"
    )

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["role", "capability"], name="uniq_role_capability"
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["organization", "capability"]),
        ]

    def clean(self):
        # Ensure org consistency
        if (
            self.role_id
            and self.organization_id
            and self.role.organization_id != self.organization_id
        ):
            raise ValidationError(
                "RoleCapability.organization must match role.organization."
            )

    def __str__(self) -> str:
        return f"{self.role.code} -> {self.capability.code}"


class MembershipRole(TenantModel):
    """
    Assign roles to a membership. Tenant-scoped.
    """

    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="membership_roles"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="membership_roles"
    )

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "role"], name="uniq_membership_role"
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "membership"]),
            models.Index(fields=["organization", "role"]),
        ]

    def clean(self):
        if (
            self.membership_id
            and self.organization_id
            and self.membership.organization_id != self.organization_id
        ):
            raise ValidationError(
                "MembershipRole.organization must match membership.organization."
            )
        if (
            self.role_id
            and self.organization_id
            and self.role.organization_id != self.organization_id
        ):
            raise ValidationError(
                "MembershipRole.organization must match role.organization."
            )

    def __str__(self) -> str:
        return f"{self.membership_id} -> {self.role.code}"


class MembershipCapabilityGrant(TenantModel):
    """
    Exception grants/denials at membership level.
    - allowed=True: add capability even if not in role
    - allowed=False: explicitly deny capability even if role has it (optional)
    """

    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="capability_grants"
    )
    capability = models.ForeignKey(
        Capability, on_delete=models.CASCADE, related_name="membership_grants"
    )
    allowed = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "capability"],
                name="uniq_membership_capability_grant",
            ),
        ]
        indexes = TenantModel.Meta.indexes + [
            models.Index(fields=["organization", "membership"]),
            models.Index(fields=["organization", "capability"]),
            models.Index(fields=["organization", "allowed"]),
        ]

    def clean(self):
        if (
            self.membership_id
            and self.organization_id
            and self.membership.organization_id != self.organization_id
        ):
            raise ValidationError(
                "MembershipCapabilityGrant.organization must match membership.organization."
            )

    def __str__(self) -> str:
        return f"{self.membership_id} -> {self.capability.code} ({'allow' if self.allowed else 'deny'})"
