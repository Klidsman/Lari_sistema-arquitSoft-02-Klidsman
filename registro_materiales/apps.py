"""App de registro de materiales."""

from django.apps import AppConfig


class RegistroMaterialesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "registro_materiales"
    verbose_name = "Registro de materiales"
