"""Navegación del panel de administrador y confirmaciones de acciones."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_admin_ve_enlace_de_administracion_de_cuentas(cliente_autenticado):
    respuesta = cliente_autenticado.get(reverse("inicio"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "Administración de cuentas" in contenido
    assert reverse("listar_cuentas") in contenido


@pytest.mark.django_db
def test_admin_ve_enlaces_de_plataforma(cliente_autenticado):
    contenido = cliente_autenticado.get(reverse("inicio")).content.decode()

    for nombre in ("listar_regiones", "listar_tenants", "listar_cuentas", "auditoria_acceso"):
        assert reverse(nombre) in contenido


@pytest.mark.django_db
def test_tenant_no_ve_administracion_de_cuentas(cliente_tenant):
    contenido = cliente_tenant.get(reverse("inicio")).content.decode()

    assert "Administración de cuentas" not in contenido


@pytest.mark.django_db
def test_cuentas_pide_confirmacion(cliente_autenticado, usuario_tenant):
    contenido = cliente_autenticado.get(reverse("listar_cuentas")).content.decode()

    assert 'data-confirmar="¿Estás seguro de desactivar esta cuenta?' in contenido


@pytest.mark.django_db
def test_tenant_detalle_pide_confirmacion(cliente_autenticado, tenant):
    contenido = cliente_autenticado.get(
        reverse("detalle_tenant", args=[tenant.pk])
    ).content.decode()

    assert 'data-confirmar="¿Estás seguro de suspender este tenant?' in contenido


@pytest.mark.django_db
def test_tecnicos_piden_confirmacion(cliente_tenant, tecnico):
    contenido = cliente_tenant.get(reverse("listar_tecnicos")).content.decode()

    assert 'data-confirmar="¿Estás seguro de desactivar este técnico?' in contenido
