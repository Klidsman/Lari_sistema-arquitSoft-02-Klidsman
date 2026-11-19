"""Contrato de acciones sobre cuentas."""

import pytest
from django.urls import reverse

from acceso.models import Rol, Usuario
from auditoria.models import RegistroCambio


@pytest.mark.django_db
def test_desactivar_cuenta(cliente_autenticado, usuario_tenant):
    version_anterior = usuario_tenant.version_sesion

    respuesta = cliente_autenticado.post(
        reverse("desactivar_cuenta", args=[usuario_tenant.pk])
    )

    assert respuesta.status_code == 302
    usuario_tenant.refresh_from_db()
    assert usuario_tenant.is_active is False
    assert usuario_tenant.version_sesion == version_anterior + 1
    assert RegistroCambio.objects.filter(
        entidad="Usuario", entidad_id=usuario_tenant.pk, campo="is_active"
    ).exists()


@pytest.mark.django_db
def test_desactivar_cuenta_ya_inactiva(cliente_autenticado, usuario_almacen):
    Usuario.objects.filter(pk=usuario_almacen.pk).update(is_active=False)
    version_anterior = usuario_almacen.version_sesion

    respuesta = cliente_autenticado.post(
        reverse("desactivar_cuenta", args=[usuario_almacen.pk])
    )

    assert respuesta.status_code == 200
    usuario_almacen.refresh_from_db()
    assert usuario_almacen.is_active is False
    assert usuario_almacen.version_sesion == version_anterior


@pytest.mark.django_db
def test_reactivar_cuenta(cliente_autenticado, usuario_almacen):
    Usuario.objects.filter(pk=usuario_almacen.pk).update(is_active=False)
    version_anterior = usuario_almacen.version_sesion

    respuesta = cliente_autenticado.post(
        reverse("reactivar_cuenta", args=[usuario_almacen.pk])
    )

    assert respuesta.status_code == 302
    usuario_almacen.refresh_from_db()
    assert usuario_almacen.is_active is True
    assert usuario_almacen.version_sesion == version_anterior + 1


@pytest.mark.django_db
def test_cuenta_inexistente(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        reverse("desactivar_cuenta", args=[9999])
    )

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_delete_no_permitido(cliente_autenticado, usuario_tenant):
    respuesta = cliente_autenticado.delete(
        reverse("desactivar_cuenta", args=[usuario_tenant.pk])
    )

    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_cambiar_rol(cliente_autenticado, usuario_almacen, region):
    version_anterior = usuario_almacen.version_sesion

    respuesta = cliente_autenticado.post(
        reverse("cambiar_rol", args=[usuario_almacen.pk]),
        {"rol": Rol.ADMIN_PLATAFORMA},
    )

    assert respuesta.status_code == 302
    usuario_almacen.refresh_from_db()
    assert usuario_almacen.rol == Rol.ADMIN_PLATAFORMA
    assert usuario_almacen.region_id is None
    assert usuario_almacen.version_sesion == version_anterior + 1


@pytest.mark.django_db
def test_cuenta_tenant_no_cambia_de_rol(cliente_autenticado, usuario_tenant):
    respuesta = cliente_autenticado.post(
        reverse("cambiar_rol", args=[usuario_tenant.pk]),
        {"rol": Rol.ADMIN_PLATAFORMA},
    )

    assert respuesta.status_code == 409
    assert "La cuenta del tenant no cambia de rol" in respuesta.content.decode()


@pytest.mark.django_db
def test_rol_no_permitido(cliente_autenticado, usuario_almacen):
    respuesta = cliente_autenticado.post(
        reverse("cambiar_rol", args=[usuario_almacen.pk]),
        {"rol": "SUPERADMIN"},
    )

    assert respuesta.status_code == 400
    assert "No puedes asignar ese rol" in respuesta.content.decode()


@pytest.mark.django_db
def test_alcance_incompatible(cliente_autenticado, usuario_admin):
    respuesta = cliente_autenticado.post(
        reverse("cambiar_rol", args=[usuario_admin.pk]),
        {"rol": Rol.RESPONSABLE_ALMACEN},
    )

    assert respuesta.status_code == 400
    assert "El alcance de la cuenta no es válido" in respuesta.content.decode()
