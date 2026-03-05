from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = (
    Path(__file__).resolve().parents[2]
)  # .../webcrm (project root alongside manage.py)

env = environ.Env(
    DEBUG=(bool, False),
)

# Load .env if present (dev convenience). In prod, rely on real env vars.
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(str(ENV_FILE))

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DEBUG", default=False)

# Hosts
_allowed_hosts_raw = env(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,.localhost",
)
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in env("CSRF_TRUSTED_ORIGINS", default="").split(",") if o.strip()
]

SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=None) or None
CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=None) or None

# -------------------------
# Tenancy configuration (v1)
# -------------------------
TENANT_BASE_DOMAIN = env("TENANT_BASE_DOMAIN", default="localhost")
TENANT_SCHEME = env("TENANT_SCHEME", default="http")
TENANT_PORT = env("TENANT_PORT", default="8000")

# Tenant-required routes (admin is tenant-scoped for normal users)
TENANT_REQUIRED_PATH_PREFIXES = [
    "/admin/",
    "/app/",
]

# Exempt admin auth endpoints so you can reach admin login without a tenant
TENANT_EXEMPT_PATH_PREFIXES = [
    "/admin/login/",
    "/admin/logout/",
    "/admin/password_reset/",
    "/admin/password_reset/done/",
    "/admin/reset/",
    "/admin/reset/done/",
]

# Fail closed on tenant-scoped ORM access unless tenant is resolved.
TENANT_STRICT_ORM = env.bool("TENANT_STRICT_ORM", default=True)

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local
    "apps.platform.organizations.apps.OrganizationsConfig",
    "apps.platform.accounts.apps.AccountsConfig",
    "apps.platform.rbac.apps.RBACConfig",
    "apps.platform.support.apps.SupportConfig",
    "apps.crm.locations.apps.LocationsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Auth must run before tenant middleware so we can enforce membership for /admin/
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Tenant must be resolved before any tenant data access
    "apps.common.tenancy.middleware.TenantResolutionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "webcrm.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "webcrm.wsgi.application"
ASGI_APPLICATION = "webcrm.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Non-negotiable: set AUTH_USER_MODEL from day 1 (avoids migration pain later)
AUTH_USER_MODEL = "accounts.User"

# Sessions (will become tenant-scoped later; keeping explicit + production-minded)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Django expects JS access sometimes; can tighten later.
