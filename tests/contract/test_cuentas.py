"""Contrato de cuentas administrativas y del tenant."""

import pytest
from django.urls import reverse

from acceso.models import Invitacion, Rol, Usuario


@pytest.mark.django_db
def test_alta_cuenta_tenant(cliente_autenticado, tenant, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        respuesta = cliente_autenticado.post(
            reverse("crear_cuenta_tenant", args=[tenant.pk]),
            {"email": "cuenta@lari.local"},
        )

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "/invitacion/" in contenido
    assert "Cuenta del tenant creada" in contenido

    usuario = Usuario.objects.get(email="cuenta@lari.local")
    assert usuario.rol == Rol.USUARIO_TENANT
    assert usuario.tenant_id == tenant.pk
    assert usuario.is_active is False
    assert usuario.has_usable_password() is False
    assert Invitacion.objects.filter(usuario=usuario).count() == 1
    assert Invitacion.objects.get(usuario=usuario).tipo == "ALTA"


@pytest.mark.django_db
def test_alta_cuenta_tenant_ya_existe(cliente_autenticado, usuario_tenant):
    respuesta = cliente_autenticado.post(
        reverse("crear_cuenta_tenant", args=[usuario_tenant.tenant_id]),
        {"email": "otra@lari.local"},
    )

    assert respuesta.status_code == 409
    assert "El tenant ya tiene una cuenta" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_cuenta_correo_duplicado(cliente_autenticado, tenant, usuario_admin):
    respuesta = cliente_autenticado.post(
        reverse("crear_cuenta_tenant", args=[tenant.pk]),
        {"email": usuario_admin.email},
    )

    assert respuesta.status_code == 409
    assert "El correo ya está registrado" in respuesta.content.decode()


@pytest.mark.django_db
def test_alta_cuenta_correo_invalido(cliente_autenticado, tenant):
    respuesta = cliente_autenticado.post(
        reverse("crear_cuenta_tenant", args=[tenant.pk]),
        {"email": "no-es-correo"},
    )

    assert respuesta.status_code == 400
    assert "El correo no es válido" in respuesta.content.decode()


@pytest.mark.django_db
def test_listado_cuentas(cliente_autenticado, usuario_admin, usuario_tenant):
    respuesta = cliente_autenticado.get(reverse("listar_cuentas"))

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert usuario_admin.email in contenido
    assert usuario_tenant.email in contenido
    assert "USUARIO_TENANT" in contenido


@pytest.mark.django_db
def test_listado_cuentas_paginado(cliente_autenticado, usuario_admin):
    for indice in range(55):
        Usuario.objects.create_user(
            email=f"cuenta{indice:03d}@lari.local",
            password="ClaveAdmin12345",
            rol=Rol.ADMIN_PLATAFORMA,
            is_active=False,
        )

    respuesta = cliente_autenticado.get(reverse("listar_cuentas"))

    assert respuesta.status_code == 200
    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2
