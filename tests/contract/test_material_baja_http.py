"""Contrato de baja lógica de materiales."""

import pytest
from django.test import Client
from django.urls import reverse

from acceso.models import Rol, Usuario
from auditoria.models import RegistroCambio
from materiales.models import Material


def _cliente_de(usuario):
    cliente = Client()
    cliente.force_login(usuario)
    sesion = cliente.session
    sesion["version_sesion"] = usuario.version_sesion
    sesion.save()
    return cliente


@pytest.mark.django_db
def test_almacen_da_de_baja(cliente_almacen, material):
    respuesta = cliente_almacen.post(
        reverse("dar_de_baja_material", args=[material.pk])
    )

    assert respuesta.status_code == 302
    material.refresh_from_db()
    assert material.activo is False
    assert RegistroCambio.objects.filter(
        entidad="Material", entidad_id=material.pk, campo="activo"
    ).exists()


@pytest.mark.django_db
def test_material_de_baja_no_aparece(cliente_almacen, material):
    cliente_almacen.post(reverse("dar_de_baja_material", args=[material.pk]))

    listado = cliente_almacen.get(reverse("listar_materiales")).content.decode()
    fragmento = cliente_almacen.get(
        reverse("buscar_materiales_htmx"),
        {"q": material.codigo},
    ).content.decode()

    assert material.codigo not in listado
    assert material.codigo not in fragmento


@pytest.mark.django_db
def test_tenant_no_puede_dar_de_baja(cliente_tenant, material):
    respuesta = cliente_tenant.post(
        reverse("dar_de_baja_material", args=[material.pk])
    )

    assert respuesta.status_code == 403
    material.refresh_from_db()
    assert material.activo is True


@pytest.mark.django_db
def test_cualquier_almacen_puede_dar_de_baja(material, region):
    otro_almacen = Usuario.objects.create_user(
        email="almacen2@lari.local",
        password="ClaveAlmacen12345",
        rol=Rol.RESPONSABLE_ALMACEN,
        region=region,
        is_active=True,
    )
    cliente = _cliente_de(otro_almacen)

    respuesta = cliente.post(
        reverse("dar_de_baja_material", args=[material.pk])
    )

    assert respuesta.status_code == 302
    material.refresh_from_db()
    assert material.activo is False


@pytest.mark.django_db
def test_baja_ya_inactiva_es_idempotente(cliente_almacen, material):
    Material.objects.filter(pk=material.pk).update(activo=False)
    antes = RegistroCambio.objects.filter(
        entidad="Material", entidad_id=material.pk, campo="activo"
    ).count()

    respuesta = cliente_almacen.post(
        reverse("dar_de_baja_material", args=[material.pk])
    )

    assert respuesta.status_code == 200
    assert (
        RegistroCambio.objects.filter(
            entidad="Material", entidad_id=material.pk, campo="activo"
        ).count()
        == antes
    )


@pytest.mark.django_db
def test_baja_material_inexistente(cliente_almacen):
    respuesta = cliente_almacen.post(
        reverse("dar_de_baja_material", args=[9999])
    )

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_delete_en_baja_no_permitido(cliente_almacen, material):
    respuesta = cliente_almacen.delete(
        reverse("dar_de_baja_material", args=[material.pk])
    )

    assert respuesta.status_code == 405
