"""Integración de cambio de rol."""

import pytest

from acceso.models import Rol, Usuario
from acceso.services import (
    AlcanceInvalido,
    CuentaTenantNoCambiaRol,
    RolNoPermitido,
    TenantSuspendido,
    cambiar_rol,
    reactivar_cuenta,
)
from auditoria.models import RegistroCambio
from tenants.models import Tenant


@pytest.mark.django_db
def test_cambiar_rol_audita_anterior_y_nuevo(usuario_almacen, usuario_admin):
    cambiar_rol(usuario_almacen, Rol.ADMIN_PLATAFORMA, usuario_admin)

    registro = RegistroCambio.objects.get(
        entidad="Usuario",
        entidad_id=usuario_almacen.pk,
        campo="rol",
    )
    assert registro.valor_anterior == Rol.RESPONSABLE_ALMACEN
    assert registro.valor_nuevo == Rol.ADMIN_PLATAFORMA


@pytest.mark.django_db
def test_cambiar_rol_rechaza_cuenta_tenant(usuario_tenant, usuario_admin):
    with pytest.raises(CuentaTenantNoCambiaRol):
        cambiar_rol(usuario_tenant, Rol.ADMIN_PLATAFORMA, usuario_admin)


@pytest.mark.django_db
def test_cambiar_rol_valida_alcance(usuario_admin):
    with pytest.raises(AlcanceInvalido):
        cambiar_rol(usuario_admin, Rol.RESPONSABLE_ALMACEN, usuario_admin)


@pytest.mark.django_db
def test_cambiar_rol_no_permitido(usuario_almacen, usuario_admin):
    with pytest.raises(RolNoPermitido):
        cambiar_rol(usuario_almacen, "SUPERADMIN", usuario_admin)


@pytest.mark.django_db
def test_reactivar_cuenta_de_tenant_suspendido(
    tenant, usuario_tenant, usuario_admin
):
    Usuario.objects.filter(pk=usuario_tenant.pk).update(is_active=False)
    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)

    with pytest.raises(TenantSuspendido):
        reactivar_cuenta(usuario_tenant, usuario_admin)
