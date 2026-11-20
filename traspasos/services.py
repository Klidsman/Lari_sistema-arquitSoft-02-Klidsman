"""Servicios de traspasos entre técnicos."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from acceso.models import Rol
from auditoria.services import registrar_cambio
from materiales.models import Material
from series.models import EstadoSerie, Serie
from stock.services import (
    StockInsuficiente,
    decrementar_stock_tecnico,
    incrementar_stock_tecnico,
    obtener_stock_tecnico,
)
from tecnicos.models import Tecnico

from .excel import generar_excel_traspaso
from .models import EstadoTraspaso, LineaTraspaso, SolicitudTraspaso


class PermisoDenegado(Exception):
    def __init__(self, mensaje="No tienes permiso para crear traspasos"):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class TraspasoNoExiste(Exception):
    mensaje = "El traspaso no existe"

    def __str__(self):
        return self.mensaje


class ValidacionTraspaso(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class EstadoTraspasoInvalido(ValidacionTraspaso):
    pass


class SerieNoAsignada(ValidacionTraspaso):
    pass


class CuadreIncorrecto(ValidacionTraspaso):
    def __init__(self, mensaje="Lo que sale debe cuadrar con lo que entra"):
        super().__init__(mensaje)


class ArchivoAlterado(ValidacionTraspaso):
    mensaje = "El archivo fue modificado, descarga bloqueada"

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)


@dataclass
class LineaValidada:
    material: Material
    serie: Serie | None
    cantidad: int
    lote: str


@dataclass(frozen=True)
class MovimientoTraspaso:
    material_id: int
    lote: str
    serie_id: int | None
    cantidad: int


@dataclass(frozen=True)
class CuadreTraspaso:
    salida: list[MovimientoTraspaso]
    entrada: list[MovimientoTraspaso]


def construir_movimientos(lineas):
    """Proyecta la lista canónica a los movimientos de salida y de entrada."""
    salida = [
        MovimientoTraspaso(
            material_id=linea.material.pk,
            lote=linea.lote,
            serie_id=linea.serie.pk if linea.serie else None,
            cantidad=linea.cantidad,
        )
        for linea in lineas
    ]
    return CuadreTraspaso(salida=list(salida), entrada=list(salida))


def _agrupar_movimientos(movimientos):
    totales = {}
    for movimiento in movimientos:
        clave = (movimiento.material_id, movimiento.lote, movimiento.serie_id)
        totales[clave] = totales.get(clave, 0) + movimiento.cantidad
    return totales


def validar_cuadre_traspaso(cuadre):
    if _agrupar_movimientos(cuadre.salida) != _agrupar_movimientos(
        cuadre.entrada
    ):
        raise CuadreIncorrecto()


def resumen_cuadre(lineas):
    resumen = {}
    for linea in lineas:
        datos = resumen.setdefault(
            linea.material.pk,
            {
                "material_id": linea.material.pk,
                "codigo": linea.material.codigo,
                "series": 0,
                "cantidad": 0,
            },
        )
        if linea.serie:
            datos["series"] += 1
        else:
            datos["cantidad"] += linea.cantidad
    return list(resumen.values())


def validar_cuenta_tenant(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol != Rol.USUARIO_TENANT or not actor.tenant_id:
        raise PermisoDenegado
    tenant = actor.tenant
    if tenant.estado != "ACTIVO":
        raise PermisoDenegado("El tenant está suspendido")
    return tenant


def validar_tecnicos(tenant, origen_id, destino_id):
    if origen_id == destino_id:
        raise ValidacionTraspaso(
            "El técnico origen y destino no pueden ser el mismo"
        )
    origen = Tecnico.objects.filter(pk=origen_id, tenant=tenant).first()
    destino = Tecnico.objects.filter(pk=destino_id, tenant=tenant).first()
    if origen is None or destino is None:
        raise ValidacionTraspaso("Los técnicos deben ser del mismo tenant")
    if not destino.activo:
        raise ValidacionTraspaso("El técnico destino no está activo")
    return origen, destino


def obtener_traspaso(tenant, traspaso_id):
    solicitud = SolicitudTraspaso.objects.filter(
        pk=traspaso_id, tenant=tenant
    ).first()
    if solicitud is None:
        raise TraspasoNoExiste
    return solicitud


def obtener_detalle_traspaso(tenant, traspaso_id):
    solicitud = obtener_traspaso(tenant, traspaso_id)
    return (
        SolicitudTraspaso.objects.filter(pk=solicitud.pk)
        .select_related("tenant", "region", "tecnico_origen", "tecnico_destino")
        .prefetch_related("lineas__material", "lineas__serie")
        .get()
    )


def listar_traspasos(tenant, estado=None):
    traspasos = SolicitudTraspaso.objects.filter(tenant=tenant)
    if estado:
        traspasos = traspasos.filter(estado=estado)
    return traspasos.order_by("-fecha", "-id")


def calcular_reservado(tecnico, material):
    from django.db.models import Q

    lineas = LineaTraspaso.objects.filter(
        tenant=tecnico.tenant,
        material=material,
        solicitud__estado=EstadoTraspaso.ENVIADA,
        solicitud__tecnico_origen=tecnico,
    ).filter(Q(serie__isnull=True) | Q(serie__tecnico=tecnico))
    return (
        lineas.filter(serie__isnull=True).aggregate(total=Sum("cantidad"))[
            "total"
        ]
        or 0
    ) + lineas.filter(serie__isnull=False).count()


def calcular_disponible(tecnico, material):
    return max(
        0,
        obtener_stock_tecnico(tecnico, material)
        - calcular_reservado(tecnico, material),
    )


def normalizar_lineas(tenant, origen, lineas):
    if not lineas:
        raise ValidacionTraspaso("El traspaso debe tener al menos una línea")

    resultado = []
    no_seriadas = {}
    series_vistas = set()

    for linea in lineas:
        material = Material.objects.filter(pk=linea.get("material_id")).first()
        if material is None:
            raise ValidacionTraspaso("El material no existe en el catálogo")
        if material.es_seriado:
            serie_ids = linea.get("serie_ids") or []
            if not serie_ids:
                raise ValidacionTraspaso("Debe indicar al menos una serie")
            series = list(
                Serie.objects.filter(
                    pk__in=serie_ids,
                    tenant=tenant,
                    material=material,
                    estado=EstadoSerie.ASIGNADA,
                    tecnico=origen,
                ).order_by("id")
            )
            if len(series) != len(set(serie_ids)):
                raise SerieNoAsignada(
                    "La serie no está asignada al técnico origen"
                )
            for serie in series:
                if serie.pk in series_vistas:
                    raise ValidacionTraspaso(
                        "La serie está duplicada en el traspaso"
                    )
                series_vistas.add(serie.pk)
                if LineaTraspaso.objects.filter(
                    serie=serie,
                    solicitud__estado=EstadoTraspaso.ENVIADA,
                ).exists():
                    raise ValidacionTraspaso(
                        "La serie está reservada en otro traspaso"
                    )
                resultado.append(
                    LineaValidada(
                        material=material,
                        serie=serie,
                        cantidad=1,
                        lote=material.lote,
                    )
                )
        else:
            if linea.get("serie_ids"):
                raise ValidacionTraspaso(
                    "El material no es seriado y no admite series"
                )
            try:
                cantidad = int(linea.get("cantidad"))
            except (TypeError, ValueError) as exc:
                raise ValidacionTraspaso(
                    "La cantidad debe ser un número entero"
                ) from exc
            if cantidad <= 0:
                raise ValidacionTraspaso("La cantidad debe ser mayor a 0")
            if cantidad > calcular_disponible(origen, material):
                raise ValidacionTraspaso(
                    "La cantidad supera el stock del técnico"
                )
            if material.pk in no_seriadas:
                no_seriadas[material.pk].cantidad += cantidad
            else:
                no_seriadas[material.pk] = LineaValidada(
                    material=material,
                    serie=None,
                    cantidad=cantidad,
                    lote=material.lote,
                )

    resultado.extend(no_seriadas.values())
    return resultado


def _auditar_alta(solicitud, actor):
    registrar_cambio(
        "SolicitudTraspaso",
        solicitud.pk,
        "alta",
        "",
        f"origen={solicitud.tecnico_origen.nif}; destino={solicitud.tecnico_destino.nif}; "
        f"estado={solicitud.estado}",
        actor,
        tenant=solicitud.tenant,
    )


def crear_borrador_traspaso(tenant, origen_id, destino_id, fecha, lineas, actor):
    tenant = validar_cuenta_tenant(actor)
    origen, destino = validar_tecnicos(tenant, origen_id, destino_id)
    if isinstance(fecha, str):
        fecha = parse_date(fecha)
    if fecha is None:
        raise ValidacionTraspaso("La fecha es obligatoria")
    lineas_validadas = normalizar_lineas(tenant, origen, lineas)
    validar_cuadre_traspaso(construir_movimientos(lineas_validadas))

    with transaction.atomic():
        solicitud = SolicitudTraspaso.objects.create(
            tenant=tenant,
            region=tenant.region,
            tecnico_origen=origen,
            tecnico_destino=destino,
            fecha=fecha,
            estado=EstadoTraspaso.BORRADOR,
            creado_por=actor,
        )
        for linea in lineas_validadas:
            LineaTraspaso.objects.create(
                tenant=tenant,
                solicitud=solicitud,
                material=linea.material,
                lote=linea.lote,
                serie=linea.serie,
                cantidad=linea.cantidad,
            )
        _auditar_alta(solicitud, actor)
    return solicitud


def actualizar_borrador_traspaso(solicitud, origen_id, destino_id, fecha, lineas, actor):
    tenant = validar_cuenta_tenant(actor)
    if solicitud.tenant_id != tenant.pk:
        raise TraspasoNoExiste
    if solicitud.estado != EstadoTraspaso.BORRADOR:
        raise EstadoTraspasoInvalido(
            "Solo se pueden editar traspasos en borrador"
        )
    origen, destino = validar_tecnicos(tenant, origen_id, destino_id)
    if isinstance(fecha, str):
        fecha = parse_date(fecha)
    lineas_validadas = normalizar_lineas(tenant, origen, lineas)
    validar_cuadre_traspaso(construir_movimientos(lineas_validadas))
    with transaction.atomic():
        bloqueada = SolicitudTraspaso.objects.select_for_update().get(
            pk=solicitud.pk
        )
        bloqueada.lineas.all().delete()
        bloqueada.tecnico_origen = origen
        bloqueada.tecnico_destino = destino
        bloqueada.fecha = fecha
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "tecnico_origen",
                "tecnico_destino",
                "fecha",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        for linea in lineas_validadas:
            LineaTraspaso.objects.create(
                tenant=tenant,
                solicitud=bloqueada,
                material=linea.material,
                lote=linea.lote,
                serie=linea.serie,
                cantidad=linea.cantidad,
            )
    return bloqueada


def enviar_traspaso(solicitud, actor):
    tenant = validar_cuenta_tenant(actor)
    with transaction.atomic():
        bloqueada = SolicitudTraspaso.objects.select_for_update().get(
            pk=solicitud.pk
        )
        if bloqueada.tenant_id != tenant.pk:
            raise TraspasoNoExiste
        if bloqueada.estado != EstadoTraspaso.BORRADOR:
            raise EstadoTraspasoInvalido(
                "Solo se pueden enviar traspasos en borrador"
            )
        ruta, hash_archivo = generar_excel_traspaso(bloqueada)
        bloqueada.excel_ruta = ruta
        bloqueada.excel_hash = hash_archivo
        bloqueada.estado = EstadoTraspaso.ENVIADA
        bloqueada.enviada_en = timezone.now()
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "excel_ruta",
                "excel_hash",
                "estado",
                "enviada_en",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "SolicitudTraspaso",
            bloqueada.pk,
            "estado",
            EstadoTraspaso.BORRADOR,
            EstadoTraspaso.ENVIADA,
            actor,
            tenant=tenant,
        )
    return bloqueada


def confirmar_traspaso(solicitud, actor):
    from asignaciones.almacen_services import validar_cuenta_almacen

    region = validar_cuenta_almacen(actor)
    if solicitud.region_id != region.pk:
        raise TraspasoNoExiste

    with transaction.atomic():
        bloqueada = SolicitudTraspaso.objects.select_for_update().get(
            pk=solicitud.pk
        )
        if bloqueada.estado != EstadoTraspaso.ENVIADA:
            raise EstadoTraspasoInvalido(
                "Solo se pueden confirmar traspasos enviados"
            )
        lineas = list(bloqueada.lineas.select_related("material", "serie"))
        series = [
            linea.serie for linea in lineas if linea.serie_id
        ]
        for serie in series:
            if (
                serie.estado != EstadoSerie.ASIGNADA
                or serie.tecnico_id != bloqueada.tecnico_origen_id
            ):
                raise SerieNoAsignada(
                    "La serie no está asignada al técnico origen"
                )

        validar_cuadre_traspaso(construir_movimientos(lineas))
        cantidades = {}
        for linea in lineas:
            cantidad = 1 if linea.serie_id else linea.cantidad
            cantidades[linea.material_id] = (
                cantidades.get(linea.material_id, 0) + cantidad
            )

        for material_id, cantidad in cantidades.items():
            material = Material.objects.get(pk=material_id)
            try:
                decrementar_stock_tecnico(
                    bloqueada.tecnico_origen, material, cantidad, actor
                )
            except StockInsuficiente as exc:
                raise ValidacionTraspaso(
                    "El técnico no tiene suficiente stock"
                ) from exc
            incrementar_stock_tecnico(
                bloqueada.tecnico_destino, material, cantidad, actor
            )

        ahora = timezone.now()
        for serie in series:
            serie.tecnico = bloqueada.tecnico_destino
            serie.asignada_en = ahora
            serie.actualizado_por = actor
            serie.save(
                update_fields=[
                    "tecnico",
                    "asignada_en",
                    "actualizado_por",
                    "actualizado_en",
                ]
            )
            registrar_cambio(
                "Serie",
                serie.pk,
                "tecnico",
                bloqueada.tecnico_origen_id,
                bloqueada.tecnico_destino_id,
                actor,
                tenant=bloqueada.tenant,
            )

        bloqueada.estado = EstadoTraspaso.CONFIRMADA
        bloqueada.confirmada_en = ahora
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
            "SolicitudTraspaso",
            bloqueada.pk,
            "estado",
            EstadoTraspaso.ENVIADA,
            EstadoTraspaso.CONFIRMADA,
            actor,
            tenant=bloqueada.tenant,
        )
    return bloqueada


def rechazar_traspaso(solicitud, motivo, actor):
    from asignaciones.almacen_services import validar_cuenta_almacen

    region = validar_cuenta_almacen(actor)
    if solicitud.region_id != region.pk:
        raise TraspasoNoExiste
    motivo = " ".join((motivo or "").split())
    if not motivo:
        raise ValidacionTraspaso("El motivo de rechazo es obligatorio")
    if len(motivo) > 1000:
        raise ValidacionTraspaso(
            "El motivo del rechazo no puede superar los 1000 caracteres"
        )
    with transaction.atomic():
        bloqueada = SolicitudTraspaso.objects.select_for_update().get(
            pk=solicitud.pk
        )
        if bloqueada.estado != EstadoTraspaso.ENVIADA:
            raise EstadoTraspasoInvalido(
                "Solo se pueden rechazar traspasos enviados"
            )
        bloqueada.estado = EstadoTraspaso.RECHAZADA
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
            "SolicitudTraspaso",
            bloqueada.pk,
            "estado",
            EstadoTraspaso.ENVIADA,
            EstadoTraspaso.RECHAZADA,
            actor,
            tenant=bloqueada.tenant,
        )
    return bloqueada


def cancelar_traspaso(solicitud, actor):
    tenant = validar_cuenta_tenant(actor)
    with transaction.atomic():
        bloqueada = SolicitudTraspaso.objects.select_for_update().get(
            pk=solicitud.pk
        )
        if bloqueada.tenant_id != tenant.pk:
            raise TraspasoNoExiste
        if bloqueada.estado != EstadoTraspaso.BORRADOR:
            raise EstadoTraspasoInvalido(
                "Solo se pueden cancelar traspasos en borrador"
            )
        bloqueada.estado = EstadoTraspaso.CANCELADA
        bloqueada.cancelada_en = timezone.now()
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "estado",
                "cancelada_en",
                "actualizado_por",
                "actualizado_en",
            ]
        )
    return bloqueada


def verificar_excel(solicitud):
    if not solicitud.excel_ruta:
        raise TraspasoNoExiste
    raiz = Path(settings.MEDIA_ROOT).resolve()
    ruta = (raiz / solicitud.excel_ruta).resolve()
    if raiz not in ruta.parents or not ruta.exists():
        raise TraspasoNoExiste
    if hashlib.sha256(ruta.read_bytes()).hexdigest() != solicitud.excel_hash:
        raise ArchivoAlterado
    return ruta


# Alias con los nombres del contrato `contracts/servicios-traspaso.md`.
# Conservan las firmas actuales (ids de técnico/material) para no romper
# vistas ni pruebas; el código futuro puede usar estos nombres sin duplicar
# lógica.
crear_solicitud_traspaso = crear_borrador_traspaso
actualizar_lineas_borrador = actualizar_borrador_traspaso
enviar_solicitud_traspaso = enviar_traspaso


def verificar_hash_excel(solicitud, contenido=None):
    if contenido is not None:
        if (
            hashlib.sha256(contenido).hexdigest()
            != solicitud.excel_hash
        ):
            raise ArchivoAlterado
    return verificar_excel(solicitud)


def series_para_tecnico(tenant, tecnico, material=None, q=""):
    series = Serie.objects.filter(
        tenant=tenant,
        tecnico=tecnico,
        estado=EstadoSerie.ASIGNADA,
    )
    if material is not None:
        series = series.filter(material=material)
    q = (q or "").strip()
    if q:
        series = series.filter(numero__icontains=q)
    return series.order_by("numero")


def validar_disponibilidad(tecnico, material, cantidad=None, series=None):
    disponible = calcular_disponible(tecnico, material)
    reservado = calcular_reservado(tecnico, material)
    errores = []
    if material.es_seriado:
        for serie in series or []:
            if serie.tecnico_id != tecnico.pk or serie.estado != EstadoSerie.ASIGNADA:
                errores.append("La serie no está asignada al técnico origen")
    elif cantidad is not None and int(cantidad) > disponible:
        errores.append("La cantidad supera el stock del técnico")
    return {
        "valido": not errores,
        "disponible": disponible,
        "reservado": reservado,
        "errores": errores,
    }
