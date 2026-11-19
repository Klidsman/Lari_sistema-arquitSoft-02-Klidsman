"""Contrato de suspensión y activación de tenants."""

import pytest
from django.urls import reverse

from acceso.models import Usuario
from auditoria.models import RegistroCambio
from tenants.models import Tenant


@pytest.mark.django_db
def test_suspender_tenant(cliente_autenticado, tenant, usuario_tenant):
    respuesta = cliente_autenticado.post(
        reverse("suspender_tenant", args=[tenant.pk])
    )

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("detalle_tenant", args=[tenant.pk])

    tenant.refresh_from_db()
    assert tenant.estado == Tenant.ESTADO_SUSPENDIDO

    usuario_tenant.refresh_from_db()
    assert usuario_tenant.version_sesion == 1

    assert RegistroCambio.objects.filter(
        entidad="Tenant", entidad_id=tenant.pk, campo="estado"
    ).exists()


@pytest.mark.django_db
def test_suspender_tenant_ya_suspendido(cliente_autenticado, tenant):
    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)
    auditorias_antes = RegistroCambio.objects.filter(
        entidad="Tenant", entidad_id=tenant.pk
    ).count()

    respuesta = cliente_autenticado.post(
        reverse("suspender_tenant", args=[tenant.pk])
    )

    assert respuesta.status_code == 200
    assert (
        RegistroCambio.objects.filter(
            entidad="Tenant", entidad_id=tenant.pk
        ).count()
        == auditorias_antes
    )


@pytest.mark.django_db
def test_activar_tenant(cliente_autenticado, tenant, usuario_tenant):
    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)

    respuesta = cliente_autenticado.post(
        reverse("activar_tenant", args=[tenant.pk])
    )

    assert respuesta.status_code == 302
    tenant.refresh_from_db()
    assert tenant.estado == Tenant.ESTADO_ACTIVO
    usuario_tenant.refresh_from_db()
    assert usuario_tenant.version_sesion == 1


@pytest.mark.django_db
def test_suspender_tenant_inexistente(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        reverse("suspender_tenant", args=[9999])
    )

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_delete_no_permitido(cliente_autenticado, tenant):
    respuesta = cliente_autenticado.delete(
        reverse("suspender_tenant", args=[tenant.pk])
    )

    assert respuesta.status_code == 405
