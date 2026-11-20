"""Concurrencia de devoluciones."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.utils import timezone

from acceso.models import Usuario
from logistica_inversa.services import registrar_devolucion
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _devolver(tenant_id, tecnico_id, serie_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        from tecnicos.models import Tecnico
        from tenants.models import Tenant

        tenant = Tenant.objects.get(pk=tenant_id)
        tecnico = Tecnico.objects.get(pk=tecnico_id)
        serie = Serie.objects.get(pk=serie_id)
        actor = Usuario.objects.get(pk=actor_id)
        registrar_devolucion(
            tenant, tecnico, date.today(), [serie], "", actor
        )
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_devoluciones_simultaneas_de_la_misma_serie(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )

    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _devolver(
                    tenant.pk,
                    tecnico.pk,
                    serie.pk,
                    usuario_tenant.pk,
                    barrera,
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["SerieNoEnTecnico", "ok"]
    serie.refresh_from_db()
    general.refresh_from_db()
    assert serie.estado == EstadoSerie.DISPONIBLE
    assert serie.tecnico_id is None
    assert general.cantidad == 1
