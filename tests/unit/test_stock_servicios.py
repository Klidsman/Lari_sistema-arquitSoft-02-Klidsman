"""Consultas fundacionales de stock."""

import pytest

from stock.services import (
    calcular_disponible,
    calcular_reservado,
    obtener_stock_general,
    obtener_stock_tecnico,
)


@pytest.mark.django_db
def test_obtener_stock_sin_fila_devuelve_cero(
    tenant, tecnico, material_no_seriado
):
    assert obtener_stock_general(tenant, material_no_seriado) == 0
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 0


@pytest.mark.django_db
def test_obtener_stock_existente(tenant, tecnico, material_seriado, stock_general, stock_tecnico):
    assert obtener_stock_general(tenant, material_seriado) == 100
    assert obtener_stock_tecnico(tecnico, material_seriado) == 10


@pytest.mark.django_db
def test_reservado_sin_asignaciones(tenant, material_seriado):
    assert calcular_reservado(tenant, material_seriado) == 0


@pytest.mark.django_db
def test_disponible(tenant, material_seriado, stock_general):
    assert calcular_disponible(tenant, material_seriado) == 100
