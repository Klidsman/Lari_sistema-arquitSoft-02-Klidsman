"""Reversión de la confirmación cuando falla la auditoría."""

from datetime import date

import pytest

from asignaciones.almacen_services import confirmar_solicitud
from asignaciones.services import crear_y_enviar_solicitud
from auditoria.models import RegistroCambio
from series.models import EstadoSerie
from stock.models import StockGeneral, StockTecnico
from stock.services import actualizar_stock_confirmacion_asignacion


def _enviada(usuario_tenant, tenant, tecnico, material, serie):
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


@pytest.mark.django_db
def test_fallo_de_auditoria_de_008_revierte_stock_y_series(
    monkeypatch,
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    antes = RegistroCambio.objects.count()
    monkeypatch.setattr(
        "stock.services.registrar_cambio",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("auditoria")),
    )

    with pytest.raises(RuntimeError, match="auditoria"):
        actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)

    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.RESERVADA
    assert serie_existente.tecnico_id is None
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 100
    assert not StockTecnico.objects.exists()
    assert RegistroCambio.objects.count() == antes


@pytest.mark.django_db
def test_fallo_de_007_despues_de_008_revierte_todo(
    monkeypatch,
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    monkeypatch.setattr(
        "asignaciones.almacen_services.registrar_cambio",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("007")),
    )

    with pytest.raises(RuntimeError, match="007"):
        confirmar_solicitud(solicitud, usuario_almacen)

    serie_existente.refresh_from_db()
    solicitud.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.RESERVADA
    assert serie_existente.tecnico_id is None
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 100
    assert not StockTecnico.objects.exists()
    assert solicitud.estado == "ENVIADA"
    assert solicitud.confirmada_en is None
