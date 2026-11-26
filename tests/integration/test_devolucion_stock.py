"""Movimientos de stock en devoluciones."""

from datetime import date

import pytest
from django.utils import timezone

from logistica_inversa.models import Devolucion
from logistica_inversa.services import registrar_devolucion
from materiales.models import Material
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _serie(tenant, material, tecnico, actor, numero):
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=actor,
    )


@pytest.mark.django_db
def test_devolucion_mueve_stock_por_material_sin_negativos(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    otro_material = Material.objects.create(
        codigo="10402529999",
        descripcion="OTRO SERIADO",
        lote="LOTE2",
        es_seriado=True,
        creado_por=usuario_tenant,
    )
    primera = _serie(
        tenant, material_seriado, tecnico, usuario_tenant, "SER000000001"
    )
    segunda = _serie(
        tenant, material_seriado, tecnico, usuario_tenant, "SER000000002"
    )
    tercera = _serie(
        tenant, otro_material, tecnico, usuario_tenant, "SER000000003"
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=2
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=otro_material, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=5
    )
    StockGeneral.objects.create(
        tenant=tenant, material=otro_material, cantidad=5
    )

    registrar_devolucion(
        tenant,
        tecnico,
        date.today(),
        [primera, segunda, tercera],
        "",
        usuario_tenant,
    )

    for material, cantidad in (
        (material_seriado, 2),
        (otro_material, 1),
    ):
        assert (
            StockTecnico.objects.get(
                tenant=tenant, tecnico=tecnico, material=material
            ).cantidad
            == 0
        )
        assert (
            StockGeneral.objects.get(
                tenant=tenant, material=material
            ).cantidad
            == 5 + cantidad
        )
    assert not StockTecnico.objects.filter(cantidad__lt=0).exists()
    assert not StockGeneral.objects.filter(cantidad__lt=0).exists()


@pytest.mark.django_db
def test_total_del_tenant_se_conserva_en_la_devolucion(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, tecnico, usuario_tenant, "SER000000001"
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=4
    )
    registrar_devolucion(
        tenant, tecnico, date.today(), [serie], "", usuario_tenant
    )
    tecnico_stock = StockTecnico.objects.get(
        tenant=tenant, tecnico=tecnico, material=material_seriado
    )
    general.refresh_from_db()
    assert tecnico_stock.cantidad + general.cantidad == 5


@pytest.mark.django_db
def test_fallo_del_acta_revierte_devolucion_y_stock(
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
    monkeypatch,
):
    serie = _serie(
        tenant, material_seriado, tecnico, usuario_tenant, "SER000000001"
    )
    tecnico_stock = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=4
    )

    def _fallar(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr("logistica_inversa.services.generar_acta", _fallar)
    with pytest.raises(RuntimeError):
        registrar_devolucion(
            tenant, tecnico, date.today(), [serie], "", usuario_tenant
        )

    serie.refresh_from_db()
    tecnico_stock.refresh_from_db()
    general.refresh_from_db()
    assert not Devolucion.objects.exists()
    assert serie.estado == EstadoSerie.ASIGNADA
    assert serie.tecnico_id == tecnico.pk
    assert tecnico_stock.cantidad == 1
    assert general.cantidad == 4
