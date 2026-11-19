"""Validaciones de recojos."""

from datetime import date

import pytest

from recojos.services import (
    clasificar_series,
    normalizar_lineas,
    validar_recojo_previo,
)


def test_clasificar_series():
    estados = clasificar_series(
        ["ABC123456789", "abc 123456789", "ABC123", "XYZ987654321"],
        {"XYZ987654321"},
    )

    assert [e["estado"] for e in estados] == [
        "valida",
        "duplicada",
        "invalida",
        "ya_existe",
    ]


def test_normalizar_lineas_ignora_vacias():
    lineas = normalizar_lineas(
        {
            "lineas": [
                {},
                {"material_id": "", "series": "", "cantidad": ""},
                {"material_id": "1"},
            ]
        }
    )

    assert lineas == [{"material_id": "1", "series": None, "cantidad": None}]


@pytest.mark.django_db
def test_fecha_obligatoria(tenant, material_no_seriado):
    resultado = validar_recojo_previo(
        tenant,
        {
            "nombre": "Recojo de prueba",
            "fecha": "",
            "lineas": [
                {"material_id": material_no_seriado.pk, "cantidad": "5"}
            ],
        },
    )

    assert resultado.errores[0] == "La fecha es obligatoria"


@pytest.mark.django_db
def test_sin_lineas(tenant):
    resultado = validar_recojo_previo(tenant, {"nombre": "Recojo de prueba", "fecha": date.today(), "lineas": []})

    assert "El recojo debe tener al menos una línea" in resultado.errores


@pytest.mark.django_db
def test_material_inexistente(tenant):
    resultado = validar_recojo_previo(
        tenant,
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [{"material_id": 9999, "cantidad": "1"}],
        },
    )

    assert "El material no existe en el catálogo" in resultado.errores


@pytest.mark.django_db
def test_seriado_sin_series(tenant, material_seriado):
    resultado = validar_recojo_previo(
        tenant,
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [{"material_id": material_seriado.pk, "series": ""}],
        },
    )

    assert "Debe indicar al menos una serie" in resultado.errores


@pytest.mark.django_db
def test_seriado_cantidad_distinta_de_uno(tenant, material_seriado):
    resultado = validar_recojo_previo(
        tenant,
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [
                {
                    "material_id": material_seriado.pk,
                    "series": "ABC123456789",
                    "cantidad": "2",
                }
            ],
        },
    )

    assert "Para un material seriado la cantidad debe ser 1" in resultado.errores


@pytest.mark.django_db
def test_no_seriado_sin_cantidad(tenant, material_no_seriado):
    resultado = validar_recojo_previo(
        tenant,
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [{"material_id": material_no_seriado.pk, "cantidad": "0"}],
        },
    )

    assert "La cantidad debe ser mayor a 0" in resultado.errores


@pytest.mark.django_db
def test_no_seriado_con_series(tenant, material_no_seriado):
    resultado = validar_recojo_previo(
        tenant,
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [
                {
                    "material_id": material_no_seriado.pk,
                    "cantidad": "1",
                    "series": "ABC123456789",
                }
            ],
        },
    )

    assert "Un material no seriado no admite series" in resultado.errores


@pytest.mark.django_db
def test_resultado_valido_expande_series(tenant, material_seriado):
    resultado = validar_recojo_previo(
        tenant,
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [
                {
                    "material_id": material_seriado.pk,
                    "series": "abc123456789\nDEF123456789",
                }
            ],
        },
    )

    assert resultado.valido is True
    assert [linea["serie_numero"] for linea in resultado.lineas] == [
        "ABC123456789",
        "DEF123456789",
    ]
