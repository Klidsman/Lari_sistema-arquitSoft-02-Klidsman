"""Concurrencia de confirmaciones y rechazos del almacén."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection

from acceso.models import Usuario
from asignaciones import almacen_services
from asignaciones.models import EstadoSolicitud, SolicitudAsignacion
from asignaciones.services import crear_y_enviar_solicitud
from series.models import EstadoSerie
from stock.models import StockGeneral, StockTecnico


def _enviada(usuario_tenant, tenant, tecnico, material, serie):
    StockGeneral.objects.create(
        tenant=tenant, material=material, cantidad=100
    )
    return crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material.pk,
                "serie_ids": [serie.pk],
            }
        ],
        usuario_tenant,
    )


def _confirmar(solicitud_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        solicitud = SolicitudAsignacion.objects.get(pk=solicitud_id)
        actor = Usuario.objects.get(pk=actor_id)
        almacen_services.confirmar_solicitud(solicitud, actor)
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_confirmaciones_simultaneas_aplican_una_sola_vez(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )

    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _confirmar(
                    solicitud.pk, usuario_almacen.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["EstadoSolicitudInvalido", "ok"]
    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.CONFIRMADA
    assert StockGeneral.objects.get(tenant=tenant).cantidad == 99
    assert StockTecnico.objects.get(
        tenant=tenant, tecnico=tecnico
    ).cantidad == 1


def _rechazar(solicitud_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        solicitud = SolicitudAsignacion.objects.get(pk=solicitud_id)
        actor = Usuario.objects.get(pk=actor_id)
        almacen_services.rechazar_solicitud(
            solicitud, "Sin stock", actor
        )
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_rechazos_simultaneos_aplican_una_sola_vez(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )

    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _rechazar(
                    solicitud.pk, usuario_almacen.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["EstadoSolicitudInvalido", "ok"]
    solicitud.refresh_from_db()
    serie_existente.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.RECHAZADA
    assert serie_existente.estado == EstadoSerie.DISPONIBLE
