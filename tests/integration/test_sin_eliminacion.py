"""No existe eliminación de regiones, tenants ni cuentas."""

import pytest
from django.urls import reverse

from acceso.services import desactivar_cuenta
from tenants.models import Region, Tenant
from tenants.services import suspender_tenant


@pytest.mark.django_db
def test_delete_no_permitido_en_rutas_de_region(cliente_autenticado, region):
    respuesta = cliente_autenticado.delete(
        reverse("editar_region", args=[region.pk])
    )
    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_delete_no_permitido_en_rutas_de_tenant(cliente_autenticado, tenant):
    respuesta = cliente_autenticado.delete(
        reverse("detalle_tenant", args=[tenant.pk])
    )
    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_delete_no_permitido_en_rutas_de_cuenta(cliente_autenticado, usuario_tenant):
    respuesta = cliente_autenticado.delete(
        reverse("desactivar_cuenta", args=[usuario_tenant.pk])
    )
    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_desactivar_conserva_cuenta_y_auditoria(usuario_tenant, usuario_admin):
    desactivar_cuenta(usuario_tenant, usuario_admin)

    usuario_tenant.refresh_from_db()
    assert usuario_tenant.pk is not None
    assert usuario_tenant.is_active is False


@pytest.mark.django_db
def test_suspender_conserva_tenant_region_y_auditoria(
    tenant, region, usuario_admin
):
    suspender_tenant(tenant, usuario_admin)

    assert Tenant.objects.filter(pk=tenant.pk).exists()
    assert Region.objects.filter(pk=region.pk).exists()
