"""Detalle de series: estados y ausencia de escrituras."""

from datetime import date

import pytest

from auditoria.models import RegistroCambio
from recojos.models import LineaRecojo, Recojo
from recojos.services import crear_recojo, previsualizar_series
from series.models import Serie
from stock.models import StockGeneral


@pytest.mark.django_db
def test_vista_previa_no_escribe(
    tenant, material_seriado, serie_existente, usuario_tenant
):
    estados = previsualizar_series(
        tenant,
        material_seriado,
        f"{serie_existente.numero}\nABC123\nNUEVA1234567\nNUEVA1234567",
    )

    assert [estado["estado"] for estado in estados] == [
        "ya_existe",
        "invalida",
        "valida",
        "duplicada",
    ]
    assert not Recojo.objects.exists()
    assert not LineaRecojo.objects.exists()
    assert not StockGeneral.objects.exists()
    assert not RegistroCambio.objects.exists()


@pytest.mark.django_db
def test_serie_ajena_es_ya_existe_sin_datos(
    tenant, material_seriado, usuario_otro_tenant, usuario_tenant
):
    Serie.objects.create(
        numero="AJENA1234567",
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        material=material_seriado,
        creado_por=usuario_otro_tenant,
    )

    estados = previsualizar_series(tenant, material_seriado, "AJENA1234567")

    assert estados == [{"numero": "AJENA1234567", "estado": "ya_existe"}]


@pytest.mark.django_db
def test_guardado_revalida(
    tenant, material_seriado, usuario_tenant, almacen, monkeypatch
):
    from recojos.services import RecojoInvalido

    monkeypatch.setattr(
        "recojos.services.series_existentes",
        lambda numeros: set(),
    )
    serie = Serie.objects.create(
        numero="ABC123456789",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        creado_por=usuario_tenant,
    )
    monkeypatch.setattr(
        "recojos.services.series_existentes",
        lambda numeros: {serie.numero},
    )

    with pytest.raises(RecojoInvalido):
        crear_recojo(
            {
                "nombre": "Recojo de prueba", "fecha": date.today(),
                "lineas": [
                    {"material_id": material_seriado.pk, "series": serie.numero}
                ],
            },
            usuario_tenant,
        )
