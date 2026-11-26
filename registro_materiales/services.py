"""Servicios de registro de materiales."""

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from acceso.models import Rol
from auditoria.models import RegistroCambio
from auditoria.services import registrar_cambio
from materiales.models import Material
from series.models import EstadoSerie, Serie
from stock.models import StockTecnico, TipoMovimientoTecnico
from stock.services import (
    StockInsuficiente,
    decrementar_stock_tecnico,
    incrementar_stock_tecnico,
    obtener_stock_tecnico,
)
from tecnicos.models import Tecnico
from tenants.models import Tenant

from .models import (
    AdvertenciaUso,
    CargaOrdenes,
    CierreMensual,
    JustificacionCierre,
    MaterialHabilitado,
    OrdenLiquidacion,
    SaldoInicialPeriodo,
    SaldoMensualMaterial,
    UsoMaterialOrden,
    UsoMaterialSerie,
)

ORDEN_RE = re.compile(r"^[A-Z0-9]+(?:[-_][A-Z0-9]+)*$")
PERIODO_RE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


class ErrorRegistro(Exception):
    mensaje = "Error de registro de materiales"

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)

    def __str__(self):
        return self.args[0]


class PermisoDenegado(ErrorRegistro):
    mensaje = "No tienes permiso para registrar materiales"


class TecnicoNoExiste(ErrorRegistro):
    mensaje = "El técnico no pertenece a tu tenant"


class MaterialNoHabilitado(ErrorRegistro):
    mensaje = "El material no está habilitado para tu tenant"


class MaterialInactivo(ErrorRegistro):
    mensaje = "El material está deshabilitado"


class CantidadInvalida(ErrorRegistro):
    mensaje = "La cantidad debe ser un número entero mayor o igual a 0"


class NumeroOrdenInvalido(ErrorRegistro):
    mensaje = (
        "El número de orden es obligatorio y debe tener entre 1 y 30 "
        "caracteres alfanuméricos, guiones y guiones bajos simples"
    )


class PeriodoInvalido(ErrorRegistro):
    mensaje = "El periodo debe tener el formato AAAA-MM"


class OrdenDuplicada(ErrorRegistro):
    mensaje = "Ya existe una orden con ese número para el técnico y mes"


class SaldoInsuficiente(ErrorRegistro):
    mensaje = "El uso supera el disponible del mes"


class SerieNoDisponible(ErrorRegistro):
    mensaje = "La serie seleccionada no está disponible en la custodia"


class PeriodoCerrado(ErrorRegistro):
    mensaje = "El mes está cerrado; solicita reapertura"


class CargaNoDeshacible(ErrorRegistro):
    mensaje = "No se puede deshacer: hay órdenes con materiales registrados"


class CierreBloqueado(ErrorRegistro):
    mensaje = "El cierre tiene pendientes sin resolver o justificar"


class BackupRequerido(ErrorRegistro):
    mensaje = "Debes registrar la referencia del respaldo antes de cerrar"


class NoEncontrado(ErrorRegistro):
    mensaje = "El registro no existe"


class MotivoRequerido(ErrorRegistro):
    mensaje = "Debes indicar un motivo"


@dataclass(frozen=True)
class ListaNormalizada:
    ordenes: list
    rechazadas: list = field(default_factory=list)


@dataclass(frozen=True)
class ResumenCarga:
    leidas: int
    nuevas: int
    omitidas: int
    tambien_otro_tecnico: int
    rechazadas: list = field(default_factory=list)


def validar_cuenta_tenant(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol != Rol.USUARIO_TENANT or not actor.tenant_id:
        raise PermisoDenegado
    if actor.tenant.estado != "ACTIVO":
        raise PermisoDenegado("El tenant está suspendido")
    return actor.tenant


def periodo_actual():
    return date.today().strftime("%Y-%m")


def validar_periodo(periodo):
    if not periodo or not PERIODO_RE.match(str(periodo)):
        raise PeriodoInvalido
    return str(periodo)


def periodo_de_fecha(fecha):
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    if not isinstance(fecha, date):
        raise PeriodoInvalido
    return fecha.strftime("%Y-%m")


def _desplazar_periodo(periodo, meses):
    anio, mes = (int(parte) for parte in periodo.split("-"))
    total = anio * 12 + (mes - 1) + meses
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def periodo_anterior(periodo):
    return _desplazar_periodo(validar_periodo(periodo), -1)


def validar_tecnico(tenant, tecnico):
    if tecnico is None or not getattr(tecnico, "pk", None):
        raise TecnicoNoExiste
    fila = Tecnico.objects.filter(
        pk=tecnico.pk, tenant=tenant, activo=True
    ).first()
    if fila is None:
        raise TecnicoNoExiste
    return fila


def normalizar_numero(numero):
    texto = str(numero or "").strip().upper()
    if len(texto) > 30 or not ORDEN_RE.match(texto):
        raise NumeroOrdenInvalido
    return texto


def _cantidad(valor):
    if valor in (None, ""):
        return 0
    if isinstance(valor, bool):
        raise CantidadInvalida
    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, float) and valor.is_integer():
        numero = int(valor)
    else:
        texto = str(valor).strip()
        if not texto.isdigit():
            raise CantidadInvalida
        numero = int(texto)
    if numero < 0:
        raise CantidadInvalida
    return numero


def materiales_habilitados(tenant, solo_activos=True):
    qs = MaterialHabilitado.objects.filter(tenant=tenant).select_related(
        "material"
    )
    if solo_activos:
        qs = qs.filter(activo=True, material__activo=True)
    return qs.order_by("orden", "material__codigo")


def habilitar_material(tenant, material, activo, actor, orden=0):
    tenant = validar_cuenta_tenant(actor)
    if material is None:
        raise MaterialNoHabilitado
    with transaction.atomic():
        fila, creada = MaterialHabilitado.objects.get_or_create(
            tenant=tenant,
            material=material,
            defaults={"activo": activo, "orden": orden, "creado_por": actor},
        )
        anterior = "" if creada else fila.activo
        if not creada:
            fila.activo = activo
            fila.orden = orden
            fila.actualizado_por = actor
            fila.save(
                update_fields=[
                    "activo",
                    "orden",
                    "actualizado_por",
                    "actualizado_en",
                ]
            )
        registrar_cambio(
            "MaterialHabilitado",
            fila.pk,
            "alta" if creada else "activo",
            anterior,
            fila.activo,
            actor,
            tenant=tenant,
        )
    return fila


def obtener_habilitado(tenant, material):
    fila = MaterialHabilitado.objects.filter(
        tenant=tenant, material=material
    ).first()
    if fila is None:
        raise MaterialNoHabilitado
    if not fila.activo:
        raise MaterialInactivo
    return fila


def _validar_mes_abierto(tenant, periodo):
    validar_periodo(periodo)
    if CierreMensual.objects.filter(
        tenant=tenant, periodo=periodo, estado=CierreMensual.CERRADO
    ).exists():
        raise PeriodoCerrado


validar_periodo_abierto = _validar_mes_abierto


def procesar_lista(texto):
    ordenes = []
    rechazadas = []
    vistos = set()
    for linea in str(texto or "").splitlines():
        limpia = linea.strip()
        if not limpia:
            continue
        if any(c in limpia for c in " \t,;"):
            rechazadas.append(limpia)
            continue
        normalizada = limpia.upper()
        if len(normalizada) > 30 or not ORDEN_RE.match(normalizada):
            rechazadas.append(limpia)
            continue
        if normalizada in vistos:
            continue
        vistos.add(normalizada)
        ordenes.append(normalizada)
    return ListaNormalizada(ordenes=ordenes, rechazadas=rechazadas)


def _resumen(tenant, tecnico, periodo, texto):
    lista = procesar_lista(texto)
    existentes = set(
        OrdenLiquidacion.objects.filter(
            tenant=tenant, tecnico=tecnico, periodo=periodo
        ).values_list("numero_normalizado", flat=True)
    )
    otros = set(
        OrdenLiquidacion.objects.filter(
            tenant=tenant, periodo=periodo
        )
        .exclude(tecnico=tecnico)
        .values_list("numero_normalizado", flat=True)
    )
    nuevas = [numero for numero in lista.ordenes if numero not in existentes]
    omitidas = [numero for numero in lista.ordenes if numero in existentes]
    otro_tecnico = [numero for numero in nuevas if numero in otros]
    return lista, ResumenCarga(
        leidas=len(lista.ordenes) + len(lista.rechazadas),
        nuevas=len(nuevas),
        omitidas=len(omitidas),
        tambien_otro_tecnico=len(otro_tecnico),
        rechazadas=lista.rechazadas,
    ), nuevas


def previsualizar_carga(tenant, tecnico, periodo, texto):
    validar_periodo(periodo)
    tecnico = validar_tecnico(tenant, tecnico)
    return _resumen(tenant, tecnico, periodo, texto)[1]


def confirmar_carga(tenant, tecnico, periodo, texto, actor):
    tenant = validar_cuenta_tenant(actor)
    validar_periodo(periodo)
    _validar_mes_abierto(tenant, periodo)
    tecnico = validar_tecnico(tenant, tecnico)
    lista, resumen, nuevas = _resumen(tenant, tecnico, periodo, texto)
    if lista.rechazadas:
        raise NumeroOrdenInvalido
    if not lista.ordenes:
        raise NumeroOrdenInvalido
    with transaction.atomic():
        # Serializa cargas concurrentes del mismo tenant y recalcula el
        # resumen con el estado ya confirmado para no chocar con la
        # restricción única de órdenes.
        Tenant.objects.select_for_update().get(pk=tenant.pk)
        lista, resumen, nuevas = _resumen(
            tenant, tecnico, periodo, texto
        )
        if lista.rechazadas or not lista.ordenes:
            raise NumeroOrdenInvalido
        carga = CargaOrdenes.objects.create(
            tenant=tenant,
            tecnico=tecnico,
            periodo=periodo,
            hash_texto=hashlib.sha256(str(texto).encode()).hexdigest(),
            total_leidas=resumen.leidas,
            total_nuevas=resumen.nuevas,
            total_omitidas=resumen.omitidas,
            total_otro_tecnico=resumen.tambien_otro_tecnico,
            creado_por=actor,
        )
        OrdenLiquidacion.objects.bulk_create(
            [
                OrdenLiquidacion(
                    tenant=tenant,
                    tecnico=tecnico,
                    numero_original=numero,
                    numero_normalizado=numero,
                    periodo=periodo,
                    carga=carga,
                    creado_por=actor,
                )
                for numero in nuevas
            ]
        )
        registrar_cambio(
            "CargaOrdenes",
            carga.pk,
            "alta",
            "",
            f"nuevas={resumen.nuevas}; omitidas={resumen.omitidas}",
            actor,
            tenant=tenant,
        )
    return carga


def deshacer_carga(carga, actor, motivo=""):
    tenant = validar_cuenta_tenant(actor)
    if carga.tenant_id != tenant.pk:
        raise NoEncontrado
    with transaction.atomic():
        ordenes = list(carga.ordenes.all())
        ids = [orden.pk for orden in ordenes]
        if UsoMaterialOrden.objects.filter(
            orden_id__in=ids, cantidad__gt=0
        ).exists():
            raise CargaNoDeshacible
        OrdenLiquidacion.objects.filter(pk__in=ids).delete()
        carga.deshecha_en = timezone.now()
        carga.deshecha_por = actor
        carga.motivo_deshacer = " ".join((motivo or "").split())
        carga.save(
            update_fields=[
                "deshecha_en",
                "deshecha_por",
                "motivo_deshacer",
            ]
        )
        registrar_cambio(
            "CargaOrdenes",
            carga.pk,
            "deshecha",
            "",
            f"ordenes={len(ids)}; motivo={carga.motivo_deshacer}",
            actor,
            tenant=tenant,
        )
    return carga


def buscar_orden(tenant, tecnico, periodo, numero):
    try:
        normalizado = normalizar_numero(numero)
    except NumeroOrdenInvalido:
        return None
    return OrdenLiquidacion.objects.filter(
        tenant=tenant,
        tecnico=tecnico,
        periodo=periodo,
        numero_normalizado=normalizado,
    ).first()


def obtener_o_crear_orden(tenant, tecnico, periodo, numero, actor):
    tenant = validar_cuenta_tenant(actor)
    validar_periodo(periodo)
    tecnico = validar_tecnico(tenant, tecnico)
    normalizado = normalizar_numero(numero)
    orden = OrdenLiquidacion.objects.filter(
        tenant=tenant,
        tecnico=tecnico,
        periodo=periodo,
        numero_normalizado=normalizado,
    ).first()
    if orden is not None:
        return orden
    with transaction.atomic():
        orden = OrdenLiquidacion.objects.create(
            tenant=tenant,
            tecnico=tecnico,
            numero_original=str(numero).strip(),
            numero_normalizado=normalizado,
            periodo=periodo,
            creado_por=actor,
        )
        registrar_cambio(
            "OrdenLiquidacion",
            orden.pk,
            "alta",
            "",
            f"{normalizado}; tecnico={tecnico.nif}; periodo={periodo}",
            actor,
            tenant=tenant,
        )
    return orden


def asignaciones_confirmadas_del_periodo(
    tenant, periodo, material=None
):
    """Cantidad confirmada por el almacén en el mes, agrupada por material."""
    validar_periodo(periodo)
    from asignaciones.models import EstadoSolicitud, LineaAsignacion

    anio, mes = (int(parte) for parte in periodo.split("-"))
    inicio = date(anio, mes, 1)
    fin = date(anio + (mes == 12), (mes % 12) + 1, 1)
    desde = timezone.make_aware(
        datetime.combine(inicio, datetime.min.time())
    )
    hasta = timezone.make_aware(
        datetime.combine(fin, datetime.min.time())
    )
    qs = LineaAsignacion.objects.filter(
        tenant=tenant,
        solicitud__estado=EstadoSolicitud.CONFIRMADA,
        solicitud__confirmada_en__gte=desde,
        solicitud__confirmada_en__lt=hasta,
    )
    if material is not None:
        qs = qs.filter(material=material)
    return {
        fila["material_id"]: fila["total"]
        for fila in qs.values("material_id").annotate(total=Sum("cantidad"))
    }


# Alias de compatibilidad para código interno heredado.
despachos_del_periodo = asignaciones_confirmadas_del_periodo


def usado_del_periodo(tenant, periodo, material=None, tecnico=None):
    validar_periodo(periodo)
    qs = UsoMaterialOrden.objects.filter(
        tenant=tenant, orden__periodo=periodo
    )
    if material is not None:
        qs = qs.filter(material=material)
    if tecnico is not None:
        qs = qs.filter(tecnico=tecnico)
    return (
        qs.aggregate(total=Sum("cantidad"))["total"] or 0
    ) if material is not None else {
        fila["material_id"]: fila["total"]
        for fila in qs.values("material_id").annotate(total=Sum("cantidad"))
    }


def _saldo_cierre_anterior(tenant, material, periodo):
    anterior = periodo_anterior(periodo)
    saldo = (
        SaldoMensualMaterial.objects.filter(
            tenant=tenant,
            material=material,
            cierre__periodo=anterior,
            cierre__estado=CierreMensual.CERRADO,
        )
        .values_list("saldo_final", flat=True)
        .first()
    )
    return saldo


def saldo_inicial_efectivo(tenant, material, periodo, _vistos=None):
    validar_periodo(periodo)
    manual = (
        SaldoInicialPeriodo.objects.filter(
            tenant=tenant, material=material, periodo=periodo
        )
        .values_list("cantidad", flat=True)
        .first()
    )
    if manual is not None:
        return manual
    heredado = _saldo_cierre_anterior(tenant, material, periodo)
    if heredado is not None:
        return heredado
    stock_actual = (
        StockTecnico.objects.filter(tenant=tenant, material=material)
        .aggregate(total=Sum("cantidad"))["total"]
        or 0
    )
    usado = usado_del_periodo(tenant, periodo, material)
    despachos = despachos_del_periodo(tenant, periodo).get(material.pk, 0)
    if stock_actual or usado or despachos:
        return stock_actual + usado - despachos
    vistos = set(_vistos or [])
    if periodo in vistos or len(vistos) > 120:
        return 0
    vistos.add(periodo)
    anterior = periodo_anterior(periodo)
    tiene_datos = (
        SaldoInicialPeriodo.objects.filter(
            tenant=tenant, material=material, periodo=anterior
        ).exists()
        or SaldoMensualMaterial.objects.filter(
            tenant=tenant,
            material=material,
            cierre__periodo=anterior,
            cierre__estado=CierreMensual.CERRADO,
        ).exists()
        or despachos_del_periodo(tenant, anterior).get(material.pk, 0) > 0
        or usado_del_periodo(tenant, anterior, material) > 0
    )
    if not tiene_datos:
        return 0
    inicial = saldo_inicial_efectivo(
        tenant, material, anterior, vistos
    )
    despachos = despachos_del_periodo(tenant, anterior).get(material.pk, 0)
    usado = usado_del_periodo(tenant, anterior, material)
    return inicial + despachos - usado


def saldo_final(tenant, material, periodo):
    inicial = saldo_inicial_efectivo(tenant, material, periodo)
    despachos = despachos_del_periodo(tenant, periodo).get(material.pk, 0)
    usado = usado_del_periodo(tenant, periodo, material)
    return inicial + despachos - usado


def _mover_stock_consumo(tecnico, material, delta, actor, uso):
    """Aplica el delta de consumo al libro de stock del técnico."""
    if delta == 0:
        return
    referencia = f"USO:{uso.pk}:{uuid.uuid4().hex[:12]}"
    try:
        if delta > 0:
            decrementar_stock_tecnico(
                tecnico,
                material,
                delta,
                actor,
                tipo=TipoMovimientoTecnico.CONSUMO,
                referencia=referencia,
            )
        else:
            incrementar_stock_tecnico(
                tecnico,
                material,
                -delta,
                actor,
                tipo=TipoMovimientoTecnico.CONSUMO,
                referencia=referencia,
            )
    except StockInsuficiente as exc:
        raise SaldoInsuficiente(
            "El consumo supera el stock actual del técnico: "
            f"{exc}"
        ) from exc


def _auditar_custodia_serie(
    serie, anterior_estado, anterior_tecnico, anterior_fecha, actor, tenant
):
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
        serie.tecnico_id or "",
        actor,
        tenant=tenant,
    )
    registrar_cambio(
        "Serie",
        serie.pk,
        "asignada_en",
        anterior_fecha,
        serie.asignada_en,
        actor,
        tenant=tenant,
    )


def _sincronizar_series_uso(uso, material, seleccionadas, orden, actor, tenant):
    """Sincroniza las series consumidas y el stock del técnico."""
    seleccionadas = {int(pk) for pk in seleccionadas}
    enlaces = {
        enlace.serie_id: enlace
        for enlace in uso.series_usadas.select_related("serie")
    }
    series = {
        serie.pk: serie
        for serie in Serie.objects.select_for_update().filter(
            tenant=tenant,
            pk__in=seleccionadas,
        )
    }
    if len(series) != len(seleccionadas):
        raise SerieNoDisponible
    for serie_id in seleccionadas - set(enlaces):
        serie = series[serie_id]
        if (
            serie.estado != EstadoSerie.ASIGNADA
            or serie.tecnico_id != orden.tecnico_id
        ):
            raise SerieNoDisponible

    for serie_id in set(enlaces) - seleccionadas:
        enlace = enlaces[serie_id]
        serie = enlace.serie
        anterior_estado = serie.estado
        anterior_tecnico = serie.tecnico_id
        anterior_fecha = serie.asignada_en
        serie.estado = EstadoSerie.ASIGNADA
        serie.tecnico = orden.tecnico
        serie.asignada_en = timezone.now()
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
        _mover_stock_consumo(
            orden.tecnico, material, -1, actor, uso
        )
        enlace.delete()
        _auditar_custodia_serie(
            serie,
            anterior_estado,
            anterior_tecnico,
            anterior_fecha,
            actor,
            tenant,
        )

    for serie_id in seleccionadas - set(enlaces):
        serie = series[serie_id]
        anterior_estado = serie.estado
        anterior_tecnico = serie.tecnico_id
        anterior_fecha = serie.asignada_en
        serie.estado = EstadoSerie.INSTALADA
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
        _mover_stock_consumo(
            orden.tecnico, material, 1, actor, uso
        )
        UsoMaterialSerie.objects.create(
            tenant=tenant,
            uso=uso,
            serie=serie,
            creado_por=actor,
        )
        _auditar_custodia_serie(
            serie,
            anterior_estado,
            anterior_tecnico,
            anterior_fecha,
            actor,
            tenant,
        )


def guardar_uso(
    orden, fecha_instalacion, cantidades, actor, series_por_material=None
):
    tenant = validar_cuenta_tenant(actor)
    if orden.tenant_id != tenant.pk:
        raise NoEncontrado
    if not isinstance(fecha_instalacion, date):
        raise PeriodoInvalido
    nuevo_periodo = periodo_de_fecha(fecha_instalacion)
    _validar_mes_abierto(tenant, orden.periodo)
    _validar_mes_abierto(tenant, nuevo_periodo)

    cantidades = cantidades or {}
    series_por_material = series_por_material or {}
    ids_materiales = {int(pk) for pk in cantidades}
    ids_materiales.update(int(pk) for pk in series_por_material)

    with transaction.atomic():
        Tenant.objects.select_for_update().get(pk=tenant.pk)
        orden = OrdenLiquidacion.objects.select_for_update().get(pk=orden.pk)
        usos_actuales = {
            uso.material_id: uso
            for uso in orden.usos.select_related("material").prefetch_related(
                "series_usadas"
            )
        }
        ids_materiales.update(
            material_id
            for material_id, uso in usos_actuales.items()
            if uso.material.es_seriado
        )

        materiales = {
            material.pk: material
            for material in Material.objects.filter(pk__in=ids_materiales)
        }
        for material_id in ids_materiales:
            material = materiales.get(material_id)
            if material is None:
                raise MaterialNoHabilitado

        anterior_periodo = orden.periodo
        anterior_fecha = orden.fecha_instalacion
        if nuevo_periodo != orden.periodo:
            if (
                OrdenLiquidacion.objects.filter(
                    tenant=tenant,
                    tecnico=orden.tecnico,
                    periodo=nuevo_periodo,
                    numero_normalizado=orden.numero_normalizado,
                )
                .exclude(pk=orden.pk)
                .exists()
            ):
                raise OrdenDuplicada
            orden.periodo = nuevo_periodo

        for material_id in sorted(ids_materiales):
            material = materiales[material_id]
            uso = usos_actuales.get(material_id)
            if material.es_seriado:
                seleccionadas = series_por_material.get(
                    material_id, series_por_material.get(str(material_id), [])
                )
                if uso is None and not seleccionadas:
                    continue
                if uso is None:
                    uso = UsoMaterialOrden.objects.create(
                        tenant=tenant,
                        orden=orden,
                        tecnico=orden.tecnico,
                        material=material,
                        cantidad=0,
                        creado_por=actor,
                    )
                    usos_actuales[material_id] = uso
                anterior = uso.cantidad
                _sincronizar_series_uso(
                    uso, material, seleccionadas, orden, actor, tenant
                )
                cantidad = len(set(int(pk) for pk in seleccionadas))
            else:
                cantidad = _cantidad(cantidades.get(material_id, 0))
                if uso is None:
                    uso = UsoMaterialOrden.objects.create(
                        tenant=tenant,
                        orden=orden,
                        tecnico=orden.tecnico,
                        material=material,
                        cantidad=0,
                        creado_por=actor,
                    )
                    usos_actuales[material_id] = uso
                anterior = uso.cantidad
                delta = cantidad - anterior
                if delta > 0:
                    disponible = obtener_stock_tecnico(
                        orden.tecnico, material
                    )
                    if delta > disponible:
                        raise SaldoInsuficiente(
                            "El uso supera el stock actual del técnico: "
                            f"disponible={disponible}, usado={anterior}, "
                            f"faltante={delta - disponible}"
                        )
                _mover_stock_consumo(
                    orden.tecnico, material, delta, actor, uso
                )

            uso.cantidad = cantidad
            uso.actualizado_por = actor
            uso.save(
                update_fields=[
                    "cantidad",
                    "actualizado_por",
                    "actualizado_en",
                ]
            )
            registrar_cambio(
                "UsoMaterialOrden",
                uso.pk,
                "cantidad",
                anterior,
                cantidad,
                actor,
                tenant=tenant,
            )
            _crear_advertencia_si_aplica(
                uso, cantidad, nuevo_periodo, actor
            )

        orden.fecha_instalacion = fecha_instalacion
        orden.actualizado_por = actor
        orden.save(
            update_fields=[
                "fecha_instalacion",
                "periodo",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "OrdenLiquidacion",
            orden.pk,
            "fecha_instalacion",
            anterior_fecha,
            fecha_instalacion,
            actor,
            tenant=tenant,
        )
        if anterior_periodo != orden.periodo:
            registrar_cambio(
                "OrdenLiquidacion",
                orden.pk,
                "periodo",
                anterior_periodo,
                orden.periodo,
                actor,
                tenant=tenant,
            )
    return orden


def _crear_advertencia_si_aplica(uso, cantidad, periodo, actor):
    factor = getattr(
        settings,
        "REGISTRO_FACTOR_ADVERTENCIA",
        getattr(settings, "REGISTRO_MATERIALES_FACTOR_ATIPICO", 3),
    )
    meses = getattr(settings, "REGISTRO_MESES_PROMEDIO", 3)
    cierres = list(
        CierreMensual.objects.filter(
            tenant=uso.tenant,
            estado=CierreMensual.CERRADO,
            periodo__lt=periodo,
        ).order_by("-periodo")[:meses]
    )
    if not cierres:
        return None
    total = (
        SaldoMensualMaterial.objects.filter(
            cierre__in=cierres, material=uso.material
        ).aggregate(total=Sum("usado"))["total"]
        or 0
    )
    promedio = total / len(cierres)
    if promedio <= 0 or cantidad <= factor * promedio:
        return None
    if uso.advertencias.filter(resuelta=False).exists():
        return None
    advertencia = AdvertenciaUso.objects.create(
        tenant=uso.tenant,
        uso=uso,
        mensaje=(
            f"La cantidad {cantidad} supera {factor} veces el promedio "
            f"mensual ({promedio:.2f}) de los últimos meses cerrados"
        ),
    )
    registrar_cambio(
        "AdvertenciaUso",
        advertencia.pk,
        "alta",
        "",
        advertencia.mensaje,
        actor,
        tenant=uso.tenant,
    )
    return advertencia


def resolver_advertencia(advertencia, justificacion, actor):
    tenant = validar_cuenta_tenant(actor)
    if advertencia.tenant_id != tenant.pk:
        raise NoEncontrado
    texto = " ".join((justificacion or "").split())
    if not texto:
        raise MotivoRequerido
    with transaction.atomic():
        advertencia.resuelta = True
        advertencia.justificacion = texto
        advertencia.resuelta_por = actor
        advertencia.resuelta_en = timezone.now()
        advertencia.save(
            update_fields=[
                "resuelta",
                "justificacion",
                "resuelta_por",
                "resuelta_en",
            ]
        )
        registrar_cambio(
            "AdvertenciaUso",
            advertencia.pk,
            "resuelta",
            False,
            True,
            actor,
            tenant=tenant,
        )
    return advertencia


def historial_orden(tenant, orden_id):
    orden = OrdenLiquidacion.objects.filter(
        pk=orden_id, tenant=tenant
    ).first()
    if orden is None:
        raise NoEncontrado
    usos = list(
        UsoMaterialOrden.objects.filter(orden=orden).values_list(
            "pk", flat=True
        )
    )
    return RegistroCambio.objects.filter(
        tenant=tenant,
        entidad__in=["OrdenLiquidacion", "UsoMaterialOrden"],
        entidad_id__in=[orden.pk] + usos,
    ).order_by("-fecha", "-id")


def registrar_saldo_inicial(tenant, material, periodo, cantidad, actor):
    tenant = validar_cuenta_tenant(actor)
    validar_periodo(periodo)
    _validar_mes_abierto(tenant, periodo)
    if material is None:
        raise MaterialNoHabilitado
    obtener_habilitado(tenant, material)
    cantidad = _cantidad(cantidad)
    despachos = despachos_del_periodo(tenant, periodo).get(material.pk, 0)
    uso = usado_del_periodo(tenant, periodo, material)
    if cantidad + despachos < uso:
        raise SaldoInsuficiente
    with transaction.atomic():
        Tenant.objects.select_for_update().get(pk=tenant.pk)
        saldo, creado = SaldoInicialPeriodo.objects.get_or_create(
            tenant=tenant,
            material=material,
            periodo=periodo,
            defaults={"cantidad": cantidad, "creado_por": actor},
        )
        anterior = 0 if creado else saldo.cantidad
        if not creado:
            saldo.cantidad = cantidad
            saldo.actualizado_por = actor
            saldo.save(
                update_fields=[
                    "cantidad",
                    "actualizado_por",
                    "actualizado_en",
                ]
            )
        registrar_cambio(
            "SaldoInicialPeriodo",
            saldo.pk,
            "alta" if creado else "cantidad",
            anterior,
            cantidad,
            actor,
            tenant=tenant,
        )
    return saldo


def _materiales_con_datos(tenant, periodo):
    ids = set()
    ids.update(
        MaterialHabilitado.objects.filter(tenant=tenant).values_list(
            "material_id", flat=True
        )
    )
    ids.update(
        SaldoInicialPeriodo.objects.filter(
            tenant=tenant, periodo=periodo
        ).values_list("material_id", flat=True)
    )
    ids.update(
        UsoMaterialOrden.objects.filter(
            tenant=tenant, orden__periodo=periodo
        ).values_list("material_id", flat=True)
    )
    ids.update(asignaciones_confirmadas_del_periodo(tenant, periodo))
    ids.update(
        StockTecnico.objects.filter(tenant=tenant).values_list(
            "material_id", flat=True
        )
    )
    return Material.objects.filter(pk__in=ids).order_by("codigo")


def dashboard_mensual(
    tenant, periodo, tecnico=None, material=None, desde=None, hasta=None
):
    validar_periodo(periodo)
    materiales = list(_materiales_con_datos(tenant, periodo))
    if material is not None:
        materiales = [m for m in materiales if m.pk == material.pk]
    ids = [mat.pk for mat in materiales]
    # Resuelve los saldos en bloque para evitar una consulta por material.
    manuales = dict(
        SaldoInicialPeriodo.objects.filter(
            tenant=tenant, periodo=periodo, material_id__in=ids
        ).values_list("material_id", "cantidad")
    )
    heredados = dict(
        SaldoMensualMaterial.objects.filter(
            tenant=tenant,
            material_id__in=ids,
            cierre__periodo=periodo_anterior(periodo),
            cierre__estado=CierreMensual.CERRADO,
        ).values_list("material_id", "saldo_final")
    )
    asignaciones = asignaciones_confirmadas_del_periodo(tenant, periodo)
    usos = usado_del_periodo(tenant, periodo, tecnico=tecnico)
    filas = []
    for mat in materiales:
        usado = usos.get(mat.pk, 0)
        if mat.pk in manuales:
            inicial = manuales[mat.pk]
        elif mat.pk in heredados:
            inicial = heredados[mat.pk]
        else:
            inicial = saldo_inicial_efectivo(tenant, mat, periodo)
        asignacion = asignaciones.get(mat.pk, 0)
        final = inicial + asignacion - usado
        filas.append(
            {
                "material": mat,
                "inicial": inicial,
                "asignaciones_confirmadas": asignacion,
                "usado": usado,
                "final": final,
                "alerta": final < 0,
            }
        )

    detalles = (
        UsoMaterialOrden.objects.filter(
            tenant=tenant, orden__periodo=periodo, cantidad__gt=0
        )
        .select_related("tecnico", "material")
        .order_by("tecnico__nif", "material__codigo")
    )
    if tecnico is not None:
        detalles = detalles.filter(tecnico=tecnico)
    if material is not None:
        detalles = detalles.filter(material=material)
    detalle = [
        {
            "tecnico": uso.tecnico,
            "material": uso.material,
            "cantidad": uso.cantidad,
        }
        for uso in detalles
    ]
    return {
        "periodo": periodo,
        "filas": filas,
        "detalle": detalle,
        "ordenes": OrdenLiquidacion.objects.filter(
            tenant=tenant, periodo=periodo
        ).count(),
        "tecnicos": len({fila["tecnico"].pk for fila in detalle}),
    }


def ordenes_pendientes(tenant, periodo=None, dias=None, tecnico=None):
    qs = OrdenLiquidacion.objects.filter(tenant=tenant).select_related(
        "tecnico"
    )
    if periodo:
        validar_periodo(periodo)
        qs = qs.filter(periodo=periodo)
    if tecnico is not None:
        qs = qs.filter(tecnico=tecnico)
    qs = qs.filter(
        ~Q(usos__cantidad__gt=0)
    ).distinct()
    if dias:
        limite = timezone.now() - timedelta(days=int(dias))
        qs = qs.filter(creado_en__lte=limite)
    return qs.order_by("creado_en", "numero_normalizado")


def _obtener_cierre(tenant, periodo):
    validar_periodo(periodo)
    cierre, _ = CierreMensual.objects.get_or_create(
        tenant=tenant, periodo=periodo
    )
    return cierre


def lista_chequeo(tenant, periodo):
    cierre = _obtener_cierre(tenant, periodo)
    justificados = {
        (just.tipo, just.referencia)
        for just in cierre.justificaciones.all()
    }
    pendientes = []
    for orden in ordenes_pendientes(tenant, periodo):
        if (
            JustificacionCierre.ORDEN_SIN_MATERIALES,
            orden.numero_normalizado,
        ) in justificados:
            continue
        pendientes.append(
            {
                "tipo": JustificacionCierre.ORDEN_SIN_MATERIALES,
                "referencia": orden.numero_normalizado,
                "descripcion": (
                    f"Orden {orden.numero_normalizado} de "
                    f"{orden.tecnico.nif} sin materiales"
                ),
            }
        )
    for fila in dashboard_mensual(tenant, periodo)["filas"]:
        if fila["final"] < 0 and (
            JustificacionCierre.SALDO_NEGATIVO,
            fila["material"].codigo,
        ) not in justificados:
            pendientes.append(
                {
                    "tipo": JustificacionCierre.SALDO_NEGATIVO,
                    "referencia": fila["material"].codigo,
                    "descripcion": (
                        f"Saldo negativo de {fila['material'].codigo}: "
                        f"{fila['final']}"
                    ),
                }
            )
    advertencias = AdvertenciaUso.objects.filter(
        tenant=tenant,
        resuelta=False,
        uso__orden__periodo=periodo,
    ).select_related("uso", "uso__material")
    for advertencia in advertencias:
        if (
            JustificacionCierre.ADVERTENCIA,
            str(advertencia.pk),
        ) in justificados:
            continue
        pendientes.append(
            {
                "tipo": JustificacionCierre.ADVERTENCIA,
                "referencia": str(advertencia.pk),
                "descripcion": advertencia.mensaje,
            }
        )
    return pendientes


def justificar_pendiente(cierre, tipo, referencia, motivo, actor):
    tenant = validar_cuenta_tenant(actor)
    if cierre.tenant_id != tenant.pk:
        raise NoEncontrado
    if tipo not in dict(JustificacionCierre.TIPOS):
        raise MotivoRequerido("El tipo de justificación no es válido")
    texto = " ".join((motivo or "").split())
    if not texto:
        raise MotivoRequerido
    with transaction.atomic():
        justificacion, _ = JustificacionCierre.objects.get_or_create(
            cierre=cierre,
            tipo=tipo,
            referencia=str(referencia),
            defaults={
                "tenant": tenant,
                "motivo": texto,
                "creado_por": actor,
            },
        )
        if tipo == JustificacionCierre.ADVERTENCIA:
            advertencia = AdvertenciaUso.objects.filter(
                pk=int(referencia), tenant=tenant
            ).first()
            if advertencia is not None and not advertencia.resuelta:
                advertencia.resuelta = True
                advertencia.justificacion = texto
                advertencia.resuelta_por = actor
                advertencia.resuelta_en = timezone.now()
                advertencia.save(
                    update_fields=[
                        "resuelta",
                        "justificacion",
                        "resuelta_por",
                        "resuelta_en",
                    ]
                )
        registrar_cambio(
            "JustificacionCierre",
            justificacion.pk,
            "alta",
            "",
            f"{tipo}; {referencia}; {texto}",
            actor,
            tenant=tenant,
        )
    return justificacion


def validar_backup_ref(backup_ref):
    texto = (backup_ref or "").strip()
    if not getattr(settings, "REGISTRO_BACKUP_REQUERIDO", True):
        return texto
    if not texto or not texto.startswith("backups/") or len(texto) <= len(
        "backups/"
    ):
        raise BackupRequerido
    return texto


def cerrar_mes(tenant, periodo, backup_ref, actor):
    tenant = validar_cuenta_tenant(actor)
    validar_periodo(periodo)
    referencia = validar_backup_ref(backup_ref)
    pendientes = lista_chequeo(tenant, periodo)
    if pendientes:
        raise CierreBloqueado
    with transaction.atomic():
        cierre = _obtener_cierre(tenant, periodo)
        cierre = CierreMensual.objects.select_for_update().get(
            pk=cierre.pk
        )
        if cierre.estado == CierreMensual.CERRADO:
            raise PeriodoCerrado("El mes ya está cerrado")
        datos = []
        for fila in dashboard_mensual(tenant, periodo)["filas"]:
            datos.append(
                SaldoMensualMaterial(
                    cierre=cierre,
                    tenant=tenant,
                    material=fila["material"],
                    saldo_inicial=fila["inicial"],
                    despachos=fila["asignaciones_confirmadas"],
                    usado=fila["usado"],
                    saldo_final=fila["final"],
                )
            )
        cierre.saldos.all().delete()
        SaldoMensualMaterial.objects.bulk_create(datos)
        cierre.estado = CierreMensual.CERRADO
        cierre.cerrado_por = actor
        cierre.cerrado_en = timezone.now()
        cierre.backup_ref = referencia
        cierre.backup_en = timezone.now()
        cierre.save(
            update_fields=[
                "estado",
                "cerrado_por",
                "cerrado_en",
                "backup_ref",
                "backup_en",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "CierreMensual",
            cierre.pk,
            "cerrado",
            "",
            f"periodo={periodo}; backup={referencia}",
            actor,
            tenant=tenant,
        )
    return cierre


def reabrir_mes(cierre, motivo, actor):
    tenant = validar_cuenta_tenant(actor)
    if cierre.tenant_id != tenant.pk:
        raise NoEncontrado
    texto = " ".join((motivo or "").split())
    if not texto:
        raise MotivoRequerido
    with transaction.atomic():
        cierre = CierreMensual.objects.select_for_update().get(pk=cierre.pk)
        if cierre.estado != CierreMensual.CERRADO:
            raise PeriodoCerrado("El mes no está cerrado")
        cierre.estado = CierreMensual.ABIERTO
        cierre.version += 1
        cierre.reabierto_por = actor
        cierre.reabierto_en = timezone.now()
        cierre.motivo_reapertura = texto
        cierre.save(
            update_fields=[
                "estado",
                "version",
                "reabierto_por",
                "reabierto_en",
                "motivo_reapertura",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "CierreMensual",
            cierre.pk,
            "reabierto",
            "",
            texto,
            actor,
            tenant=tenant,
        )
    return cierre
