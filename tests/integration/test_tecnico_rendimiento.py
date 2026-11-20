"""Rendimiento: listado, búsqueda y fragmento sin N+1."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tecnicos.models import Tecnico


def _crear(tenant, usuario, cantidad, desde=0):
    for indice in range(desde, desde + cantidad):
        Tecnico.objects.create(
            tenant=tenant,
            nif=f"LA{indice:04d}",
            nombre=f"Tecnico {indice:02d}",
            creado_por=usuario,
        )


def _consultas(cliente, url, datos=None):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = cliente.get(url, datos or {})
    assert respuesta.status_code == 200
    return len(contexto)


@pytest.mark.django_db
def test_listado_sin_n_mas_uno(cliente_tenant, tenant, usuario_tenant):
    _crear(tenant, usuario_tenant, 2)
    pocas = _consultas(cliente_tenant, reverse("listar_tecnicos"))

    _crear(tenant, usuario_tenant, 10, desde=100)
    muchas = _consultas(cliente_tenant, reverse("listar_tecnicos"))

    assert pocas == muchas


@pytest.mark.django_db
def test_busqueda_sin_n_mas_uno(cliente_tenant, tenant, usuario_tenant):
    _crear(tenant, usuario_tenant, 2)
    pocas = _consultas(
        cliente_tenant, reverse("listar_tecnicos"), {"q": "Tecnico"}
    )

    _crear(tenant, usuario_tenant, 10, desde=100)
    muchas = _consultas(
        cliente_tenant, reverse("listar_tecnicos"), {"q": "Tecnico"}
    )

    assert pocas == muchas


@pytest.mark.django_db
def test_fragmento_sin_n_mas_uno(cliente_tenant, tenant, usuario_tenant):
    _crear(tenant, usuario_tenant, 2)
    pocas = _consultas(
        cliente_tenant, reverse("buscar_tecnicos_htmx"), {"q": "Tecnico"}
    )

    _crear(tenant, usuario_tenant, 10, desde=100)
    muchas = _consultas(
        cliente_tenant, reverse("buscar_tecnicos_htmx"), {"q": "Tecnico"}
    )

    assert pocas == muchas
