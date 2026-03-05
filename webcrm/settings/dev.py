from .base import *  # noqa: F403

DEBUG = True

# Allow localhost + subdomains of localhost for tenant testing (e.g., acme.localhost)
ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1", ".localhost"]  # noqa: F405

CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS or [  # noqa: F405
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Path-based tenancy on localhost: do NOT set cookie domains.
# Setting Domain=.localhost often causes browsers to drop cookies entirely,
# which breaks CSRF.
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None

# Explicitly keep these non-secure in dev (http)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
