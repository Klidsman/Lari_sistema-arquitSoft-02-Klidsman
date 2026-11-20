"""Registro de materiales: normalización y cálculos."""

from datetime import date

import pytest

from registro_materiales.services import (
    CantidadInvalida,
    PeriodoInvalido,
    periodo_actual,
    periodo_anterior,
    periodo_de_fecha,
    procesar_lista,
    validar_periodo,
)


def test_procesar_lista_normaliza_y_deduplica():
    texto = "  ABC1  \n\nabc1\n  XYZ9\n\n"
    lista = procesar_lista(texto)
    assert lista.ordenes == ["ABC1", "XYZ9"]
    assert lista.rechazadas == []


def test_procesar_lista_rechaza_espacios_internos_y_separadores():
    lista = procesar_lista("AB 1\nAB,1\nAB;1\nOK1")
    assert lista.ordenes == ["OK1"]
    assert len(lista.rechazadas) == 3


def test_periodo_de_fecha_y_desplazamiento():
    assert periodo_de_fecha(date(2026, 11, 18)) == "2026-11"
    assert periodo_actual() == date.today().strftime("%Y-%m")
    assert periodo_anterior("2026-01") == "2025-12"
    with pytest.raises(PeriodoInvalido):
        validar_periodo("2026-13")
