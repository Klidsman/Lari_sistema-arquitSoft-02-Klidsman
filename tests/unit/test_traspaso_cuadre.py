"""Cuadre de movimientos de traspaso."""

import pytest

from traspasos.services import (
    CuadreIncorrecto,
    CuadreTraspaso,
    MovimientoTraspaso,
    construir_movimientos,
    validar_cuadre_traspaso,
)


class _Linea:
    def __init__(self, material_id, lote, serie_id, cantidad):
        self.material = type("Material", (), {"pk": material_id})()
        self.lote = lote
        self.serie = (
            type("Serie", (), {"pk": serie_id})() if serie_id else None
        )
        self.cantidad = cantidad


def _cuadre(salida, entrada):
    return CuadreTraspaso(salida=salida, entrada=entrada)


def test_cuadre_correcto_por_series_y_cantidades():
    lineas = [
        _Linea(1, "L1", 10, 1),
        _Linea(1, "L1", 11, 1),
        _Linea(2, "", None, 5),
    ]
    cuadre = construir_movimientos(lineas)
    validar_cuadre_traspaso(cuadre)
    assert len(cuadre.salida) == 3
    assert cuadre.salida == cuadre.entrada


def test_serie_que_sale_y_no_entra():
    salida = [MovimientoTraspaso(1, "L1", 10, 1)]
    with pytest.raises(CuadreIncorrecto, match="Lo que sale debe cuadrar"):
        validar_cuadre_traspaso(_cuadre(salida, []))


def test_serie_duplicada_en_entrada():
    salida = [MovimientoTraspaso(1, "L1", 10, 1)]
    entrada = [
        MovimientoTraspaso(1, "L1", 10, 1),
        MovimientoTraspaso(1, "L1", 10, 1),
    ]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))


def test_serie_con_lote_distinto():
    salida = [MovimientoTraspaso(1, "L1", 10, 1)]
    entrada = [MovimientoTraspaso(1, "L2", 10, 1)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))


def test_cantidad_no_seriada_distinta():
    salida = [MovimientoTraspaso(2, "", None, 50)]
    entrada = [MovimientoTraspaso(2, "", None, 40)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))


def test_movimiento_extra_y_faltante():
    salida = [MovimientoTraspaso(2, "", None, 10)]
    entrada = [MovimientoTraspaso(3, "", None, 10)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))
