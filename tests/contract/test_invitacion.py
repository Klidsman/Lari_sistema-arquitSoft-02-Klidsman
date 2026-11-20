"""Contrato de aceptación de invitaciones."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from acceso.models import Invitacion, Rol, Usuario
from acceso.tokens import hash_token


def _usuario_inactivo(tenant):
    return Usuario.objects.create_user(
        email="invitado@lari.local",
        password=None,
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=False,
    )


def _invitacion(usuario, token="token-valido", **cambios):
    datos = {
        "usuario": usuario,
        "token_hash": hash_token(token),
        "correo": usuario.email,
        "expira_en": timezone.now() + timedelta(hours=2),
        "creada_por": usuario,
    }
    datos.update(cambios)
    return Invitacion.objects.create(**datos)


@pytest.mark.django_db
def test_get_invitacion_valida(client, tenant):
    usuario = _usuario_inactivo(tenant)
    _invitacion(usuario)

    respuesta = client.get(reverse("aceptar_invitacion", args=["token-valido"]))

    assert respuesta.status_code == 200


@pytest.mark.django_db
def test_post_invitacion_valida(client, tenant):
    usuario = _usuario_inactivo(tenant)
    _invitacion(usuario)

    respuesta = client.post(
        reverse("aceptar_invitacion", args=["token-valido"]),
        {
            "password": "ClaveSegura12345",
            "password_confirmacion": "ClaveSegura12345",
        },
    )

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login")

    usuario.refresh_from_db()
    assert usuario.is_active is True
    assert usuario.check_password("ClaveSegura12345")

    invitacion = Invitacion.objects.get(token_hash=hash_token("token-valido"))
    assert invitacion.usada_en is not None


@pytest.mark.django_db
def test_invitacion_vencida(client, tenant):
    usuario = _usuario_inactivo(tenant)
    _invitacion(
        usuario,
        expira_en=timezone.now() - timedelta(hours=1),
    )

    respuesta = client.get(reverse("aceptar_invitacion", args=["token-valido"]))

    assert respuesta.status_code == 410
    assert "La invitación venció o ya fue usada" in respuesta.content.decode()


@pytest.mark.django_db
def test_invitacion_usada(client, tenant):
    usuario = _usuario_inactivo(tenant)
    _invitacion(usuario, usada_en=timezone.now())

    respuesta = client.get(reverse("aceptar_invitacion", args=["token-valido"]))

    assert respuesta.status_code == 410
    assert "La invitación venció o ya fue usada" in respuesta.content.decode()


@pytest.mark.django_db
def test_invitacion_revocada(client, tenant):
    usuario = _usuario_inactivo(tenant)
    _invitacion(usuario, revocada_en=timezone.now())

    respuesta = client.get(reverse("aceptar_invitacion", args=["token-valido"]))

    assert respuesta.status_code == 410
    assert "La invitación venció o ya fue usada" in respuesta.content.decode()


@pytest.mark.django_db
def test_invitacion_token_inexistente(client):
    respuesta = client.get(reverse("aceptar_invitacion", args=["no-existe"]))

    assert respuesta.status_code == 410
    assert "La invitación venció o ya fue usada" in respuesta.content.decode()


@pytest.mark.django_db
def test_password_debil(client, tenant):
    usuario = _usuario_inactivo(tenant)
    _invitacion(usuario)

    respuesta = client.post(
        reverse("aceptar_invitacion", args=["token-valido"]),
        {"password": "corta", "password_confirmacion": "corta"},
    )

    assert respuesta.status_code == 400
    assert "contraseña" in respuesta.content.decode().lower()
