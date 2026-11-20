"""Contrato del fragmento HTMX de técnicos."""

import pytest
from django.urls import reverse

from tecnicos.models import Tecnico


@pytest.mark.django_db
def test_atributos_del_fragmento(cliente_tenant, tecnico):
    respuesta = cliente_tenant.get(
        reverse("buscar_tecnicos_htmx"),
        {"q": "LA1234"},
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert f'data-nif="{tecnico.nif}"' in contenido
    assert f'data-nombre="{tecnico.nombre}"' in contenido
    assert 'data-activo="true"' in contenido
    assert "<html" not in contenido


@pytest.mark.django_db
def test_solo_activos(cliente_tenant, tecnico_desactivado):
    respuesta = cliente_tenant.get(
        reverse("buscar_tecnicos_htmx"),
        {"q": tecnico_desactivado.nif},
    )

    contenido = respuesta.content.decode()
    assert tecnico_desactivado.nif not in contenido
    assert "No se encontraron técnicos" in contenido


@pytest.mark.django_db
def test_limit_por_defecto_y_maximo(cliente_tenant, tenant, usuario_tenant):
    for indice in range(60):
        Tecnico.objects.create(
            tenant=tenant,
            nif=f"LA{indice:04d}",
            nombre=f"Tecnico {indice:02d}",
            creado_por=usuario_tenant,
        )

    por_defecto = cliente_tenant.get(reverse("buscar_tecnicos_htmx"))
    maximo = cliente_tenant.get(
        reverse("buscar_tecnicos_htmx"), {"limit": "999"}
    )

    assert por_defecto.content.decode().count('class="resultado-tecnico"') == 20
    assert maximo.content.decode().count('class="resultado-tecnico"') == 50


@pytest.mark.django_db
def test_estado_vacio(cliente_tenant):
    respuesta = cliente_tenant.get(
        reverse("buscar_tecnicos_htmx"), {"q": "NOEXISTE"}
    )

    assert "No se encontraron técnicos" in respuesta.content.decode()


@pytest.mark.django_db
def test_sin_datos_sensibles(cliente_tenant, tecnico):
    contenido = cliente_tenant.get(
        reverse("buscar_tecnicos_htmx"), {"q": tecnico.nif}
    ).content.decode()

    assert "tenant_id" not in contenido
    assert "region_id" not in contenido
    assert "stock" not in contenido
    assert tecnico.creado_por.email not in contenido


@pytest.mark.django_db
def test_post_y_roles(cliente_tenant, cliente_autenticado):
    assert cliente_tenant.post(reverse("buscar_tecnicos_htmx")).status_code == 405
    assert cliente_autenticado.get(reverse("buscar_tecnicos_htmx")).status_code == 403
