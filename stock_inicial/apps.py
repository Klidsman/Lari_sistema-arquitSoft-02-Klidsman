"""App de stock inicial de técnicos."""

from django.apps import AppConfig


class StockInicialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stock_inicial"
    verbose_name = "Stock inicial de técnicos"
