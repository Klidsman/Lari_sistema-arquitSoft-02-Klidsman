"""Servicios del almacén sobre solicitudes de asignación (007)."""

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from acceso.models import Rol
from auditoria.services import registrar_cambio
from series.models import EstadoSerie, Serie
from stock.services import (
    ConfirmacionStockInvalida,
    StockInsuficiente,
    actualizar_stock_confirmacion_asignacion,
)

from .models import EnvioCorreo, EstadoSolicitud, SolicitudAsignacion


class PermisoDenegado(Exception):
    mensaje = "No tienes permiso para gestionar despachos"

    def __str__(self):
        return self.mensaje


class SolicitudNoExiste(Exception):
    mensaje = "La solicitud no existe"

    def __str__(self):
        return self.mensaje


class EstadoSolicitudInvalido(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class MotivoRechazoInvalido(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class ArchivoAlterado(Exception):
    mensaje = "El archivo fue modificado, descarga bloqueada"

    def __str__(self):
        return self.mensaje


def validar_cuenta_almacen(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol != Rol.RESPONSABLE_ALMACEN or not actor.region_id:
        raise PermisoDenegado
    region = actor.region
    if not region.activa:
        raise PermisoDenegado
    try:
        almacen = region.almacen
    except Exception as exc:
        raise PermisoDenegado from exc
    if not almacen.activo:
        raise PermisoDenegado
    return region


def bandeja(region, estado=None):
    solicitudes = SolicitudAsignacion.objects.filter(
        region=region,
        estado__in=[
            EstadoSolicitud.ENVIADA,
            EstadoSolicitud.CONFIRMADA,
            EstadoSolicitud.RECHAZADA,
        ],
    ).select_related("tenant")
    if estado in {
        EstadoSolicitud.ENVIADA,
        EstadoSolicitud.CONFIRMADA,
        EstadoSolicitud.RECHAZADA,
    }:
        solicitudes = solicitudes.filter(estado=estado)
    return solicitudes.prefetch_related("lineas__tecnico").order_by("-enviada_en", "-id")


def obtener_solicitud_region(region, solicitud_id):
    solicitud = (
        SolicitudAsignacion.objects.filter(
            pk=solicitud_id,
            region=region,
            estado__in=[
                EstadoSolicitud.ENVIADA,
                EstadoSolicitud.CONFIRMADA,
                EstadoSolicitud.RECHAZADA,
            ],
        )
        .select_related("tenant", "region")
        .first()
    )
    if solicitud is None:
        raise SolicitudNoExiste
    return solicitud


def detalle_solicitud_region(region, solicitud_id):
    solicitud = obtener_solicitud_region(region, solicitud_id)
    return (
        SolicitudAsignacion.objects.filter(pk=solicitud.pk)
        .select_related("tenant", "region")
        .prefetch_related("lineas__material", "lineas__serie", "lineas__tecnico", "envios_correo")
        .get()
    )


def confirmar_solicitud(solicitud, actor):
    region = validar_cuenta_almacen(actor)
    if solicitud.region_id != region.pk:
        raise SolicitudNoExiste

    with transaction.atomic():
        bloqueada = (
            SolicitudAsignacion.objects.select_for_update()
            .select_related("tenant", "region")
            .get(pk=solicitud.pk)
        )
        if bloqueada.estado != EstadoSolicitud.ENVIADA:
            raise EstadoSolicitudInvalido(
                "Solo se pueden confirmar solicitudes enviadas"
            )

        try:
            actualizar_stock_confirmacion_asignacion(bloqueada, actor)
        except (StockInsuficiente, ConfirmacionStockInvalida) as exc:
            raise EstadoSolicitudInvalido(str(exc)) from exc

        bloqueada.estado = EstadoSolicitud.CONFIRMADA
        bloqueada.confirmada_en = timezone.now()
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "estado",
                "confirmada_en",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "SolicitudAsignacion",
            bloqueada.pk,
            "estado",
            EstadoSolicitud.ENVIADA,
            EstadoSolicitud.CONFIRMADA,
            actor,
            tenant=bloqueada.tenant,
        )

    return bloqueada


def rechazar_solicitud(solicitud, motivo, actor):
    region = validar_cuenta_almacen(actor)
    if solicitud.region_id != region.pk:
        raise SolicitudNoExiste

    motivo = " ".join((motivo or "").split())
    if not motivo:
        raise MotivoRechazoInvalido("Debe indicar el motivo del rechazo")
    if len(motivo) > 1000:
        raise MotivoRechazoInvalido(
            "El motivo del rechazo no puede superar los 1000 caracteres"
        )

    with transaction.atomic():
        bloqueada = SolicitudAsignacion.objects.select_for_update().get(
            pk=solicitud.pk
        )
        if bloqueada.estado != EstadoSolicitud.ENVIADA:
            raise EstadoSolicitudInvalido(
                "Solo se pueden rechazar solicitudes enviadas"
            )

        serie_ids = list(
            bloqueada.lineas.filter(serie__isnull=False).values_list(
                "serie_id", flat=True
            )
        )
        series = list(
            Serie.objects.select_for_update()
            .filter(
                pk__in=serie_ids,
                estado=EstadoSerie.RESERVADA,
            )
            .order_by("id")
        )
        for serie in series:
            serie.estado = EstadoSerie.DISPONIBLE
            serie.actualizado_por = actor
            serie.save(
                update_fields=["estado", "actualizado_por", "actualizado_en"]
            )
            registrar_cambio(
                "Serie",
                serie.pk,
                "estado",
                EstadoSerie.RESERVADA,
                EstadoSerie.DISPONIBLE,
                actor,
                tenant=bloqueada.tenant,
            )

        bloqueada.estado = EstadoSolicitud.RECHAZADA
        bloqueada.motivo_rechazo = motivo
        bloqueada.rechazada_en = timezone.now()
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "estado",
                "motivo_rechazo",
                "rechazada_en",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "SolicitudAsignacion",
            bloqueada.pk,
            "estado",
            EstadoSolicitud.ENVIADA,
            EstadoSolicitud.RECHAZADA,
            actor,
            tenant=bloqueada.tenant,
        )

    return bloqueada


def ruta_absoluta_solicitud(solicitud):
    if not solicitud.excel_ruta:
        raise SolicitudNoExiste
    raiz = Path(settings.MEDIA_ROOT).resolve()
    ruta = (raiz / solicitud.excel_ruta).resolve()
    if raiz not in ruta.parents:
        raise SolicitudNoExiste
    return ruta


def verificar_archivo(solicitud):
    ruta = ruta_absoluta_solicitud(solicitud)
    if not ruta.exists():
        raise SolicitudNoExiste
    hash_actual = hashlib.sha256(ruta.read_bytes()).hexdigest()
    if hash_actual != solicitud.excel_hash:
        raise ArchivoAlterado
    return ruta


def enviar_correo_solicitud(solicitud_id, numero_intento=1):
    solicitud = SolicitudAsignacion.objects.filter(pk=solicitud_id).first()
    if solicitud is None:
        return None
    try:
        ruta = verificar_archivo(solicitud)
        almacen = solicitud.region.almacen
        envio = EnvioCorreo.objects.create(
            solicitud=solicitud,
            tenant=solicitud.tenant,
            region=solicitud.region,
            numero_intento=numero_intento,
            destinatario=almacen.buzon,
            archivo=solicitud.excel_ruta,
            hash_sha256=solicitud.excel_hash,
            estado=EnvioCorreo.ESTADO_REINTENTANDO,
        )
        mensaje = EmailMessage(
            subject=settings.ALMACEN_ALERTA_ASUNTO,
            body=(
                f"Solicitud de asignación {solicitud.pk} "
                f"del tenant {solicitud.tenant.codigo}."
            ),
            from_email=settings.ENVIOS_REMITENTE,
            to=[almacen.buzon],
        )
        mensaje.attach(
            f"asignacion-{solicitud.pk}.xlsx",
            ruta.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        mensaje.send(fail_silently=False)
    except Exception as exc:
        if "envio" in locals():
            envio.estado = EnvioCorreo.ESTADO_FALLIDO
            envio.error_mensaje = str(exc)[:500]
            envio.enviado_en = timezone.now()
            envio.save(update_fields=["estado", "error_mensaje", "enviado_en"])
        return None

    envio.estado = EnvioCorreo.ESTADO_EXITOSO
    envio.enviado_en = timezone.now()
    envio.save(update_fields=["estado", "enviado_en"])
    return envio


def ultimo_envio(solicitud):
    return solicitud.envios_correo.order_by("-numero_intento").first()


def envio_definitivo_fallido(solicitud):
    envios = list(solicitud.envios_correo.all())
    if any(envio.estado == EnvioCorreo.ESTADO_EXITOSO for envio in envios):
        return False
    return any(
        envio.numero_intento >= settings.ENVIOS_MAX_INTENTOS
        and envio.estado == EnvioCorreo.ESTADO_FALLIDO
        for envio in envios
    )


def historicos(actor, filtros=None):
    filtros = filtros or {}
    if actor.rol == Rol.ADMIN_PLATAFORMA:
        solicitudes = SolicitudAsignacion.objects.all()
    else:
        region = validar_cuenta_almacen(actor)
        solicitudes = SolicitudAsignacion.objects.filter(region=region)

    solicitudes = solicitudes.exclude(excel_ruta="")
    if filtros.get("estado"):
        solicitudes = solicitudes.filter(estado=filtros["estado"])
    if filtros.get("tenant"):
        solicitudes = solicitudes.filter(tenant_id=filtros["tenant"])
    if filtros.get("tecnico"):
        solicitudes = solicitudes.filter(lineas__tecnico_id=filtros["tecnico"]).distinct()
    return solicitudes.order_by("-fecha", "-id")
