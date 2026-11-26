"""Servicios del almacén sobre solicitudes de asignación (007)."""

import hashlib
import logging
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from acceso.models import Rol, Usuario
from auditoria.services import registrar_cambio
from series.models import EstadoSerie, Serie
from stock.services import (
    ConfirmacionStockInvalida,
    StockInsuficiente,
    actualizar_stock_confirmacion_asignacion,
)

from .models import EnvioCorreo, EstadoSolicitud, SolicitudAsignacion

logger = logging.getLogger(__name__)


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
        transaction.on_commit(
            lambda: __import__(
                "asignaciones.notificaciones",
                fromlist=["publicar_cambio_estado"],
            ).publicar_cambio_estado(
                bloqueada,
                EstadoSolicitud.ENVIADA,
                EstadoSolicitud.CONFIRMADA,
            )
        )

    return bloqueada


def _notificar_tenant_rechazo(solicitud):
    """Avisa a la cuenta activa del tenant que la solicitud fue rechazada."""
    usuario = (
        Usuario.objects.filter(
            tenant=solicitud.tenant,
            rol=Rol.USUARIO_TENANT,
            is_active=True,
        )
        .order_by("pk")
        .first()
    )
    if usuario is None:
        return
    try:
        send_mail(
            subject=f"Solicitud de asignación #{solicitud.pk} rechazada",
            message=(
                f"La solicitud de asignación #{solicitud.pk} del tenant "
                f"{solicitud.tenant.codigo} fue rechazada.\n\n"
                f"Motivo: {solicitud.motivo_rechazo}\n\n"
                f"Revisa el detalle en {settings.BASE_URL.rstrip('/')}"
                f"/asignaciones/{solicitud.pk}/\n"
            ),
            from_email=settings.ENVIOS_REMITENTE,
            recipient_list=[usuario.email],
            fail_silently=True,
        )
    except Exception:
        logger.warning(
            "No se pudo avisar el rechazo al tenant",
            exc_info=True,
        )


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
        transaction.on_commit(
            lambda: _notificar_tenant_rechazo(bloqueada)
        )
        transaction.on_commit(
            lambda: __import__(
                "asignaciones.notificaciones",
                fromlist=["publicar_cambio_estado"],
            ).publicar_cambio_estado(
                bloqueada,
                EstadoSolicitud.ENVIADA,
                EstadoSolicitud.RECHAZADA,
            )
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


class ErrorEnvioCorreo(Exception):
    """Error de negocio del envío, con mensaje apto para EnvioCorreo."""

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self):
        return self.mensaje


def _almacen_de(solicitud):
    try:
        almacen = solicitud.region.almacen
    except Exception:
        return None
    return almacen


def _buzon_de(solicitud, obligatorio=True):
    almacen = _almacen_de(solicitud)
    if almacen is None or not almacen.activo:
        if obligatorio:
            raise ErrorEnvioCorreo("El almacén de la región no está activo")
        return ""
    if not almacen.buzon:
        if obligatorio:
            raise ErrorEnvioCorreo("El buzón del almacén no está configurado")
        return ""
    return almacen.buzon


def _crear_intento(solicitud, numero_intento):
    """Crea el intento una sola vez; si ya existe, devuelve el existente."""
    existente = EnvioCorreo.objects.filter(
        solicitud=solicitud,
        numero_intento=numero_intento,
    ).first()
    if existente is not None:
        return existente

    try:
        return EnvioCorreo.objects.create(
            solicitud=solicitud,
            tenant=solicitud.tenant,
            region=solicitud.region,
            numero_intento=numero_intento,
            destinatario=_buzon_de(solicitud, obligatorio=False),
            archivo=solicitud.excel_ruta,
            hash_sha256=solicitud.excel_hash,
            estado=EnvioCorreo.ESTADO_REINTENTANDO,
        )
    except IntegrityError:
        return EnvioCorreo.objects.get(
            solicitud=solicitud,
            numero_intento=numero_intento,
        )


def _actor_de(solicitud):
    return solicitud.actualizado_por or solicitud.creado_por


def _cerrar(envio, solicitud, estado, error_mensaje=""):
    anterior = envio.estado
    envio.estado = estado
    envio.error_mensaje = (error_mensaje or "")[:500]
    envio.enviado_en = timezone.now()
    with transaction.atomic():
        envio.save(update_fields=["estado", "error_mensaje", "enviado_en"])
        registrar_cambio(
            "EnvioCorreo",
            envio.pk,
            "estado",
            anterior,
            estado,
            _actor_de(solicitud),
            tenant=solicitud.tenant,
        )
    return envio


def _mensaje_error(exc):
    if isinstance(exc, (SolicitudNoExiste, ArchivoAlterado)):
        return "El archivo del Excel no está disponible o fue modificado"
    if isinstance(exc, ErrorEnvioCorreo):
        return exc.mensaje
    return str(exc)[:500]


def _cuerpo_correo(solicitud):
    from .services import totales_solicitud

    totales = totales_solicitud(solicitud)
    return (
        f"Solicitud de asignación {solicitud.pk} del tenant "
        f"{solicitud.tenant.codigo}.\n"
        f"Fecha: {solicitud.fecha.isoformat()}\n"
        f"Técnicos: {solicitud.nifs_tecnicos or '—'}\n"
        f"Líneas: {totales['total_lineas']} · "
        f"Series: {totales['total_series']} · "
        f"Cantidad: {totales['total_cantidad']}\n\n"
        "Revisa la solicitud en la bandeja de despachos del almacén."
    )


def _enviar_correo(solicitud, envio):
    buzon = _buzon_de(solicitud)
    ruta = verificar_archivo(solicitud)
    mensaje = EmailMessage(
        subject=(
            f"{settings.ALMACEN_ALERTA_ASUNTO} "
            f"#{solicitud.pk} · {solicitud.tenant.codigo}"
        ),
        body=_cuerpo_correo(solicitud),
        from_email=settings.ENVIOS_REMITENTE,
        to=[buzon],
    )
    mensaje.attach(
        f"asignacion-{solicitud.pk}.xlsx",
        ruta.read_bytes(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    mensaje.send(fail_silently=False)


def _notificar_tenant_fallo(solicitud, envio):
    usuario = (
        Usuario.objects.filter(
            tenant=solicitud.tenant,
            rol=Rol.USUARIO_TENANT,
            is_active=True,
        )
        .order_by("pk")
        .first()
    )
    if usuario is None:
        return
    try:
        send_mail(
            subject=(
                f"No se pudo enviar la solicitud {solicitud.pk} al almacén"
            ),
            message=(
                f"El envío de la solicitud {solicitud.pk} al almacén no se "
                f"pudo completar después de {envio.numero_intento} intentos. "
                "La solicitud sigue disponible en tu bandeja para revisión."
            ),
            from_email=settings.ENVIOS_REMITENTE,
            recipient_list=[usuario.email],
            fail_silently=True,
        )
    except Exception:
        pass


def _programar_siguiente(solicitud, numero_intento):
    siguiente = _crear_intento(solicitud, numero_intento)
    if siguiente.estado != EnvioCorreo.ESTADO_REINTENTANDO:
        return siguiente

    try:
        from .tasks import enviar_excel_solicitud

        enviar_excel_solicitud.apply_async(
            args=[solicitud.pk, numero_intento],
            countdown=settings.ENVIOS_INTERVALO_REINTENTO_SEGUNDOS,
        )
    except Exception:
        _cerrar(
            siguiente,
            solicitud,
            EnvioCorreo.ESTADO_FALLIDO,
            "No se pudo programar el envío del correo",
        )
        _notificar_tenant_fallo(solicitud, siguiente)

    return siguiente


def programar_envio_solicitud(solicitud_id):
    """Crea el intento 1 y encola el envío. Idempotente."""
    solicitud = (
        SolicitudAsignacion.objects.select_related("tenant", "region")
        .filter(pk=solicitud_id)
        .first()
    )
    if solicitud is None or solicitud.estado != EstadoSolicitud.ENVIADA:
        return None

    if not solicitud.excel_ruta or not solicitud.excel_hash:
        envio = _crear_intento(solicitud, 1)
        if envio.estado == EnvioCorreo.ESTADO_REINTENTANDO:
            _cerrar(
                envio,
                solicitud,
                EnvioCorreo.ESTADO_FALLIDO,
                "El archivo del Excel no está disponible o fue modificado",
            )
        _notificar_tenant_fallo(solicitud, envio)
        return envio

    envio = _crear_intento(solicitud, 1)
    if envio.estado != EnvioCorreo.ESTADO_REINTENTANDO:
        return envio

    try:
        from .tasks import enviar_excel_solicitud

        enviar_excel_solicitud.apply_async(args=[solicitud.pk, 1])
    except Exception:
        _cerrar(
            envio,
            solicitud,
            EnvioCorreo.ESTADO_FALLIDO,
            "No se pudo programar el envío del correo",
        )
        _notificar_tenant_fallo(solicitud, envio)

    return envio


def encolar_envio_solicitud(solicitud_id):
    """Encola el intento 1; si el broker falla, deja el intento fallido."""
    try:
        from .tasks import programar_envio_solicitud as tarea_programar

        tarea_programar.delay(solicitud_id)
    except Exception:
        registrar_fallo_programacion(solicitud_id)


def registrar_fallo_programacion(solicitud_id):
    solicitud = (
        SolicitudAsignacion.objects.select_related("tenant", "region")
        .filter(pk=solicitud_id)
        .first()
    )
    if solicitud is None or solicitud.estado != EstadoSolicitud.ENVIADA:
        return None

    envio = _crear_intento(solicitud, 1)
    if envio.estado == EnvioCorreo.ESTADO_REINTENTANDO:
        _cerrar(
            envio,
            solicitud,
            EnvioCorreo.ESTADO_FALLIDO,
            "No se pudo programar el envío del correo",
        )
        _notificar_tenant_fallo(solicitud, envio)
    return envio


def procesar_envio_solicitud(solicitud_id, numero_intento):
    """Ejecuta un intento, lo cierra y reprograma o notifica."""
    solicitud = (
        SolicitudAsignacion.objects.select_related("tenant", "region")
        .filter(pk=solicitud_id)
        .first()
    )
    if solicitud is None or solicitud.estado != EstadoSolicitud.ENVIADA:
        return None

    envio = _crear_intento(solicitud, numero_intento)
    if envio.estado != EnvioCorreo.ESTADO_REINTENTANDO:
        return envio

    try:
        _enviar_correo(solicitud, envio)
    except Exception as exc:
        _cerrar(
            envio,
            solicitud,
            EnvioCorreo.ESTADO_FALLIDO,
            _mensaje_error(exc),
        )
        if numero_intento < settings.ENVIOS_MAX_INTENTOS:
            _programar_siguiente(solicitud, numero_intento + 1)
        else:
            _notificar_tenant_fallo(solicitud, envio)
    else:
        _cerrar(envio, solicitud, EnvioCorreo.ESTADO_EXITOSO)

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
