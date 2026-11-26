"""Servicios de conciliación de stock."""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from acceso.models import Rol
from auditoria.services import registrar_cambio
from materiales.models import Material
from series.models import EstadoSerie, Serie
from series.services import crear_serie
from stock.models import StockTecnico
from stock.services import (
    decrementar_stock_tecnico,
    incrementar_stock_tecnico,
)
from tecnicos.models import Tecnico
from tenants.models import Tenant

from .excel import (
    CantidadInvalida,
    ColumnasFaltantes,
    FormatoInvalido,
    HojaGeneralAusente,
    leer_reporte,
)
from .models import (
    Conciliacion,
    DiferenciaCantidad,
    DiferenciaSerie,
    EstadoConciliacion,
    MaterialNoCatalogado,
    TipoDiferenciaSerie,
)

NIF_RE = re.compile(r"^LA[0-9]{4}$")
SERIE_RE = re.compile(r"^[A-Z0-9]{12}$")


class ErrorConciliacion(Exception):
    mensaje = "Error de conciliación"

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)

    def __str__(self):
        return self.args[0]


class PermisoDenegado(ErrorConciliacion):
    mensaje = "No tienes permiso para cargar conciliaciones"


class ConciliacionEnRevision(ErrorConciliacion):
    mensaje = "Ya hay una conciliación en revisión"


class TecnicosFueraRegion(ErrorConciliacion):
    mensaje = "El reporte contiene técnicos que no pertenecen a la región"


class TecnicoFormatoInvalido(ErrorConciliacion):
    mensaje = "El NIF del técnico no tiene el formato LAXXXX"


class MaterialNoExiste(ErrorConciliacion):
    mensaje = "El reporte contiene materiales que no existen en el catálogo"


class SerieFormatoInvalido(ErrorConciliacion):
    mensaje = "La serie no tiene el formato correcto"


class SerieDuplicada(ErrorConciliacion):
    mensaje = "La serie está duplicada en el reporte"


class SerieInstalada(ErrorConciliacion):
    mensaje = "La serie está instalada y no puede reasignarse"


class SerieInactiva(ErrorConciliacion):
    mensaje = "La serie está inactiva y no puede conciliarse"


class SerieReservada(ErrorConciliacion):
    mensaje = "La serie está reservada para otra operación"


class SerieFueraTenant(ErrorConciliacion):
    mensaje = "La serie no pertenece a este tenant"


class MaterialSerieIncoherente(ErrorConciliacion):
    mensaje = "El material no coincide con la presencia de número de serie"


class EstadoConciliacionInvalido(ErrorConciliacion):
    mensaje = "Solo se puede aprobar o rechazar una conciliación en revisión"


class AprobacionBloqueada(ErrorConciliacion):
    mensaje = (
        "Aprobación bloqueada: hay materiales que no existen en el catálogo"
    )


class HuboCambios(ErrorConciliacion):
    mensaje = "Hubo cambios, revise de nuevo"


class NoEncontrado(ErrorConciliacion):
    mensaje = "La conciliación no existe"


class ArchivoNoDisponible(ErrorConciliacion):
    mensaje = "El archivo no está disponible"


class MotivoInvalido(ErrorConciliacion):
    mensaje = "El motivo del rechazo no puede superar los 1000 caracteres"


@dataclass(frozen=True)
class ClasificacionTecnicos:
    presentes: list
    ignorados: set


@dataclass
class ReporteValidado:
    filas: list
    materiales: dict
    no_catalogados: dict


@dataclass(frozen=True)
class DiferenciaSerieCalc:
    tecnico: Tecnico
    material: Material
    numero: str
    tipo: str
    lote: str = ""
    tecnico_sistema: Tecnico | None = None


@dataclass(frozen=True)
class DiferenciaCantidadCalc:
    tecnico: Tecnico
    material: Material
    cantidad_sistema: int
    cantidad_reporte: int

    @property
    def diferencia(self):
        return self.cantidad_reporte - self.cantidad_sistema


@dataclass(frozen=True)
class AjusteCantidad:
    tecnico_id: int
    material_id: int
    cantidad_anterior: int
    cantidad_nueva: int


@dataclass(frozen=True)
class ResultadoConciliacion:
    conciliacion_id: int
    series_creadas: list = field(default_factory=list)
    series_instaladas: list = field(default_factory=list)
    series_reasignadas: list = field(default_factory=list)
    ajustes_cantidad: list = field(default_factory=list)
    fecha_aprobacion: object = None


class _ArchivoEnMemoria:
    def __init__(self, nombre, contenido):
        self.name = nombre
        self._contenido = contenido

    def read(self):
        return self._contenido


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


def validar_puede_cargar(tenant):
    if Conciliacion.objects.filter(
        tenant=tenant, estado=EstadoConciliacion.EN_REVISION
    ).exists():
        raise ConciliacionEnRevision


def obtener_conciliacion(tenant, conciliacion_id):
    conciliacion = Conciliacion.objects.filter(
        pk=conciliacion_id, tenant=tenant
    ).first()
    if conciliacion is None:
        raise NoEncontrado
    return conciliacion


def listar_conciliaciones(tenant, estado=None):
    conciliaciones = Conciliacion.objects.filter(tenant=tenant)
    if estado:
        conciliaciones = conciliaciones.filter(estado=estado)
    return conciliaciones.order_by("-fecha_carga", "-id")


def clasificar_tecnicos(tenant, filas):
    presentes = []
    ignorados = set()
    vistos = {}
    for fila in filas:
        nif = fila.nif
        if not NIF_RE.match(nif or ""):
            raise TecnicoFormatoInvalido
        if nif in vistos:
            continue
        tecnico = (
            Tecnico.objects.select_related("tenant")
            .filter(nif=nif)
            .first()
        )
        if tecnico is None:
            raise TecnicosFueraRegion
        if tecnico.tenant_id == tenant.pk:
            presentes.append(tecnico)
            vistos[nif] = tecnico
        elif tecnico.tenant.region_id == tenant.region_id:
            ignorados.add(nif)
            vistos[nif] = None
        else:
            raise TecnicosFueraRegion
    return ClasificacionTecnicos(
        presentes=sorted(presentes, key=lambda t: t.pk),
        ignorados=ignorados,
    )


def validar_filas(tenant, filas, clasificacion):
    presentes_nif = {tecnico.nif: tecnico for tecnico in clasificacion.presentes}
    codigos = {fila.material_codigo for fila in filas}
    materiales = {
        material.codigo: material
        for material in Material.objects.filter(codigo__in=codigos)
    }
    no_catalogados = {}
    filas_validas = []
    series_vistas = set()

    for fila in filas:
        if fila.nif in clasificacion.ignorados or fila.nif not in presentes_nif:
            continue
        tecnico = presentes_nif[fila.nif]
        material = materiales.get(fila.material_codigo)
        if material is None:
            datos = no_catalogados.setdefault(
                fila.material_codigo,
                {
                    "descripcion": fila.descripcion,
                    "tecnico_nif": fila.nif,
                    "filas": 0,
                },
            )
            datos["filas"] += 1
            continue
        if material.es_seriado:
            numero = fila.numero_serie
            if not numero or not SERIE_RE.match(numero):
                raise SerieFormatoInvalido
            if numero in series_vistas:
                raise SerieDuplicada
            series_vistas.add(numero)
            existente = Serie.objects.filter(numero=numero).first()
            if existente is not None:
                if existente.tenant_id != tenant.pk:
                    raise SerieFueraTenant
                if existente.estado == EstadoSerie.INSTALADA:
                    raise SerieInstalada
        else:
            if fila.numero_serie:
                raise MaterialSerieIncoherente
            if fila.libre_utilizacion is None:
                raise CantidadInvalida
        filas_validas.append((fila, tecnico, material))

    return ReporteValidado(
        filas=filas_validas,
        materiales=materiales,
        no_catalogados=no_catalogados,
    )


def comparar_series(tenant, clasificacion, valido):
    diferencias = []
    reporte = {}
    for fila, tecnico, material in valido.filas:
        if not material.es_seriado:
            continue
        reporte[fila.numero_serie] = (tecnico, material, fila.lote)

    existentes = {
        serie.numero: serie
        for serie in Serie.objects.filter(
            tenant=tenant, numero__in=list(reporte)
        ).select_related("tecnico", "material")
    }

    for numero, (tecnico, material, lote) in reporte.items():
        serie = existentes.get(numero)
        if serie is None:
            diferencias.append(
                DiferenciaSerieCalc(
                    tecnico=tecnico,
                    material=material,
                    numero=numero,
                    tipo=TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA,
                    lote=lote,
                )
            )
        elif serie.tecnico_id is None:
            if serie.estado == EstadoSerie.RESERVADA:
                raise SerieReservada(
                    f"La serie {numero} está reservada para otra operación"
                )
            if serie.estado == EstadoSerie.INACTIVA:
                raise SerieInactiva(
                    f"La serie {numero} está inactiva y no se puede conciliar"
                )
            diferencias.append(
                DiferenciaSerieCalc(
                    tecnico=tecnico,
                    material=material,
                    numero=numero,
                    tipo=TipoDiferenciaSerie.EN_SISTEMA_SIN_TECNICO,
                    lote=lote,
                )
            )
        elif serie.tecnico_id != tecnico.pk:
            diferencias.append(
                DiferenciaSerieCalc(
                    tecnico=tecnico,
                    material=material,
                    numero=numero,
                    tipo=TipoDiferenciaSerie.EN_OTRO_TECNICO,
                    lote=lote,
                    tecnico_sistema=serie.tecnico,
                )
            )

    sistema = (
        Serie.objects.filter(
            tenant=tenant,
            estado=EstadoSerie.ASIGNADA,
            tecnico__in=clasificacion.presentes,
        )
        .select_related("tecnico", "material")
        .order_by("numero")
    )
    for serie in sistema:
        if serie.numero in reporte:
            continue
        diferencias.append(
            DiferenciaSerieCalc(
                tecnico=serie.tecnico,
                material=serie.material,
                numero=serie.numero,
                tipo=TipoDiferenciaSerie.EN_SISTEMA_NO_REPORTE,
                lote=serie.lote,
            )
        )
    return diferencias


def comparar_cantidades(tenant, clasificacion, valido):
    reporte = {}
    materiales_reporte = {}
    for fila, tecnico, material in valido.filas:
        if material.es_seriado:
            continue
        clave = (tecnico.pk, material.pk)
        reporte[clave] = reporte.get(clave, 0) + fila.libre_utilizacion
        materiales_reporte[material.pk] = material

    filas_sistema = list(
        StockTecnico.objects.filter(
            tenant=tenant,
            tecnico__in=clasificacion.presentes,
            material__es_seriado=False,
        ).select_related("tecnico", "material")
    )
    sistema = {
        (fila.tecnico_id, fila.material_id): fila for fila in filas_sistema
    }
    materiales = dict(materiales_reporte)
    for fila in filas_sistema:
        materiales.setdefault(fila.material_id, fila.material)

    tecnicos = {tecnico.pk: tecnico for tecnico in clasificacion.presentes}
    diferencias = []
    for clave in set(reporte) | set(sistema):
        tecnico_id, material_id = clave
        material = materiales.get(material_id)
        if material is None:
            continue
        fila_sistema = sistema.get(clave)
        cantidad_sistema = fila_sistema.cantidad if fila_sistema else 0
        cantidad_reporte = reporte.get(clave, 0)
        if cantidad_sistema == cantidad_reporte:
            continue
        diferencias.append(
            DiferenciaCantidadCalc(
                tecnico=tecnicos[tecnico_id],
                material=material,
                cantidad_sistema=cantidad_sistema,
                cantidad_reporte=cantidad_reporte,
            )
        )
    return diferencias


def _tecnicos_de_calculos(series, cantidades):
    tecnicos = {}
    for diferencia in series:
        tecnicos[diferencia.tecnico.pk] = diferencia.tecnico
        if diferencia.tecnico_sistema is not None:
            tecnicos[diferencia.tecnico_sistema.pk] = diferencia.tecnico_sistema
    for diferencia in cantidades:
        tecnicos[diferencia.tecnico.pk] = diferencia.tecnico
    return sorted(tecnicos.values(), key=lambda t: t.pk)



def calcular_huella_stock(tenant, tecnicos_presentes, numeros=None):
    tecnicos = sorted(tecnicos_presentes, key=lambda t: t.pk)
    ids = [tecnico.pk for tecnico in tecnicos]
    datos = {"stocks": [], "series": []}
    for tecnico_id, material_id, cantidad in (
        StockTecnico.objects.filter(tenant=tenant, tecnico_id__in=ids)
        .order_by("tecnico_id", "material_id")
        .values_list("tecnico_id", "material_id", "cantidad")
    ):
        datos["stocks"].append([tecnico_id, material_id, cantidad])

    series = Serie.objects.filter(tenant=tenant)
    if numeros:
        series = series.filter(
            Q(tecnico_id__in=ids) | Q(numero__in=list(numeros))
        )
    else:
        series = series.filter(tecnico_id__in=ids)
    for numero, material_id, estado, tecnico_id, asignada_en in (
        series.order_by("numero").values_list(
            "numero", "material_id", "estado", "tecnico_id", "asignada_en"
        )
    ):
        datos["series"].append(
            [
                numero,
                material_id,
                estado,
                tecnico_id or 0,
                asignada_en.isoformat() if asignada_en else "",
            ]
        )
    canonico = json.dumps(datos, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonico.encode()).hexdigest()


def _leer_y_validar(tenant, nombre, contenido):
    reporte = leer_reporte(_ArchivoEnMemoria(nombre, contenido))
    clasificacion = clasificar_tecnicos(tenant, reporte.filas)
    validado = validar_filas(tenant, reporte.filas, clasificacion)
    return reporte, clasificacion, validado


def _guardar_archivo(tenant, nombre, contenido):
    relativa = (
        Path(settings.CONCILIACIONES_DIR)
        / tenant.codigo
        / f"{uuid.uuid4().hex}.xlsx"
    )
    absoluta = Path(settings.MEDIA_ROOT) / relativa
    absoluta.parent.mkdir(parents=True, exist_ok=True)
    absoluta.write_bytes(contenido)
    return str(relativa).replace("\\", "/")


def _auditar_alta(conciliacion, actor):
    registrar_cambio(
        "Conciliacion",
        conciliacion.pk,
        "alta",
        "",
        f"archivo={conciliacion.archivo_nombre}; hash={conciliacion.hash_sha256}",
        actor,
        tenant=conciliacion.tenant,
    )
    registrar_cambio(
        "Conciliacion",
        conciliacion.pk,
        "archivo",
        "",
        conciliacion.archivo_ruta,
        actor,
        tenant=conciliacion.tenant,
    )


def crear_conciliacion(actor, archivo):
    tenant = validar_cuenta_tenant(actor)
    validar_puede_cargar(tenant)
    nombre = Path(getattr(archivo, "name", "") or "").name
    contenido = archivo.read()
    if isinstance(contenido, str):
        contenido = contenido.encode()
    if len(contenido) > settings.CONCILIACIONES_MAX_BYTES:
        raise FormatoInvalido
    hash_archivo = hashlib.sha256(contenido).hexdigest()
    _, clasificacion, validado = _leer_y_validar(tenant, nombre, contenido)
    series = comparar_series(tenant, clasificacion, validado)
    cantidades = comparar_cantidades(tenant, clasificacion, validado)
    numeros = {diferencia.numero for diferencia in series}
    afectados = _tecnicos_de_calculos(series, cantidades)
    huella = calcular_huella_stock(tenant, afectados, numeros)

    ruta = _guardar_archivo(tenant, nombre, contenido)
    try:
        with transaction.atomic():
            conciliacion = Conciliacion.objects.create(
                tenant=tenant,
                region=tenant.region,
                archivo_nombre=nombre,
                archivo_ruta=ruta,
                hash_sha256=hash_archivo,
                huella_stock=huella,
                creado_por=actor,
            )
            _guardar_diferencias(conciliacion, series, cantidades, validado)
            _auditar_alta(conciliacion, actor)
    except IntegrityError as exc:
        # Dos cargas simultáneas compiten por el índice parcial de una sola
        # conciliación EN_REVISION por tenant. Se traduce a un error de
        # dominio para que la vista responda 409 en lugar de 500.
        (Path(settings.MEDIA_ROOT) / ruta).unlink(missing_ok=True)
        raise ConciliacionEnRevision from exc
    except Exception:
        (Path(settings.MEDIA_ROOT) / ruta).unlink(missing_ok=True)
        raise
    return conciliacion


def _guardar_diferencias(conciliacion, series, cantidades, validado):
    DiferenciaSerie.objects.bulk_create(
        [
            DiferenciaSerie(
                tenant=conciliacion.tenant,
                conciliacion=conciliacion,
                tecnico=diferencia.tecnico,
                material=diferencia.material,
                numero=diferencia.numero,
                tipo=diferencia.tipo,
                tecnico_sistema=diferencia.tecnico_sistema,
                lote=diferencia.lote,
            )
            for diferencia in series
        ]
    )
    DiferenciaCantidad.objects.bulk_create(
        [
            DiferenciaCantidad(
                tenant=conciliacion.tenant,
                conciliacion=conciliacion,
                tecnico=diferencia.tecnico,
                material=diferencia.material,
                cantidad_sistema=diferencia.cantidad_sistema,
                cantidad_reporte=diferencia.cantidad_reporte,
                diferencia=diferencia.diferencia,
            )
            for diferencia in cantidades
        ]
    )
    MaterialNoCatalogado.objects.bulk_create(
        [
            MaterialNoCatalogado(
                tenant=conciliacion.tenant,
                conciliacion=conciliacion,
                codigo=codigo,
                descripcion=datos["descripcion"],
                tecnico_nif=datos["tecnico_nif"],
                filas=datos["filas"],
            )
            for codigo, datos in validado.no_catalogados.items()
        ]
    )


def _contenido_guardado(conciliacion):
    if not conciliacion.archivo_ruta:
        raise ArchivoNoDisponible
    ruta = (Path(settings.MEDIA_ROOT) / conciliacion.archivo_ruta).resolve()
    raiz = Path(settings.MEDIA_ROOT).resolve()
    if raiz not in ruta.parents or not ruta.exists():
        raise ArchivoNoDisponible
    return ruta.read_bytes()


def recalcular_diferencias(conciliacion, actor):
    tenant = validar_cuenta_tenant(actor, conciliacion.tenant)
    if conciliacion.estado != EstadoConciliacion.EN_REVISION:
        raise EstadoConciliacionInvalido
    contenido = _contenido_guardado(conciliacion)
    _, clasificacion, validado = _leer_y_validar(
        tenant, conciliacion.archivo_nombre, contenido
    )
    series = comparar_series(tenant, clasificacion, validado)
    cantidades = comparar_cantidades(tenant, clasificacion, validado)
    numeros = {diferencia.numero for diferencia in series}
    afectados = _tecnicos_de_calculos(series, cantidades)
    huella = calcular_huella_stock(tenant, afectados, numeros)

    with transaction.atomic():
        bloqueada = Conciliacion.objects.select_for_update().get(
            pk=conciliacion.pk
        )
        if bloqueada.estado != EstadoConciliacion.EN_REVISION:
            raise EstadoConciliacionInvalido
        bloqueada.diferencias_series.all().delete()
        bloqueada.diferencias_cantidades.all().delete()
        bloqueada.materiales_no_catalogados.all().delete()
        _guardar_diferencias(bloqueada, series, cantidades, validado)
        bloqueada.huella_stock = huella
        bloqueada.requiere_revision = True
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "huella_stock",
                "requiere_revision",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "Conciliacion",
            bloqueada.pk,
            "recalculo",
            "",
            f"series={len(series)}; cantidades={len(cantidades)}",
            actor,
            tenant=bloqueada.tenant,
        )
    return bloqueada


def _tecnicos_de(conciliacion):
    tecnicos = {}
    for diferencia in conciliacion.diferencias_series.all():
        tecnicos[diferencia.tecnico_id] = diferencia.tecnico
        if diferencia.tecnico_sistema_id:
            tecnicos[diferencia.tecnico_sistema_id] = (
                diferencia.tecnico_sistema
            )
    for diferencia in conciliacion.diferencias_cantidades.all():
        tecnicos[diferencia.tecnico_id] = diferencia.tecnico
    return sorted(tecnicos.values(), key=lambda t: t.pk)


def _ajustar_cantidad(tecnico, material, objetivo, actor):
    actual = (
        StockTecnico.objects.filter(tecnico=tecnico, material=material)
        .values_list("cantidad", flat=True)
        .first()
        or 0
    )
    if objetivo == actual:
        return None
    if objetivo > actual:
        incrementar_stock_tecnico(tecnico, material, objetivo - actual, actor)
    else:
        decrementar_stock_tecnico(tecnico, material, actual - objetivo, actor)
    return AjusteCantidad(
        tecnico_id=tecnico.pk,
        material_id=material.pk,
        cantidad_anterior=actual,
        cantidad_nueva=objetivo,
    )


def aprobar_conciliacion(conciliacion, actor):
    tenant = validar_cuenta_tenant(actor, conciliacion.tenant)
    conciliacion = obtener_conciliacion(tenant, conciliacion.pk)
    if conciliacion.estado != EstadoConciliacion.EN_REVISION:
        raise EstadoConciliacionInvalido

    numeros = set(
        conciliacion.diferencias_series.values_list("numero", flat=True)
    )
    tecnicos = _tecnicos_de(conciliacion)
    huella_actual = calcular_huella_stock(tenant, tecnicos, numeros)
    if huella_actual != conciliacion.huella_stock:
        recalcular_diferencias(conciliacion, actor)
        registrar_cambio(
            "Conciliacion",
            conciliacion.pk,
            "hubo_cambios",
            conciliacion.huella_stock,
            huella_actual,
            actor,
            tenant=tenant,
        )
        raise HuboCambios

    if conciliacion.materiales_no_catalogados.exists():
        raise AprobacionBloqueada

    ahora = timezone.now()
    creadas = []
    instaladas = []
    reasignadas = []
    ajustes = []

    with transaction.atomic():
        bloqueada = Conciliacion.objects.select_for_update().get(
            pk=conciliacion.pk
        )
        if bloqueada.estado != EstadoConciliacion.EN_REVISION:
            raise EstadoConciliacionInvalido
        Tenant.objects.select_for_update().get(pk=tenant.pk)

        diferencias_series = list(
            bloqueada.diferencias_series.select_related(
                "tecnico", "material", "tecnico_sistema"
            )
        )
        diferencias_cantidades = list(
            bloqueada.diferencias_cantidades.select_related(
                "tecnico", "material"
            )
        )
        tecnicos_bloqueados = _tecnicos_de(bloqueada)
        list(
            StockTecnico.objects.select_for_update()
            .filter(tenant=tenant, tecnico__in=tecnicos_bloqueados)
            .order_by("tecnico_id", "material_id")
        )

        numeros_bloqueados = sorted(
            {diferencia.numero for diferencia in diferencias_series}
        )
        series_bloqueadas = {
            serie.numero: serie
            for serie in Serie.objects.select_for_update()
            .filter(tenant=tenant, numero__in=numeros_bloqueados)
            .order_by("numero")
        }

        huella_actual = calcular_huella_stock(
            tenant, tecnicos_bloqueados, numeros_bloqueados
        )
        if huella_actual != bloqueada.huella_stock:
            raise HuboCambios

        for diferencia in diferencias_series:
            if diferencia.tipo == TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA:
                serie = crear_serie(
                    tenant,
                    tenant.region,
                    diferencia.material,
                    diferencia.numero,
                    diferencia.lote,
                    actor,
                    estado=EstadoSerie.ASIGNADA,
                    tecnico=diferencia.tecnico,
                    asignada_en=ahora,
                )
                creadas.append(serie.pk)
                registrar_cambio(
                    "Serie",
                    serie.pk,
                    "alta",
                    "",
                    f"{serie.numero}; tecnico={diferencia.tecnico.nif}",
                    actor,
                    tenant=tenant,
                )
            elif diferencia.tipo in {
                TipoDiferenciaSerie.EN_OTRO_TECNICO,
                TipoDiferenciaSerie.EN_SISTEMA_SIN_TECNICO,
            }:
                serie = series_bloqueadas.get(diferencia.numero)
                if serie is None:
                    raise HuboCambios
                if (
                    diferencia.tipo
                    == TipoDiferenciaSerie.EN_SISTEMA_SIN_TECNICO
                    and serie.estado != EstadoSerie.DISPONIBLE
                ):
                    raise HuboCambios
                anterior = serie.tecnico_id
                anterior_fecha = serie.asignada_en
                anterior_estado = serie.estado
                serie.tecnico = diferencia.tecnico
                serie.estado = EstadoSerie.ASIGNADA
                serie.asignada_en = ahora
                serie.actualizado_por = actor
                serie.save(
                    update_fields=[
                        "tecnico",
                        "estado",
                        "asignada_en",
                        "actualizado_por",
                        "actualizado_en",
                    ]
                )
                reasignadas.append(serie.pk)
                if anterior_estado != serie.estado:
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
                    anterior,
                    serie.tecnico_id,
                    actor,
                    tenant=tenant,
                )
                registrar_cambio(
                    "Serie",
                    serie.pk,
                    "asignada_en",
                    anterior_fecha,
                    ahora,
                    actor,
                    tenant=tenant,
                )
            elif (
                diferencia.tipo
                == TipoDiferenciaSerie.EN_SISTEMA_NO_REPORTE
            ):
                serie = series_bloqueadas.get(diferencia.numero)
                if serie is None:
                    raise HuboCambios
                anterior = serie.estado
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
                instaladas.append(serie.pk)
                registrar_cambio(
                    "Serie",
                    serie.pk,
                    "estado",
                    anterior,
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

        for diferencia in diferencias_cantidades:
            ajuste = _ajustar_cantidad(
                diferencia.tecnico,
                diferencia.material,
                diferencia.cantidad_reporte,
                actor,
            )
            if ajuste is not None:
                ajustes.append(ajuste)

        pares_seriados = set()
        for diferencia in diferencias_cantidades:
            if diferencia.material.es_seriado:
                pares_seriados.add(
                    (diferencia.tecnico_id, diferencia.material_id)
                )
        for diferencia in diferencias_series:
            pares_seriados.add(
                (diferencia.tecnico_id, diferencia.material_id)
            )
            if diferencia.tecnico_sistema_id:
                pares_seriados.add(
                    (diferencia.tecnico_sistema_id, diferencia.material_id)
                )
        for tecnico in tecnicos_bloqueados:
            for material_id in (
                StockTecnico.objects.filter(
                    tenant=tenant, tecnico=tecnico, material__es_seriado=True
                ).values_list("material_id", flat=True)
            ):
                pares_seriados.add((tecnico.pk, material_id))

        tecnicos_por_id = {tecnico.pk: tecnico for tecnico in tecnicos_bloqueados}
        for tecnico_id, material_id in sorted(pares_seriados):
            tecnico = tecnicos_por_id.get(tecnico_id)
            if tecnico is None:
                continue
            material = Material.objects.get(pk=material_id)
            objetivo = Serie.objects.filter(
                tenant=tenant,
                tecnico_id=tecnico_id,
                material_id=material_id,
                estado=EstadoSerie.ASIGNADA,
            ).count()
            ajuste = _ajustar_cantidad(tecnico, material, objetivo, actor)
            if ajuste is not None:
                ajustes.append(ajuste)

        total_ajustes = (
            len(creadas)
            + len(instaladas)
            + len(reasignadas)
            + len(ajustes)
        )
        bloqueada.estado = EstadoConciliacion.APROBADA
        bloqueada.fecha_aprobacion = ahora
        bloqueada.aprobado_por = actor
        bloqueada.actualizado_por = actor
        bloqueada.requiere_revision = False
        bloqueada.ajustes_aplicados = total_ajustes
        bloqueada.save(
            update_fields=[
                "estado",
                "fecha_aprobacion",
                "aprobado_por",
                "actualizado_por",
                "requiere_revision",
                "ajustes_aplicados",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "Conciliacion",
            bloqueada.pk,
            "estado",
            EstadoConciliacion.EN_REVISION,
            EstadoConciliacion.APROBADA,
            actor,
            tenant=tenant,
        )

    return ResultadoConciliacion(
        conciliacion_id=bloqueada.pk,
        series_creadas=creadas,
        series_instaladas=instaladas,
        series_reasignadas=reasignadas,
        ajustes_cantidad=ajustes,
        fecha_aprobacion=ahora,
    )


def rechazar_conciliacion(conciliacion, actor, motivo=""):
    tenant = validar_cuenta_tenant(actor, conciliacion.tenant)
    motivo = " ".join((motivo or "").split())
    if len(motivo) > 1000:
        raise MotivoInvalido
    with transaction.atomic():
        bloqueada = Conciliacion.objects.select_for_update().get(
            pk=conciliacion.pk
        )
        if bloqueada.tenant_id != tenant.pk:
            raise NoEncontrado
        if bloqueada.estado != EstadoConciliacion.EN_REVISION:
            raise EstadoConciliacionInvalido
        bloqueada.estado = EstadoConciliacion.RECHAZADA
        bloqueada.fecha_rechazo = timezone.now()
        bloqueada.motivo_rechazo = motivo
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "estado",
                "fecha_rechazo",
                "motivo_rechazo",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "Conciliacion",
            bloqueada.pk,
            "estado",
            EstadoConciliacion.EN_REVISION,
            EstadoConciliacion.RECHAZADA,
            actor,
            tenant=tenant,
        )
        if motivo:
            registrar_cambio(
                "Conciliacion",
                bloqueada.pk,
                "motivo_rechazo",
                "",
                motivo,
                actor,
                tenant=tenant,
            )
    return bloqueada


def detalle_conciliacion(conciliacion):
    return {
        "series": {
            "en_reporte_no_sistema": conciliacion.diferencias_series.filter(
                tipo=TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA
            )
            .select_related("tecnico", "material")
            .order_by("numero"),
            "en_sistema_no_reporte": conciliacion.diferencias_series.filter(
                tipo=TipoDiferenciaSerie.EN_SISTEMA_NO_REPORTE
            )
            .select_related("tecnico", "material")
            .order_by("numero"),
            "en_otro_tecnico": conciliacion.diferencias_series.filter(
                tipo=TipoDiferenciaSerie.EN_OTRO_TECNICO
            )
            .select_related("tecnico", "material", "tecnico_sistema")
            .order_by("numero"),
            "en_sistema_sin_tecnico": (
                conciliacion.diferencias_series.filter(
                    tipo=TipoDiferenciaSerie.EN_SISTEMA_SIN_TECNICO
                )
                .select_related("tecnico", "material")
                .order_by("numero")
            ),
        },
        "cantidades": conciliacion.diferencias_cantidades.select_related(
            "tecnico", "material"
        ).order_by("tecnico__nif", "material__codigo"),
        "no_catalogados": conciliacion.materiales_no_catalogados.order_by(
            "codigo"
        ),
        "alertas": alertas_conciliacion(conciliacion),
    }


def alertas_conciliacion(conciliacion):
    series = conciliacion.diferencias_series.all()
    material_ajeno = [
        diferencia
        for diferencia in series
        if diferencia.tipo == TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA
    ]
    faltantes = [
        diferencia
        for diferencia in series
        if diferencia.tipo == TipoDiferenciaSerie.EN_SISTEMA_NO_REPORTE
    ]
    conteo = {}
    for diferencia in series:
        conteo[diferencia.tecnico_id] = (
            conteo.get(diferencia.tecnico_id, 0) + 1
        )
    for diferencia in conciliacion.diferencias_cantidades.all():
        conteo[diferencia.tecnico_id] = (
            conteo.get(diferencia.tecnico_id, 0) + 1
        )
    tecnicos = Tecnico.objects.filter(pk__in=conteo).order_by("nif")
    inconsistentes = [
        {"tecnico": tecnico, "diferencias": conteo[tecnico.pk]}
        for tecnico in tecnicos
        if conteo[tecnico.pk] >= 2
    ]
    return {
        "material_ajeno": material_ajeno,
        "series_faltantes": faltantes,
        "tecnicos_inconsistentes": inconsistentes,
    }
