"""Servicios de reportes mensuales."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

import openpyxl
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from acceso.models import Rol
from asignaciones.models import EstadoSolicitud, LineaAsignacion
from auditoria.models import RegistroCambio
from auditoria.services import registrar_cambio
from conciliaciones.models import Conciliacion
from logistica_inversa.models import LineaDevolucion

from .models import CorteMensual


class ErrorReporte(Exception):
    mensaje = "Error de reporte"

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)

    def __str__(self):
        return self.args[0]


class PermisoDenegado(ErrorReporte):
    mensaje = "No tienes permiso para generar este corte"


class CorteExistente(ErrorReporte):
    mensaje = "Ya existe un corte para este mes/año"


class CorteNoExiste(ErrorReporte):
    mensaje = "El corte no existe"


class MesInvalido(ErrorReporte):
    mensaje = "El mes debe estar entre 1 y 12"


class AnioInvalido(ErrorReporte):
    mensaje = "El año no es válido"


@dataclass(frozen=True)
class TotalesCorte:
    solicitados: int
    asignados: int
    liquidados_instalados: int
    devueltos: int
    no_justificado: int
    porcentaje_merma: Decimal


@dataclass(frozen=True)
class ArchivoReporte:
    nombre: str
    contenido: bytes
    content_type: str


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def validar_cuenta_admin(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol != Rol.ADMIN_PLATAFORMA:
        raise PermisoDenegado


def resolver_alcance(actor, tenant):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if tenant is None:
        if actor.rol != Rol.ADMIN_PLATAFORMA:
            raise PermisoDenegado(
                "Solo el administrador puede generar cortes globales"
            )
        return "GLOBAL"
    if actor.rol == Rol.ADMIN_PLATAFORMA:
        return "TENANT"
    if actor.rol == Rol.USUARIO_TENANT and actor.tenant_id == tenant.pk:
        return "TENANT"
    raise PermisoDenegado


def validar_cuenta_tenant_o_admin(actor, tenant):
    return resolver_alcance(actor, tenant)


def validar_mes_anio(mes, anio):
    try:
        mes = int(mes)
    except (TypeError, ValueError) as exc:
        raise MesInvalido from exc
    try:
        anio = int(anio)
    except (TypeError, ValueError) as exc:
        raise AnioInvalido from exc
    if mes < 1 or mes > 12:
        raise MesInvalido
    if anio < 2000 or anio > 2100:
        raise AnioInvalido
    return mes, anio


def rango_mes(mes, anio):
    mes, anio = validar_mes_anio(mes, anio)
    inicio = timezone.make_aware(datetime(anio, mes, 1))
    if mes == 12:
        fin = timezone.make_aware(datetime(anio + 1, 1, 1))
    else:
        fin = timezone.make_aware(datetime(anio, mes + 1, 1))
    return inicio, fin


def _unidades(lineas):
    con_serie = lineas.filter(serie__isnull=False).count()
    sin_serie = (
        lineas.filter(serie__isnull=True).aggregate(total=Sum("cantidad"))[
            "total"
        ]
        or 0
    )
    return con_serie + sin_serie


def calcular_totales(tenant, mes, anio):
    mes, anio = validar_mes_anio(mes, anio)
    inicio, fin = rango_mes(mes, anio)
    inicio_dia = date(anio, mes, 1)
    fin_dia = fin.date()

    lineas = LineaAsignacion.objects.all()
    solicitudes = lineas.filter(
        solicitud__estado__in=[
            EstadoSolicitud.ENVIADA,
            EstadoSolicitud.CONFIRMADA,
            EstadoSolicitud.RECHAZADA,
        ],
        solicitud__fecha__gte=inicio_dia,
        solicitud__fecha__lt=fin_dia,
    )
    confirmadas = lineas.filter(
        solicitud__estado=EstadoSolicitud.CONFIRMADA,
        solicitud__confirmada_en__gte=inicio,
        solicitud__confirmada_en__lt=fin,
    )
    if tenant is not None:
        solicitudes = solicitudes.filter(solicitud__tenant=tenant)
        confirmadas = confirmadas.filter(solicitud__tenant=tenant)
    solicitados = _unidades(solicitudes)
    asignados = _unidades(confirmadas)

    instaladas = RegistroCambio.objects.filter(
        entidad="Serie",
        campo="estado",
        valor_nuevo="INSTALADA",
        fecha__gte=inicio,
        fecha__lt=fin,
    )
    devoluciones = LineaDevolucion.objects.filter(
        devolucion__fecha__gte=inicio_dia,
        devolucion__fecha__lt=fin_dia,
    )
    if tenant is not None:
        instaladas = instaladas.filter(tenant=tenant)
        devoluciones = devoluciones.filter(tenant=tenant)
    liquidados = instaladas.values("entidad_id").distinct().count()
    devueltos = devoluciones.count()

    no_justificado = max(0, asignados - liquidados - devueltos)
    if asignados == 0:
        merma = Decimal("0.00")
    else:
        merma = (
            Decimal(no_justificado)
            / Decimal(asignados)
            * Decimal(100)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return TotalesCorte(
        solicitados=solicitados,
        asignados=asignados,
        liquidados_instalados=liquidados,
        devueltos=devueltos,
        no_justificado=no_justificado,
        porcentaje_merma=merma,
    )


def _buscar_corte(tenant, mes, anio):
    qs = CorteMensual.objects.filter(anio=anio, mes=mes)
    if tenant is None:
        return qs.filter(tenant__isnull=True).first()
    return qs.filter(tenant=tenant).first()


def generar_corte(tenant, mes, anio, actor):
    resolver_alcance(actor, tenant)
    mes, anio = validar_mes_anio(mes, anio)
    if _buscar_corte(tenant, mes, anio) is not None:
        raise CorteExistente
    totales = calcular_totales(tenant, mes, anio)
    with transaction.atomic():
        corte = CorteMensual.objects.create(
            tenant=tenant,
            anio=anio,
            mes=mes,
            solicitados=totales.solicitados,
            asignados=totales.asignados,
            liquidados_instalados=totales.liquidados_instalados,
            devueltos=totales.devueltos,
            no_justificado=totales.no_justificado,
            porcentaje_merma=totales.porcentaje_merma,
            generado_por=actor,
        )
        registrar_cambio(
            "CorteMensual",
            corte.pk,
            "alta",
            "",
            (
                f"alcance={'global' if tenant is None else tenant.codigo}; "
                f"{anio}-{mes:02d}; solicitados={totales.solicitados}; "
                f"asignados={totales.asignados}"
            ),
            actor,
            tenant=tenant,
        )
    return corte


def regenerar_corte(corte, actor):
    resolver_alcance(actor, corte.tenant)
    with transaction.atomic():
        corte = CorteMensual.objects.select_for_update().get(pk=corte.pk)
        totales = calcular_totales(corte.tenant, corte.mes, corte.anio)
        anterior = (
            f"solicitados={corte.solicitados}; asignados={corte.asignados}; "
            f"liquidados={corte.liquidados_instalados}; "
            f"devueltos={corte.devueltos}; merma={corte.porcentaje_merma}"
        )
        corte.solicitados = totales.solicitados
        corte.asignados = totales.asignados
        corte.liquidados_instalados = totales.liquidados_instalados
        corte.devueltos = totales.devueltos
        corte.no_justificado = totales.no_justificado
        corte.porcentaje_merma = totales.porcentaje_merma
        corte.version += 1
        corte.regenerado_en = timezone.now()
        corte.actualizado_por = actor
        corte.save(
            update_fields=[
                "solicitados",
                "asignados",
                "liquidados_instalados",
                "devueltos",
                "no_justificado",
                "porcentaje_merma",
                "version",
                "regenerado_en",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        nuevo = (
            f"solicitados={corte.solicitados}; asignados={corte.asignados}; "
            f"liquidados={corte.liquidados_instalados}; "
            f"devueltos={corte.devueltos}; merma={corte.porcentaje_merma}"
        )
        registrar_cambio(
            "CorteMensual",
            corte.pk,
            "regenerado",
            anterior,
            nuevo,
            actor,
            tenant=corte.tenant,
        )
    return corte


def _xlsx(nombre, encabezados, filas):
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Reporte"
    hoja.append(encabezados)
    for fila in filas:
        hoja.append(fila)
    buffer = BytesIO()
    libro.save(buffer)
    libro.close()
    return ArchivoReporte(
        nombre=nombre, contenido=buffer.getvalue(), content_type=XLSX
    )


def _alcance(tenant):
    return tenant.codigo if tenant is not None else "global"


def exportar_auditoria(tenant, mes, anio, actor):
    resolver_alcance(actor, tenant)
    inicio, fin = rango_mes(mes, anio)
    registros = RegistroCambio.objects.filter(
        fecha__gte=inicio, fecha__lt=fin
    ).select_related("usuario")
    if tenant is not None:
        registros = registros.filter(tenant=tenant)
    filas = [
        [
            timezone.localtime(registro.fecha).isoformat(timespec="seconds"),
            registro.usuario.email,
            registro.entidad,
            registro.campo,
            registro.valor_anterior,
            registro.valor_nuevo,
        ]
        for registro in registros.order_by("fecha", "id")
    ]
    return _xlsx(
        f"auditoria-{_alcance(tenant)}-{anio}-{mes:02d}.xlsx",
        [
            "Fecha",
            "Usuario",
            "Entidad",
            "Acción",
            "Valor anterior",
            "Valor nuevo",
        ],
        filas,
    )


def exportar_conciliacion(tenant, mes, anio, actor):
    resolver_alcance(actor, tenant)
    inicio, fin = rango_mes(mes, anio)
    conciliaciones = Conciliacion.objects.filter(
        fecha_carga__gte=inicio, fecha_carga__lt=fin
    ).select_related("tenant")
    if tenant is not None:
        conciliaciones = conciliaciones.filter(tenant=tenant)
    conciliaciones = conciliaciones.annotate(
        num_series=Count("diferencias_series", distinct=True),
        num_cantidades=Count("diferencias_cantidades", distinct=True),
    ).order_by("fecha_carga", "id")
    global_ = tenant is None
    encabezados = ["Fecha", "Estado"]
    if global_:
        encabezados.append("Tenant")
    encabezados += [
        "Diferencias series",
        "Diferencias cantidades",
        "Ajustes aplicados",
    ]
    filas = []
    for conciliacion in conciliaciones:
        fila = [
            timezone.localtime(conciliacion.fecha_carga).isoformat(
                timespec="seconds"
            ),
            conciliacion.estado,
        ]
        if global_:
            fila.append(conciliacion.tenant.codigo)
        fila += [
            conciliacion.num_series,
            conciliacion.num_cantidades,
            (
                conciliacion.ajustes_aplicados
                if conciliacion.estado == "APROBADA"
                else 0
            ),
        ]
        filas.append(fila)
    return _xlsx(
        f"conciliacion-{_alcance(tenant)}-{anio}-{mes:02d}.xlsx",
        encabezados,
        filas,
    )


def listar_cortes(tenant, anio=None):
    cortes = CorteMensual.objects.select_related("tenant")
    if tenant is None:
        cortes = cortes.filter(tenant__isnull=True)
    else:
        cortes = cortes.filter(tenant=tenant)
    if anio:
        cortes = cortes.filter(anio=anio)
    return cortes.order_by("-anio", "-mes", "id")


def obtener_corte(tenant, corte_id):
    corte = _buscar_corte_por_id(tenant, corte_id)
    if corte is None:
        raise CorteNoExiste
    return corte


def _buscar_corte_por_id(tenant, corte_id):
    qs = CorteMensual.objects.filter(pk=corte_id)
    if tenant is None:
        return qs.filter(tenant__isnull=True).first()
    return qs.filter(tenant=tenant).first()


def obtener_corte_visible(actor, corte_id):
    corte = CorteMensual.objects.filter(pk=corte_id).select_related(
        "tenant"
    ).first()
    if corte is None:
        raise CorteNoExiste
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol == Rol.ADMIN_PLATAFORMA:
        return corte
    if actor.rol == Rol.USUARIO_TENANT and corte.tenant_id == actor.tenant_id:
        return corte
    raise CorteNoExiste


def detalle_corte(corte):
    return {
        "corte": corte,
        "alcance": "Global" if corte.tenant_id is None else corte.tenant.codigo,
    }
