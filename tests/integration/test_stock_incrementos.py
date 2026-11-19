"""Incrementos y decrementos fundacionales de stock."""

import pytest

from auditoria.models import RegistroCambio
from stock.models import StockGeneral, StockTecnico
from stock.services import (
    CantidadInvalida,
    StockInsuficiente,
    TenantNoCoincide,
    decrementar_stock_general,
    decrementar_stock_tecnico,
    incrementar_stock_general,
    incrementar_stock_tecnico,
)


@pytest.mark.django_db
def test_incrementar_general_crea_y_suma(tenant, material_seriado, usuario_tenant):
    assert (
        incrementar_stock_general(tenant, material_seriado, 5, usuario_tenant)
        == 5
    )
    assert (
        incrementar_stock_general(tenant, material_seriado, 7, usuario_tenant)
        == 12
    )

    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 12
    )
    assert (
        RegistroCambio.objects.filter(
            entidad="StockGeneral", campo="cantidad"
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_incrementar_tecnico_copia_tenant(
    tenant, tecnico, material_seriado, usuario_tenant
):
    assert (
        incrementar_stock_tecnico(
            tecnico, material_seriado, 5, usuario_tenant
        )
        == 5
    )

    fila = StockTecnico.objects.get(
        tecnico=tecnico, material=material_seriado
    )
    assert fila.tenant_id == tenant.pk
    assert fila.cantidad == 5


@pytest.mark.django_db
def test_cantidades_invalidas(tenant, tecnico, material_seriado, usuario_tenant):
    for cantidad in (0, -1, 1.5, "1", True):
        with pytest.raises(CantidadInvalida):
            incrementar_stock_general(
                tenant, material_seriado, cantidad, usuario_tenant
            )
        with pytest.raises(CantidadInvalida):
            incrementar_stock_tecnico(
                tecnico, material_seriado, cantidad, usuario_tenant
            )


@pytest.mark.django_db
def test_decrementar_general(tenant, material_seriado, usuario_tenant, stock_general):
    assert (
        decrementar_stock_general(tenant, material_seriado, 30, usuario_tenant)
        == 70
    )
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 70
    )


@pytest.mark.django_db
def test_decrementar_general_insuficiente(
    tenant, material_seriado, usuario_tenant, stock_general
):
    with pytest.raises(
        StockInsuficiente,
        match="El tenant no tiene suficiente stock general",
    ):
        decrementar_stock_general(
            tenant, material_seriado, 101, usuario_tenant
        )

    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 100
    )


@pytest.mark.django_db
def test_decrementar_tecnico(tenant, tecnico, material_seriado, usuario_tenant, stock_tecnico):
    assert (
        decrementar_stock_tecnico(tecnico, material_seriado, 4, usuario_tenant)
        == 6
    )


@pytest.mark.django_db
def test_decrementar_tecnico_insuficiente(
    tenant, tecnico, material_seriado, usuario_tenant, stock_tecnico
):
    with pytest.raises(
        StockInsuficiente, match="El técnico no tiene suficiente stock"
    ):
        decrementar_stock_tecnico(
            tecnico, material_seriado, 11, usuario_tenant
        )

    assert StockTecnico.objects.get(pk=stock_tecnico.pk).cantidad == 10


@pytest.mark.django_db
def test_tenant_no_coincide(
    tecnico, material_seriado, usuario_tenant, usuario_otro_tenant
):
    StockTecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        tecnico=tecnico,
        material=material_seriado,
        cantidad=10,
    )

    with pytest.raises(TenantNoCoincide):
        decrementar_stock_tecnico(
            tecnico, material_seriado, 1, usuario_tenant
        )
