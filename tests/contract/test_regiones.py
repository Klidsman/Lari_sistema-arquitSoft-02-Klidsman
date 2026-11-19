"""Contrato de regiones y almacenes."""

import pytest
from django.urls import reverse

from auditoria.models import RegistroCambio
from tenants.models import Almacen, Region


def _datos_validos(**cambios):
    datos = {
        "codigo": "ARE",
        "nombre": "Arequipa",
        "centro": "PR05",
        "almacen": "BE03",
        "buzon": "almacen.are@lari.local",
    }
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_listado_regiones(cliente_autenticado, region):
    respuesta = cliente_autenticado.get(reverse("listar_regiones"))

    assert respuesta.status_code == 200
    assert "LIM" in respuesta.content.decode()


@pytest.mark.django_db
def test_listado_paginado_50_por_pagina(cliente_autenticado, usuario_admin):
    for indice in range(55):
        nueva = Region.objects.create(
            codigo=f"R{indice:03d}",
            nombre=f"Región {indice}",
            creado_por=usuario_admin,
        )
        Almacen.objects.create(
            region=nueva,
            centro="PR05",
            codigo_almacen=f"B{indice:03d}",
            buzon=f"region{indice}@lari.local",
            creado_por=usuario_admin,
        )

    respuesta = cliente_autenticado.get(reverse("listar_regiones"))

    assert respuesta.status_code == 200
    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2


@pytest.mark.django_db
def test_alta_region_redirige_al_listado(cliente_autenticado):
    respuesta = cliente_autenticado.post(reverse("crear_region"), _datos_validos())

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("listar_regiones")

    region = Region.objects.get(codigo="ARE")
    assert region.nombre == "Arequipa"
    assert region.almacen.centro == "PR05"
    assert region.almacen.codigo_almacen == "BE03"
    assert RegistroCambio.objects.filter(entidad="Region", campo="alta").exists()


@pytest.mark.django_db
def test_alta_codigo_duplicado(cliente_autenticado, region):
    respuesta = cliente_autenticado.post(
        reverse("crear_region"),
        _datos_validos(codigo="LIM"),
    )

    assert respuesta.status_code == 409
    assert "El código de región ya existe" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_buzon_invalido(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        reverse("crear_region"),
        _datos_validos(buzon="no-es-un-correo"),
    )

    assert respuesta.status_code == 400
    assert "El buzón no es válido" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_centro_o_almacen_vacios(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        reverse("crear_region"),
        _datos_validos(centro="", almacen=""),
    )

    assert respuesta.status_code == 400
    assert "Centro y Almacén son obligatorios" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_nombre_vacio(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        reverse("crear_region"),
        _datos_validos(nombre=""),
    )

    assert respuesta.status_code == 400
    assert "El nombre es obligatorio" in respuesta.content.decode()


@pytest.mark.django_db
def test_edicion_auditada(cliente_autenticado, region, almacen):
    respuesta = cliente_autenticado.post(
        reverse("editar_region", args=[region.pk]),
        {
            "nombre": "Lima Norte",
            "centro": "PR05",
            "almacen": "BE03",
            "buzon": "nuevo.lim@lari.local",
            "activa": "on",
        },
    )

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("listar_regiones")

    region.refresh_from_db()
    assert region.nombre == "Lima Norte"

    registro = RegistroCambio.objects.get(
        entidad="Region",
        entidad_id=region.pk,
        campo="nombre",
    )
    assert registro.valor_anterior == "Lima"
    assert registro.valor_nuevo == "Lima Norte"


@pytest.mark.django_db
def test_edicion_region_inexistente(cliente_autenticado):
    respuesta = cliente_autenticado.get(reverse("editar_region", args=[9999]))

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_delete_no_permitido(cliente_autenticado, region):
    respuesta_listado = cliente_autenticado.delete(reverse("listar_regiones"))
    respuesta_edicion = cliente_autenticado.delete(
        reverse("editar_region", args=[region.pk])
    )

    assert respuesta_listado.status_code == 405
    assert respuesta_edicion.status_code == 405


@pytest.mark.django_db
def test_solo_admin_plataforma(cliente_autenticado, usuario_admin):
    from django.test import Client

    from acceso.models import Rol, Usuario

    usuario = Usuario.objects.create_user(
        email="otro-admin@lari.local",
        password="ClaveAdmin12345",
        rol=Rol.ADMIN_PLATAFORMA,
        is_active=True,
    )
    cliente = Client()
    cliente.force_login(usuario)

    respuesta = cliente.get(reverse("listar_regiones"))

    assert respuesta.status_code == 200
    assert usuario_admin.rol == Rol.ADMIN_PLATAFORMA
