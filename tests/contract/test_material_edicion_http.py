"""Contrato de edición de materiales."""

import pytest
from django.urls import reverse

from materiales.models import Material


@pytest.mark.django_db
def test_creador_edita(cliente_almacen, material):
    respuesta = cliente_almacen.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": "ROSETA ÓPTICA", "lote": "FIBERHOME"},
    )

    assert respuesta.status_code == 302
    material.refresh_from_db()
    assert material.descripcion == "ROSETA ÓPTICA"


@pytest.mark.django_db
def test_admin_edita(cliente_autenticado, material):
    respuesta = cliente_autenticado.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": "EDITADA POR ADMIN", "lote": ""},
    )

    assert respuesta.status_code == 302
    material.refresh_from_db()
    assert material.descripcion == "EDITADA POR ADMIN"


@pytest.mark.django_db
def test_otra_cuenta_no_edita(cliente_otro_tenant, material):
    respuesta = cliente_otro_tenant.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": "NO PERMITIDO", "lote": ""},
    )

    assert respuesta.status_code == 403
    assert "No tienes permiso para editar este material" in respuesta.content.decode()


@pytest.mark.django_db
def test_almacen_edita_material_creado_por_tenant(cliente_almacen, usuario_tenant):
    material = Material.objects.create(
        codigo="10402520001",
        descripcion="LEGADO",
        lote="",
        es_seriado=True,
        creado_por=usuario_tenant,
    )

    respuesta = cliente_almacen.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": "EDITADO POR ALMACEN", "lote": ""},
    )

    assert respuesta.status_code == 302
    material.refresh_from_db()
    assert material.descripcion == "EDITADO POR ALMACEN"


@pytest.mark.django_db
def test_tenant_creador_no_edita(cliente_tenant, usuario_tenant):
    material = Material.objects.create(
        codigo="10402520002",
        descripcion="LEGADO",
        lote="",
        es_seriado=True,
        creado_por=usuario_tenant,
    )

    respuesta = cliente_tenant.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": "INTENTO", "lote": ""},
    )

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_material_inexistente(cliente_almacen):
    respuesta = cliente_almacen.get(reverse("editar_material", args=[9999]))

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_codigo_no_editable(cliente_almacen, material):
    respuesta = cliente_almacen.post(
        reverse("editar_material", args=[material.pk]),
        {
            "codigo": "99999999999",
            "descripcion": material.descripcion,
            "lote": material.lote,
        },
    )

    assert respuesta.status_code == 400
    assert "El código no se puede cambiar" in respuesta.content.decode()

    material.refresh_from_db()
    assert material.codigo == "10402520279"


@pytest.mark.django_db
def test_descripcion_solo_espacios(cliente_almacen, material):
    respuesta = cliente_almacen.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": "   ", "lote": ""},
    )

    assert respuesta.status_code == 400
    assert "La descripción es obligatoria" in respuesta.content.decode()


@pytest.mark.django_db
def test_delete_no_permitido(cliente_almacen, material):
    respuesta = cliente_almacen.delete(
        reverse("editar_material", args=[material.pk])
    )

    assert respuesta.status_code == 405
