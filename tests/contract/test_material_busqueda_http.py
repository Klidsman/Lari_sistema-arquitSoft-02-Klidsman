"""Contrato de búsqueda en el listado de materiales."""

import pytest
from django.urls import reverse

from materiales.models import Material


@pytest.mark.django_db
def test_busqueda_por_descripcion(cliente_tenant, material):
    respuesta = cliente_tenant.get(reverse("listar_materiales"), {"q": "ROSETA"})

    assert respuesta.status_code == 200
    assert material.codigo in respuesta.content.decode()


@pytest.mark.django_db
def test_busqueda_por_codigo(cliente_tenant, material):
    respuesta = cliente_tenant.get(
        reverse("listar_materiales"),
        {"q": "1040252"},
    )

    assert material.codigo in respuesta.content.decode()


@pytest.mark.django_db
def test_busqueda_vacia_no_filtra(cliente_tenant, material):
    respuesta = cliente_tenant.get(reverse("listar_materiales"), {"q": ""})

    assert material.codigo in respuesta.content.decode()


@pytest.mark.django_db
def test_mismos_resultados_para_dos_tenants(
    cliente_tenant, cliente_otro_tenant, material
):
    respuesta_a = cliente_tenant.get(
        reverse("listar_materiales"), {"q": "ROSETA"}
    )
    respuesta_b = cliente_otro_tenant.get(
        reverse("listar_materiales"), {"q": "ROSETA"}
    )

    assert material.codigo in respuesta_a.content.decode()
    assert material.codigo in respuesta_b.content.decode()


@pytest.mark.django_db
def test_busqueda_paginada(cliente_tenant, usuario_tenant):
    for indice in range(55):
        Material.objects.create(
            codigo=f"1{indice:010d}",
            descripcion="COMUN",
            lote="",
            es_seriado=False,
            creado_por=usuario_tenant,
        )

    respuesta = cliente_tenant.get(
        reverse("listar_materiales"), {"q": "COMUN"}
    )

    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2
