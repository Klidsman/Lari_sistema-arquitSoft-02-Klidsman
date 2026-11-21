"""Contrato de segundo factor y logout."""

import pyotp
import pytest
from django.test import Client
from django.urls import reverse

from acceso.services import CLAVE_PENDIENTE_2FA
from acceso.totp import cifrar_secreto

SECRETO = "JBSWY3DPEHPK3PXPJBSWY3DPJBSWY3DP"
SECRETO_AGRUPADO = "JBSW Y3DP EHPK 3PXP JBSW Y3DP JBSW Y3DP"


@pytest.fixture
def admin_2fa(db, usuario_admin):
    usuario_admin.secreto_totp = cifrar_secreto(SECRETO)
    usuario_admin.segundo_factor_habilitado = True
    usuario_admin.save(update_fields=["secreto_totp", "segundo_factor_habilitado"])
    return usuario_admin, SECRETO


def _dejar_pendiente(client, usuario):
    client.post(
        reverse("login"),
        {"email": usuario.email, "password": "ClaveAdmin12345"},
    )


@pytest.mark.django_db
def test_2fa_codigo_valido_abre_sesion(client, admin_2fa):
    usuario, secreto = admin_2fa
    _dejar_pendiente(client, usuario)

    respuesta = client.post(
        reverse("login_2fa"),
        {"codigo": pyotp.TOTP(secreto).now()},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == "/plataforma/regiones/"
    assert client.session["_auth_user_id"] == str(usuario.pk)
    assert CLAVE_PENDIENTE_2FA not in client.session


@pytest.mark.django_db
def test_2fa_codigo_invalido(client, admin_2fa):
    usuario, _ = admin_2fa
    _dejar_pendiente(client, usuario)

    respuesta = client.post(reverse("login_2fa"), {"codigo": "000000"})

    assert respuesta.status_code == 400
    assert "Debes completar el segundo factor" in respuesta.content.decode()


@pytest.mark.django_db
def test_2fa_sin_sesion_pendiente(client):
    respuesta = client.get(reverse("login_2fa"))

    assert respuesta.status_code == 403
    assert "Debes iniciar sesión" in respuesta.content.decode()


@pytest.mark.django_db
def test_logout_exige_post_y_csrf(usuario_tenant):
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(usuario_tenant)

    respuesta = cliente.get(reverse("logout"))
    assert respuesta.status_code == 405

    respuesta = cliente.post(reverse("logout"))
    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_alta_2fa_muestra_pasos_y_clave_agrupada(client, usuario_admin):
    usuario_admin.secreto_totp = cifrar_secreto(SECRETO)
    usuario_admin.save(update_fields=["secreto_totp"])
    _dejar_pendiente(client, usuario_admin)

    respuesta = client.get(reverse("login_2fa"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "Paso 1" in contenido
    assert "Paso 2" in contenido
    assert SECRETO_AGRUPADO in contenido
    assert "No hay recuperación de códigos" in contenido
    assert "no-store" in respuesta["Cache-Control"]


@pytest.mark.django_db
def test_alta_2fa_conserva_clave_tras_codigo_invalido(client, usuario_admin):
    usuario_admin.secreto_totp = cifrar_secreto(SECRETO)
    usuario_admin.save(update_fields=["secreto_totp"])
    _dejar_pendiente(client, usuario_admin)

    respuesta = client.post(reverse("login_2fa"), {"codigo": "000000"})
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 400
    assert "Debes completar el segundo factor" in contenido
    assert SECRETO_AGRUPADO in contenido


@pytest.mark.django_db
def test_perfil_muestra_la_clave_del_segundo_factor(client, usuario_admin):
    usuario_admin.secreto_totp = cifrar_secreto(SECRETO)
    usuario_admin.save(update_fields=["secreto_totp"])
    client.force_login(usuario_admin)

    respuesta = client.get(reverse("configurar_2fa"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert SECRETO_AGRUPADO in contenido
    assert "Paso 3" in contenido
    assert "no-store" in respuesta["Cache-Control"]
