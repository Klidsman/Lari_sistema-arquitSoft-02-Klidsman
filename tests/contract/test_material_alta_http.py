"""Contrato del alta de materiales."""

import pytest
from django.urls import reverse

from materiales.models import Material


def _datos(**cambios):
    datos = {
        "codigo": "10402520279",
        "descripcion": "ROSETA",
        "lote": "FIBERHOME",
        "tipo": "SERIADO",
    }
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_alta_material(cliente_almacen):
    respuesta = cliente_almacen.post(reverse("crear_material"), _datos())

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("listar_materiales")
    assert Material.objects.filter(codigo="10402520279").exists()


@pytest.mark.django_db
def test_codigo_invalido(cliente_almacen):
    respuesta = cliente_almacen.post(
        reverse("crear_material"),
        _datos(codigo="1040252027"),
    )

    assert respuesta.status_code == 400
    assert "El código debe tener 11 dígitos" in respuesta.content.decode()


@pytest.mark.django_db
def test_codigo_duplicado(cliente_almacen, material):
    respuesta = cliente_almacen.post(
        reverse("crear_material"),
        _datos(codigo=material.codigo),
    )

    assert respuesta.status_code == 409
    assert "El material ya existe" in respuesta.content.decode()


@pytest.mark.django_db
def test_descripcion_solo_espacios(cliente_almacen):
    respuesta = cliente_almacen.post(
        reverse("crear_material"),
        _datos(descripcion="    "),
    )

    assert respuesta.status_code == 400
    assert "La descripción es obligatoria" in respuesta.content.decode()


@pytest.mark.django_db
def test_lote_demasiado_largo(cliente_almacen):
    respuesta = cliente_almacen.post(
        reverse("crear_material"),
        _datos(lote="X" * 51),
    )

    assert respuesta.status_code == 400
    assert "El lote no puede superar los 50 caracteres" in respuesta.content.decode()


@pytest.mark.django_db
def test_tipo_ausente(cliente_almacen):
    datos = _datos()
    datos.pop("tipo")

    respuesta = cliente_almacen.post(reverse("crear_material"), datos)

    assert respuesta.status_code == 400
    assert "El tipo es obligatorio" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_con_codigo_de_baja_reactiva(cliente_almacen, usuario_almacen):
    material = Material.objects.create(
        codigo="10402520279",
        descripcion="VIEJA",
        lote="",
        es_seriado=True,
        activo=False,
        creado_por=usuario_almacen,
    )

    respuesta = cliente_almacen.post(
        reverse("crear_material"),
        _datos(descripcion="NUEVA", lote="NUEVO", tipo="NO_SERIADO"),
    )

    assert respuesta.status_code == 302
    material.refresh_from_db()
    assert material.activo is True
    assert material.descripcion == "NUEVA"
    assert material.es_seriado is False


@pytest.mark.django_db
def test_tenant_no_puede_crear(cliente_tenant):
    respuesta = cliente_tenant.post(reverse("crear_material"), _datos())

    assert respuesta.status_code == 403
    assert not Material.objects.filter(codigo="10402520279").exists()


@pytest.mark.django_db
def test_admin_no_puede_crear(cliente_autenticado):
    respuesta = cliente_autenticado.post(reverse("crear_material"), _datos())

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_delete_no_permitido(cliente_almacen):
    respuesta = cliente_almacen.delete(reverse("crear_material"))

    assert respuesta.status_code == 405
