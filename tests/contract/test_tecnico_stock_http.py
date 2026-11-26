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


@pytest.mark.django_db
def test_stock_actual_lista_todos_los_tecnicos_y_materiales(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    stock_tecnico,
    usuario_almacen,
):
    otro = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Técnico Destino",
        creado_por=usuario_tenant,
    )
    otro_material = Material.objects.create(
        codigo="10402528888",
        descripcion="CABLE DE PRUEBA",
        lote="LOTE-2",
        es_seriado=False,
        creado_por=usuario_almacen,
    )
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=otro,
        material=otro_material,
        cantidad=4,
    )

    respuesta = cliente_tenant.get(reverse("stock_actual_tecnicos"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "Stock actual" in contenido
    assert tecnico.nombre in contenido
    assert otro.nombre in contenido
    assert material_seriado.codigo in contenido
    assert otro_material.codigo in contenido
    assert ">14<" in contenido


@pytest.mark.django_db
def test_stock_actual_filtra_por_tecnico_y_material(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    stock_tecnico,
    usuario_almacen,
):
    otro = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Técnico Destino",
        creado_por=usuario_tenant,
    )
    otro_material = Material.objects.create(
        codigo="10402527777",
        descripcion="FIBRA DE PRUEBA",
        lote="LOTE-3",
        es_seriado=False,
        creado_por=usuario_almacen,
    )
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=otro,
        material=otro_material,
        cantidad=2,
    )

    por_tecnico = cliente_tenant.get(
        reverse("stock_actual_tecnicos"), {"q": "LA2222"}
    ).content.decode()
    assert otro_material.codigo in por_tecnico
    assert material_seriado.codigo not in por_tecnico

    por_material = cliente_tenant.get(
        reverse("stock_actual_tecnicos"), {"q": "ROSETA"}
    ).content.decode()
    assert material_seriado.codigo in por_material
    assert otro_material.codigo not in por_material


@pytest.mark.django_db
def test_stock_actual_no_muestra_otro_tenant(
    cliente_tenant,
    usuario_otro_tenant,
    usuario_almacen,
    tecnico,
    material_seriado,
    stock_tecnico,
):
    otro_tenant = usuario_otro_tenant.tenant
    otro_tecnico = Tecnico.objects.create(
        tenant=otro_tenant,
        nif="LA7777",
        nombre="Ajeno",
        creado_por=usuario_otro_tenant,
    )
    otro_material = Material.objects.create(
        codigo="10402526666",
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

    contenido = cliente_tenant.get(
        reverse("stock_actual_tecnicos")
    ).content.decode()

    assert otro_material.codigo not in contenido
    assert otro_tecnico.nombre not in contenido
    assert material_seriado.codigo in contenido


@pytest.mark.django_db
def test_stock_actual_requiere_cuenta_tenant(
    cliente_autenticado, cliente_almacen
):
    assert (
        cliente_autenticado.get(reverse("stock_actual_tecnicos")).status_code
        == 403
    )
    assert (
        cliente_almacen.get(reverse("stock_actual_tecnicos")).status_code
        == 403
    )
