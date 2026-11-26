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
    cerrar_mes,
    confirmar_carga,
    guardar_uso,
    obtener_o_crear_orden,
    reabrir_mes,
    registrar_saldo_inicial,
)
from stock.models import StockTecnico
from tecnicos.models import Tecnico

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
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
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


def _cargar(tenant_id, tecnico_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        from tenants.models import Tenant

        tenant = Tenant.objects.get(pk=tenant_id)
        tecnico = Tecnico.objects.get(pk=tecnico_id)
        actor = Usuario.objects.get(pk=actor_id)
        carga = confirmar_carga(
            tenant, tecnico, PERIODO, "A1", actor
        )
        return f"ok:{carga.total_nuevas}"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_cargas_simultaneas_crean_una_sola_orden(
    usuario_tenant, tenant, tecnico, almacen
):
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _cargar(
                    tenant.pk,
                    tecnico.pk,
                    usuario_tenant.pk,
                    barrera,
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["ok:0", "ok:1"]
    assert OrdenLiquidacion.objects.filter(
        tenant=tenant, periodo=PERIODO, numero_normalizado="A1"
    ).count() == 1


def _cerrar(tenant_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        from tenants.models import Tenant

        tenant = Tenant.objects.get(pk=tenant_id)
        actor = Usuario.objects.get(pk=actor_id)
        cierre = cerrar_mes(
            tenant, PERIODO, "backups/lari.sql", actor
        )
        return f"ok:{cierre.version}"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_cierres_simultaneos_cierran_una_sola_vez(
    usuario_tenant, tenant, almacen
):
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _cerrar(
                    tenant.pk, usuario_tenant.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["PeriodoCerrado", "ok:1"]


def _reabrir(cierre_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        from registro_materiales.models import CierreMensual

        cierre = CierreMensual.objects.get(pk=cierre_id)
        actor = Usuario.objects.get(pk=actor_id)
        reabierto = reabrir_mes(cierre, "Corrección", actor)
        return f"ok:{reabierto.version}"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_reaperturas_simultaneas_reabren_una_sola_vez(
    usuario_tenant, tenant, almacen
):
    cierre = cerrar_mes(
        tenant, PERIODO, "backups/lari.sql", usuario_tenant
    )
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _reabrir(
                    cierre.pk, usuario_tenant.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["PeriodoCerrado", "ok:2"]
