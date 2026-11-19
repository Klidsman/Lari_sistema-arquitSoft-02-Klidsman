"""Integración del alta de recojos."""

from datetime import date

import pytest

from acceso.models import Usuario
from auditoria.models import RegistroCambio
from recojos.models import Recojo
from recojos.services import crear_recojo
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral
from tenants.models import Tenant


def _datos(lineas, fecha=None):
    return {
        "nombre": "Recojo de prueba",
        "fecha": fecha or date.today(),
        "lineas": lineas,
    }


@pytest.mark.django_db
def test_alta_seriada_crea_series_stock_y_auditoria(
    usuario_tenant, tenant, material_seriado, almacen
):
    recojo = crear_recojo(
        _datos(
            [
                {
                    "material_id": material_seriado.pk,
                    "series": "ABC123456789\nDEF123456789\nGHI123456789",
                }
            ]
        ),
        usuario_tenant,
    )

    series = Serie.objects.filter(tenant=tenant)
    assert series.count() == 3
    assert set(series.values_list("estado", flat=True)) == {EstadoSerie.DISPONIBLE}
    assert set(series.values_list("region_id", flat=True)) == {tenant.region_id}
    assert set(series.values_list("lote", flat=True)) == {material_seriado.lote}

    stock = StockGeneral.objects.get(tenant=tenant, material=material_seriado)
    assert stock.cantidad == 3

    assert RegistroCambio.objects.filter(
        entidad="Recojo", entidad_id=recojo.pk, campo="alta"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="StockGeneral", entidad_id=stock.pk, campo="cantidad"
    ).exists()


@pytest.mark.django_db
def test_alta_no_seriada_stock_exacto(
    usuario_tenant, tenant, material_no_seriado, almacen
):
    crear_recojo(
        _datos([{"material_id": material_no_seriado.pk, "cantidad": 25}]),
        usuario_tenant,
    )

    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_no_seriado
        ).cantidad
        == 25
    )
    assert not Serie.objects.exists()


@pytest.mark.django_db
def test_normalizacion_antes_de_guardar(
    usuario_tenant, tenant, material_seriado, almacen
):
    crear_recojo(
        _datos(
            [
                {
                    "material_id": material_seriado.pk,
                    "series": " abc 123456789 ",
                }
            ]
        ),
        usuario_tenant,
    )

    assert Serie.objects.get().numero == "ABC123456789"


@pytest.mark.django_db
def test_region_desde_tenant(
    usuario_tenant, tenant, material_no_seriado, almacen, usuario_otro_tenant
):
    recojo = crear_recojo(
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "region_id": usuario_otro_tenant.tenant.region_id,
            "lineas": [{"material_id": material_no_seriado.pk, "cantidad": 1}],
        },
        usuario_tenant,
    )

    assert recojo.region_id == tenant.region_id


@pytest.mark.django_db
def test_tenant_suspendido(tenant, usuario_tenant, material_no_seriado, almacen):
    from recojos.services import TenantSuspendido

    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)
    actor = Usuario.objects.get(pk=usuario_tenant.pk)

    with pytest.raises(TenantSuspendido):
        crear_recojo(
            _datos([{"material_id": material_no_seriado.pk, "cantidad": 1}]),
            actor,
        )


@pytest.mark.django_db
def test_fallo_no_deja_auditoria(
    usuario_tenant, material_seriado, almacen
):
    from recojos.services import RecojoInvalido

    antes = RegistroCambio.objects.count()

    with pytest.raises(RecojoInvalido):
        crear_recojo(
            _datos(
                [
                    {
                        "material_id": material_seriado.pk,
                        "series": "ABC123456789\nABC123",
                    }
                ]
            ),
            usuario_tenant,
        )

    assert RegistroCambio.objects.count() == antes
    assert not Recojo.objects.exists()
