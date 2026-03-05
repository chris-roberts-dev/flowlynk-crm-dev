from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIRS = [
    "webcrm/settings",
    "templates",
    "apps/platform/organizations",
    "apps/platform/accounts",
    "apps/platform/rbac",
    "apps/platform/audit",
    "apps/platform/support",
    "apps/crm/locations",
    "apps/crm/catalog",
    "apps/crm/leads",
    "apps/crm/quotes",
    "apps/crm/clients",
    "apps/crm/pricing",
    "apps/crm/tasks",
    "apps/crm/communications",
    "apps/ops/scheduling",
    "apps/ops/routing",
    "apps/ops/quality",
    "apps/ops/reporting",
    "apps/common/tenancy",
    "apps/common/utils",
    "apps/common/mixins",
    "apps/common/storage",
    "apps/common/admin",
    "tests",
    "scripts",
]

FILES = [
    "webcrm/__init__.py",
    "webcrm/settings/__init__.py",
    "webcrm/settings/base.py",
    "webcrm/settings/dev.py",
    "webcrm/settings/prod.py",
    "webcrm/urls.py",
    "webcrm/asgi.py",
    "webcrm/wsgi.py",
    "manage.py",
    "pytest.ini",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
    "README.md",
]

INIT_DIRS = [
    "apps",
    "apps/platform",
    "apps/platform/organizations",
    "apps/platform/accounts",
    "apps/platform/rbac",
    "apps/platform/audit",
    "apps/platform/support",
    "apps/crm",
    "apps/crm/locations",
    "apps/crm/catalog",
    "apps/crm/leads",
    "apps/crm/quotes",
    "apps/crm/clients",
    "apps/crm/pricing",
    "apps/crm/tasks",
    "apps/crm/communications",
    "apps/ops",
    "apps/ops/scheduling",
    "apps/ops/routing",
    "apps/ops/quality",
    "apps/ops/reporting",
    "apps/common",
    "apps/common/tenancy",
    "apps/common/utils",
    "apps/common/mixins",
    "apps/common/storage",
    "apps/common/admin",
    "tests",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_file(path: Path, content: str = "") -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main() -> None:
    for d in DIRS:
        ensure_dir(ROOT / d)

    # __init__.py markers
    for d in INIT_DIRS:
        ensure_file(ROOT / d / "__init__.py", "")

    # placeholders
    for f in FILES:
        ensure_file(ROOT / f, "")

    print("Project skeleton created/verified.")


if __name__ == "__main__":
    main()
