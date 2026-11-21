"""Contrato de los resultados de confirmación de stock (008)."""

from dataclasses import FrozenInstanceError, fields

import pytest

from stock.services import CambioStockMaterial, ResultadoConfirmacionStock


def test_campos_del_resultado():
    nombres = {campo.name for campo in fields(ResultadoConfirmacionStock)}
    assert nombres == {
        "solicitud_id",
        "series_actualizadas",
        "cambios_por_material",
        "confirmada_en",
        "total_series",
        "total_cantidad",
    }


def test_campos_del_cambio_por_material():
    nombres = {campo.name for campo in fields(CambioStockMaterial)}
    assert nombres == {
        "material_id",
        "stock_general_anterior",
        "stock_general_nuevo",
        "stock_tecnico_anterior",
        "stock_tecnico_nuevo",
        "tecnico_id",
    }


def test_resultado_es_inmutable():
    resultado = ResultadoConfirmacionStock(
        solicitud_id=1,
        series_actualizadas=[10],
        cambios_por_material=[],
        total_series=1,
        total_cantidad=0,
    )
    with pytest.raises(FrozenInstanceError):
        resultado.total_series = 2
