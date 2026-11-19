"""Traducción de conflictos de unicidad y equivalencia secuencial."""

import pytest
from django.db import IntegrityError, transaction
from django.test.utils import override_settings

from acceso.models import Rol, Usuario
from acceso.services import CuentaDuplicada, crear_cuenta_tenant
from tenants.models import Region
from tenants.services import RegionDuplicada, crear_region


@pytest.mark.django_db
def test_dos_altas_de_region_con_el_mismo_codigo(usuario_admin):
    datos = {
        "codigo": "CON",
        "nombre": "Concurrente",
        "centro": "PR05",
        "almacen": "BE03",
        "buzon": "con@lari.local",
    }

    crear_region(datos, usuario_admin)

    with pytest.raises(RegionDuplicada):
        crear_region(datos, usuario_admin)

    assert Region.objects.filter(codigo="CON").count() == 1


@pytest.mark.django_db
def test_dos_cuentas_de_tenant_dejan_solo_una(
    tenant, usuario_admin, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        crear_cuenta_tenant(tenant, "primera@lari.local", usuario_admin)

    with pytest.raises(CuentaDuplicada):
        crear_cuenta_tenant(tenant, "segunda@lari.local", usuario_admin)

    assert Usuario.objects.para_tenant(tenant).count() == 1


@pytest.mark.django_db
def test_dos_altas_con_el_mismo_correo_falla(usuario_admin):
    Usuario.objects.create_user(
        email="repetido@lari.local",
        password="ClaveAdmin12345",
        rol=Rol.ADMIN_PLATAFORMA,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.create_user(
                email="repetido@lari.local",
                password="ClaveAdmin12345",
                rol=Rol.ADMIN_PLATAFORMA,
            )


@pytest.mark.django_db
def test_correo_unico_normalizado(usuario_admin):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Usuario.objects.create(
                email=usuario_admin.email,
                rol=Rol.ADMIN_PLATAFORMA,
            )
