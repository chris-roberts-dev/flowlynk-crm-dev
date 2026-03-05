from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.platform.organizations.models import Organization
from apps.platform.rbac.models import Capability, Role, RoleCapability


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise CommandError(f"Failed to read JSON file: {path} ({e})") from e


class Command(BaseCommand):
    help = "Import/upsert org roles from JSON. Supports --dry-run."

    def add_arguments(self, parser):
        parser.add_argument("--org", required=True, help="Organization slug.")
        parser.add_argument("--file", required=True, help="Path to roles JSON file.")
        parser.add_argument(
            "--dry-run", action="store_true", help="Validate only; do not write."
        )

    def handle(self, *args, **options):
        org_slug: str = options["org"]
        path = Path(options["file"])
        dry_run: bool = bool(options["dry_run"])

        org = Organization.objects.filter(slug=org_slug).first()
        if not org:
            raise CommandError(f"Organization not found: {org_slug}")

        if not path.exists():
            raise CommandError(f"File not found: {path}")

        payload = _load_json(path)
        roles = payload.get("roles")
        if not isinstance(roles, list):
            raise CommandError("JSON must include a top-level 'roles' list.")

        # Validate duplicate role codes in file
        codes = [r.get("code") for r in roles if isinstance(r, dict)]
        if len(codes) != len(set(codes)):
            raise CommandError("Duplicate role codes found in file.")

        # Validate capabilities exist
        cap_codes_needed = set()
        for r in roles:
            if not isinstance(r, dict):
                raise CommandError("Each role entry must be an object.")
            cap_list = r.get("capabilities", [])
            if not isinstance(cap_list, list):
                raise CommandError(f"Role {r.get('code')} capabilities must be a list.")
            cap_codes_needed |= set(cap_list)

        existing_caps = set(
            Capability.objects.filter(code__in=cap_codes_needed).values_list(
                "code", flat=True
            )
        )
        missing = sorted(cap_codes_needed - existing_caps)
        if missing:
            raise CommandError(f"Unknown capability codes: {missing}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run: validated successfully (no changes applied)."
                )
            )
            return

        with transaction.atomic():
            created = 0
            updated = 0
            mappings_created = 0

            cap_map = {
                c.code: c for c in Capability.objects.filter(code__in=cap_codes_needed)
            }

            for r in roles:
                code = (r.get("code") or "").strip()
                name = (r.get("name") or "").strip()
                if not code or not name:
                    raise CommandError(
                        "Each role must have non-empty 'code' and 'name'."
                    )

                role, was_created = Role.objects.unscoped().update_or_create(
                    organization_id=org.id,
                    code=code,
                    defaults={
                        "name": name,
                        "description": (r.get("description") or "").strip(),
                        "is_system": bool(r.get("is_system", False)),
                        "is_active": bool(r.get("is_active", True)),
                        # audit fields left null here; admin/service can set them later
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

                desired_caps = set(r.get("capabilities") or [])
                # Replace mappings (safe + deterministic)
                RoleCapability.objects.unscoped().filter(
                    organization_id=org.id, role_id=role.id
                ).delete()

                rc_rows = []
                for cap_code in desired_caps:
                    rc_rows.append(
                        RoleCapability(
                            organization_id=org.id,
                            role_id=role.id,
                            capability_id=cap_map[cap_code].id,
                        )
                    )
                if rc_rows:
                    RoleCapability.objects.unscoped().bulk_create(
                        rc_rows, batch_size=200
                    )
                    mappings_created += len(rc_rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported roles for org={org.slug}. created={created} updated={updated} role_capabilities={mappings_created}"
            )
        )
