"""Contrato del listado de materiales."""

import pytest
from django.urls import reverse

from materiales.models import Material


@pytest.mark.django_db
def test_listado_muestra_campos(cliente_tenant, material):
    respuesta = cliente_tenant.get(reverse("listar_materiales"))

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert material.codigo in contenido
    assert material.descripcion in contenido
    assert material.lote in contenido
    assert material.tipo in contenido
    assert material.creado_por.email in contenido


@pytest.mark.django_db
def test_listado_ordenado_por_codigo(cliente_tenant, material, usuario_tenant):
    Material.objects.create(
        codigo="10402520000",
        descripcion="ANTERIOR",
        lote="",
        es_seriado=False,
        creado_por=usuario_tenant,
    )

    respuesta = cliente_tenant.get(reverse("listar_materiales"))
    contenido = respuesta.content.decode()

    assert contenido.index("10402520000") < contenido.index(material.codigo)


@pytest.mark.django_db
def test_listado_paginado(cliente_tenant, usuario_tenant):
    for indice in range(55):
        Material.objects.create(
            codigo=f"1{indice:010d}",
            descripcion=f"Material {indice}",
            lote="",
            es_seriado=False,
            creado_por=usuario_tenant,
        )

    respuesta = cliente_tenant.get(reverse("listar_materiales"))

    assert respuesta.status_code == 200
    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2


@pytest.mark.django_db
def test_sin_sesion_redirige_al_login(client):
    respuesta = client.get(reverse("listar_materiales"))

    assert respuesta.status_code == 302
    assert "/login/" in respuesta.url
