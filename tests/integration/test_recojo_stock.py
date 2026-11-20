"""Integración de stock y aislamiento de recojos."""

from datetime import date

import pytest

from recojos.models import Recojo
from recojos.services import (
    NoEncontrado,
    crear_recojo,
    listar_recojos,
    obtener_detalle_recojo,
)
from stock.models import StockGeneral


@pytest.mark.django_db
def test_stock_no_seriado_y_series_no_se_mezclan(
    usuario_tenant, tenant, material_seriado, material_no_seriado, almacen
):
    crear_recojo(
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [
                {"material_id": material_seriado.pk, "series": "ABC123456789"},
                {"material_id": material_no_seriado.pk, "cantidad": 10},
            ],
        },
        usuario_tenant,
    )

    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 1
    )
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_no_seriado
        ).cantidad
        == 10
    )


@pytest.mark.django_db
def test_recojo_de_otro_tenant_no_se_ve(
    usuario_tenant, tenant, recojo, usuario_otro_tenant
):
    otro = Recojo.objects.create(
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        fecha=date.today(),
        creado_por=usuario_otro_tenant,
    )

    assert list(listar_recojos(tenant).values_list("pk", flat=True)) == [recojo.pk]

    with pytest.raises(NoEncontrado, match="El recojo no existe"):
        obtener_detalle_recojo(tenant, otro.pk)


@pytest.mark.django_db
def test_totales_del_detalle(
    usuario_tenant, tenant, material_seriado, material_no_seriado, almacen
):
    recojo = crear_recojo(
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [
                {
                    "material_id": material_seriado.pk,
                    "series": "ABC123456789\nDEF123456789",
                },
                {"material_id": material_no_seriado.pk, "cantidad": 7},
            ],
        },
        usuario_tenant,
    )

    from recojos.services import totales_recojo

    detalle = obtener_detalle_recojo(tenant, recojo.pk)
    assert totales_recojo(detalle) == {
        "total_lineas": 3,
        "total_series": 2,
        "total_cantidad": 7,
    }
