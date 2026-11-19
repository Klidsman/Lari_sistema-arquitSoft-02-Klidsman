"""Contrato de inicio de sesión."""

import pytest
from django.urls import reverse

from acceso.models import Rol, Usuario
from acceso.services import CLAVE_PENDIENTE_2FA
from acceso.totp import cifrar_secreto
from tenants.models import Region, Tenant


@pytest.fixture
def admin_con_2fa(db, usuario_admin):
    usuario_admin.secreto_totp = cifrar_secreto("JBSWY3DPEHPK3PXP")
    usuario_admin.segundo_factor_habilitado = True
    usuario_admin.save(update_fields=["secreto_totp", "segundo_factor_habilitado"])
    return usuario_admin


@pytest.mark.django_db
def test_login_sin_2fa_redirige_a_pendiente(client, admin_con_2fa):
    respuesta = client.post(
        reverse("login"),
        {"email": admin_con_2fa.email, "password": "ClaveAdmin12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login_2fa")
    assert client.session[CLAVE_PENDIENTE_2FA] == admin_con_2fa.pk


@pytest.mark.django_db
def test_login_credenciales_invalidas(client, admin_con_2fa):
    respuesta = client.post(
        reverse("login"),
        {"email": admin_con_2fa.email, "password": "incorrecta"},
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
def test_login_tenant_sin_2fa_abre_sesion(client, usuario_tenant):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == "/"
    assert client.session["_auth_user_id"] == str(usuario_tenant.pk)
