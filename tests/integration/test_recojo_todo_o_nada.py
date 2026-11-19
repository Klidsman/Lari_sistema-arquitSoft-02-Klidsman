"""Regla todo o nada del recojo."""

from datetime import date

import pytest

from auditoria.models import RegistroCambio
from recojos.models import LineaRecojo, Recojo
from recojos.services import crear_recojo
from series.models import Serie
from stock.models import StockGeneral


def _datos(material, series):
    return {
        "nombre": "Recojo de prueba", "fecha": date.today(),
        "lineas": [{"material_id": material.pk, "series": series}],
    }


@pytest.mark.django_db
def test_serie_invalida_no_deja_nada(usuario_tenant, material_seriado, almacen):
    from recojos.services import RecojoInvalido

    series = "\n".join(f"ABC12345678{i}" for i in range(10)) + "\nABC123"

    with pytest.raises(RecojoInvalido):
        crear_recojo(_datos(material_seriado, series), usuario_tenant)

    assert not Recojo.objects.exists()
    assert not LineaRecojo.objects.exists()
    assert not Serie.objects.exists()
    assert not StockGeneral.objects.exists()
    assert not RegistroCambio.objects.filter(entidad="Recojo").exists()


@pytest.mark.django_db
def test_fallo_de_stock_revierte_todo(
    usuario_tenant, material_seriado, almacen, monkeypatch
):
    def stock_que_falla(*args, **kwargs):
        raise RuntimeError("falla de stock")

    monkeypatch.setattr("recojos.services.incrementar_stock_general", stock_que_falla)

    with pytest.raises(RuntimeError):
        crear_recojo(_datos(material_seriado, "ABC123456789"), usuario_tenant)

    assert not Recojo.objects.exists()
    assert not Serie.objects.exists()
    assert not StockGeneral.objects.exists()


@pytest.mark.django_db
def test_fallo_de_auditoria_revierte_todo(
    usuario_tenant, material_seriado, almacen, monkeypatch
):
    def auditoria_que_falla(*args, **kwargs):
        raise RuntimeError("falla de auditoría")

    monkeypatch.setattr("recojos.services.registrar_cambio", auditoria_que_falla)

    with pytest.raises(RuntimeError):
        crear_recojo(_datos(material_seriado, "ABC123456789"), usuario_tenant)

    assert not Recojo.objects.exists()
    assert not Serie.objects.exists()
    assert not StockGeneral.objects.exists()
