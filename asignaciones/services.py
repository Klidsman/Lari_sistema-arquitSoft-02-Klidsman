"""Servicios de solicitudes de asignación."""

import hashlib
import hmac
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
from stock.services import obtener_stock_general
from tecnicos.models import Tecnico
from tenants.models import Tenant

from .excel import ExcelAsignacionInvalido, generar_excel_solicitud
from .models import EstadoSolicitud, LineaAsignacion, SolicitudAsignacion


class ValidacionAsignacion(Exception):
    def __init__(self, mensaje, errores=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.errores = errores or []

    def __str__(self):
        return self.mensaje


class PermisoDenegado(ValidacionAsignacion):
    pass


class TenantSuspendido(ValidacionAsignacion):
    pass


class SolicitudNoExiste(ValidacionAsignacion):
    pass


class TecnicoNoDisponible(ValidacionAsignacion):
    pass


class MaterialNoExiste(ValidacionAsignacion):
    pass


class SerieNoDisponible(ValidacionAsignacion):
    pass


class SerieDuplicada(ValidacionAsignacion):
    pass


class MaterialDuplicado(ValidacionAsignacion):
    pass


class CantidadInvalida(ValidacionAsignacion):
    pass


class CantidadExcedeDisponible(ValidacionAsignacion):
    pass


class EstadoSolicitudInvalido(ValidacionAsignacion):
    pass


class ArchivoNoDisponible(ValidacionAsignacion):
    def __init__(self, mensaje="El archivo no está disponible"):
        super().__init__(mensaje)


class ArchivoAlterado(ValidacionAsignacion):
    def __init__(self, mensaje="El archivo fue modificado, descarga bloqueada"):
        super().__init__(mensaje)


@dataclass(frozen=True)
class ErrorValidacion:
    fila: int | None
    campo: str
    mensaje: str


@dataclass(frozen=True)
class LineaValidada:
    material: Material
    serie: Serie | None
    cantidad: int
    lote: str
    fila_origen: int | None = None
    tecnico: Tecnico | None = None


@dataclass(frozen=True)
class SobranteMaterial:
    material: Material
    seriado: bool
    disponible: int
    solicitado: int
    sobrante: int


@dataclass(frozen=True)
class AlertaCupo:
    tecnico: Tecnico
    mensaje: str
    series: list


@dataclass(frozen=True)
class MaterialDisponible:
    material: Material
    disponible: int
    seriado: bool


def validar_cuenta_tenant(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado("No tienes permiso para crear asignaciones")
    if actor.rol != Rol.USUARIO_TENANT or not actor.tenant_id:
        raise PermisoDenegado("No tienes permiso para crear asignaciones")
    tenant = actor.tenant
    if tenant.estado != Tenant.ESTADO_ACTIVO:
        raise TenantSuspendido("El tenant está suspendido")
    return tenant


def validar_tecnico_para_asignacion(tenant, tecnico_id):
    tecnico = Tecnico.objects.filter(pk=tecnico_id, tenant=tenant).first()
    if tecnico is None:
        raise TecnicoNoDisponible("El técnico no existe en este tenant")
    if not tecnico.activo:
        raise TecnicoNoDisponible("El técnico está desactivado")
    return tecnico


def obtener_solicitud(tenant, solicitud_id):
    solicitud = SolicitudAsignacion.objects.filter(
        pk=solicitud_id, tenant=tenant
    ).first()
    if solicitud is None:
        raise SolicitudNoExiste("La solicitud no existe")
    return solicitud


def obtener_detalle_solicitud(tenant, solicitud_id):
    solicitud = obtener_solicitud(tenant, solicitud_id)
    return (
        SolicitudAsignacion.objects.filter(pk=solicitud.pk)
        .select_related("tenant", "region", "creado_por")
        .prefetch_related("lineas__material", "lineas__serie", "lineas__tecnico")
        .get()
    )


def listar_solicitudes(tenant, estado=None):
    solicitudes = SolicitudAsignacion.objects.filter(tenant=tenant)
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    return solicitudes.prefetch_related("lineas__tecnico").order_by("-fecha", "-id")


def totales_solicitud(solicitud):
    lineas = list(solicitud.lineas.all())
    return {
        "total_lineas": len(lineas),
        "total_tecnicos": len({linea.tecnico_id for linea in lineas}),
        "total_series": sum(1 for linea in lineas if linea.serie_id),
        "total_cantidad": sum(
            linea.cantidad for linea in lineas if linea.serie_id is None
        ),
    }


def calcular_reservado(tenant, material):
    return (
        LineaAsignacion.objects.filter(
            tenant=tenant,
            material=material,
            serie__isnull=True,
            solicitud__estado=EstadoSolicitud.ENVIADA,
        ).aggregate(total=Sum("cantidad"))["total"]
        or 0
    )


def calcular_disponible(tenant, material):
    return max(
        0,
        obtener_stock_general(tenant, material)
        - calcular_reservado(tenant, material),
    )


def validar_cantidad_disponible(tenant, material, cantidad):
    disponible = calcular_disponible(tenant, material)
    if cantidad > disponible:
        raise CantidadExcedeDisponible(
            f"La cantidad supera el stock disponible; solo quedan {disponible}"
        )


def materiales_disponibles_para_asignacion(tenant):
    """Materiales con existencias reales del tenant, según recojos y series."""
    from django.db.models import Q

    candidatos = (
        Material.objects.filter(activo=True)
        .filter(
            Q(
                stock_general__tenant=tenant,
                stock_general__cantidad__gt=0,
                es_seriado=False,
            )
            | Q(series__tenant=tenant, series__estado=EstadoSerie.DISPONIBLE)
        )
        .distinct()
        .order_by("codigo")
    )
    disponibles = []
    for material in candidatos:
        if material.es_seriado:
            cantidad = material.series.filter(
                tenant=tenant, estado=EstadoSerie.DISPONIBLE
            ).count()
        else:
            cantidad = calcular_disponible(tenant, material)
        if cantidad > 0:
            disponibles.append(
                MaterialDisponible(
                    material=material,
                    disponible=cantidad,
                    seriado=material.es_seriado,
                )
            )
    return disponibles


def materiales_para_formulario(tenant, solicitud=None):
    """Materiales disponibles más los ya usados por el borrador que se edita."""
    disponibles = materiales_disponibles_para_asignacion(tenant)
    por_id = {fila.material.pk: fila for fila in disponibles}
    if solicitud is not None:
        for linea in solicitud.lineas.select_related("material"):
            if linea.material_id in por_id:
                continue
            material = linea.material
            if material.es_seriado:
                cantidad = Serie.objects.filter(
                    tenant=tenant,
                    material=material,
                    estado=EstadoSerie.DISPONIBLE,
                ).count()
            else:
                cantidad = calcular_disponible(tenant, material)
            por_id[material.pk] = MaterialDisponible(
                material=material,
                disponible=max(0, cantidad),
                seriado=material.es_seriado,
            )
    return sorted(por_id.values(), key=lambda fila: fila.material.codigo)


def datos_iniciales_solicitud(solicitud):
    """Bloques y filas para precargar el formulario de edición."""
    bloques = []
    indices_tecnico = {}
    for linea in solicitud.lineas.select_related(
        "tecnico", "material", "serie"
    ).order_by("id"):
        if linea.tecnico_id not in indices_tecnico:
            indices_tecnico[linea.tecnico_id] = len(bloques)
            bloques.append(
                {
                    "tecnico": linea.tecnico_id,
                    "titulo": f"{linea.tecnico.nif} - {linea.tecnico.nombre}",
                    "filas": [],
                }
            )
        bloque = bloques[indices_tecnico[linea.tecnico_id]]
        fila = next(
            (
                item
                for item in bloque["filas"]
                if item["material"] == linea.material_id
            ),
            None,
        )
        if fila is None:
            fila = {
                "material": linea.material_id,
                "seriado": linea.material.es_seriado,
                "cantidad": 0,
                "series": [],
            }
            bloque["filas"].append(fila)
        if linea.serie_id:
            fila["series"].append(linea.serie_id)
        else:
            fila["cantidad"] += linea.cantidad
    for bloque in bloques:
        for fila in bloque["filas"]:
            if fila["seriado"]:
                fila["cantidad"] = 1
    return bloques


def lineas_para_sobrante(solicitud):
    lineas = []
    for linea in solicitud.lineas.all():
        if linea.serie_id:
            lineas.append(
                {
                    "material_id": linea.material_id,
                    "serie_ids": [linea.serie_id],
                }
            )
        else:
            lineas.append(
                {
                    "material_id": linea.material_id,
                    "cantidad": linea.cantidad,
                }
            )
    return lineas


def validar_series_disponibles(tenant, material, series):
    for serie in series:
        if (
            serie.tenant_id != tenant.pk
            or serie.material_id != material.pk
            or serie.estado != EstadoSerie.DISPONIBLE
        ):
            raise SerieNoDisponible("La serie no está disponible")


def _resolver_material(material_id):
    if not str(material_id or "").isdigit():
        raise MaterialNoExiste("El material no existe en el catálogo")
    material = Material.objects.filter(pk=material_id).first()
    if material is None:
        raise MaterialNoExiste("El material no existe en el catálogo")
    return material


def _resolver_tecnico(tenant, linea, cache):
    tecnico_id = linea.get("tecnico_id")
    if not tecnico_id:
        raise ValidacionAsignacion("Cada línea debe indicar su técnico")
    if tecnico_id not in cache:
        cache[tecnico_id] = validar_tecnico_para_asignacion(tenant, tecnico_id)
    return cache[tecnico_id]


def _validar_no_seriados_por_material(tenant, lineas):
    """La suma de no seriados de un material, entre técnicos, no supera el disponible."""
    totales = {}
    for linea in lineas:
        if linea.serie is None:
            material, total = totales.get(linea.material.pk, (linea.material, 0))
            totales[linea.material.pk] = (material, total + linea.cantidad)
    for material, total in totales.values():
        validar_cantidad_disponible(tenant, material, total)


def normalizar_lineas_solicitud(tenant, lineas):
    if not lineas:
        raise ValidacionAsignacion("La solicitud debe tener al menos una línea")

    resultado = []
    series_vistas = set()
    materiales_vistos = set()
    tecnicos = {}

    for indice, linea in enumerate(lineas, start=2):
        tecnico = _resolver_tecnico(tenant, linea, tecnicos)
        material = _resolver_material(linea.get("material_id"))
        clave_material = (tecnico.pk, material.pk)
        if clave_material in materiales_vistos:
            raise MaterialDuplicado(
                "El material ya fue agregado para este técnico"
            )
        materiales_vistos.add(clave_material)
        if material.es_seriado:
            serie_ids = linea.get("serie_ids") or []
            if not serie_ids:
                raise ValidacionAsignacion("Debe indicar al menos una serie")
            series = list(
                Serie.objects.filter(
                    tenant=tenant,
                    material=material,
                    pk__in=serie_ids,
                ).order_by("id")
            )
            if len(series) != len(set(serie_ids)):
                raise SerieNoDisponible("La serie no está disponible")
            for serie in series:
                if serie.pk in series_vistas:
                    raise SerieDuplicada("La serie está duplicada en la solicitud")
                series_vistas.add(serie.pk)
            validar_series_disponibles(tenant, material, series)
            for serie in series:
                resultado.append(
                    LineaValidada(
                        material=material,
                        serie=serie,
                        cantidad=1,
                        lote=material.lote,
                        fila_origen=indice,
                        tecnico=tecnico,
                    )
                )
        else:
            if linea.get("serie_ids"):
                raise ValidacionAsignacion(
                    "El material no es seriado y no admite series"
                )
            valor_cantidad = linea.get("cantidad")
            if isinstance(valor_cantidad, bool) or (
                isinstance(valor_cantidad, float)
                and not valor_cantidad.is_integer()
            ):
                raise CantidadInvalida("La cantidad debe ser un número entero")
            try:
                cantidad = int(valor_cantidad)
            except (TypeError, ValueError) as exc:
                raise CantidadInvalida("La cantidad debe ser un número entero") from exc
            if cantidad <= 0:
                raise CantidadInvalida("La cantidad debe ser mayor a 0")
            resultado.append(
                LineaValidada(
                    material=material,
                    serie=None,
                    cantidad=cantidad,
                    lote=material.lote,
                    fila_origen=indice,
                    tecnico=tecnico,
                )
            )

    _validar_no_seriados_por_material(tenant, resultado)
    return resultado


def _auditar_alta_solicitud(solicitud, actor):
    return registrar_cambio(
        "SolicitudAsignacion",
        solicitud.pk,
        "alta",
        "",
        f"fecha={solicitud.fecha.isoformat()}; tecnicos={solicitud.nifs_tecnicos}; "
        f"estado={solicitud.estado}",
        actor,
        tenant=solicitud.tenant,
    )


def crear_borrador_solicitud(tenant, fecha, lineas, actor):
    tenant = validar_cuenta_tenant(actor)
    if isinstance(fecha, str):
        fecha = parse_date(fecha)
    if fecha is None:
        raise ValidacionAsignacion("La fecha es obligatoria")
    lineas_validadas = normalizar_lineas_solicitud(tenant, lineas)

    with transaction.atomic():
        solicitud = SolicitudAsignacion.objects.create(
            tenant=tenant,
            region=tenant.region,
            fecha=fecha,
            estado=EstadoSolicitud.BORRADOR,
            creado_por=actor,
        )
        for linea in sorted(
            lineas_validadas, key=lambda item: item.fila_origen or 0
        ):
            LineaAsignacion.objects.create(
                tenant=tenant,
                solicitud=solicitud,
                tecnico=linea.tecnico,
                material=linea.material,
                lote=linea.lote,
                serie=linea.serie,
                cantidad=linea.cantidad,
            )
        _auditar_alta_solicitud(solicitud, actor)

    return solicitud


def _describir_linea(linea):
    serie = linea.serie.numero if linea.serie_id else ""
    return (
        f"{linea.material.codigo}; tecnico={linea.tecnico.nif}; "
        f"lote={linea.lote}; serie={serie}; cantidad={linea.cantidad}"
    )


def actualizar_borrador_solicitud(solicitud, fecha, lineas, actor):
    """Reemplaza las líneas de un borrador sin enviarlo ni reservar stock."""
    tenant = validar_cuenta_tenant(actor)
    if solicitud.tenant_id != tenant.pk:
        raise SolicitudNoExiste("La solicitud no existe")
    if solicitud.estado != EstadoSolicitud.BORRADOR:
        raise EstadoSolicitudInvalido(
            "Solo se pueden editar solicitudes en borrador"
        )
    if isinstance(fecha, str):
        fecha = parse_date(fecha)
    if fecha is None:
        raise ValidacionAsignacion("La fecha es obligatoria")
    lineas_validadas = normalizar_lineas_solicitud(tenant, lineas)

    with transaction.atomic():
        bloqueada = SolicitudAsignacion.objects.select_for_update().get(
            pk=solicitud.pk
        )
        if bloqueada.tenant_id != tenant.pk:
            raise SolicitudNoExiste("La solicitud no existe")
        if bloqueada.estado != EstadoSolicitud.BORRADOR:
            raise EstadoSolicitudInvalido(
                "Solo se pueden editar solicitudes en borrador"
            )

        anteriores = list(
            bloqueada.lineas.select_related("material", "serie", "tecnico")
        )
        anterior_fecha = bloqueada.fecha
        for linea in anteriores:
            registrar_cambio(
                "LineaAsignacion",
                linea.pk,
                "baja",
                _describir_linea(linea),
                "",
                actor,
                tenant=tenant,
            )
        bloqueada.lineas.all().delete()

        for linea in sorted(
            lineas_validadas, key=lambda item: item.fila_origen or 0
        ):
            nueva = LineaAsignacion.objects.create(
                tenant=tenant,
                solicitud=bloqueada,
                tecnico=linea.tecnico,
                material=linea.material,
                lote=linea.lote,
                serie=linea.serie,
                cantidad=linea.cantidad,
            )
            registrar_cambio(
                "LineaAsignacion",
                nueva.pk,
                "alta",
                "",
                _describir_linea(nueva),
                actor,
                tenant=tenant,
            )

        bloqueada.fecha = fecha
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=["fecha", "actualizado_por", "actualizado_en"]
        )
        if anterior_fecha != fecha:
            registrar_cambio(
                "SolicitudAsignacion",
                bloqueada.pk,
                "fecha",
                anterior_fecha,
                fecha,
                actor,
                tenant=tenant,
            )
        registrar_cambio(
            "SolicitudAsignacion",
            bloqueada.pk,
            "actualizado",
            "",
            f"lineas={len(lineas_validadas)}",
            actor,
            tenant=tenant,
        )
    return bloqueada


def _lineas_no_seriadas(solicitud):
    return [
        linea
        for linea in solicitud.lineas.select_related("material")
        if linea.serie_id is None
    ]


def _validar_disponibilidad_solicitud(solicitud):
    _validar_no_seriados_por_material(solicitud.tenant, _lineas_no_seriadas(solicitud))


def enviar_solicitud(solicitud, actor):
    tenant = validar_cuenta_tenant(actor)
    if solicitud.tenant_id != tenant.pk:
        raise SolicitudNoExiste("La solicitud no existe")

    with transaction.atomic():
        bloqueada = (
            SolicitudAsignacion.objects.select_for_update()
            .select_related("tenant", "region")
            .get(pk=solicitud.pk)
        )
        if bloqueada.estado != EstadoSolicitud.BORRADOR:
            raise EstadoSolicitudInvalido(
                "Solo se pueden enviar solicitudes en borrador"
            )

        Tenant.objects.select_for_update().get(pk=tenant.pk)
        lineas = list(
            bloqueada.lineas.select_related("material", "serie", "tecnico")
        )
        if not lineas:
            raise ValidacionAsignacion(
                "La solicitud debe tener al menos una línea"
            )

        for linea in lineas:
            if linea.serie_id:
                serie = (
                    Serie.objects.select_for_update()
                    .filter(pk=linea.serie_id)
                    .first()
                )
                if (
                    serie is None
                    or serie.estado != EstadoSerie.DISPONIBLE
                    or serie.material_id != linea.material_id
                    or serie.tenant_id != tenant.pk
                ):
                    raise SerieNoDisponible("La serie no está disponible")
        _validar_no_seriados_por_material(tenant, lineas)

        for linea in lineas:
            if linea.serie_id:
                serie = linea.serie
                serie.estado = EstadoSerie.RESERVADA
                serie.actualizado_por = actor
                serie.save(
                    update_fields=["estado", "actualizado_por", "actualizado_en"]
                )
                registrar_cambio(
                    "Serie",
                    serie.pk,
                    "estado",
                    EstadoSerie.DISPONIBLE,
                    EstadoSerie.RESERVADA,
                    actor,
                    tenant=tenant,
                )

        ruta, hash_archivo, generado_en = generar_excel_solicitud(bloqueada)
        bloqueada.excel_ruta = ruta
        bloqueada.excel_hash = hash_archivo
        bloqueada.excel_generado_en = generado_en
        bloqueada.estado = EstadoSolicitud.ENVIADA
        bloqueada.enviada_en = timezone.now()
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=[
                "excel_ruta",
                "excel_hash",
                "excel_generado_en",
                "estado",
                "enviada_en",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "SolicitudAsignacion",
            bloqueada.pk,
            "estado",
            EstadoSolicitud.BORRADOR,
            EstadoSolicitud.ENVIADA,
            actor,
            tenant=tenant,
        )
        registrar_cambio(
            "SolicitudAsignacion",
            bloqueada.pk,
            "excel",
            "",
            f"{ruta}; hash={hash_archivo}",
            actor,
            tenant=tenant,
        )
        transaction.on_commit(
            lambda: __import__(
                "asignaciones.notificaciones",
                fromlist=["publicar_solicitud_enviada"],
            ).publicar_solicitud_enviada(bloqueada)
        )
        transaction.on_commit(
            lambda: __import__(
                "asignaciones.correo",
                fromlist=["encolar_envio_solicitud"],
            ).encolar_envio_solicitud(bloqueada.pk)
        )

    return bloqueada


def crear_y_enviar_solicitud(tenant, fecha, lineas, actor):
    with transaction.atomic():
        solicitud = crear_borrador_solicitud(tenant, fecha, lineas, actor)
        return enviar_solicitud(solicitud, actor)


def cancelar_solicitud(solicitud, actor):
    tenant = validar_cuenta_tenant(actor)
    if solicitud.tenant_id != tenant.pk:
        raise SolicitudNoExiste("La solicitud no existe")

    with transaction.atomic():
        bloqueada = SolicitudAsignacion.objects.select_for_update().get(
            pk=solicitud.pk
        )
        if bloqueada.estado != EstadoSolicitud.BORRADOR:
            raise EstadoSolicitudInvalido(
                "Solo se pueden cancelar solicitudes en borrador"
            )
        bloqueada.estado = EstadoSolicitud.CANCELADA
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=["estado", "actualizado_por", "actualizado_en"]
        )
        registrar_cambio(
            "SolicitudAsignacion",
            bloqueada.pk,
            "estado",
            EstadoSolicitud.BORRADOR,
            EstadoSolicitud.CANCELADA,
            actor,
            tenant=tenant,
        )
    return bloqueada


def verificar_excel_solicitud(solicitud):
    """Devuelve la ruta del Excel si existe y su hash coincide."""
    if not solicitud.excel_ruta:
        raise ArchivoNoDisponible
    raiz = Path(settings.MEDIA_ROOT).resolve()
    ruta = (raiz / solicitud.excel_ruta).resolve()
    if raiz not in ruta.parents or not ruta.exists():
        raise ArchivoNoDisponible
    contenido = ruta.read_bytes()
    if not hmac.compare_digest(
        hashlib.sha256(contenido).hexdigest(), solicitud.excel_hash
    ):
        raise ArchivoAlterado
    return ruta


def calcular_sobrante(tenant, lineas):
    """Todos los materiales disponibles y lo que la solicitud en curso ya asigna."""
    agregados = {}
    for linea in lineas:
        material_id = linea.get("material_id")
        if not str(material_id or "").isdigit():
            continue
        material = Material.objects.filter(pk=material_id).first()
        if material is None:
            continue
        datos = agregados.setdefault(
            material.pk, {"series": set(), "cantidad": 0}
        )
        if material.es_seriado:
            for serie_id in linea.get("serie_ids") or []:
                datos["series"].add(serie_id)
        else:
            try:
                datos["cantidad"] += max(0, int(linea.get("cantidad") or 0))
            except (TypeError, ValueError):
                continue

    disponibles = {
        fila.material.pk: fila
        for fila in materiales_disponibles_para_asignacion(tenant)
    }
    for material_id in agregados:
        if material_id not in disponibles:
            material = Material.objects.filter(pk=material_id).first()
            if material is not None:
                disponibles[material_id] = MaterialDisponible(
                    material=material,
                    disponible=0,
                    seriado=material.es_seriado,
                )

    resultado = []
    for material_id, fila in sorted(
        disponibles.items(), key=lambda item: item[1].material.codigo
    ):
        datos = agregados.get(material_id, {"series": set(), "cantidad": 0})
        solicitado = (
            len(datos["series"])
            if fila.seriado
            else datos["cantidad"]
        )
        resultado.append(
            SobranteMaterial(
                material=fila.material,
                seriado=fila.seriado,
                disponible=fila.disponible,
                solicitado=solicitado,
                sobrante=fila.disponible - solicitado,
            )
        )
    return resultado


def alertas_cupo_solicitud(solicitud):
    tecnicos = solicitud.tecnicos
    return [
        alerta
        for alerta in (calcular_alerta_cupo(tecnico) for tecnico in tecnicos)
        if alerta is not None
    ]


def series_disponibles_para_asignacion(tenant, material, q="", excluir_ids=None):
    series = Serie.objects.filter(
        tenant=tenant,
        material=material,
        estado=EstadoSerie.DISPONIBLE,
    )
    if excluir_ids:
        series = series.exclude(pk__in=excluir_ids)
    q = (q or "").strip()
    if q:
        series = series.filter(numero__icontains=q)
    return series.order_by("numero")


def dias_en_mano_serie(serie, hoy=None):
    if serie.estado != EstadoSerie.ASIGNADA or serie.asignada_en is None:
        return None
    hoy = hoy or timezone.localdate()
    return (hoy - serie.asignada_en.date()).days


def series_en_custodia_tecnico(tecnico):
    series = Serie.objects.filter(
        tenant=tecnico.tenant,
        tecnico=tecnico,
        estado=EstadoSerie.ASIGNADA,
    ).select_related("material")
    return [
        {
            "serie": serie,
            "material": serie.material,
            "asignada_en": serie.asignada_en,
            "dias": dias_en_mano_serie(serie),
        }
        for serie in series
    ]


def calcular_alerta_cupo(tecnico):
    series = series_en_custodia_tecnico(tecnico)
    excedidas = [
        item
        for item in series
        if item["dias"] is not None
        and item["dias"] > settings.DIAS_ALERTA_CUSTODIA
    ]
    if not excedidas:
        return None
    return AlertaCupo(
        tecnico=tecnico,
        mensaje=f"El técnico supera los {settings.DIAS_ALERTA_CUSTODIA} días en mano",
        series=excedidas,
    )
