"""Revocación de sesiones por desactivación, cambio de rol y suspensión."""

import pytest
from django.urls import reverse

from acceso.models import Rol, Usuario
from acceso.services import cambiar_rol, desactivar_cuenta
from tenants.models import Tenant
from tenants.services import activar_tenant, suspender_tenant


@pytest.mark.django_db
def test_desactivar_invalida_sesion_abierta(client, usuario_tenant, usuario_admin):
    client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )
    assert client.get(reverse("inicio")).status_code == 200

    desactivar_cuenta(usuario_tenant, usuario_admin)

    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login")


@pytest.mark.django_db
def test_cambio_rol_incrementa_version_y_cambia_rol(
    client, usuario_almacen, usuario_admin
):
    client.force_login(usuario_almacen)
    sesion = client.session
    sesion["version_sesion"] = usuario_almacen.version_sesion
    sesion.save()
    assert client.get(reverse("inicio")).status_code == 200

    cambiar_rol(usuario_almacen, Rol.ADMIN_PLATAFORMA, usuario_admin)

    usuario_almacen.refresh_from_db()
    assert usuario_almacen.version_sesion == 1
    assert usuario_almacen.rol == Rol.ADMIN_PLATAFORMA

    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("login")

    client.force_login(usuario_almacen)
    sesion = client.session
    sesion["version_sesion"] = usuario_almacen.version_sesion
    sesion.save()

    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 200
    assert respuesta.context["request"].rol == Rol.ADMIN_PLATAFORMA


@pytest.mark.django_db
def test_suspender_y_activar_no_modifican_datos(
    client, tenant, usuario_tenant, usuario_admin
):
    region_id = tenant.region_id

    suspender_tenant(tenant, usuario_admin)

    tenant.refresh_from_db()
    assert tenant.estado == Tenant.ESTADO_SUSPENDIDO
    assert tenant.region_id == region_id
    assert Tenant.objects.filter(pk=tenant.pk).exists()

    respuesta = client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )
    assert respuesta.status_code == 403
    assert "El tenant está suspendido" in respuesta.content.decode()

    activar_tenant(tenant, usuario_admin)

    tenant.refresh_from_db()
    assert tenant.estado == Tenant.ESTADO_ACTIVO
    assert tenant.region_id == region_id

    respuesta = client.post(
        reverse("login"),
        {"email": usuario_tenant.email, "password": "ClaveTenant12345"},
    )
    assert respuesta.status_code == 302
    assert respuesta.url == "/"
