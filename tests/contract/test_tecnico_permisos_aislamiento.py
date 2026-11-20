"""Matriz de permisos y aislamiento de técnicos."""

import pytest
from django.test import Client
from django.urls import reverse

from acceso.models import Usuario
from tenants.models import Tenant
from tecnicos.models import Tecnico


def _cliente(usuario):
    cliente = Client()
    cliente.force_login(usuario)
    sesion = cliente.session
    sesion["version_sesion"] = usuario.version_sesion
    sesion.save()
    return cliente


@pytest.mark.django_db
def test_admin_y_almacen_rechazados_en_todas_las_rutas(
    cliente_autenticado, cliente_almacen, tecnico, tecnico_desactivado
):
    rutas_get = [
        reverse("listar_tecnicos"),
        reverse("buscar_tecnicos_htmx"),
        reverse("crear_tecnico"),
        reverse("detalle_tecnico", args=[tecnico.pk]),
        reverse("editar_tecnico", args=[tecnico.pk]),
    ]
    rutas_post = [
        reverse("desactivar_tecnico", args=[tecnico.pk]),
        reverse("reactivar_tecnico", args=[tecnico_desactivado.pk]),
    ]

    for cliente in (cliente_autenticado, cliente_almacen):
        for ruta in rutas_get:
            respuesta = cliente.get(ruta)
            assert respuesta.status_code == 403
            assert "No tienes permiso para gestionar técnicos" in respuesta.content.decode()
        for ruta in rutas_post:
            assert cliente.post(ruta).status_code == 403


@pytest.mark.django_db
def test_tecnicos_de_otro_tenant_404(cliente_tenant, tecnico_otro_tenant):
    assert (
        cliente_tenant.get(
            reverse("detalle_tecnico", args=[tecnico_otro_tenant.pk])
        ).status_code
        == 404
    )
    assert (
        cliente_tenant.get(
            reverse("editar_tecnico", args=[tecnico_otro_tenant.pk])
        ).status_code
        == 404
    )
    assert (
        cliente_tenant.post(
            reverse("desactivar_tecnico", args=[tecnico_otro_tenant.pk])
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_tenant_id_forzado_se_ignora(cliente_tenant, tenant, usuario_otro_tenant):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        {
            "nif": "LA1234",
            "nombre": "Juan Pérez",
            "tenant_id": usuario_otro_tenant.tenant_id,
        },
    )

    assert respuesta.status_code == 302
    assert Tecnico.objects.get(nif="LA1234").tenant_id == tenant.pk


@pytest.mark.django_db
def test_tenant_suspendido_no_opera(cliente_tenant, tenant):
    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)

    respuesta = cliente_tenant.get(reverse("listar_tecnicos"))

    assert respuesta.status_code == 302
    assert "/login/" in respuesta.url


@pytest.mark.django_db
def test_cuenta_inactiva_no_opera(client, usuario_tenant):
    Usuario.objects.filter(pk=usuario_tenant.pk).update(is_active=False)
    cliente = _cliente(Usuario.objects.get(pk=usuario_tenant.pk))

    respuesta = cliente.get(reverse("listar_tecnicos"))

    assert respuesta.status_code == 302
    assert "/login/" in respuesta.url
