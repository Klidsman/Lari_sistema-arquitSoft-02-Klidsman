"""Rendimiento de listado, detalle y vista previa."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from recojos.models import Recojo


def _contar(cliente, url, datos=None):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = cliente.get(url, datos or {})
    assert respuesta.status_code == 200
    return len(contexto)


@pytest.mark.django_db
def test_listado_sin_n_mas_uno(cliente_tenant, recojo):
    pocas = _contar(cliente_tenant, reverse("lista_recojos"))
    for indice in range(10):
        Recojo.objects.create(
            tenant=recojo.tenant,
            region=recojo.region,
            fecha=recojo.fecha,
            creado_por=recojo.creado_por,
        )
    muchas = _contar(cliente_tenant, reverse("lista_recojos"))

    assert pocas == muchas


@pytest.mark.django_db
def test_detalle_usa_precarga(cliente_tenant, recojo):
    respuesta = cliente_tenant.get(reverse("detalle_recojo", args=[recojo.pk]))

    assert respuesta.status_code == 200
    assert len(respuesta.context["recojo"].lineas.all()) == 1
