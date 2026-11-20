"""Sesión, revocación y alcance."""

import pyotp
import pytest
from django.urls import reverse

from acceso.models import Usuario
from acceso.totp import cifrar_secreto


@pytest.mark.django_db
def test_sesion_pendiente_solo_accede_a_2fa(client, usuario_admin):
    usuario_admin.secreto_totp = cifrar_secreto("JBSWY3DPEHPK3PXPJBSWY3DPJBSWY3DP")
    usuario_admin.segundo_factor_habilitado = True
    usuario_admin.save(update_fields=["secreto_totp", "segundo_factor_habilitado"])

    client.post(
        reverse("login"),
        {"email": usuario_admin.email, "password": "ClaveAdmin12345"},
    )

    respuesta = client.get("/")
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login_2fa")

    respuesta = client.get(reverse("login_2fa"))
    assert respuesta.status_code == 200


@pytest.mark.django_db
def test_version_sesion_desactualizada_cierra_sesion(client, usuario_tenant):
    client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )
    assert client.session["_auth_user_id"] == str(usuario_tenant.pk)

    Usuario.objects.filter(pk=usuario_tenant.pk).update(
        version_sesion=usuario_tenant.version_sesion + 1
    )

    respuesta = client.get("/")
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login")


@pytest.mark.django_db
def test_almacen_exige_segundo_factor(client, usuario_almacen):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_almacen.email, "password": "ClaveAlmacen12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login_2fa")


@pytest.mark.django_db
def test_tenant_no_exige_segundo_factor(client, usuario_tenant):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == "/"
