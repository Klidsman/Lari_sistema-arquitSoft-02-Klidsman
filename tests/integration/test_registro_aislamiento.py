"""Aislamiento por tenant y RLS del registro de materiales."""

import pytest
from django.db import connection

from registro_materiales.exportacion import exportar_reporte_mensual
from registro_materiales.models import (
    CierreMensual,
    MaterialHabilitado,
    OrdenLiquidacion,
)
from registro_materiales.services import (
    buscar_orden,
    dashboard_mensual,
    obtener_o_crear_orden,
)

PERIODO = "2026-11"


@pytest.mark.django_db
def test_otro_tenant_no_ve_ordenes_ni_dashboard(
    usuario_tenant,
    usuario_otro_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    MaterialHabilitado.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        creado_por=usuario_tenant,
    )
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    ajeno = usuario_otro_tenant.tenant

    assert buscar_orden(ajeno, tecnico, PERIODO, "A1") is None
    assert dashboard_mensual(ajeno, PERIODO)["ordenes"] == 0
    archivo = exportar_reporte_mensual(ajeno, PERIODO, "csv")
    assert b"A1" not in archivo.contenido
    assert not OrdenLiquidacion.objects.filter(tenant=ajeno).exists()
    assert orden.tenant_id == tenant.pk


@pytest.mark.django_db
def test_rls_activa_en_tablas_de_registro():
    tablas = [
        OrdenLiquidacion._meta.db_table,
        MaterialHabilitado._meta.db_table,
        CierreMensual._meta.db_table,
    ]
    with connection.cursor() as cursor:
        for tabla in tablas:
            cursor.execute(
                "SELECT relrowsecurity FROM pg_class WHERE relname = %s",
                [tabla],
            )
            fila = cursor.fetchone()
            assert fila is not None, tabla
            assert fila[0] is True, tabla
