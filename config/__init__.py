"""Paquete de configuración del proyecto."""

from .celery import app as celery_app

__all__ = ("celery_app",)
