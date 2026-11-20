"""Integración de anulación de recojos."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from auditoria.models import RegistroCambio
from recojos.models import EstadoRecojo, Recojo
from recojos.services import (
    AnulacionNoPermitida,
    PlazoAnulacionVencido,
    anular_recojo,
    crear_recojo,
    listar_recojos,
    puede_anular_recojo,
)
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral


def _recojo(usuario, material):
    return crear_recojo(
        {
            "nombre": "Recojo anulable",
            "fecha": date.today(),
            "lineas": [
                {"material_id": material.pk, "series": "ABC123456789"}
            ],
        },
        usuario,
    )


@pytest.mark.django_db
def test_anulacion_revierte_stock_y_audita(
    usuario_tenant, tenant, material_seriado, almacen
):
    recojo = _recojo(usuario_tenant, material_seriado)

    anular_recojo(recojo, "Error de carga", usuario_tenant)

    recojo.refresh_from_db()
    assert recojo.estado == EstadoRecojo.ANULADO
    assert recojo.motivo_anulacion == "Error de carga"
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 0
    )
    serie = Serie.objects.get()
    assert serie.estado == EstadoSerie.DISPONIBLE

    assert RegistroCambio.objects.filter(
        entidad="Recojo", entidad_id=recojo.pk, campo="motivo_anulacion"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="Serie", entidad_id=serie.pk, campo="reactivada"
    ).exists()


@pytest.mark.django_db
def test_limite_de_24_horas(
    usuario_tenant, material_seriado, almacen
):
    recojo = _recojo(usuario_tenant, material_seriado)
    Recojo.objects.filter(pk=recojo.pk).update(
        creado_en=timezone.now() - timedelta(hours=24, minutes=1)
    )
    recojo.refresh_from_db()

    with pytest.raises(PlazoAnulacionVencido):
        anular_recojo(recojo, "Tarde", usuario_tenant)


@pytest.mark.django_db
def test_anulacion_idempotente(
    usuario_tenant, material_seriado, almacen
):
    recojo = _recojo(usuario_tenant, material_seriado)
    anular_recojo(recojo, "Error", usuario_tenant)
    antes = RegistroCambio.objects.count()

    anular_recojo(recojo, "Error de nuevo", usuario_tenant)

    assert RegistroCambio.objects.count() == antes
    recojo.refresh_from_db()
    assert recojo.motivo_anulacion == "Error"


@pytest.mark.django_db
def test_rollback_si_falla_stock(
    usuario_tenant, tenant, material_seriado, almacen, monkeypatch
):
    recojo = _recojo(usuario_tenant, material_seriado)

    def falla(*args, **kwargs):
        raise RuntimeError("falla de stock")

    monkeypatch.setattr("recojos.services.decrementar_stock_general", falla)

    with pytest.raises(RuntimeError):
        anular_recojo(recojo, "Error", usuario_tenant)

    recojo.refresh_from_db()
    assert recojo.estado == EstadoRecojo.REGISTRADO
    assert Serie.objects.get().estado == EstadoSerie.DISPONIBLE
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 1
    )


@pytest.mark.django_db
def test_rollback_si_falla_auditoria(
    usuario_tenant, tenant, material_seriado, almacen, monkeypatch
):
    recojo = _recojo(usuario_tenant, material_seriado)

    def falla(*args, **kwargs):
        raise RuntimeError("falla de auditoría")

    monkeypatch.setattr("recojos.services.registrar_cambio", falla)

    with pytest.raises(RuntimeError):
        anular_recojo(recojo, "Error", usuario_tenant)

    recojo.refresh_from_db()
    assert recojo.estado == EstadoRecojo.REGISTRADO
    assert Serie.objects.get().estado == EstadoSerie.DISPONIBLE
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 1
    )


@pytest.mark.django_db
def test_puede_anular_y_filtros(
    usuario_tenant, tenant, material_seriado, almacen
):
    recojo = _recojo(usuario_tenant, material_seriado)
    puede, mensaje = puede_anular_recojo(recojo)
    assert puede is True
    assert "24 horas" in mensaje

    anular_recojo(recojo, "Error", usuario_tenant)
    recojo.refresh_from_db()
    puede, mensaje = puede_anular_recojo(recojo)
    assert puede is False
    assert "ya fue anulado" in mensaje

    assert listar_recojos(tenant, estado="registrados").count() == 0
    assert listar_recojos(tenant, estado="anulados").count() == 1
    assert listar_recojos(tenant, estado="todos").count() == 1
