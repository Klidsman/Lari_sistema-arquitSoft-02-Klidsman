"""App de recojos de materiales."""

from django.apps import AppConfig


class RecojosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recojos"
    verbose_name = "Recojos de materiales"

    def ready(self):
        from materiales.services import registrar_verificacion_movimientos

        from .services import materiales_tiene_movimientos

        registrar_verificacion_movimientos(materiales_tiene_movimientos)
