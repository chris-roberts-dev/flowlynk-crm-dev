from .base import *  # noqa: F403

DEBUG = False

# Use sqlite for fast unit tests (foundation epic). Postgres required in later epics for constraints/indexes.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
