from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.platform.rbac.defaults import CAPABILITIES
from apps.platform.rbac.models import Capability


class Command(BaseCommand):
    help = "Idempotently seed global Capability rows."

    def handle(self, *args, **options):
        existing = set(Capability.objects.values_list("code", flat=True))
        to_create = []
        for code, desc in CAPABILITIES.items():
            if code not in existing:
                to_create.append(
                    Capability(code=code, description=desc, is_active=True)
                )

        if to_create:
            Capability.objects.bulk_create(to_create, batch_size=200)
        self.stdout.write(
            self.style.SUCCESS(f"Seeded capabilities. Created={len(to_create)}")
        )
