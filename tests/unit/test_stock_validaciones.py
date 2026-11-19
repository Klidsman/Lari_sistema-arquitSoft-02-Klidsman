"""Restricciones de los modelos de stock."""

import pytest
from django.db import DatabaseError, transaction

from stock.models import StockGeneral, StockTecnico


@pytest.mark.django_db
def test_stock_general_unico_por_tenant_material(
    tenant, material_seriado, stock_general
):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            StockGeneral.objects.create(
                tenant=tenant,
                material=material_seriado,
                cantidad=1,
            )


@pytest.mark.django_db
def test_stock_tecnico_unico_por_tecnico_material(
    tenant, tecnico, material_seriado, stock_tecnico
):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            StockTecnico.objects.create(
                tenant=tenant,
                tecnico=tecnico,
                material=material_seriado,
                cantidad=1,
            )


@pytest.mark.django_db
def test_cantidad_negativa_falla(tenant, material_seriado):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            StockGeneral.objects.create(
                tenant=tenant,
                material=material_seriado,
                cantidad=-1,
            )


@pytest.mark.django_db
def test_stock_tecnico_con_tenant(tenant, tecnico, material_seriado):
    fila = StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_seriado,
        cantidad=5,
    )

    assert fila.tenant_id == tecnico.tenant_id
