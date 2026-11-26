"""Rendimiento de la exportación de registro de materiales."""

import time
from datetime import date

import pytest

from materiales.models import Material
from registro_materiales.exportacion import (
    exportar_detalle_ordenes,
    exportar_reporte_mensual,
)
from registro_materiales.models import (
    MaterialHabilitado,
    OrdenLiquidacion,
    SaldoInicialPeriodo,
    UsoMaterialOrden,
)
from registro_materiales.services import dashboard_mensual

PERIODO = "2026-11"


@pytest.mark.django_db
def test_exportacion_de_mil_ordenes_en_menos_de_diez_segundos(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    MaterialHabilitado.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        creado_por=usuario_tenant,
    )
    SaldoInicialPeriodo.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        periodo=PERIODO,
        cantidad=10000,
        creado_por=usuario_tenant,
    )
    ordenes = OrdenLiquidacion.objects.bulk_create(
        [
            OrdenLiquidacion(
                tenant=tenant,
                tecnico=tecnico,
                numero_original=f"R{indice:05d}",
                numero_normalizado=f"R{indice:05d}",
                periodo=PERIODO,
                fecha_instalacion=date(2026, 11, 10),
                creado_por=usuario_tenant,
            )
            for indice in range(1000)
        ]
    )
    UsoMaterialOrden.objects.bulk_create(
        [
            UsoMaterialOrden(
                tenant=tenant,
                orden=orden,
                tecnico=tecnico,
                material=material_no_seriado,
                cantidad=1,
                creado_por=usuario_tenant,
            )
            for orden in ordenes
        ]
    )

    inicio = time.perf_counter()
    archivo = exportar_detalle_ordenes(tenant, PERIODO, "xlsx")
    duracion = time.perf_counter() - inicio

    assert archivo.contenido[:2] == b"PK"
    assert duracion < 10


@pytest.mark.django_db
def test_dashboard_con_cien_materiales_mil_ordenes_y_cinco_mil_usos(
    usuario_tenant,
    tenant,
    tecnico,
    almacen,
    django_assert_max_num_queries,
):
    materiales = Material.objects.bulk_create(
        [
            Material(
                codigo=f"9000{indice:07d}",
                descripcion=f"Material {indice}",
                lote="",
                es_seriado=False,
                creado_por=usuario_tenant,
            )
            for indice in range(100)
        ]
    )
    MaterialHabilitado.objects.bulk_create(
        [
            MaterialHabilitado(
                tenant=tenant, material=material, creado_por=usuario_tenant
            )
            for material in materiales
        ]
    )
    SaldoInicialPeriodo.objects.bulk_create(
        [
            SaldoInicialPeriodo(
                tenant=tenant,
                material=material,
                periodo=PERIODO,
                cantidad=1000,
                creado_por=usuario_tenant,
            )
            for material in materiales
        ]
    )
    ordenes = OrdenLiquidacion.objects.bulk_create(
        [
            OrdenLiquidacion(
                tenant=tenant,
                tecnico=tecnico,
                numero_original=f"R{indice:05d}",
                numero_normalizado=f"R{indice:05d}",
                periodo=PERIODO,
                fecha_instalacion=date(2026, 11, 10),
                creado_por=usuario_tenant,
            )
            for indice in range(1000)
        ]
    )
    usos = []
    for indice, orden in enumerate(ordenes):
        for posicion in range(5):
            usos.append(
                UsoMaterialOrden(
                    tenant=tenant,
                    orden=orden,
                    tecnico=tecnico,
                    material=materiales[(indice * 5 + posicion) % 100],
                    cantidad=1,
                    creado_por=usuario_tenant,
                )
            )
    UsoMaterialOrden.objects.bulk_create(usos)

    inicio = time.perf_counter()
    with django_assert_max_num_queries(20):
        datos = dashboard_mensual(tenant, PERIODO)
    duracion = time.perf_counter() - inicio

    assert len(datos["filas"]) == 100
    assert sum(fila["usado"] for fila in datos["filas"]) == 5000
    assert duracion < 10

    with django_assert_max_num_queries(20):
        archivo = exportar_reporte_mensual(tenant, PERIODO, "xlsx")
    assert archivo.contenido[:2] == b"PK"
