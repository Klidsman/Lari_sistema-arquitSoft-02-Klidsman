"""Contrato de tenants."""

import pytest
from django.urls import reverse

from auditoria.models import RegistroCambio
from tenants.models import Tenant


def _datos(region, **cambios):
    datos = {"codigo": "TEN-100", "nombre": "Nuevo tenant", "region": region.pk}
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_listado_tenants(cliente_autenticado, tenant):
    respuesta = cliente_autenticado.get(reverse("listar_tenants"))

    assert respuesta.status_code == 200
    assert "TEN-001" in respuesta.content.decode()


@pytest.mark.django_db
def test_listado_paginado_50_por_pagina(cliente_autenticado, region, usuario_admin):
    for indice in range(55):
        Tenant.objects.create(
            codigo=f"T{indice:03d}",
            nombre=f"Tenant {indice}",
            region=region,
            creado_por=usuario_admin,
        )

    respuesta = cliente_autenticado.get(reverse("listar_tenants"))

    assert respuesta.status_code == 200
    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2


@pytest.mark.django_db
def test_alta_tenant_redirige_al_detalle(cliente_autenticado, region):
    respuesta = cliente_autenticado.post(
        reverse("crear_tenant"),
        _datos(region),
    )

    assert respuesta.status_code == 302
    tenant = Tenant.objects.get(codigo="TEN-100")
    assert tenant.estado == Tenant.ESTADO_ACTIVO
    assert respuesta.url == reverse("detalle_tenant", args=[tenant.pk])
    assert RegistroCambio.objects.filter(
        entidad="Tenant", entidad_id=tenant.pk, campo="alta"
    ).exists()


@pytest.mark.django_db
def test_alta_tenant_sin_region(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        reverse("crear_tenant"),
        {"codigo": "TEN-100", "nombre": "Sin región"},
    )

    assert respuesta.status_code == 400
    assert "El tenant debe pertenecer a una región" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_tenant_region_inactiva(cliente_autenticado, region):
    region.activa = False
    region.save(update_fields=["activa"])

    respuesta = cliente_autenticado.post(
        reverse("crear_tenant"),
        _datos(region),
    )

    assert respuesta.status_code == 400
    assert "La región seleccionada no está disponible" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_tenant_codigo_duplicado(cliente_autenticado, tenant):
    respuesta = cliente_autenticado.post(
        reverse("crear_tenant"),
        _datos(tenant.region, codigo="TEN-001"),
    )

    assert respuesta.status_code == 409
    assert "El código de tenant ya existe" in respuesta.content.decode()


@pytest.mark.django_db
def test_detalle_tenant(cliente_autenticado, tenant):
    respuesta = cliente_autenticado.get(
        reverse("detalle_tenant", args=[tenant.pk])
    )

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "TEN-001" in contenido
    assert "Lima" in contenido


@pytest.mark.django_db
def test_detalle_tenant_inexistente(cliente_autenticado):
    respuesta = cliente_autenticado.get(reverse("detalle_tenant", args=[9999]))

    assert respuesta.status_code == 404
