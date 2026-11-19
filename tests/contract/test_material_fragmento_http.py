"""Contrato del fragmento HTMX de búsqueda."""

import pytest
from django.urls import reverse

from materiales.models import Material


@pytest.mark.django_db
def test_fragmento_expone_atributos(cliente_tenant, material):
    respuesta = cliente_tenant.get(
        reverse("buscar_materiales_htmx"),
        {"q": "ROSETA"},
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert f'data-codigo="{material.codigo}"' in contenido
    assert f'data-descripcion="{material.descripcion}"' in contenido
    assert f'data-lote="{material.lote}"' in contenido
    assert f'data-tipo="{material.tipo}"' in contenido
    assert "<html" not in contenido


@pytest.mark.django_db
def test_fragmento_limit_por_defecto(cliente_tenant, usuario_tenant):
    for indice in range(25):
        Material.objects.create(
            codigo=f"1{indice:010d}",
            descripcion=f"Material {indice}",
            lote="",
            es_seriado=False,
            creado_por=usuario_tenant,
        )

    respuesta = cliente_tenant.get(reverse("buscar_materiales_htmx"))
    contenido = respuesta.content.decode()

    assert contenido.count('class="resultado-material"') == 20


@pytest.mark.django_db
def test_fragmento_limit_maximo(cliente_tenant, usuario_tenant):
    for indice in range(60):
        Material.objects.create(
            codigo=f"1{indice:010d}",
            descripcion=f"Material {indice}",
            lote="",
            es_seriado=False,
            creado_por=usuario_tenant,
        )

    respuesta = cliente_tenant.get(
        reverse("buscar_materiales_htmx"),
        {"limit": "999"},
    )

    assert respuesta.content.decode().count('class="resultado-material"') == 50


@pytest.mark.django_db
def test_fragmento_sin_resultados(cliente_tenant):
    respuesta = cliente_tenant.get(
        reverse("buscar_materiales_htmx"),
        {"q": "NOEXISTE"},
    )

    assert respuesta.status_code == 200
    assert "No se encontraron materiales" in respuesta.content.decode()


@pytest.mark.django_db
def test_fragmento_sin_datos_sensibles(cliente_tenant, material):
    respuesta = cliente_tenant.get(
        reverse("buscar_materiales_htmx"),
        {"q": material.codigo},
    )
    contenido = respuesta.content.decode()

    assert "tenant_id" not in contenido
    assert "region_id" not in contenido
    assert "stock" not in contenido
    assert material.creado_por.email not in contenido


@pytest.mark.django_db
def test_fragmento_solo_get(cliente_tenant):
    respuesta = cliente_tenant.post(reverse("buscar_materiales_htmx"))

    assert respuesta.status_code == 405
