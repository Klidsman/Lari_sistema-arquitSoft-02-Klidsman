"""Rendimiento de la exportación de registro de materiales."""

import time
from datetime import date

import pytest

from registro_materiales.exportacion import exportar_detalle_ordenes
from registro_materiales.models import (
    MaterialHabilitado,
    OrdenLiquidacion,
    SaldoInicialPeriodo,
    UsoMaterialOrden,
)

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
