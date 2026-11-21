"""Tareas Celery del envío de asignaciones al almacén (007)."""

from celery import shared_task


@shared_task
def programar_envio_solicitud(solicitud_id: int):
    """Crea el intento 1 y encola el envío del Excel."""
    from . import correo

    return correo.programar_envio_solicitud(solicitud_id)


@shared_task
def enviar_excel_solicitud(solicitud_id: int, numero_intento: int):
    """Ejecuta un intento de envío y programa el siguiente si falla."""
    from . import correo

    return correo.procesar_envio_solicitud(
        solicitud_id,
        numero_intento,
    )
