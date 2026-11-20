"""Contrato de desactivación y reactivación."""

import pytest
from django.urls import reverse

from auditoria.models import RegistroCambio


@pytest.mark.django_db
def test_desactivar(cliente_tenant, tecnico):
    respuesta = cliente_tenant.post(
        reverse("desactivar_tecnico", args=[tecnico.pk])
    )

    assert respuesta.status_code == 302
    tecnico.refresh_from_db()
    assert tecnico.activo is False


@pytest.mark.django_db
def test_desactivar_dos_veces_no_duplica_auditoria(cliente_tenant, tecnico):
    cliente_tenant.post(reverse("desactivar_tecnico", args=[tecnico.pk]))
    antes = RegistroCambio.objects.filter(
        entidad="Tecnico", entidad_id=tecnico.pk, campo="activo"
    ).count()

    respuesta = cliente_tenant.post(
        reverse("desactivar_tecnico", args=[tecnico.pk])
    )

    assert respuesta.status_code == 302
    assert (
        RegistroCambio.objects.filter(
            entidad="Tecnico", entidad_id=tecnico.pk, campo="activo"
        ).count()
        == antes
    )


@pytest.mark.django_db
def test_reactivar(cliente_tenant, tecnico_desactivado):
    respuesta = cliente_tenant.post(
        reverse("reactivar_tecnico", args=[tecnico_desactivado.pk])
    )

    assert respuesta.status_code == 302
    tecnico_desactivado.refresh_from_db()
    assert tecnico_desactivado.activo is True


@pytest.mark.django_db
def test_tecnico_de_otro_tenant_404(cliente_tenant, tecnico_otro_tenant):
    for accion in ("desactivar_tecnico", "reactivar_tecnico"):
        respuesta = cliente_tenant.post(
            reverse(accion, args=[tecnico_otro_tenant.pk])
        )
        assert respuesta.status_code == 404


@pytest.mark.django_db
def test_admin_y_almacen_no_cambian_estado(
    cliente_autenticado, cliente_almacen, tecnico
):
    for cliente in (cliente_autenticado, cliente_almacen):
        respuesta = cliente.post(
            reverse("desactivar_tecnico", args=[tecnico.pk])
        )
        assert respuesta.status_code == 403


@pytest.mark.django_db
def test_get_y_delete_no_permitidos(cliente_tenant, tecnico):
    assert (
        cliente_tenant.get(reverse("desactivar_tecnico", args=[tecnico.pk])).status_code
        == 405
    )
    assert (
        cliente_tenant.delete(reverse("desactivar_tecnico", args=[tecnico.pk])).status_code
        == 405
    )
