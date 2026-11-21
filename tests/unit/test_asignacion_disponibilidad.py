"""Disponibilidad y reservas de asignaciones."""

from datetime import date

import pytest

from asignaciones.services import (
    CantidadExcedeDisponible,
    calcular_disponible,
    calcular_reservado,
    crear_y_enviar_solicitud,
    validar_cantidad_disponible,
)
from stock.models import StockGeneral


@pytest.mark.django_db
def test_disponible_es_stock_menos_reservado(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )
    crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [{"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 20}],
        usuario_tenant,
    )

    assert calcular_reservado(tenant, material_no_seriado) == 20
    assert calcular_disponible(tenant, material_no_seriado) == 30
    validar_cantidad_disponible(tenant, material_no_seriado, 30)
    with pytest.raises(CantidadExcedeDisponible):
        validar_cantidad_disponible(tenant, material_no_seriado, 31)


@pytest.mark.django_db
def test_material_sin_stock_tiene_disponible_cero(
    tenant, material_no_seriado
):
    assert calcular_disponible(tenant, material_no_seriado) == 0
    with pytest.raises(CantidadExcedeDisponible):
        validar_cantidad_disponible(tenant, material_no_seriado, 1)
