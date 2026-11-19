"""Configuración para la suite de pruebas sobre PostgreSQL."""

import os

from .base import *  # noqa: F403

DEBUG = False

DATABASES["default"]["TEST"] = {  # noqa: F405
    "NAME": os.getenv("TEST_DATABASE_NAME", "test_lari"),
}
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
# La tarea de correo registra el error y reintenta; en pruebas no debe romper el test.
CELERY_TASK_EAGER_PROPAGATES = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

TOTP_ENCRYPTION_KEY = os.getenv(
    "TOTP_ENCRYPTION_KEY",
    "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
