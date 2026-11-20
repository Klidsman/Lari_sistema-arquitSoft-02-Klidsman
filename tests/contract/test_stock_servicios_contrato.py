"""Contrato de firmas y retornos de los servicios de stock."""

import inspect

from stock import services


def test_firmas_fundacionales():
    esperadas = {
        "obtener_stock_general": ["tenant", "material"],
        "obtener_stock_tecnico": ["tecnico", "material"],
        "calcular_reservado": ["tenant", "material"],
        "calcular_disponible": ["tenant", "material"],
        "incrementar_stock_general": ["tenant", "material", "cantidad", "actor"],
        "decrementar_stock_general": ["tenant", "material", "cantidad", "actor"],
        "incrementar_stock_tecnico": ["tecnico", "material", "cantidad", "actor"],
        "decrementar_stock_tecnico": ["tecnico", "material", "cantidad", "actor"],
    }

    for nombre, parametros in esperadas.items():
        firma = inspect.signature(getattr(services, nombre))
        assert list(firma.parameters) == parametros


def test_excepciones_con_mensajes():
    assert str(services.CantidadInvalida()) == "La cantidad debe ser mayor a 0"
    assert (
        str(services.StockInsuficiente())
        == "El tenant no tiene suficiente stock general"
    )
    assert (
        str(services.SerieNoReservada())
        == "La serie no está reservada para esta asignación"
    )
    assert (
        str(services.ConfirmacionStockInvalida())
        == "No se puede confirmar el stock de la asignación"
    )
