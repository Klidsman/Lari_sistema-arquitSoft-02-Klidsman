"""Normalización y validación de técnicos."""

import pytest

from tecnicos.services import (
    ValidacionTecnico,
    normalizar_nif,
    normalizar_nombre,
    validar_nif,
    validar_nombre,
)


def test_normalizar_nif():
    assert normalizar_nif(" la1234 ") == "LA1234"
    assert normalizar_nif(None) == ""


def test_validar_nif_formatos_invalidos():
    for nif in ("LA123", "LA12345", "A1234", "LA12A4", "LA 1234", "LA-1234"):
        with pytest.raises(
            ValidacionTecnico, match="El NIF debe tener el formato LAXXXX"
        ):
            validar_nif(nif)


def test_validar_nif_valido():
    assert validar_nif("la1234") == "LA1234"


def test_normalizar_nombre():
    assert normalizar_nombre("  Juan   Pérez ") == "Juan Pérez"


def test_nombre_limites():
    assert validar_nombre("X" * 100) == "X" * 100

    with pytest.raises(
        ValidacionTecnico, match="El nombre no puede superar los 100 caracteres"
    ):
        validar_nombre("X" * 101)


def test_nombre_vacio():
    with pytest.raises(ValidacionTecnico, match="El nombre es obligatorio"):
        validar_nombre("    ")
