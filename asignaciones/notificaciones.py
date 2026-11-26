"""Notificaciones en tiempo real del almacén (007)."""

import json
import logging

import redis
from django.conf import settings

from .models import EstadoSolicitud, SolicitudAsignacion

logger = logging.getLogger(__name__)


def canal_region(region) -> str:
    return f"{settings.ALMACEN_SSE_PREFIJO_CANAL}{region.pk}"


def cliente_redis():
    return redis.Redis.from_url(
        settings.REDIS_NOTIFICACIONES_URL,
        decode_responses=True,
    )


def contar_pendientes(region) -> int:
    return SolicitudAsignacion.objects.filter(
        region=region,
        estado=EstadoSolicitud.ENVIADA,
    ).count()


def evento_solicitud_enviada(solicitud) -> dict:
    lineas = list(solicitud.lineas.all())
    tecnicos = sorted(
        {
            linea.tecnico.nif
            for linea in lineas
            if getattr(linea, "tecnico_id", None)
        }
    )
    return {
        "tipo": "solicitud_enviada",
        "solicitud_id": solicitud.pk,
        "tenant": solicitud.tenant.codigo,
        "tecnicos": tecnicos,
        "total_lineas": len(lineas),
        "total_series": sum(1 for linea in lineas if linea.serie_id),
        "total_cantidad": sum(
            linea.cantidad for linea in lineas if linea.serie_id is None
        ),
        "pendientes": contar_pendientes(solicitud.region),
        "url": f"/almacen/solicitudes/{solicitud.pk}/",
    }


def publicar_evento_region(region, evento) -> bool:
    """Publica un evento en el canal de la región; nunca revierte la operación."""
    try:
        cliente = cliente_redis()
        try:
            cliente.publish(
                canal_region(region),
                json.dumps(evento, ensure_ascii=False),
            )
        finally:
            cliente.close()
        return True
    except Exception:
        logger.warning(
            "No se pudo publicar la notificación del almacén",
            exc_info=True,
        )
        return False


def publicar_solicitud_enviada(solicitud) -> bool:
    try:
        evento = evento_solicitud_enviada(solicitud)
    except Exception:
        logger.warning(
            "No se pudo construir la notificación de la solicitud",
            exc_info=True,
        )
        return False
    return publicar_evento_region(solicitud.region, evento)


def suscribir_region(region, heartbeat_segundos=None):
    """Genera eventos SSE para la región y heartbeats cuando no hay novedades."""
    if heartbeat_segundos is None:
        heartbeat_segundos = settings.ALMACEN_SSE_HEARTBEAT_SEGUNDOS
    cliente = cliente_redis()
    pubsub = cliente.pubsub()
    try:
        pubsub.subscribe(canal_region(region))
        while True:
            mensaje = pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=heartbeat_segundos,
            )
            if mensaje and mensaje.get("type") == "message":
                yield f"event: notificacion\ndata: {mensaje['data']}\n\n"
            else:
                yield ": heartbeat\n\n"
    finally:
        try:
            pubsub.close()
        finally:
            cliente.close()
