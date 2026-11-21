"""Servicios, permisos y transiciones de asignaciones."""

from datetime import date

import pytest

from asignaciones.models import EstadoSolicitud
from asignaciones.services import (
    EstadoSolicitudInvalido,
    PermisoDenegado,
    SolicitudNoExiste,
    TenantSuspendido,
    cancelar_solicitud,
    crear_borrador_solicitud,
    enviar_solicitud,
    listar_solicitudes,
    obtener_solicitud,
    totales_solicitud,
    validar_cuenta_tenant,
)
from stock.models import StockGeneral
from tenants.models import Tenant


def _borrador(usuario_tenant, tenant, tecnico, material_no_seriado, cantidad=2):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    return crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": cantidad,
            }
        ],
        usuario_tenant,
    )


@pytest.mark.django_db
def test_validar_cuenta_tenant_roles_y_estados(
    usuario_tenant, usuario_admin, usuario_almacen, tenant
):
    assert validar_cuenta_tenant(usuario_tenant) == tenant
    for actor in (usuario_admin, usuario_almacen):
        with pytest.raises(PermisoDenegado):
            validar_cuenta_tenant(actor)

    usuario_tenant.is_active = False
    usuario_tenant.save(update_fields=["is_active"])
    with pytest.raises(PermisoDenegado):
        validar_cuenta_tenant(usuario_tenant)

    usuario_tenant.is_active = True
    usuario_tenant.save(update_fields=["is_active"])
    tenant.estado = Tenant.ESTADO_SUSPENDIDO
    tenant.save(update_fields=["estado"])
    with pytest.raises(TenantSuspendido):
        validar_cuenta_tenant(usuario_tenant)


@pytest.mark.django_db
def test_obtener_solicitud_ajena_404(
    usuario_tenant, usuario_otro_tenant, tenant
):
    from asignaciones.models import SolicitudAsignacion

    ajena = SolicitudAsignacion.objects.create(
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        fecha=date.today(),
        creado_por=usuario_otro_tenant,
    )
    with pytest.raises(SolicitudNoExiste):
        obtener_solicitud(tenant, ajena.pk)


@pytest.mark.django_db
def test_listar_filtra_por_tenant_y_estado(
    usuario_tenant, tenant, tecnico, material_no_seriado, usuario_otro_tenant
):
    propia = _borrador(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    from asignaciones.models import SolicitudAsignacion

    SolicitudAsignacion.objects.create(
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        fecha=date.today(),
        creado_por=usuario_otro_tenant,
    )

    assert listar_solicitudes(tenant).count() == 1
    assert listar_solicitudes(tenant, EstadoSolicitud.BORRADOR).count() == 1
    assert listar_solicitudes(tenant, EstadoSolicitud.ENVIADA).count() == 0
    assert listar_solicitudes(tenant).get() == propia


@pytest.mark.django_db
def test_totales_y_transiciones(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _borrador(
        usuario_tenant, tenant, tecnico, material_no_seriado, cantidad=3
    )
    totales = totales_solicitud(solicitud)
    assert totales["total_lineas"] == 1
    assert totales["total_cantidad"] == 3
    assert totales["total_series"] == 0

    enviar_solicitud(solicitud, usuario_tenant)
    with pytest.raises(EstadoSolicitudInvalido):
        cancelar_solicitud(solicitud, usuario_tenant)
    with pytest.raises(EstadoSolicitudInvalido):
        enviar_solicitud(solicitud, usuario_tenant)
