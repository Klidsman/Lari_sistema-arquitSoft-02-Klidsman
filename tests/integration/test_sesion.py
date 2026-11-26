"""Sesión, revocación y alcance."""

import pytest
from django.urls import reverse

from acceso.models import Usuario


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
def test_admin_entra_sin_segundo_factor(client, usuario_admin):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_admin.email, "password": "ClaveAdmin12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == "/plataforma/regiones/"
    assert client.session["_auth_user_id"] == str(usuario_admin.pk)


@pytest.mark.django_db
def test_almacen_entra_sin_segundo_factor(client, usuario_almacen):
    respuesta = client.post(
        reverse("login"),
        {"email": usuario_almacen.email, "password": "ClaveAlmacen12345"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == "/"
    assert client.session["_auth_user_id"] == str(usuario_almacen.pk)
