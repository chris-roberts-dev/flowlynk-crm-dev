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
    help = "Bootstrap an organization + admin membership with 'owner' RBAC role, plus Django admin access."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-slug", required=True, help="Organization slug (tenant subdomain)."
        )
        parser.add_argument(
            "--org-name",
            required=False,
            help="Organization name (used if org is created).",
        )
        parser.add_argument(
            "--email", required=True, help="User email for the org admin."
        )
        parser.add_argument(
            "--password",
            required=False,
            help="Set password for user (created or reset).",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Validate only; do not write."
        )

    def handle(self, *args, **options):
        org_slug: str = options["org_slug"].strip()
        org_name: str | None = (options.get("org_name") or "").strip() or None
        email: str = options["email"].strip().lower()
        password: str | None = (options.get("password") or "").strip() or None
        dry_run: bool = bool(options["dry_run"])

        if not org_slug:
            raise CommandError("--org-slug is required")
        if not email:
            raise CommandError("--email is required")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry-run: no changes will be applied.")
            )

        # Models we want visible to a tenant admin in admin-first MVP
        TENANT_ADMIN_MODELS = [
            # Platform (tenant-relevant)
            User,
            Membership,
            Role,
            MembershipRole,
            MembershipCapabilityGrant,
            # CRM
            Location,
        ]

        with transaction.atomic():
            org = Organization.objects.filter(slug=org_slug).first()
            created_org = False
            if not org:
                if not org_name:
                    raise CommandError(
                        "Org does not exist; --org-name is required to create it."
                    )
                if dry_run:
                    self.stdout.write(
                        f"[dry-run] Would create org slug={org_slug} name={org_name}"
                    )
                    return
                org = Organization.objects.create(
                    slug=org_slug,
                    name=org_name,
                    status=Organization.Status.ACTIVE,
                )
                created_org = True

            user = User.objects.filter(email__iexact=email).first()
            created_user = False
            if not user:
                if dry_run:
                    self.stdout.write(f"[dry-run] Would create user email={email}")
                    return
                user = User.objects.create_user(email=email, password=password or None)
                user.is_active = True
                user.save(update_fields=["is_active"])
                created_user = True
            else:
                if password and not dry_run:
                    user.set_password(password)
                    user.save(update_fields=["password"])

                if not user.is_active and not dry_run:
                    user.is_active = True
                    user.save(update_fields=["is_active"])

            membership = Membership.objects.filter(user=user, organization=org).first()
            created_membership = False
            if not membership:
                if dry_run:
                    self.stdout.write(
                        f"[dry-run] Would create membership user={email} org={org.slug}"
                    )
                    return
                membership = Membership.objects.create(
                    user=user,
                    organization=org,
                    status=Membership.Status.ACTIVE,
                )
                created_membership = True
            else:
                if membership.status != Membership.Status.ACTIVE and not dry_run:
                    membership.status = Membership.Status.ACTIVE
                    membership.save(update_fields=["status"])

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS("Dry-run: validated and would succeed.")
                )
                return

            # Ensure RBAC owner role exists + assigned
            r = ensure_owner_assigned(organization=org, membership_id=membership.id)

            # Ensure the user can *see* models in Django Admin:
            staff_enabled, perms_added = ensure_staff_and_admin_perms_for_models(
                user=user, models=TENANT_ADMIN_MODELS
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
