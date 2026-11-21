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
    def __init__(
        self,
        material_id,
        lote,
        serie_id,
        cantidad,
        origen_id=1,
        destino_id=2,
    ):
        self.material = type("Material", (), {"pk": material_id})()
        self.lote = lote
        self.serie = (
            type("Serie", (), {"pk": serie_id})() if serie_id else None
        )
        self.cantidad = cantidad
        self.tecnico_origen = type("Tecnico", (), {"pk": origen_id})()
        self.tecnico_destino = type("Tecnico", (), {"pk": destino_id})()


def _mov(material, lote, serie, cantidad, origen=1, destino=2):
    return MovimientoTraspaso(
        material, lote, serie, cantidad, origen, destino
    )


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
    salida = [_mov(1, "L1", 10, 1)]
    with pytest.raises(CuadreIncorrecto, match="Lo que sale debe cuadrar"):
        validar_cuadre_traspaso(_cuadre(salida, []))


def test_serie_duplicada_en_entrada():
    salida = [_mov(1, "L1", 10, 1)]
    entrada = [_mov(1, "L1", 10, 1), _mov(1, "L1", 10, 1)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))


def test_serie_con_lote_distinto():
    salida = [_mov(1, "L1", 10, 1)]
    entrada = [_mov(1, "L2", 10, 1)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))


def test_cantidad_no_seriada_distinta():
    salida = [_mov(2, "", None, 50)]
    entrada = [_mov(2, "", None, 40)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))


def test_movimiento_extra_y_faltante():
    salida = [_mov(2, "", None, 10)]
    entrada = [_mov(3, "", None, 10)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))


def test_cuadre_con_origen_y_destino_distintos_por_linea():
    salida = [_mov(2, "", None, 10, origen=1, destino=2)]
    entrada = [_mov(2, "", None, 10, origen=1, destino=3)]
    with pytest.raises(CuadreIncorrecto):
        validar_cuadre_traspaso(_cuadre(salida, entrada))
