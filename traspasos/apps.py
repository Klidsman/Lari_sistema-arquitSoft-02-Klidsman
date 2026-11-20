"""App de traspasos entre técnicos."""

from django.apps import AppConfig


class TraspasosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "traspasos"
    verbose_name = "Traspasos entre técnicos"
