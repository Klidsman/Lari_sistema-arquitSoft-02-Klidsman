"""Aislamiento por tenant y región."""

import pytest
from django.test import Client
from django.urls import reverse

from acceso.models import Rol, Usuario
from acceso.services import PermisoDenegado, crear_cuenta_tenant
from auditoria.models import RegistroCambio
from tenants.models import Region, Tenant


@pytest.fixture
def otra_region(db, usuario_admin):
    return Region.objects.create(
        codigo="TRU",
        nombre="Trujillo",
        creado_por=usuario_admin,
    )


@pytest.fixture
def otro_tenant(db, otra_region, usuario_admin):
    return Tenant.objects.create(
        codigo="TEN-002",
        nombre="Otro tenant",
        region=otra_region,
        creado_por=usuario_admin,
    )


def _cliente_con(usuario):
    cliente = Client()
    cliente.force_login(usuario)
    sesion = cliente.session
    sesion["version_sesion"] = usuario.version_sesion
    sesion.save()
    return cliente


@pytest.mark.django_db
def test_tenant_ignora_tenant_id_y_region_id_del_cliente(
    usuario_tenant, otro_tenant
):
    cliente = _cliente_con(usuario_tenant)

    respuesta = cliente.get(
        reverse("inicio"),
        {
            "tenant_id": otro_tenant.pk,
            "region_id": otro_tenant.region_id,
        },
    )

    assert respuesta.status_code == 200
    request = respuesta.context["request"]
    assert request.tenant.pk == usuario_tenant.tenant_id
    assert request.region.pk == usuario_tenant.tenant.region_id


@pytest.mark.django_db
def test_tenant_no_ve_auditoria_de_otro_tenant(
    usuario_tenant, otro_tenant, usuario_admin
):
    ajena = RegistroCambio.objects.create(
        tenant=otro_tenant,
        entidad="Tenant",
        entidad_id=otro_tenant.pk,
        campo="estado",
        valor_anterior="ACTIVO",
        valor_nuevo="SUSPENDIDO",
        usuario=usuario_admin,
    )
    cliente = _cliente_con(usuario_tenant)

    respuesta = cliente.get(
        reverse("auditoria_acceso"),
        {"registro_id": ajena.pk},
    )

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_almacen_no_ve_auditoria_de_otra_region(
    usuario_almacen, otro_tenant, usuario_admin
):
    ajena = RegistroCambio.objects.create(
        tenant=otro_tenant,
        entidad="Tenant",
        entidad_id=otro_tenant.pk,
        campo="estado",
        valor_anterior="ACTIVO",
        valor_nuevo="SUSPENDIDO",
        usuario=usuario_admin,
    )
    cliente = _cliente_con(usuario_almacen)

    respuesta = cliente.get(
        reverse("auditoria_acceso"),
        {"registro_id": ajena.pk},
    )

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_cuenta_tenant_no_puede_crear_cuentas(usuario_tenant, tenant):
    cliente = _cliente_con(usuario_tenant)

    respuesta = cliente.post(
        reverse("crear_cuenta_tenant", args=[tenant.pk]),
        {"email": "nueva@lari.local"},
    )

    assert respuesta.status_code == 403

    with pytest.raises(PermisoDenegado):
        crear_cuenta_tenant(tenant, "otra@lari.local", usuario_tenant)


@pytest.mark.django_db
def test_tenant_solo_ve_su_propia_auditoria(usuario_tenant, tenant, usuario_admin):
    propia = RegistroCambio.objects.create(
        tenant=tenant,
        entidad="Tenant",
        entidad_id=tenant.pk,
        campo="nombre",
        valor_anterior="Antes",
        valor_nuevo="Después",
        usuario=usuario_admin,
    )
    cliente = _cliente_con(usuario_tenant)

    respuesta = cliente.get(
        reverse("auditoria_acceso"),
        {"registro_id": propia.pk},
    )

    assert respuesta.status_code == 200


@pytest.mark.django_db
def test_almacen_ve_auditoria_de_su_region(usuario_almacen, tenant, usuario_admin):
    propia = RegistroCambio.objects.create(
        tenant=tenant,
        entidad="Tenant",
        entidad_id=tenant.pk,
        campo="nombre",
        valor_anterior="Antes",
        valor_nuevo="Después",
        usuario=usuario_admin,
    )
    cliente = _cliente_con(usuario_almacen)

    respuesta = cliente.get(
        reverse("auditoria_acceso"),
        {"registro_id": propia.pk},
    )

    assert respuesta.status_code == 200


@pytest.mark.django_db
def test_rol_del_tenant_es_unico(usuario_tenant):
    assert usuario_tenant.rol == Rol.USUARIO_TENANT
    assert Usuario.objects.para_tenant(usuario_tenant.tenant).count() == 1
