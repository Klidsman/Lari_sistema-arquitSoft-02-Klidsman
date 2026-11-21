"""Concurrencia de la confirmación de stock (008)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from django.db import connections

from asignaciones.models import EstadoSolicitud, LineaAsignacion, SolicitudAsignacion
from series.models import EstadoSerie
from stock.models import StockGeneral, StockTecnico
from stock.services import (
    StockInsuficiente,
    actualizar_stock_confirmacion_asignacion,
)


class _Resultado:
    def __init__(self, valor=None, error=None):
        self.valor = valor
        self.error = error


def _confirmar(solicitud, actor):
    connections.close_all()
    try:
        return _Resultado(
            valor=actualizar_stock_confirmacion_asignacion(solicitud, actor)
        )
    except Exception as exc:  # noqa: BLE001 - se inspecciona en el test
        return _Resultado(error=exc)
    finally:
        connections.close_all()


def _enviada(tenant, usuario_tenant, tecnico, material, cantidad=1):
    solicitud = SolicitudAsignacion.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        estado=EstadoSolicitud.ENVIADA,
        creado_por=usuario_tenant,
    )
    LineaAsignacion.objects.create(
        tenant=tenant,
        solicitud=solicitud,
        tecnico=tecnico,
        material=material,
        lote=material.lote,
        cantidad=cantidad,
    )
    return solicitud


@pytest.mark.django_db(transaction=True)
def test_dos_confirmaciones_de_la_misma_solicitud_mueven_stock_una_vez(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    from asignaciones.services import crear_y_enviar_solicitud

    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie_existente.pk],
            }
        ],
        usuario_tenant,
    )

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(
            ejecutor.map(
                lambda _: _confirmar(solicitud, usuario_almacen), range(2)
            )
        )

    assert sum(1 for r in resultados if r.valor is not None) == 1
    assert sum(1 for r in resultados if r.error is not None) == 1
    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.ASIGNADA
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 99
    assert StockTecnico.objects.get(
        tecnico=tecnico, material=material_seriado
    ).cantidad == 1


@pytest.mark.django_db(transaction=True)
def test_dos_solicitudes_compiten_por_el_mismo_stock(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=1
    )
    primera = _enviada(
        tenant, usuario_tenant, tecnico, material_no_seriado
    )
    segunda = _enviada(
        tenant, usuario_tenant, tecnico, material_no_seriado
    )

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(
            ejecutor.map(
                lambda solicitud: _confirmar(solicitud, usuario_almacen),
                [primera, segunda],
            )
        )

    assert sum(1 for r in resultados if r.valor is not None) == 1
    assert sum(1 for r in resultados if r.error is not None) == 1
    errores = [r.error for r in resultados if r.error is not None]
    assert any(isinstance(error, StockInsuficiente) for error in errores)
    assert StockGeneral.objects.get(
        tenant=tenant, material=material_no_seriado
    ).cantidad == 0
    assert StockTecnico.objects.get(
        tecnico=tecnico, material=material_no_seriado
    ).cantidad == 1
