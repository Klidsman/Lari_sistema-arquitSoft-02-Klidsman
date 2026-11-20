"""Operación condicionada a la cuenta activa del tenant."""

import pytest
from django.urls import reverse

from acceso.models import Rol, Usuario


@pytest.mark.django_db
def test_tenant_sin_cuenta_activa_no_esta_operativo(tenant):
    assert tenant.tiene_cuenta_activa() is False


@pytest.mark.django_db
def test_tenant_con_cuenta_activa_esta_operativo(tenant):
    Usuario.objects.create_user(
        email="operativo@lari.local",
        password="ClaveTenant12345",
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=True,
    )

    assert tenant.tiene_cuenta_activa() is True


@pytest.mark.django_db
def test_peticion_con_cuenta_inactiva_es_rechazada(client, tenant):
    usuario = Usuario.objects.create_user(
        email="inactivo@lari.local",
        password="ClaveTenant12345",
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=False,
    )
    client.force_login(usuario)

    respuesta = client.get(reverse("inicio"))

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login")
