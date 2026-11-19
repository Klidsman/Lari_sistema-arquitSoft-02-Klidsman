"""Restricciones de alcance e identidad en la base de datos."""

import pytest
from django.db import IntegrityError, transaction

from acceso.models import Rol, Usuario
from tenants.models import Region


@pytest.mark.django_db
def test_usuario_con_tenant_y_region_falla(tenant, region):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.create(
                email="ambos@lari.local",
                rol=Rol.USUARIO_TENANT,
                tenant=tenant,
                region=region,
            )


@pytest.mark.django_db
def test_dos_cuentas_tenant_para_el_mismo_tenant_falla(
    tenant, usuario_tenant
):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.create_user(
                email="segunda@lari.local",
                password="ClaveTenant12345",
                rol=Rol.USUARIO_TENANT,
                tenant=tenant,
                is_active=False,
            )


@pytest.mark.django_db
def test_correo_duplicado_falla(usuario_admin):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.create(
                email=usuario_admin.email,
                rol=Rol.ADMIN_PLATAFORMA,
            )


@pytest.mark.django_db
def test_cuenta_almacen_sin_region_falla(region):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.create(
                email="sin-region@lari.local",
                rol=Rol.RESPONSABLE_ALMACEN,
            )


@pytest.mark.django_db
def test_region_sin_codigo_falla(usuario_admin):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Region.objects.create(
                codigo="",
                nombre="Sin código",
                creado_por=usuario_admin,
            )
