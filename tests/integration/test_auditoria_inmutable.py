"""Inmutabilidad de la auditoría y ausencia de secretos."""

import pytest
from django.db import DatabaseError, transaction

from acceso.models import Rol, Usuario
from acceso.services import cambiar_rol, desactivar_cuenta
from auditoria.models import RegistroCambio
from tenants.services import crear_region, suspender_tenant

CAMPOS_PROHIBIDOS = ("password", "token_hash", "secreto_totp", "contraseña")


@pytest.mark.django_db
def test_update_y_delete_fallan_por_permisos(tenant, usuario_admin):
    registro = RegistroCambio.objects.create(
        tenant=tenant,
        entidad="Tenant",
        entidad_id=tenant.pk,
        campo="nombre",
        valor_anterior="Antes",
        valor_nuevo="Después",
        usuario=usuario_admin,
    )

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            RegistroCambio.objects.filter(pk=registro.pk).update(campo="alterado")

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            RegistroCambio.objects.filter(pk=registro.pk).delete()


@pytest.mark.django_db
def test_ningun_registro_contiene_secretos(
    tenant, region, usuario_admin, usuario_almacen
):
    crear_region(
        {
            "codigo": "SEC",
            "nombre": "Segura",
            "centro": "PR05",
            "almacen": "BE03",
            "buzon": "sec@lari.local",
        },
        usuario_admin,
    )
    cambiar_rol(usuario_almacen, Rol.ADMIN_PLATAFORMA, usuario_admin)
    desactivar_cuenta(usuario_almacen, usuario_admin)
    suspender_tenant(tenant, usuario_admin)

    for registro in RegistroCambio.objects.all():
        texto = " ".join(
            [
                registro.campo,
                registro.valor_anterior,
                registro.valor_nuevo,
            ]
        ).lower()
        for prohibido in CAMPOS_PROHIBIDOS:
            assert prohibido not in texto


@pytest.mark.django_db
def test_altas_cambios_y_desactivaciones_generan_auditoria(
    tenant, region, usuario_admin, usuario_almacen
):
    crear_region(
        {
            "codigo": "AUD",
            "nombre": "Auditada",
            "centro": "PR05",
            "almacen": "BE03",
            "buzon": "aud@lari.local",
        },
        usuario_admin,
    )
    cambiar_rol(usuario_almacen, Rol.ADMIN_PLATAFORMA, usuario_admin)
    desactivar_cuenta(usuario_almacen, usuario_admin)
    suspender_tenant(tenant, usuario_admin)

    assert RegistroCambio.objects.filter(entidad="Region", campo="alta").exists()
    assert RegistroCambio.objects.filter(
        entidad="Usuario", campo="rol"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="Usuario", campo="is_active"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="Tenant", campo="estado"
    ).exists()
