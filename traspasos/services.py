"""Servicios de traspasos entre técnicos (1→N / N→1)."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from acceso.models import Rol
from auditoria.services import registrar_cambio
from materiales.models import Material
from series.models import EstadoSerie, Serie
from stock.models import TipoMovimientoTecnico
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


class EstructuraTecnicosInvalida(ValidacionTraspaso):
    pass


class CuadreIncorrecto(ValidacionTraspaso):
    def __init__(self, mensaje="Lo que sale debe cuadrar con lo que entra"):
        super().__init__(mensaje)


class ArchivoAlterado(ValidacionTraspaso):
    mensaje = "El archivo fue modificado, descarga bloqueada"

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)


ESTADOS_RESERVA = (EstadoTraspaso.BORRADOR, EstadoTraspaso.ENVIADA)


@dataclass(frozen=True)
class StockTraspaso:
    material: Material
    stock: int
    reservado: int
    disponible: int


@dataclass
class LineaValidada:
    tecnico_origen: Tecnico
    tecnico_destino: Tecnico
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
    tecnico_origen_id: int
    tecnico_destino_id: int


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
            tecnico_origen_id=linea.tecnico_origen.pk,
            tecnico_destino_id=linea.tecnico_destino.pk,
        )
        for linea in lineas
    ]
    return CuadreTraspaso(salida=list(salida), entrada=list(salida))


def _agrupar_movimientos(movimientos):
    totales = {}
    for movimiento in movimientos:
        clave = (
            movimiento.material_id,
            movimiento.lote,
            movimiento.serie_id,
            movimiento.tecnico_origen_id,
            movimiento.tecnico_destino_id,
        )
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
        clave = (
            linea.tecnico_origen.pk,
            linea.tecnico_destino.pk,
            linea.material.pk,
        )
        datos = resumen.setdefault(
            clave,
            {
                "material_id": linea.material.pk,
                "codigo": linea.material.codigo,
                "origen": linea.tecnico_origen.nif,
                "destino": linea.tecnico_destino.nif,
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


def validar_estructura_tecnicos(lineas, tenant):
    """Exige al menos dos técnicos y que ninguna línea se entregue a sí misma."""
    tecnicos = {}
    for linea in lineas:
        origen = linea.tecnico_origen
        destino = linea.tecnico_destino
        if origen.tenant_id != tenant.pk or destino.tenant_id != tenant.pk:
            raise ValidacionTraspaso(
                "Los técnicos deben ser del mismo tenant"
            )
        if origen.pk == destino.pk:
            raise ValidacionTraspaso(
                "El técnico origen y destino no pueden ser el mismo"
            )
        if not destino.activo:
            raise ValidacionTraspaso("El técnico destino no está activo")
        tecnicos[origen.pk] = origen
        tecnicos[destino.pk] = destino

    if len(tecnicos) < 2:
        raise EstructuraTecnicosInvalida(
            "El traspaso debe implicar al menos dos técnicos distintos"
        )


def tecnicos_implicados(lineas):
    tecnicos = {}
    for linea in lineas:
        tecnicos[linea.tecnico_origen.pk] = linea.tecnico_origen
        tecnicos[linea.tecnico_destino.pk] = linea.tecnico_destino
    return list(tecnicos.values())


def revalidar_disponibilidad(lineas, solicitud=None):
    """Revalida series y cantidades de una solicitud antes de enviarla."""
    for linea in lineas:
        if not linea.serie_id:
            continue
        serie = linea.serie
        if (
            serie.estado != EstadoSerie.ASIGNADA
            or serie.tecnico_id != linea.tecnico_origen_id
        ):
            raise SerieNoAsignada(
                "La serie no está asignada al técnico origen"
            )
        reservada = LineaTraspaso.objects.filter(
            serie=serie,
            solicitud__estado__in=ESTADOS_RESERVA,
        )
        if solicitud is not None:
            reservada = reservada.exclude(solicitud=solicitud)
        if reservada.exists():
            raise ValidacionTraspaso(
                "La serie está reservada en otro traspaso"
            )

    totales = {}
    for linea in lineas:
        if linea.serie_id:
            continue
        clave = (linea.tecnico_origen.pk, linea.material.pk)
        totales[clave] = totales.get(clave, 0) + linea.cantidad
    for (origen_id, material_id), cantidad in totales.items():
        origen = Tecnico.objects.get(pk=origen_id)
        material = Material.objects.get(pk=material_id)
        if cantidad > calcular_disponible(origen, material, solicitud):
            raise ValidacionTraspaso(
                "La cantidad supera el stock del técnico"
            )


def revalidar_traspaso(solicitud):
    lineas = list(
        LineaTraspaso.objects.filter(solicitud=solicitud).select_related(
            "material", "serie", "tecnico_origen", "tecnico_destino"
        )
    )
    validar_estructura_tecnicos(lineas, solicitud.tenant)
    revalidar_disponibilidad(lineas, solicitud)
    validar_cuadre_traspaso(construir_movimientos(lineas))


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
        .select_related("tenant", "region")
        .prefetch_related(
            "lineas__material",
            "lineas__serie",
            "lineas__tecnico_origen",
            "lineas__tecnico_destino",
        )
        .get()
    )


def listar_traspasos(tenant, estado=None):
    traspasos = SolicitudTraspaso.objects.filter(tenant=tenant)
    if estado:
        traspasos = traspasos.filter(estado=estado)
    return traspasos.prefetch_related(
        "lineas__tecnico_origen", "lineas__tecnico_destino"
    ).order_by("-fecha", "-id")


def calcular_reservado(tecnico, material, excluir_solicitud=None):
    lineas = LineaTraspaso.objects.filter(
        tenant=tecnico.tenant,
        material=material,
        tecnico_origen=tecnico,
        solicitud__estado__in=ESTADOS_RESERVA,
    )
    if excluir_solicitud is not None:
        lineas = lineas.exclude(solicitud=excluir_solicitud)
    no_seriadas = (
        lineas.filter(serie__isnull=True).aggregate(total=Sum("cantidad"))[
            "total"
        ]
        or 0
    )
    return no_seriadas + lineas.filter(serie__isnull=False).count()


def calcular_disponible(tecnico, material, excluir_solicitud=None):
    return max(
        0,
        obtener_stock_tecnico(tecnico, material)
        - calcular_reservado(tecnico, material, excluir_solicitud),
    )


def _resolver_tecnico(tenant, tecnico_id, cache):
    if tecnico_id in (None, ""):
        raise ValidacionTraspaso("Debe indicar el técnico de la línea")
    try:
        clave = int(tecnico_id)
    except (TypeError, ValueError) as exc:
        raise ValidacionTraspaso("El técnico no existe") from exc
    if clave not in cache:
        tecnico = Tecnico.objects.filter(pk=clave, tenant=tenant).first()
        if tecnico is None:
            raise ValidacionTraspaso(
                "Los técnicos deben ser del mismo tenant"
            )
        cache[clave] = tecnico
    return cache[clave]


def normalizar_lineas(tenant, lineas, solicitud=None):
    if not lineas:
        raise ValidacionTraspaso("El traspaso debe tener al menos una línea")

    resultado = []
    no_seriadas = {}
    series_vistas = set()
    cache_tecnicos = {}

    for linea in lineas:
        material = Material.objects.filter(pk=linea.get("material_id")).first()
        if material is None:
            raise ValidacionTraspaso("El material no existe en el catálogo")
        origen = _resolver_tecnico(
            tenant, linea.get("tecnico_origen_id"), cache_tecnicos
        )
        destino = _resolver_tecnico(
            tenant, linea.get("tecnico_destino_id"), cache_tecnicos
        )
        if origen.pk == destino.pk:
            raise ValidacionTraspaso(
                "El técnico origen y destino no pueden ser el mismo"
            )
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
                    solicitud__estado__in=ESTADOS_RESERVA,
                ).exclude(solicitud=solicitud).exists():
                    raise ValidacionTraspaso(
                        "La serie está reservada en otro traspaso"
                    )
                resultado.append(
                    LineaValidada(
                        tecnico_origen=origen,
                        tecnico_destino=destino,
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
            clave = (origen.pk, destino.pk, material.pk)
            if clave in no_seriadas:
                no_seriadas[clave].cantidad += cantidad
            else:
                no_seriadas[clave] = LineaValidada(
                    tecnico_origen=origen,
                    tecnico_destino=destino,
                    material=material,
                    serie=None,
                    cantidad=cantidad,
                    lote=material.lote,
                )

    resultado.extend(no_seriadas.values())

    validar_estructura_tecnicos(resultado, tenant)

    # Disponibilidad agregada por técnico origen y material.
    totales_por_origen = {}
    for linea in resultado:
        if linea.serie:
            continue
        clave = (linea.tecnico_origen.pk, linea.material.pk)
        totales_por_origen[clave] = (
            totales_por_origen.get(clave, 0) + linea.cantidad
        )
    for (origen_id, material_id), cantidad in totales_por_origen.items():
        origen = cache_tecnicos.get(origen_id)
        if origen is None:
            origen = Tecnico.objects.get(pk=origen_id)
        material = Material.objects.get(pk=material_id)
        if cantidad > calcular_disponible(origen, material, solicitud):
            raise ValidacionTraspaso(
                "La cantidad supera el stock del técnico"
            )

    return resultado


def _inyectar_tecnicos(lineas, origen_id, destino_id):
    resultado = []
    for linea in lineas:
        copia = dict(linea)
        if origen_id is not None and not copia.get("tecnico_origen_id"):
            copia["tecnico_origen_id"] = origen_id
        if destino_id is not None and not copia.get("tecnico_destino_id"):
            copia["tecnico_destino_id"] = destino_id
        resultado.append(copia)
    return resultado


def _auditar_alta(solicitud, lineas, actor):
    nifs = ", ".join(
        f"{linea.tecnico_origen.nif}->{linea.tecnico_destino.nif}"
        for linea in lineas
    )
    registrar_cambio(
        "SolicitudTraspaso",
        solicitud.pk,
        "alta",
        "",
        f"tecnicos={nifs}; estado={solicitud.estado}",
        actor,
        tenant=solicitud.tenant,
    )
    for linea in lineas:
        registrar_cambio(
            "LineaTraspaso",
            linea.pk,
            "alta",
            "",
            f"origen={linea.tecnico_origen.nif}; "
            f"destino={linea.tecnico_destino.nif}; "
            f"material={linea.material.codigo}; "
            f"cantidad={linea.cantidad}",
            actor,
            tenant=solicitud.tenant,
        )


def _crear_lineas(solicitud, lineas):
    creadas = []
    for linea in lineas:
        creadas.append(
            LineaTraspaso.objects.create(
                tenant=solicitud.tenant,
                solicitud=solicitud,
                tecnico_origen=linea.tecnico_origen,
                tecnico_destino=linea.tecnico_destino,
                material=linea.material,
                lote=linea.lote,
                serie=linea.serie,
                cantidad=linea.cantidad,
            )
        )
    return creadas


def crear_solicitud_traspaso(
    tenant, fecha, lineas, actor, clave_idempotencia=None
):
    tenant = validar_cuenta_tenant(actor)
    if clave_idempotencia:
        existente = SolicitudTraspaso.objects.filter(
            tenant=tenant,
            clave_idempotencia=clave_idempotencia,
        ).first()
        if existente is not None:
            return existente
    if isinstance(fecha, str):
        fecha = parse_date(fecha)
    if fecha is None:
        raise ValidacionTraspaso("La fecha es obligatoria")
    lineas_validadas = normalizar_lineas(tenant, lineas)
    validar_cuadre_traspaso(construir_movimientos(lineas_validadas))

    with transaction.atomic():
        try:
            with transaction.atomic():
                solicitud = SolicitudTraspaso.objects.create(
                    tenant=tenant,
                    region=tenant.region,
                    fecha=fecha,
                    estado=EstadoTraspaso.BORRADOR,
                    creado_por=actor,
                    clave_idempotencia=clave_idempotencia or None,
                )
                creadas = _crear_lineas(solicitud, lineas_validadas)
                _auditar_alta(solicitud, creadas, actor)
        except IntegrityError:
            if not clave_idempotencia:
                raise
            existente = SolicitudTraspaso.objects.filter(
                tenant=tenant,
                clave_idempotencia=clave_idempotencia,
            ).first()
            if existente is None:
                raise
            return existente
    return solicitud


def crear_y_enviar_traspaso(
    tenant, fecha, lineas, actor, clave_idempotencia=None
):
    """Crea y envía en una sola transacción; un fallo no deja borrador."""
    with transaction.atomic():
        solicitud = crear_solicitud_traspaso(
            tenant,
            fecha,
            lineas,
            actor,
            clave_idempotencia=clave_idempotencia,
        )
        if solicitud.estado == EstadoTraspaso.BORRADOR:
            return enviar_solicitud_traspaso(solicitud, actor)
        return solicitud


def crear_borrador_traspaso(
    tenant, origen_id, destino_id, fecha, lineas, actor
):
    """Compatibilidad: admite origen/destino comunes o por línea."""
    return crear_solicitud_traspaso(
        tenant,
        fecha,
        _inyectar_tecnicos(lineas, origen_id, destino_id),
        actor,
    )


def actualizar_lineas_borrador(solicitud, fecha, lineas, actor):
    tenant = validar_cuenta_tenant(actor)
    if solicitud.tenant_id != tenant.pk:
        raise TraspasoNoExiste
    if solicitud.estado != EstadoTraspaso.BORRADOR:
        raise EstadoTraspasoInvalido(
            "Solo se pueden editar traspasos en borrador"
        )
    if isinstance(fecha, str):
        fecha = parse_date(fecha)
    if fecha is None:
        raise ValidacionTraspaso("La fecha es obligatoria")
    lineas_validadas = normalizar_lineas(tenant, lineas, solicitud)
    validar_cuadre_traspaso(construir_movimientos(lineas_validadas))
    with transaction.atomic():
        bloqueada = (
            SolicitudTraspaso.objects.select_for_update()
            .prefetch_related("lineas")
            .get(pk=solicitud.pk)
        )
        for anterior in bloqueada.lineas.all():
            registrar_cambio(
                "LineaTraspaso",
                anterior.pk,
                "baja",
                f"origen={anterior.tecnico_origen.nif}; "
                f"destino={anterior.tecnico_destino.nif}; "
                f"material={anterior.material.codigo}",
                "",
                actor,
                tenant=tenant,
            )
        bloqueada.lineas.all().delete()
        bloqueada.fecha = fecha
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "fecha",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        creadas = _crear_lineas(bloqueada, lineas_validadas)
        for linea in creadas:
            registrar_cambio(
                "LineaTraspaso",
                linea.pk,
                "alta",
                "",
                f"origen={linea.tecnico_origen.nif}; "
                f"destino={linea.tecnico_destino.nif}; "
                f"material={linea.material.codigo}; "
                f"cantidad={linea.cantidad}",
                actor,
                tenant=tenant,
            )
    return bloqueada


def actualizar_borrador_traspaso(
    solicitud, origen_id, destino_id, fecha, lineas, actor
):
    """Compatibilidad: admite origen/destino comunes o por línea."""
    return actualizar_lineas_borrador(
        solicitud,
        fecha,
        _inyectar_tecnicos(lineas, origen_id, destino_id),
        actor,
    )


def enviar_solicitud_traspaso(solicitud, actor):
    tenant = validar_cuenta_tenant(actor)
    with transaction.atomic():
        bloqueada = (
            SolicitudTraspaso.objects.select_for_update()
            .prefetch_related(
                "lineas__tecnico_origen",
                "lineas__tecnico_destino",
                "lineas__material",
                "lineas__serie",
            )
            .get(pk=solicitud.pk)
        )
        if bloqueada.tenant_id != tenant.pk:
            raise TraspasoNoExiste
        if bloqueada.estado != EstadoTraspaso.BORRADOR:
            raise EstadoTraspasoInvalido(
                "Solo se pueden enviar traspasos en borrador"
            )
        lineas = list(bloqueada.lineas.all())
        validar_estructura_tecnicos(lineas, tenant)
        revalidar_disponibilidad(lineas, bloqueada)
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


enviar_traspaso = enviar_solicitud_traspaso


def confirmar_traspaso(solicitud, actor):
    from asignaciones.almacen_services import validar_cuenta_almacen

    region = validar_cuenta_almacen(actor)
    if solicitud.region_id != region.pk:
        raise TraspasoNoExiste

    with transaction.atomic():
        bloqueada = (
            SolicitudTraspaso.objects.select_for_update()
            .prefetch_related(
                "lineas__tecnico_origen",
                "lineas__tecnico_destino",
                "lineas__material",
                "lineas__serie",
            )
            .get(pk=solicitud.pk)
        )
        if bloqueada.estado != EstadoTraspaso.ENVIADA:
            raise EstadoTraspasoInvalido(
                "Solo se pueden confirmar traspasos enviados"
            )
        lineas = list(bloqueada.lineas.all())
        validar_estructura_tecnicos(lineas, bloqueada.tenant)
        for linea in lineas:
            if not linea.serie_id:
                continue
            serie = linea.serie
            if (
                serie.estado != EstadoSerie.ASIGNADA
                or serie.tecnico_id != linea.tecnico_origen_id
            ):
                raise SerieNoAsignada(
                    "La serie no está asignada al técnico origen"
                )

        validar_cuadre_traspaso(construir_movimientos(lineas))

        cantidades = {}
        for linea in lineas:
            cantidad = 1 if linea.serie_id else linea.cantidad
            clave = (
                linea.tecnico_origen_id,
                linea.tecnico_destino_id,
                linea.material_id,
            )
            cantidades[clave] = cantidades.get(clave, 0) + cantidad

        ahora = timezone.now()
        for linea in lineas:
            if not linea.serie_id:
                continue
            serie = linea.serie
            serie.tecnico = linea.tecnico_destino
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
                linea.tecnico_origen_id,
                linea.tecnico_destino_id,
                actor,
                tenant=bloqueada.tenant,
            )
            registrar_cambio(
                "Serie",
                serie.pk,
                "asignada_en",
                "",
                ahora.isoformat(),
                actor,
                tenant=bloqueada.tenant,
            )

        for (origen_id, destino_id, material_id), cantidad in cantidades.items():
            origen = next(
                linea.tecnico_origen
                for linea in lineas
                if linea.tecnico_origen_id == origen_id
            )
            destino = next(
                linea.tecnico_destino
                for linea in lineas
                if linea.tecnico_destino_id == destino_id
            )
            material = Material.objects.get(pk=material_id)
            referencia = (
                f"TRASPASO:{bloqueada.pk}:{origen_id}:"
                f"{destino_id}:{material_id}"
            )
            try:
                decrementar_stock_tecnico(
                    origen,
                    material,
                    cantidad,
                    actor,
                    tipo=TipoMovimientoTecnico.TRASPASO_SALIDA,
                    referencia=referencia + ":SALIDA",
                )
            except StockInsuficiente as exc:
                raise ValidacionTraspaso(
                    "El técnico no tiene suficiente stock"
                ) from exc
            incrementar_stock_tecnico(
                destino,
                material,
                cantidad,
                actor,
                tipo=TipoMovimientoTecnico.TRASPASO_ENTRADA,
                referencia=referencia + ":ENTRADA",
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
        registrar_cambio(
            "SolicitudTraspaso",
            bloqueada.pk,
            "estado",
            EstadoTraspaso.BORRADOR,
            EstadoTraspaso.CANCELADA,
            actor,
            tenant=bloqueada.tenant,
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


def verificar_hash_excel(solicitud, contenido=None):
    if contenido is not None:
        if hashlib.sha256(contenido).hexdigest() != solicitud.excel_hash:
            raise ArchivoAlterado
    return verificar_excel(solicitud)


def series_para_tecnico(
    tenant, tecnico, material=None, q="", excluir_solicitud=None
):
    series = Serie.objects.filter(
        tenant=tenant,
        tecnico=tecnico,
        estado=EstadoSerie.ASIGNADA,
    )
    reservadas = LineaTraspaso.objects.filter(
        solicitud__estado__in=ESTADOS_RESERVA,
        serie__isnull=False,
    )
    if excluir_solicitud is not None:
        reservadas = reservadas.exclude(solicitud=excluir_solicitud)
    series = series.exclude(pk__in=reservadas.values("serie_id"))
    if material is not None:
        series = series.filter(material=material)
    q = (q or "").strip()
    if q:
        series = series.filter(numero__icontains=q)
    return series.order_by("numero")


def stock_tecnico_para_traspaso(
    tenant, tecnico, excluir_solicitud=None
):
    """Stock del técnico con lo reservado por borradores y traspasos enviados."""
    from stock.models import StockTecnico

    filas = (
        StockTecnico.objects.filter(
            tenant=tenant, tecnico=tecnico, cantidad__gt=0
        )
        .select_related("material")
        .order_by("material__codigo")
    )
    resultado = []
    for fila in filas:
        reservado = calcular_reservado(
            tecnico, fila.material, excluir_solicitud
        )
        resultado.append(
            StockTraspaso(
                material=fila.material,
                stock=fila.cantidad,
                reservado=reservado,
                disponible=max(0, fila.cantidad - reservado),
            )
        )
    return resultado


def validar_disponibilidad(
    tecnico, material, cantidad=None, series=None, excluir_solicitud=None
):
    disponible = calcular_disponible(
        tecnico, material, excluir_solicitud
    )
    reservado = calcular_reservado(tecnico, material, excluir_solicitud)
    errores = []
    if material.es_seriado:
        for serie in series or []:
            if (
                serie.tecnico_id != tecnico.pk
                or serie.estado != EstadoSerie.ASIGNADA
            ):
                errores.append(
                    "La serie no está asignada al técnico origen"
                )
    elif cantidad is not None and int(cantidad) > disponible:
        errores.append("La cantidad supera el stock del técnico")
    return {
        "valido": not errores,
        "disponible": disponible,
        "reservado": reservado,
        "errores": errores,
    }


# Nombres canónicos del contrato.
crear_solicitud_traspaso = crear_solicitud_traspaso
actualizar_lineas_borrador = actualizar_lineas_borrador
enviar_solicitud_traspaso = enviar_solicitud_traspaso
