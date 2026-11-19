"""App de conciliación de stock."""

from django.apps import AppConfig


class ConciliacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "conciliaciones"
    verbose_name = "Conciliación de stock"
