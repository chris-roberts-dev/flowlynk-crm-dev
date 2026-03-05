from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.crm.locations.models import Location
from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization
from apps.platform.rbac.bootstrap import (
    ensure_owner_assigned,
    ensure_staff_and_admin_perms_for_models,
)
from apps.platform.rbac.models import MembershipCapabilityGrant, MembershipRole, Role


class Command(BaseCommand):
    help = (
        "Bootstrap an organization + tenant admin membership with 'owner' RBAC role, "
        "plus Django admin access for admin-first MVP."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-slug",
            required=True,
            help="Organization slug (used in path-based tenancy: /t/<slug>/admin/).",
        )
        parser.add_argument(
            "--org-name",
            required=False,
            help="Organization name (required if org does not exist).",
        )
        parser.add_argument(
            "--email",
            required=True,
            help="User email for the tenant admin.",
        )
        parser.add_argument(
            "--password",
            required=False,
            help="Password for the user (required if creating a new user; optional reset for existing).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and print actions only; do not write.",
        )

    def handle(self, *args, **options):
        org_slug: str = (options["org_slug"] or "").strip()
        org_name: str | None = (options.get("org_name") or "").strip() or None
        email: str = (options["email"] or "").strip().lower()
        password: str | None = (options.get("password") or "").strip() or None
        dry_run: bool = bool(options.get("dry_run"))

        if not org_slug:
            raise CommandError("--org-slug is required")
        if not email:
            raise CommandError("--email is required")

        # Correct URLs for the current routing design
        tenant_admin_entry_url = f"/t/{org_slug}/admin/"
        platform_admin_url = "/admin/"
        tenant_email_discovery_url = "/login/"

        # Models we want visible to a tenant admin in admin-first MVP
        tenant_admin_models = [
            # Platform (tenant-relevant)
            User,
            Membership,
            Role,
            MembershipRole,
            MembershipCapabilityGrant,
            # CRM
            Location,
        ]

        # Read-only preflight (used for dry-run output + validation)
        org = Organization.objects.filter(slug=org_slug).first()
        user = User.objects.filter(email__iexact=email).first()
        membership = None
        if org and user:
            membership = Membership.objects.filter(user=user, organization=org).first()

        would_create_org = org is None
        would_create_user = user is None
        would_create_membership = (
            membership is None
            if (org and user)
            else (org is not None and user is not None)
        )

        # Validation
        if would_create_org and not org_name:
            raise CommandError(
                "Org does not exist; --org-name is required to create it."
            )
        if would_create_user and not password:
            raise CommandError(
                "User does not exist; --password is required to create a new user."
            )

        actions: list[str] = []

        if would_create_org:
            actions.append(
                f"Create org slug={org_slug} name={org_name!r} status=ACTIVE"
            )
        else:
            # We may normalize org status to ACTIVE if needed
            if org.status != Organization.Status.ACTIVE:
                actions.append(f"Update org slug={org_slug} status -> ACTIVE")

        if would_create_user:
            actions.append(f"Create user email={email} (active) and set password")
        else:
            if password:
                actions.append(f"Reset password for user email={email}")
            if not user.is_active:
                actions.append(f"Activate user email={email}")

        if org and user:
            if membership is None:
                actions.append(
                    f"Create membership user={email} org={org_slug} status=ACTIVE"
                )
            else:
                if membership.status != Membership.Status.ACTIVE:
                    actions.append(
                        f"Update membership user={email} org={org_slug} status -> ACTIVE"
                    )

        actions.append("Ensure RBAC 'owner' role exists + assigned to membership")
        actions.append(
            f"Grant Django admin perms for {len(tenant_admin_models)} model(s) and ensure is_staff=True"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry-run: no changes will be applied.")
            )
            for a in actions:
                self.stdout.write(f"[dry-run] {a}")

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Dry-run validated successfully."))
            self.stdout.write("Next URLs:")
            self.stdout.write(f"  Tenant admin entry: {tenant_admin_entry_url}")
            self.stdout.write(f"  Tenant email discovery: {tenant_email_discovery_url}")
            self.stdout.write(f"  Platform admin: {platform_admin_url}")
            return

        # Apply changes
        with transaction.atomic():
            created_org = False
            created_user = False
            created_membership = False

            org = Organization.objects.filter(slug=org_slug).first()
            if not org:
                org = Organization.objects.create(
                    slug=org_slug,
                    name=org_name,  # validated above
                    status=Organization.Status.ACTIVE,
                )
                created_org = True
            elif org.status != Organization.Status.ACTIVE:
                org.status = Organization.Status.ACTIVE
                org.save(update_fields=["status"])

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                user = User.objects.create_user(email=email, password=password)
                user.is_active = True
                user.save(update_fields=["is_active"])
                created_user = True
            else:
                if password:
                    user.set_password(password)
                    user.save(update_fields=["password"])
                if not user.is_active:
                    user.is_active = True
                    user.save(update_fields=["is_active"])

            membership = Membership.objects.filter(user=user, organization=org).first()
            if not membership:
                membership = Membership.objects.create(
                    user=user,
                    organization=org,
                    status=Membership.Status.ACTIVE,
                )
                created_membership = True
            elif membership.status != Membership.Status.ACTIVE:
                membership.status = Membership.Status.ACTIVE
                membership.save(update_fields=["status"])

            # Ensure RBAC owner role exists + assigned
            r = ensure_owner_assigned(organization=org, membership_id=membership.id)

            # Ensure the user can *see* models in Django Admin
            staff_enabled, perms_added = ensure_staff_and_admin_perms_for_models(
                user=user, models=tenant_admin_models
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Bootstrap complete: "
                f"org={'created' if created_org else 'existing'} "
                f"user={'created' if created_user else 'existing'} "
                f"membership={'created' if created_membership else 'existing'} "
                f"owner_role_assigned={r.assigned_membership_roles} "
                f"staff_enabled={staff_enabled} "
                f"django_perms_added={perms_added}"
            )
        )
        self.stdout.write("Next URLs:")
        self.stdout.write(f"  Tenant admin entry: {tenant_admin_entry_url}")
        self.stdout.write(f"  Tenant email discovery: {tenant_email_discovery_url}")
        self.stdout.write(f"  Platform admin: {platform_admin_url}")
