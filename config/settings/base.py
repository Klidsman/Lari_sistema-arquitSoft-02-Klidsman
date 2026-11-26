"""Configuración base compartida por todos los entornos."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-inseguro-cambiar-en-produccion")
DEBUG = os.getenv("DEBUG", "False").strip().lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tenants",
    "acceso",
    "auditoria",
    "materiales",
    "tecnicos",
    "stock",
    "series",
    "recojos",
    "stock_inicial",
    "asignaciones",
    "traspasos",
    "conciliaciones",
    "logistica_inversa",
    "registro_materiales",
    "reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "acceso.middleware.ContextoUsuarioMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://lari_app:lari_app@localhost:5432/lari",
        ),
        conn_max_age=int(os.getenv("DATABASE_CONN_MAX_AGE", "600")),
        conn_health_checks=True,
    )
}

AUTH_USER_MODEL = "acceso.Usuario"

AUTHENTICATION_BACKENDS = [
    "acceso.authentication.EmailBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "es"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Lima")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@lari.local")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "300"))

SERIE_LONGITUD = int(os.getenv("SERIE_LONGITUD", "12"))
SERIE_PATRON = os.getenv("SERIE_PATRON", r"^[A-Z0-9]{12}$")

PERMITIR_REINICIO_STOCK_INICIAL = os.getenv(
    "PERMITIR_REINICIO_STOCK_INICIAL", "False"
).strip().lower() in {"1", "true", "yes", "on"}

MOVIMIENTO_ASIGNACION = os.getenv("MOVIMIENTO_ASIGNACION", "Z31")
DIAS_ALERTA_CUSTODIA = int(os.getenv("DIAS_ALERTA_CUSTODIA", "20"))
ASIGNACIONES_EXCEL_DIR = os.getenv("ASIGNACIONES_EXCEL_DIR", "asignaciones")

ENVIOS_MAX_INTENTOS = int(os.getenv("ENVIOS_MAX_INTENTOS", "4"))
ENVIOS_INTERVALO_REINTENTO_SEGUNDOS = int(
    os.getenv("ENVIOS_INTERVALO_REINTENTO_SEGUNDOS", "300")
)
ENVIOS_REMITENTE = os.getenv("ENVIOS_REMITENTE", "no-reply@lari.local")
ALMACEN_ALERTA_ASUNTO = os.getenv(
    "ALMACEN_ALERTA_ASUNTO", "Nueva solicitud de asignación"
)
ALMACEN_SSE_PREFIJO_CANAL = os.getenv("ALMACEN_SSE_PREFIJO_CANAL", "almacen:region:")
ALMACEN_SSE_HEARTBEAT_SEGUNDOS = int(
    os.getenv("ALMACEN_SSE_HEARTBEAT_SEGUNDOS", "25")
)
REDIS_NOTIFICACIONES_URL = os.getenv(
    "REDIS_NOTIFICACIONES_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

TRASPASOS_EXCEL_DIR = os.getenv("TRASPASOS_EXCEL_DIR", "traspasos")

CONCILIACIONES_DIR = os.getenv("CONCILIACIONES_DIR", "conciliaciones")
CONCILIACIONES_MAX_BYTES = int(
    os.getenv("CONCILIACIONES_MAX_BYTES", str(10 * 1024 * 1024))
)

ACTAS_DIR = os.getenv("ACTAS_DIR", "actas")

REGISTRO_MATERIALES_FACTOR_ATIPICO = float(
    os.getenv("REGISTRO_MATERIALES_FACTOR_ATIPICO", "3")
)
REGISTRO_FACTOR_ADVERTENCIA = float(
    os.getenv("REGISTRO_FACTOR_ADVERTENCIA", "3")
)
REGISTRO_MESES_PROMEDIO = int(os.getenv("REGISTRO_MESES_PROMEDIO", "3"))
REGISTRO_BACKUP_REQUERIDO = (
    os.getenv("REGISTRO_BACKUP_REQUERIDO", "True") == "True"
)
