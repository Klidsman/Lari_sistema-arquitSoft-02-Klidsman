"""Rendimiento: listado y fragmento sin N+1."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from materiales.models import Material


def _crear(usuario, cantidad, desde=0):
    for indice in range(desde, desde + cantidad):
        Material.objects.create(
            codigo=f"1{indice:010d}",
            descripcion=f"Material {indice}",
            lote="",
            es_seriado=False,
            creado_por=usuario,
        )


def _contar_consultas(cliente, url, datos=None):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = cliente.get(url, datos or {})
    assert respuesta.status_code == 200
    return len(contexto)


@pytest.mark.django_db
def test_listado_sin_n_mas_uno(cliente_tenant, usuario_tenant):
    _crear(usuario_tenant, 2)
    pocas = _contar_consultas(cliente_tenant, reverse("listar_materiales"))

    _crear(usuario_tenant, 10, desde=100)
    muchas = _contar_consultas(cliente_tenant, reverse("listar_materiales"))

    assert pocas == muchas


@pytest.mark.django_db
def test_fragmento_sin_n_mas_uno(cliente_tenant, usuario_tenant):
    _crear(usuario_tenant, 2)
    pocas = _contar_consultas(
        cliente_tenant,
        reverse("buscar_materiales_htmx"),
        {"q": "Material"},
    )

    _crear(usuario_tenant, 10, desde=100)
    muchas = _contar_consultas(
        cliente_tenant,
        reverse("buscar_materiales_htmx"),
        {"q": "Material"},
    )

    assert pocas == muchas


@pytest.mark.django_db
def test_busqueda_en_listado_sin_n_mas_uno(cliente_tenant, usuario_tenant):
    _crear(usuario_tenant, 2)
    pocas = _contar_consultas(
        cliente_tenant,
        reverse("listar_materiales"),
        {"q": "Material"},
    )

    _crear(usuario_tenant, 10, desde=100)
    muchas = _contar_consultas(
        cliente_tenant,
        reverse("listar_materiales"),
        {"q": "Material"},
    )

    assert pocas == muchas
