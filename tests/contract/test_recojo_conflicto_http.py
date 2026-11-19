"""Conflicto de serie existente detectado en la base."""

from datetime import date

import pytest
from django.urls import reverse

from recojos.models import Recojo
from series.models import Serie


@pytest.mark.django_db
def test_conflicto_de_serie_responde_409(
    cliente_tenant,
    material_seriado,
    serie_existente,
    almacen,
    monkeypatch,
):
    monkeypatch.setattr(
        "recojos.services.series_existentes",
        lambda numeros: set(),
    )
    monkeypatch.setattr(
        "recojos.services.clasificar_series",
        lambda numeros, existentes: [
            {"numero": n, "estado": "valida"} for n in numeros
        ],
    )

    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        {
            "nombre": "Recojo de prueba",
            "fecha": date.today().isoformat(),
            "lineas-TOTAL_FORMS": "1",
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "0",
            "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-material_id": material_seriado.pk,
            "lineas-0-series": serie_existente.numero,
            "lineas-0-cantidad": "",
        },
    )

    assert respuesta.status_code == 409
    assert "La serie ya está registrada en el sistema" in respuesta.content.decode()
    assert not Recojo.objects.exists()
    assert Serie.objects.filter(numero=serie_existente.numero).count() == 1
