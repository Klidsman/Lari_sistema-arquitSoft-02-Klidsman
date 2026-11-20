"""Conflictos de concurrencia y suma de stock."""

from datetime import date

import pytest

from recojos.models import Recojo
from recojos.services import SerieYaExiste, crear_recojo
from series.models import Serie
from stock.models import StockGeneral


@pytest.mark.django_db
def test_misma_serie_en_dos_altas_deja_una_sola(
    usuario_tenant, material_seriado, almacen, monkeypatch
):
    datos = {
        "nombre": "Recojo de prueba", "fecha": date.today(),
        "lineas": [
            {"material_id": material_seriado.pk, "series": "ABC123456789"}
        ],
    }
    crear_recojo(datos, usuario_tenant)

    # Simula la carrera: la validación previa no ve la serie recién creada.
    monkeypatch.setattr(
        "recojos.services.series_existentes",
        lambda numeros: set(),
    )

    with pytest.raises(SerieYaExiste):
        crear_recojo(datos, usuario_tenant)

    assert Serie.objects.filter(numero="ABC123456789").count() == 1
    assert Recojo.objects.count() == 1


@pytest.mark.django_db
def test_dos_recojos_suman_stock(
    usuario_tenant, tenant, material_no_seriado, almacen
):
    for _ in range(2):
        crear_recojo(
            {
                "nombre": "Recojo de prueba", "fecha": date.today(),
                "lineas": [
                    {"material_id": material_no_seriado.pk, "cantidad": 5}
                ],
            },
            usuario_tenant,
        )

    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_no_seriado
        ).cantidad
        == 10
    )
