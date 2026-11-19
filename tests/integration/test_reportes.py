"""Reportes mensuales: cortes, merma y exportaciones."""

from datetime import date, datetime
from decimal import Decimal

import openpyxl
import pytest
from django.utils import timezone

from asignaciones.models import EstadoSolicitud, LineaAsignacion, SolicitudAsignacion
from auditoria.models import RegistroCambio
from conciliaciones.models import Conciliacion
from logistica_inversa.models import Devolucion, LineaDevolucion
from reportes.models import CorteMensual
from reportes.services import (
    CorteExistente,
    CorteNoExiste,
    MesInvalido,
    PermisoDenegado,
    calcular_totales,
    exportar_auditoria,
    exportar_conciliacion,
    generar_corte,
    obtener_corte_visible,
    rango_mes,
    regenerar_corte,
)
from series.models import EstadoSerie, Serie

MES = 11
ANIO = 2026


def _solicitud(
    tenant,
    tecnico,
    usuario,
    estado,
    fecha,
    confirmada_en,
    cantidad,
    material,
):
    solicitud = SolicitudAsignacion.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=fecha,
        estado=estado,
        confirmada_en=confirmada_en,
        creado_por=usuario,
    )
    LineaAsignacion.objects.create(
        tenant=tenant,
        solicitud=solicitud,
        tecnico=tecnico,
        material=material,
        cantidad=cantidad,
    )
    return solicitud


def _serie(tenant, material, usuario, numero):
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=EstadoSerie.INACTIVA,
        creado_por=usuario,
    )


@pytest.mark.django_db
def test_calculo_de_merma(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    material_seriado,
    almacen,
    monkeypatch,
):
    _solicitud(
        tenant,
        tecnico,
        usuario_tenant,
        EstadoSolicitud.CONFIRMADA,
        date(ANIO, MES, 10),
        timezone.make_aware(datetime(ANIO, MES, 10, 12)),
        100,
        material_no_seriado,
    )
    instalado_en = timezone.make_aware(datetime(ANIO, MES, 15, 12))
    monkeypatch.setattr("django.utils.timezone.now", lambda: instalado_en)
    for indice in range(80):
        RegistroCambio.objects.create(
            tenant=tenant,
            entidad="Serie",
            entidad_id=10_000 + indice,
            campo="estado",
            valor_anterior="ASIGNADA",
            valor_nuevo="INSTALADA",
            usuario=usuario_tenant,
        )
    devolucion = Devolucion.objects.create(
        tenant=tenant,
        region=tenant.region,
        tecnico=tecnico,
        fecha=date(ANIO, MES, 20),
        creado_por=usuario_tenant,
    )
    for indice in range(5):
        serie = _serie(
            tenant, material_seriado, usuario_tenant, f"REP{indice:09d}"
        )
        LineaDevolucion.objects.create(
            tenant=tenant,
            devolucion=devolucion,
            serie=serie,
            material=material_seriado,
            descripcion="ROSETA",
            lote=serie.lote,
        )

    totales = calcular_totales(tenant, MES, ANIO)
    assert totales.solicitados == 100
    assert totales.asignados == 100
    assert totales.liquidados_instalados == 80
    assert totales.devueltos == 5
    assert totales.no_justificado == 15
    assert totales.porcentaje_merma == Decimal("15.00")


@pytest.mark.django_db
def test_asignados_cero_da_merma_cero(tenant, material_no_seriado):
    totales = calcular_totales(tenant, MES, ANIO)
    assert totales.asignados == 0
    assert totales.no_justificado == 0
    assert totales.porcentaje_merma == Decimal("0.00")


@pytest.mark.django_db
def test_generar_y_regenerar_corte(
    usuario_admin,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    monkeypatch,
):
    corte = generar_corte(tenant, MES, ANIO, usuario_tenant)
    assert corte.version == 1
    assert corte.asignados == 0

    with pytest.raises(CorteExistente):
        generar_corte(tenant, MES, ANIO, usuario_tenant)

    _solicitud(
        tenant,
        tecnico,
        usuario_tenant,
        EstadoSolicitud.CONFIRMADA,
        date(ANIO, MES, 5),
        timezone.make_aware(datetime(ANIO, MES, 5, 10)),
        4,
        material_no_seriado,
    )
    corte = regenerar_corte(corte, usuario_tenant)
    assert corte.version == 2
    assert corte.asignados == 4
    assert corte.porcentaje_merma == Decimal("100.00")

    global_corte = generar_corte(None, MES, ANIO, usuario_admin)
    assert global_corte.tenant_id is None
    assert global_corte.asignados == 4


@pytest.mark.django_db
def test_permisos_de_alcance(
    usuario_admin, usuario_tenant, usuario_almacen, tenant, almacen
):
    with pytest.raises(PermisoDenegado):
        generar_corte(None, MES, ANIO, usuario_tenant)
    with pytest.raises(PermisoDenegado):
        generar_corte(tenant, MES, ANIO, usuario_almacen)
    with pytest.raises(MesInvalido):
        generar_corte(tenant, 13, ANIO, usuario_tenant)
    with pytest.raises(MesInvalido):
        rango_mes(0, ANIO)


@pytest.mark.django_db
def test_exportar_auditoria_solo_del_tenant(
    usuario_tenant,
    usuario_otro_tenant,
    tenant,
    almacen,
    monkeypatch,
):
    momento = timezone.make_aware(datetime(ANIO, MES, 15, 9))
    monkeypatch.setattr("django.utils.timezone.now", lambda: momento)
    propio = RegistroCambio.objects.create(
        tenant=tenant,
        entidad="Serie",
        entidad_id=1,
        campo="estado",
        valor_anterior="ASIGNADA",
        valor_nuevo="INSTALADA",
        usuario=usuario_tenant,
    )
    RegistroCambio.objects.create(
        tenant=usuario_otro_tenant.tenant,
        entidad="Serie",
        entidad_id=2,
        campo="estado",
        valor_anterior="ASIGNADA",
        valor_nuevo="INSTALADA",
        usuario=usuario_otro_tenant,
    )
    archivo = exportar_auditoria(tenant, MES, ANIO, usuario_tenant)
    libro = openpyxl.load_workbook(__import__("io").BytesIO(archivo.contenido))
    try:
        hoja = libro.active
        assert hoja.max_row == 2
        assert hoja["A1"].value == "Fecha"
        assert hoja["C2"].value == "Serie"
    finally:
        libro.close()


@pytest.mark.django_db
def test_exportar_conciliacion_global_y_tenant(
    usuario_admin, usuario_tenant, tenant, almacen
):
    Conciliacion.objects.create(
        tenant=tenant,
        region=tenant.region,
        archivo_nombre="reporte.xlsx",
        archivo_ruta="conciliaciones/reporte.xlsx",
        hash_sha256="a" * 64,
        huella_stock="b" * 64,
        creado_por=usuario_tenant,
        ajustes_aplicados=3,
    )
    archivo = exportar_conciliacion(tenant, MES, ANIO, usuario_tenant)
    libro = openpyxl.load_workbook(__import__("io").BytesIO(archivo.contenido))
    try:
        hoja = libro.active
        assert hoja["A1"].value == "Fecha"
        assert hoja["B1"].value == "Estado"
        assert hoja["C1"].value == "Diferencias series"
    finally:
        libro.close()

    global_archivo = exportar_conciliacion(None, MES, ANIO, usuario_admin)
    libro = openpyxl.load_workbook(
        __import__("io").BytesIO(global_archivo.contenido)
    )
    try:
        hoja = libro.active
        assert hoja["C1"].value == "Tenant"
        assert hoja["C2"].value == tenant.codigo
    finally:
        libro.close()


@pytest.mark.django_db
def test_obtener_corte_ajeno_no_existe(usuario_otro_tenant, usuario_tenant, tenant):
    corte = generar_corte(tenant, MES, ANIO, usuario_tenant)
    with pytest.raises(CorteNoExiste):
        obtener_corte_visible(usuario_otro_tenant, corte.pk)
