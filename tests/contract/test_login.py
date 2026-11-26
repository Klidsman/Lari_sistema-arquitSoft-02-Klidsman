"""Contrato de inicio de sesión."""

import pytest
from django.urls import reverse

from tenants.models import Tenant


@pytest.mark.django_db
def test_login_admin_abre_sesion_directamente(client, usuario_admin):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_admin.email, "password": "ClaveAdmin12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == "/plataforma/regiones/"
    assert client.session["_auth_user_id"] == str(usuario_admin.pk)


@pytest.mark.django_db
def test_login_credenciales_invalidas(client, usuario_admin):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_admin.email, "password": "incorrecta"},
    )

    assert respuesta.status_code == 400
    assert "Correo o contraseña incorrectos" in respuesta.content.decode()


@pytest.mark.django_db
def test_login_cuenta_desactivada(client, usuario_admin):
    usuario_admin.is_active = False
    usuario_admin.save(update_fields=["is_active"])

    respuesta = client.post(
        reverse("login"),
        {"email": usuario_admin.email, "password": "ClaveAdmin12345"},
    )

    assert respuesta.status_code == 403
    assert "La cuenta está desactivada" in respuesta.content.decode()


@pytest.mark.django_db
def test_login_tenant_suspendido(client, usuario_tenant):
    tenant = usuario_tenant.tenant
    tenant.estado = Tenant.ESTADO_SUSPENDIDO
    tenant.save(update_fields=["estado"])

    respuesta = client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )

    assert respuesta.status_code == 403
    assert "El tenant está suspendido" in respuesta.content.decode()


@pytest.mark.django_db
def test_login_tenant_abre_sesion(client, usuario_tenant):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == "/"
    assert client.session["_auth_user_id"] == str(usuario_tenant.pk)
