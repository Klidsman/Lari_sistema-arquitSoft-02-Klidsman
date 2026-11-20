"""Integración de cuentas de Responsable de almacén."""

import pytest

from acceso.models import Invitacion, Rol, Usuario
from acceso.services import CorreoDuplicado, crear_cuenta_almacen
from auditoria.models import RegistroCambio


@pytest.mark.django_db
def test_crear_cuenta_almacen(
    usuario_admin, region, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        usuario = crear_cuenta_almacen(
            region,
            "responsable@lari.local",
            usuario_admin,
        )

    assert usuario.rol == Rol.RESPONSABLE_ALMACEN
    assert usuario.region_id == region.pk
    assert usuario.tenant_id is None
    assert usuario.is_active is False
    assert usuario.has_usable_password() is False
    assert Invitacion.objects.filter(usuario=usuario).count() == 1
    assert RegistroCambio.objects.filter(
        entidad="Usuario", entidad_id=usuario.pk, campo="alta"
    ).exists()


@pytest.mark.django_db
def test_crear_cuenta_almacen_correo_duplicado(usuario_admin, region, usuario_tenant):
    with pytest.raises(CorreoDuplicado):
        crear_cuenta_almacen(
            region,
            usuario_tenant.email,
            usuario_admin,
        )

    assert not Usuario.objects.filter(email=usuario_tenant.email).count() > 1
