"""Concurrencia del registro de materiales."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection

from acceso.models import Usuario
from registro_materiales.models import (
    MaterialHabilitado,
    OrdenLiquidacion,
    UsoMaterialOrden,
)
from registro_materiales.services import (
    guardar_uso,
    obtener_o_crear_orden,
    registrar_saldo_inicial,
)

PERIODO = "2026-11"


def _guardar(orden_id, material_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        orden = OrdenLiquidacion.objects.get(pk=orden_id)
        actor = Usuario.objects.get(pk=actor_id)
        guardar_uso(
            orden, date(2026, 11, 10), {material_id: 8}, actor
        )
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_usos_simultaneos_no_superan_el_disponible(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    MaterialHabilitado.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        creado_por=usuario_tenant,
    )
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 10, usuario_tenant
    )
    primera = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    segunda = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A2", usuario_tenant
    )

    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda orden_id: _guardar(
                    orden_id,
                    material_no_seriado.pk,
                    usuario_tenant.pk,
                    barrera,
                ),
                [primera.pk, segunda.pk],
            )
        )

    assert sorted(resultados) == ["SaldoInsuficiente", "ok"]
    total = sum(
        UsoMaterialOrden.objects.filter(
            orden__periodo=PERIODO
        ).values_list("cantidad", flat=True)
    )
    assert total == 8
