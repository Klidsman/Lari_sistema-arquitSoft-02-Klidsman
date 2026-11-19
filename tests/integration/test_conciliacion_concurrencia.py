"""Concurrencia de la aprobación de conciliaciones."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection

from acceso.models import Usuario
from conciliaciones.models import Conciliacion, EstadoConciliacion
from conciliaciones.services import aprobar_conciliacion, crear_conciliacion
from stock.models import StockTecnico
from tests.reportes import archivo_xlsx, fila_no_seriada


def _aprobar(conciliacion_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        conciliacion = Conciliacion.objects.get(pk=conciliacion_id)
        actor = Usuario.objects.get(pk=actor_id)
        aprobar_conciliacion(conciliacion, actor)
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_aprobaciones_simultaneas_aplican_una_sola_vez(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_no_seriada(material_no_seriado, tecnico.nif, 4)]
        ),
    )
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _aprobar(
                    conciliacion.pk, usuario_tenant.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["EstadoConciliacionInvalido", "ok"]
    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.APROBADA
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 4
    )
