"""Servicios fundacionales de stock."""

from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from auditoria.services import registrar_cambio
from tecnicos.models import Tecnico
from tenants.models import Tenant

from .models import StockGeneral, StockTecnico

MENSAJE_CANTIDAD = "La cantidad debe ser mayor a 0"
MENSAJE_STOCK_GENERAL = "El tenant no tiene suficiente stock general"
MENSAJE_STOCK_TECNICO = "El técnico no tiene suficiente stock"
MENSAJE_SERIE_NO_RESERVADA = "La serie no está reservada para esta asignación"
MENSAJE_CONFIRMACION = "No se puede confirmar el stock de la asignación"
MENSAJE_TENANT_NO_COINCIDE = "El tenant no coincide"


class CantidadInvalida(Exception):
    def __init__(self, mensaje=MENSAJE_CANTIDAD):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class StockInsuficiente(Exception):
    def __init__(self, mensaje=MENSAJE_STOCK_GENERAL):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class StockNoExiste(Exception):
    def __init__(self, mensaje="El stock no existe"):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class TecnicoNoExiste(Exception):
    def __init__(self, mensaje="El técnico no existe"):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class SerieNoReservada(Exception):
    def __init__(self, mensaje=MENSAJE_SERIE_NO_RESERVADA):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class ConfirmacionStockInvalida(Exception):
    def __init__(self, mensaje=MENSAJE_CONFIRMACION):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


class TenantNoCoincide(Exception):
    def __init__(self, mensaje=MENSAJE_TENANT_NO_COINCIDE):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


def _validar_cantidad(cantidad):
    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
        raise CantidadInvalida


def _bloquear_tenant(tenant):
    return Tenant.objects.select_for_update().get(pk=tenant.pk)


def _auditar(entidad, entidad_id, anterior, nuevo, actor, tenant):
    return registrar_cambio(
        entidad,
        entidad_id,
        "cantidad",
        anterior,
        nuevo,
        actor,
        tenant=tenant,
    )


def obtener_stock_general(tenant, material) -> int:
    fila = StockGeneral.objects.filter(
        tenant=tenant,
        material=material,
    ).first()
    return fila.cantidad if fila is not None else 0


def obtener_stock_tecnico(tecnico, material) -> int:
    fila = StockTecnico.objects.filter(
        tecnico=tecnico,
        material=material,
    ).first()
    return fila.cantidad if fila is not None else 0


def calcular_reservado(tenant, material) -> int:
    """Suma líneas no seriadas de asignaciones ENVIADA, si 006 está instalada."""
    try:
        from asignaciones.models import LineaAsignacion, SolicitudAsignacion
    except (ImportError, LookupError):
        return 0

    return (
        LineaAsignacion.objects.filter(
            solicitud__tenant=tenant,
            solicitud__estado="ENVIADA",
            material=material,
            serie__isnull=True,
        ).aggregate(total=Sum("cantidad"))["total"]
        or 0
    )


def calcular_disponible(tenant, material) -> int:
    return max(
        0,
        obtener_stock_general(tenant, material)
        - calcular_reservado(tenant, material),
    )


def incrementar_stock_general(tenant, material, cantidad, actor) -> int:
    _validar_cantidad(cantidad)

    with transaction.atomic():
        _bloquear_tenant(tenant)
        fila = (
            StockGeneral.objects.select_for_update()
            .filter(tenant=tenant, material=material)
            .first()
        )
        if fila is None:
            fila = StockGeneral.objects.create(
                tenant=tenant,
                material=material,
                cantidad=0,
            )

        anterior = fila.cantidad
        fila.cantidad = anterior + cantidad
        fila.save(update_fields=["cantidad"])
        _auditar("StockGeneral", fila.pk, anterior, fila.cantidad, actor, tenant)

    return fila.cantidad


def decrementar_stock_general(tenant, material, cantidad, actor) -> int:
    _validar_cantidad(cantidad)

    with transaction.atomic():
        _bloquear_tenant(tenant)
        fila = (
            StockGeneral.objects.select_for_update()
            .filter(tenant=tenant, material=material)
            .first()
        )
        if fila is None or fila.cantidad < cantidad:
            raise StockInsuficiente(MENSAJE_STOCK_GENERAL)

        anterior = fila.cantidad
        fila.cantidad = anterior - cantidad
        fila.save(update_fields=["cantidad"])
        _auditar("StockGeneral", fila.pk, anterior, fila.cantidad, actor, tenant)

    return fila.cantidad


def _validar_tecnico(tecnico):
    if tecnico is None or not getattr(tecnico, "pk", None):
        raise TecnicoNoExiste
    if not Tecnico.objects.filter(pk=tecnico.pk).exists():
        raise TecnicoNoExiste


def incrementar_stock_tecnico(tecnico, material, cantidad, actor) -> int:
    _validar_cantidad(cantidad)
    _validar_tecnico(tecnico)
    tenant = tecnico.tenant

    with transaction.atomic():
        _bloquear_tenant(tenant)
        fila = (
            StockTecnico.objects.select_for_update()
            .filter(tecnico=tecnico, material=material)
            .first()
        )
        if fila is not None and fila.tenant_id != tenant.pk:
            raise TenantNoCoincide
        if fila is None:
            fila = StockTecnico.objects.create(
                tenant=tenant,
                tecnico=tecnico,
                material=material,
                cantidad=0,
            )

        anterior = fila.cantidad
        fila.cantidad = anterior + cantidad
        fila.save(update_fields=["cantidad"])
        _auditar("StockTecnico", fila.pk, anterior, fila.cantidad, actor, tenant)

    return fila.cantidad


@dataclass(frozen=True)
class CambioStockMaterial:
    material_id: int
    stock_general_anterior: int
    stock_general_nuevo: int
    stock_tecnico_anterior: int
    stock_tecnico_nuevo: int
    tecnico_id: int | None = None


@dataclass(frozen=True)
class ResultadoConfirmacionStock:
    solicitud_id: int
    series_actualizadas: list
    cambios_por_material: list
    confirmada_en: object = None
    total_series: int = 0
    total_cantidad: int = 0


def actualizar_stock_confirmacion_asignacion(solicitud, actor):
    """Mueve series RESERVADA→ASIGNADA y stock general→técnico de cada línea."""
    from asignaciones.models import EstadoSolicitud
    from series.models import EstadoSerie, Serie

    if solicitud.estado != EstadoSolicitud.ENVIADA:
        raise ConfirmacionStockInvalida()

    lineas = list(
        solicitud.lineas.select_related("material", "serie", "tecnico")
    )
    if not lineas:
        raise ConfirmacionStockInvalida()

    for linea in lineas:
        if linea.tecnico.tenant_id != solicitud.tenant_id:
            raise TenantNoCoincide()

    por_material = {}
    por_tecnico_material = {}
    materiales = {}
    tecnicos = {}
    for linea in lineas:
        cantidad = 1 if linea.serie_id else linea.cantidad
        if cantidad <= 0:
            raise CantidadInvalida()
        por_material[linea.material_id] = por_material.get(linea.material_id, 0) + cantidad
        clave = (linea.tecnico_id, linea.material_id)
        por_tecnico_material[clave] = por_tecnico_material.get(clave, 0) + cantidad
        materiales[linea.material_id] = linea.material
        tecnicos[linea.tecnico_id] = linea.tecnico

    series_ids = [linea.serie_id for linea in lineas if linea.serie_id]
    tecnico_por_serie = {
        linea.serie_id: linea.tecnico for linea in lineas if linea.serie_id
    }
    material_por_serie = {
        linea.serie_id: linea.material_id for linea in lineas if linea.serie_id
    }
    cambios = []
    series_actualizadas = []

    with transaction.atomic():
        _bloquear_tenant(solicitud.tenant)
        series = list(
            Serie.objects.select_for_update()
            .filter(pk__in=series_ids)
            .order_by("id")
        )
        if len(series) != len(set(series_ids)):
            raise SerieNoReservada()
        for serie in series:
            if (
                serie.estado != EstadoSerie.RESERVADA
                or serie.tenant_id != solicitud.tenant_id
                or serie.material_id != material_por_serie[serie.pk]
            ):
                raise SerieNoReservada()

        general_anterior = {}
        for material_id in sorted(por_material):
            cantidad = por_material[material_id]
            general_anterior[material_id] = obtener_stock_general(
                solicitud.tenant, materiales[material_id]
            )
            if general_anterior[material_id] < cantidad:
                raise StockInsuficiente(MENSAJE_STOCK_GENERAL)
            decrementar_stock_general(
                solicitud.tenant, materiales[material_id], cantidad, actor
            )

        for tecnico_id, material_id in sorted(por_tecnico_material):
            cantidad = por_tecnico_material[(tecnico_id, material_id)]
            tecnico = tecnicos[tecnico_id]
            tecnico_anterior = obtener_stock_tecnico(tecnico, materiales[material_id])
            tecnico_nuevo = incrementar_stock_tecnico(
                tecnico, materiales[material_id], cantidad, actor
            )
            cambios.append(
                CambioStockMaterial(
                    material_id=material_id,
                    stock_general_anterior=general_anterior[material_id],
                    stock_general_nuevo=general_anterior[material_id]
                    - por_material[material_id],
                    stock_tecnico_anterior=tecnico_anterior,
                    stock_tecnico_nuevo=tecnico_nuevo,
                    tecnico_id=tecnico_id,
                )
            )

        ahora = timezone.now()
        for serie in series:
            tecnico = tecnico_por_serie[serie.pk]
            anterior_estado = serie.estado
            anterior_tecnico = serie.tecnico_id
            anterior_fecha = serie.asignada_en
            serie.estado = EstadoSerie.ASIGNADA
            serie.tecnico = tecnico
            serie.asignada_en = ahora
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
            series_actualizadas.append(serie.pk)
            registrar_cambio(
                "Serie",
                serie.pk,
                "estado",
                anterior_estado,
                EstadoSerie.ASIGNADA,
                actor,
                tenant=solicitud.tenant,
            )
            registrar_cambio(
                "Serie",
                serie.pk,
                "tecnico",
                anterior_tecnico or "",
                tecnico.pk,
                actor,
                tenant=solicitud.tenant,
            )
            registrar_cambio(
                "Serie",
                serie.pk,
                "asignada_en",
                anterior_fecha.isoformat() if anterior_fecha else "",
                ahora.isoformat(),
                actor,
                tenant=solicitud.tenant,
            )

    return ResultadoConfirmacionStock(
        solicitud_id=solicitud.pk,
        series_actualizadas=series_actualizadas,
        cambios_por_material=cambios,
        confirmada_en=solicitud.confirmada_en,
        total_series=len(series_actualizadas),
        total_cantidad=sum(
            linea.cantidad for linea in lineas if linea.serie_id is None
        ),
    )

def decrementar_stock_tecnico(tecnico, material, cantidad, actor) -> int:
    _validar_cantidad(cantidad)
    _validar_tecnico(tecnico)
    tenant = tecnico.tenant

    with transaction.atomic():
        _bloquear_tenant(tenant)
        fila = (
            StockTecnico.objects.select_for_update()
            .filter(tecnico=tecnico, material=material)
            .first()
        )
        if fila is not None and fila.tenant_id != tenant.pk:
            raise TenantNoCoincide
        if fila is None or fila.cantidad < cantidad:
            raise StockInsuficiente(MENSAJE_STOCK_TECNICO)

        anterior = fila.cantidad
        fila.cantidad = anterior - cantidad
        fila.save(update_fields=["cantidad"])
        _auditar("StockTecnico", fila.pk, anterior, fila.cantidad, actor, tenant)

    return fila.cantidad
