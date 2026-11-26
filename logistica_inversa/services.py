"""Servicios de logística inversa."""

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from acceso.models import Rol
from auditoria.services import registrar_cambio
from materiales.models import Material
from series.models import EstadoSerie, Serie
from stock.services import (
    decrementar_stock_general,
    decrementar_stock_tecnico,
    incrementar_stock_general,
)
from tecnicos.models import Tecnico

from .acta import generar_acta
from .models import BajaEquipo, CausaBaja, Devolucion, LineaDevolucion


class ErrorLogistica(Exception):
    mensaje = "Error de logística inversa"

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)

    def __str__(self):
        return self.args[0]


class PermisoDenegado(ErrorLogistica):
    mensaje = "No tienes permiso para registrar devoluciones"


class TecnicoNoExiste(ErrorLogistica):
    mensaje = "El técnico no existe o no pertenece al tenant"


class SerieNoEnTecnico(ErrorLogistica):
    mensaje = "La serie no está asignada al técnico"


class SerieNoDisponible(ErrorLogistica):
    mensaje = "La serie no está disponible para la baja"


class SerieReservada(ErrorLogistica):
    mensaje = "La serie está reservada en otro traspaso"


class SerieYaInactiva(ErrorLogistica):
    mensaje = "La serie ya fue dada de baja"


class SerieInstalada(ErrorLogistica):
    mensaje = (
        "La serie está instalada y no puede devolverse ni darse de baja"
    )


class SerieFueraTenant(ErrorLogistica):
    mensaje = "La serie no pertenece a este tenant"


class CausaRequerida(ErrorLogistica):
    mensaje = "Debe indicar la causa de la baja"


class CausaInvalida(ErrorLogistica):
    mensaje = "La causa de la baja no es válida"


class FechaInvalida(ErrorLogistica):
    mensaje = "La fecha de devolución no es válida"


class SinSeries(ErrorLogistica):
    mensaje = "Debe seleccionar al menos una serie"


class NoEncontrado(ErrorLogistica):
    mensaje = "La devolución no existe"


class BajaNoEncontrada(ErrorLogistica):
    mensaje = "La baja no existe"


class ArchivoNoDisponible(ErrorLogistica):
    mensaje = "El acta no está disponible"


class HashNoCoincide(ErrorLogistica):
    mensaje = "El acta fue modificada, descarga bloqueada"


def validar_cuenta_tenant(actor, tenant=None):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol != Rol.USUARIO_TENANT or not actor.tenant_id:
        raise PermisoDenegado
    propio = actor.tenant
    if tenant is not None and tenant.pk != propio.pk:
        raise PermisoDenegado
    if propio.estado != "ACTIVO":
        raise PermisoDenegado("El tenant está suspendido")
    return propio


def validar_tecnico(tenant, tecnico):
    if tecnico is None or not getattr(tecnico, "pk", None):
        raise TecnicoNoExiste
    fila = Tecnico.objects.filter(pk=tecnico.pk, tenant=tenant).first()
    if fila is None or fila.tenant.region_id != tenant.region_id:
        raise TecnicoNoExiste
    return fila


def validar_fecha_devolucion(fecha):
    if isinstance(fecha, str):
        fecha = parse_date(fecha)
    if not isinstance(fecha, date):
        raise FechaInvalida
    if fecha > date.today():
        raise FechaInvalida
    return fecha


def _reservada_en_traspaso(serie):
    from traspasos.models import EstadoTraspaso, LineaTraspaso

    return LineaTraspaso.objects.filter(
        serie=serie, solicitud__estado=EstadoTraspaso.ENVIADA
    ).exists()


def validar_serie_para_devolucion(serie, tecnico):
    if serie.tenant_id != tecnico.tenant_id:
        raise SerieFueraTenant
    if serie.estado == EstadoSerie.INACTIVA:
        raise SerieYaInactiva
    if serie.estado == EstadoSerie.INSTALADA:
        raise SerieInstalada
    if serie.estado == EstadoSerie.RESERVADA:
        raise SerieReservada
    if (
        serie.estado != EstadoSerie.ASIGNADA
        or serie.tecnico_id != tecnico.pk
    ):
        raise SerieNoEnTecnico
    if _reservada_en_traspaso(serie):
        raise SerieReservada
    return serie


def validar_serie_para_baja(serie, tenant):
    if serie.tenant_id != tenant.pk:
        raise SerieFueraTenant
    if serie.estado == EstadoSerie.INACTIVA:
        raise SerieYaInactiva
    if serie.estado == EstadoSerie.INSTALADA:
        raise SerieInstalada
    if serie.estado == EstadoSerie.RESERVADA:
        raise SerieReservada
    if serie.estado == EstadoSerie.ASIGNADA:
        if serie.tecnico_id is None or serie.asignada_en is None:
            raise SerieNoDisponible
        if _reservada_en_traspaso(serie):
            raise SerieReservada
        return serie
    if serie.estado == EstadoSerie.DISPONIBLE:
        if serie.tecnico_id is not None or serie.asignada_en is not None:
            raise SerieNoDisponible
        return serie
    raise SerieNoDisponible


def _resolver_series(tenant, series):
    resultado = []
    vistos = set()
    for serie in series:
        if isinstance(serie, Serie):
            fila = serie
        else:
            fila = Serie.objects.filter(pk=serie, tenant=tenant).first()
        if fila is None:
            raise SerieFueraTenant
        if fila.pk in vistos:
            continue
        vistos.add(fila.pk)
        resultado.append(fila)
    if not resultado:
        raise SinSeries
    return resultado


def _auditar_serie(serie, anterior_estado, anterior_tecnico, anterior_fecha, actor, tenant):
    registrar_cambio(
        "Serie",
        serie.pk,
        "estado",
        anterior_estado,
        serie.estado,
        actor,
        tenant=tenant,
    )
    registrar_cambio(
        "Serie",
        serie.pk,
        "tecnico",
        anterior_tecnico,
        "",
        actor,
        tenant=tenant,
    )
    registrar_cambio(
        "Serie",
        serie.pk,
        "asignada_en",
        anterior_fecha,
        "",
        actor,
        tenant=tenant,
    )


def registrar_devolucion(
    tenant, tecnico, fecha, series, observaciones, actor
):
    tenant = validar_cuenta_tenant(actor, tenant)
    tecnico = validar_tecnico(tenant, tecnico)
    fecha = validar_fecha_devolucion(fecha)
    series = _resolver_series(tenant, series)
    for serie in series:
        validar_serie_para_devolucion(serie, tecnico)

    ruta_acta = ""
    try:
        with transaction.atomic():
            list(
                Serie.objects.select_for_update()
                .filter(pk__in=[serie.pk for serie in series])
                .order_by("pk")
            )
            for serie in series:
                serie.refresh_from_db()
                validar_serie_para_devolucion(serie, tecnico)

            devolucion = Devolucion.objects.create(
                tenant=tenant,
                region=tenant.region,
                tecnico=tecnico,
                fecha=fecha,
                observaciones=" ".join((observaciones or "").split()),
                creado_por=actor,
            )
            for serie in series:
                LineaDevolucion.objects.create(
                    tenant=tenant,
                    devolucion=devolucion,
                    serie=serie,
                    material=serie.material,
                    descripcion=serie.material.descripcion,
                    lote=serie.lote,
                )

            cantidades = {}
            for serie in series:
                cantidades[serie.material_id] = (
                    cantidades.get(serie.material_id, 0) + 1
                )
                anterior_estado = serie.estado
                anterior_tecnico = serie.tecnico_id
                anterior_fecha = serie.asignada_en
                serie.estado = EstadoSerie.DISPONIBLE
                serie.tecnico = None
                serie.asignada_en = None
                serie.actualizado_por = actor
                serie.save(
                    update_fields=[
                        "estado",
                        "tecnico",
                        "asignada_en",
                        "actualizado_por",
                        "actualizado_en",
                    ]
                )
                _auditar_serie(
                    serie,
                    anterior_estado,
                    anterior_tecnico,
                    anterior_fecha,
                    actor,
                    tenant,
                )

            for material_id, cantidad in cantidades.items():
                material = Material.objects.get(pk=material_id)
                decrementar_stock_tecnico(
                    tecnico, material, cantidad, actor
                )
                incrementar_stock_general(
                    tenant, material, cantidad, actor
                )

            ruta_acta, hash_acta = generar_acta(devolucion)
            devolucion.acta_ruta = ruta_acta
            devolucion.acta_hash = hash_acta
            devolucion.acta_generada_en = timezone.now()
            devolucion.save(
                update_fields=[
                    "acta_ruta",
                    "acta_hash",
                    "acta_generada_en",
                ]
            )
            registrar_cambio(
                "Devolucion",
                devolucion.pk,
                "alta",
                "",
                f"tecnico={tecnico.nif}; series={len(series)}; fecha={fecha}",
                actor,
                tenant=tenant,
            )
            for linea in devolucion.lineas.select_related("serie", "material"):
                registrar_cambio(
                    "LineaDevolucion",
                    linea.pk,
                    "alta",
                    "",
                    f"{linea.serie.numero}; {linea.material.codigo}",
                    actor,
                    tenant=tenant,
                )
            registrar_cambio(
                "Devolucion",
                devolucion.pk,
                "acta",
                "",
                ruta_acta,
                actor,
                tenant=tenant,
            )
    except Exception:
        if ruta_acta:
            (Path(settings.MEDIA_ROOT) / ruta_acta).unlink(missing_ok=True)
        raise
    return devolucion


def registrar_baja_equipo(tenant, serie, causa, observaciones, actor):
    tenant = validar_cuenta_tenant(actor, tenant)
    causa = (causa or "").strip().upper()
    if not causa:
        raise CausaRequerida
    if causa not in CausaBaja.values:
        raise CausaInvalida
    if serie is None or not getattr(serie, "pk", None):
        raise SerieFueraTenant
    serie = Serie.objects.filter(pk=serie.pk, tenant=tenant).first()
    if serie is None:
        raise SerieFueraTenant
    validar_serie_para_baja(serie, tenant)

    with transaction.atomic():
        serie = (
            Serie.objects.select_for_update().filter(pk=serie.pk).first()
        )
        if serie is None:
            raise SerieFueraTenant
        validar_serie_para_baja(serie, tenant)
        anterior_estado = serie.estado
        anterior_tecnico = serie.tecnico_id
        anterior_fecha = serie.asignada_en
        baja = BajaEquipo.objects.create(
            tenant=tenant,
            region=tenant.region,
            serie=serie,
            material=serie.material,
            causa=causa,
            observaciones=" ".join((observaciones or "").split()),
            creado_por=actor,
        )
        if anterior_estado == EstadoSerie.ASIGNADA:
            decrementar_stock_tecnico(
                serie.tecnico, serie.material, 1, actor
            )
        else:
            decrementar_stock_general(tenant, serie.material, 1, actor)

        serie.estado = EstadoSerie.INACTIVA
        serie.tecnico = None
        serie.asignada_en = None
        serie.actualizado_por = actor
        serie.save(
            update_fields=[
                "estado",
                "tecnico",
                "asignada_en",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        _auditar_serie(
            serie,
            anterior_estado,
            anterior_tecnico,
            anterior_fecha,
            actor,
            tenant,
        )
        registrar_cambio(
            "BajaEquipo",
            baja.pk,
            "alta",
            "",
            f"{serie.numero}; causa={causa}; obs={baja.observaciones}",
            actor,
            tenant=tenant,
        )
    return baja


def registrar_bajas_equipo(
    tenant, tecnico, series, causa, observaciones, actor
):
    """Registra la baja de varias series asignadas a un mismo técnico."""
    tenant = validar_cuenta_tenant(actor, tenant)
    tecnico = validar_tecnico(tenant, tecnico)
    causa = (causa or "").strip().upper()
    if not causa:
        raise CausaRequerida
    if causa not in CausaBaja.values:
        raise CausaInvalida
    series = _resolver_series(tenant, series)
    for serie in series:
        validar_serie_para_baja(serie, tenant)
        if (
            serie.estado != EstadoSerie.ASIGNADA
            or serie.tecnico_id != tecnico.pk
        ):
            raise SerieNoEnTecnico(
                "La serie no está asignada al técnico"
            )

    bajas = []
    with transaction.atomic():
        for serie in series:
            bajas.append(
                registrar_baja_equipo(
                    tenant, serie, causa, observaciones, actor
                )
            )
    return bajas


def registrar_baja_por_numero(tenant, numero, causa, observaciones, actor):
    tenant = validar_cuenta_tenant(actor, tenant)
    serie = Serie.objects.filter(
        numero=(numero or "").strip().upper(), tenant=tenant
    ).first()
    if serie is None:
        raise SerieFueraTenant
    return registrar_baja_equipo(tenant, serie, causa, observaciones, actor)


def verificar_hash_acta(devolucion, contenido=None):
    if not devolucion.acta_ruta:
        raise ArchivoNoDisponible
    raiz = Path(settings.MEDIA_ROOT).resolve()
    ruta = (raiz / devolucion.acta_ruta).resolve()
    if raiz not in ruta.parents or not ruta.exists():
        raise ArchivoNoDisponible
    datos = contenido if contenido is not None else ruta.read_bytes()
    if hashlib.sha256(datos).hexdigest() != devolucion.acta_hash:
        raise HashNoCoincide
    return ruta


def listar_devoluciones(tenant, fecha_desde=None, fecha_hasta=None):
    devoluciones = Devolucion.objects.filter(tenant=tenant).select_related(
        "tecnico"
    )
    if fecha_desde:
        devoluciones = devoluciones.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        devoluciones = devoluciones.filter(fecha__lte=fecha_hasta)
    return devoluciones.order_by("-fecha", "-id")


def obtener_devolucion(tenant, devolucion_id):
    devolucion = (
        Devolucion.objects.filter(pk=devolucion_id, tenant=tenant)
        .select_related("tecnico", "region")
        .prefetch_related("lineas__material", "lineas__serie")
        .first()
    )
    if devolucion is None:
        raise NoEncontrado
    return devolucion


def detalle_devolucion(devolucion):
    return devolucion.lineas.select_related("material", "serie").order_by(
        "serie__numero"
    )


def listar_bajas(tenant, causa=None):
    bajas = BajaEquipo.objects.filter(tenant=tenant).select_related(
        "serie", "material"
    )
    if causa:
        bajas = bajas.filter(causa=causa)
    return bajas.order_by("-creado_en", "-id")


def obtener_baja(tenant, baja_id):
    baja = (
        BajaEquipo.objects.filter(pk=baja_id, tenant=tenant)
        .select_related("serie", "material")
        .first()
    )
    if baja is None:
        raise BajaNoEncontrada
    return baja
