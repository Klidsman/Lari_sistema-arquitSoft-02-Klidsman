"""Movimientos de stock en bajas de equipos."""

import pytest
from django.utils import timezone

from logistica_inversa.services import registrar_baja_equipo
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _serie(tenant, material, actor, estado, tecnico=None):
    asignada = estado == EstadoSerie.ASIGNADA
    return Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=estado,
        tecnico=tecnico if asignada else None,
        asignada_en=timezone.now() if asignada else None,
        creado_por=actor,
    )


@pytest.mark.django_db
def test_baja_asignada_solo_descuenta_tecnico(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        EstadoSerie.ASIGNADA,
        tecnico,
    )
    tecnico_stock = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=3
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=10
    )
    registrar_baja_equipo(tenant, serie, "AVERIA", "", usuario_tenant)
    tecnico_stock.refresh_from_db()
    general.refresh_from_db()
    assert tecnico_stock.cantidad == 2
    assert general.cantidad == 10
    assert tecnico_stock.cantidad + general.cantidad == 12


@pytest.mark.django_db
def test_baja_disponible_solo_descuenta_general(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        EstadoSerie.DISPONIBLE,
    )
    tecnico_stock = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=3
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=10
    )
    registrar_baja_equipo(tenant, serie, "MIGRACION", "", usuario_tenant)
    tecnico_stock.refresh_from_db()
    general.refresh_from_db()
    assert tecnico_stock.cantidad == 3
    assert general.cantidad == 9
    assert tecnico_stock.cantidad + general.cantidad == 12


@pytest.mark.django_db
def test_baja_no_deja_stock_negativo(
    usuario_tenant, tenant, material_seriado, almacen
):
    serie = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        EstadoSerie.DISPONIBLE,
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=1
    )
    registrar_baja_equipo(tenant, serie, "OTRO", "", usuario_tenant)
    general.refresh_from_db()
    assert general.cantidad == 0
    assert not StockGeneral.objects.filter(cantidad__lt=0).exists()
