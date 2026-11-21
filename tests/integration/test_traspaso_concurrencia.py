"""Concurrencia de la confirmación de traspasos."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.utils import timezone

from acceso.models import Usuario
from series.models import EstadoSerie, Serie
from stock.models import StockTecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso, SolicitudTraspaso
from traspasos.services import confirmar_traspaso


def _ejecutar_confirmacion(solicitud_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        solicitud = SolicitudTraspaso.objects.get(pk=solicitud_id)
        actor = Usuario.objects.get(pk=actor_id)
        confirmar_traspaso(solicitud, actor)
        return "ok"
    except Exception as exc:  # el resultado se inspecciona en el test
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_confirmaciones_simultaneas_mueven_una_sola_vez(
    usuario_tenant, usuario_almacen, tenant, tecnico, material_seriado, almacen
):
    destino = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Destino",
        creado_por=usuario_tenant,
    )
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
    StockTecnico.objects.create(
        tenant=tenant, tecnico=destino, material=material_seriado, cantidad=0
    )
    solicitud = SolicitudTraspaso.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        estado=EstadoTraspaso.ENVIADA,
        creado_por=usuario_tenant,
        enviada_en=timezone.now(),
    )
    from traspasos.models import LineaTraspaso

    LineaTraspaso.objects.create(
        tenant=tenant,
        solicitud=solicitud,
        tecnico_origen=tecnico,
        tecnico_destino=destino,
        material=material_seriado,
        serie=serie,
        cantidad=1,
    )

    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _ejecutar_confirmacion(
                    solicitud.pk, usuario_almacen.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["EstadoTraspasoInvalido", "ok"]
    solicitud.refresh_from_db()
    serie.refresh_from_db()
    assert solicitud.estado == EstadoTraspaso.CONFIRMADA
    assert serie.tecnico_id == destino.pk
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_seriado
        ).cantidad
        == 0
    )
    assert (
        StockTecnico.objects.get(
            tecnico=destino, material=material_seriado
        ).cantidad
        == 1
    )
