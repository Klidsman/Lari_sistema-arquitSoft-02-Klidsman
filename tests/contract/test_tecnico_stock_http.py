"""Stock actual visible en el detalle del técnico (003)."""

import pytest
from django.urls import reverse

from materiales.models import Material
from stock.models import StockTecnico
from tecnicos.models import Tecnico


@pytest.mark.django_db
def test_detalle_muestra_stock_por_material(
    cliente_tenant, tecnico, material_seriado, stock_tecnico
):
    respuesta = cliente_tenant.get(
        reverse("detalle_tecnico", args=[tecnico.pk])
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "Stock actual" in contenido
    assert material_seriado.codigo in contenido
    assert material_seriado.descripcion in contenido
    assert "Seriado" in contenido
    assert "10" in contenido


@pytest.mark.django_db
def test_detalle_sin_stock_muestra_estado_vacio(
    cliente_tenant, tecnico
):
    respuesta = cliente_tenant.get(
        reverse("detalle_tecnico", args=[tecnico.pk])
    )

    assert "Este técnico no tiene stock registrado." in respuesta.content.decode()


@pytest.mark.django_db
def test_stock_de_otro_tenant_no_se_muestra(
    cliente_tenant,
    usuario_otro_tenant,
    tecnico,
    material_seriado,
    stock_tecnico,
    usuario_almacen,
):
    otro_tenant = usuario_otro_tenant.tenant
    otro_tecnico = Tecnico.objects.create(
        tenant=otro_tenant,
        nif="LA7777",
        nombre="Ajeno",
        creado_por=usuario_otro_tenant,
    )
    otro_material = Material.objects.create(
        codigo="10402529999",
        descripcion="MATERIAL AJENO",
        lote="AJENO",
        es_seriado=False,
        creado_por=usuario_almacen,
    )
    StockTecnico.objects.create(
        tenant=otro_tenant,
        tecnico=otro_tecnico,
        material=otro_material,
        cantidad=99,
    )

    respuesta = cliente_tenant.get(
        reverse("detalle_tecnico", args=[tecnico.pk])
    )
    contenido = respuesta.content.decode()

    assert otro_material.codigo not in contenido
    assert "MATERIAL AJENO" not in contenido
    assert material_seriado.codigo in contenido


@pytest.mark.django_db
def test_tecnico_desactivado_conserva_stock_visible(
    cliente_tenant, tecnico, material_seriado, stock_tecnico
):
    tecnico.activo = False
    tecnico.save(update_fields=["activo"])

    respuesta = cliente_tenant.get(
        reverse("detalle_tecnico", args=[tecnico.pk])
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert material_seriado.codigo in contenido
    assert "10" in contenido
