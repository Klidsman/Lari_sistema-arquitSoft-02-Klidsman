"""Contrato del listado y detalle de técnicos."""

import pytest
from django.urls import reverse

from tecnicos.models import Tecnico


@pytest.mark.django_db
def test_listado_muestra_campos(cliente_tenant, tecnico):
    respuesta = cliente_tenant.get(reverse("listar_tecnicos"))

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert tecnico.nif in contenido
    assert tecnico.nombre in contenido
    assert "Activo" in contenido


@pytest.mark.django_db
def test_listado_ordenado_por_nombre_y_nif(cliente_tenant, tenant, usuario_tenant):
    Tecnico.objects.create(
        tenant=tenant,
        nif="LA0002",
        nombre="Zulema",
        creado_por=usuario_tenant,
    )
    Tecnico.objects.create(
        tenant=tenant,
        nif="LA0001",
        nombre="Ana",
        creado_por=usuario_tenant,
    )

    respuesta = cliente_tenant.get(reverse("listar_tecnicos"))
    contenido = respuesta.content.decode()

    assert contenido.index("Ana") < contenido.index("Zulema")


@pytest.mark.django_db
def test_listado_paginado(cliente_tenant, tenant, usuario_tenant):
    for indice in range(55):
        Tecnico.objects.create(
            tenant=tenant,
            nif=f"LA{indice:04d}",
            nombre=f"Tecnico {indice:02d}",
            creado_por=usuario_tenant,
        )

    respuesta = cliente_tenant.get(reverse("listar_tecnicos"))

    assert respuesta.status_code == 200
    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2


@pytest.mark.django_db
def test_detalle(cliente_tenant, tecnico):
    respuesta = cliente_tenant.get(
        reverse("detalle_tecnico", args=[tecnico.pk])
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert tecnico.nif in contenido
    assert tecnico.nombre in contenido


@pytest.mark.django_db
def test_detalle_de_otro_tenant_404(cliente_tenant, tecnico_otro_tenant):
    respuesta = cliente_tenant.get(
        reverse("detalle_tecnico", args=[tecnico_otro_tenant.pk])
    )

    assert respuesta.status_code == 404
    assert "El técnico no existe" in respuesta.content.decode()
    assert tecnico_otro_tenant.nif not in respuesta.content.decode()


@pytest.mark.django_db
def test_detalle_inexistente(cliente_tenant):
    respuesta = cliente_tenant.get(reverse("detalle_tecnico", args=[9999]))

    assert respuesta.status_code == 404
    assert "El técnico no existe" in respuesta.content.decode()


@pytest.mark.django_db
def test_admin_y_almacen_no_acceden(cliente_autenticado, cliente_almacen):
    for cliente in (cliente_autenticado, cliente_almacen):
        assert cliente.get(reverse("listar_tecnicos")).status_code == 403
        assert cliente.get(reverse("crear_tecnico")).status_code == 403


@pytest.mark.django_db
def test_metodos_no_permitidos(cliente_tenant, tecnico):
    assert cliente_tenant.delete(reverse("listar_tecnicos")).status_code == 405
    assert (
        cliente_tenant.delete(reverse("detalle_tecnico", args=[tecnico.pk])).status_code
        == 405
    )
