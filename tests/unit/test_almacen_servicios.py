"""Permisos y alcance de los servicios del almacén (007)."""

from datetime import date

import pytest

from acceso.models import Rol, Usuario
from asignaciones import almacen_services as services
from asignaciones.models import EstadoSolicitud
from asignaciones.services import (
    cancelar_solicitud,
    crear_borrador_solicitud,
    crear_y_enviar_solicitud,
)
from stock.models import StockGeneral
from tenants.models import Region


def _enviada(usuario_tenant, tenant, tecnico, material):
    StockGeneral.objects.create(
        tenant=tenant, material=material, cantidad=10
    )
    return crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )


# --- T013: permisos y alcance -------------------------------------------


@pytest.mark.django_db
def test_validar_cuenta_almacen_acepta_almacen_activo(
    usuario_almacen, almacen, region
):
    assert services.validar_cuenta_almacen(usuario_almacen).pk == region.pk


@pytest.mark.django_db
def test_validar_cuenta_almacen_rechaza_otros_roles(
    usuario_admin, usuario_tenant, almacen
):
    for actor in (usuario_admin, usuario_tenant):
        with pytest.raises(services.PermisoDenegado):
            services.validar_cuenta_almacen(actor)


@pytest.mark.django_db
def test_validar_cuenta_almacen_rechaza_cuenta_inactiva(
    usuario_almacen, almacen
):
    usuario_almacen.is_active = False
    usuario_almacen.save(update_fields=["is_active"])
    with pytest.raises(services.PermisoDenegado):
        services.validar_cuenta_almacen(usuario_almacen)


@pytest.mark.django_db
def test_validar_cuenta_almacen_rechaza_region_inactiva(
    usuario_almacen, region, almacen
):
    region.activa = False
    region.save(update_fields=["activa"])
    with pytest.raises(services.PermisoDenegado):
        services.validar_cuenta_almacen(usuario_almacen)


@pytest.mark.django_db
def test_validar_cuenta_almacen_rechaza_sin_almacen(
    usuario_admin, region, almacen
):
    sin = Region.objects.create(
        codigo="SIN", nombre="Sin almacén", creado_por=usuario_admin
    )
    actor = Usuario.objects.create_user(
        email="sin@lari.local",
        password="ClaveSin12345",
        rol=Rol.RESPONSABLE_ALMACEN,
        region=sin,
        is_active=True,
    )
    with pytest.raises(services.PermisoDenegado):
        services.validar_cuenta_almacen(actor)


@pytest.mark.django_db
def test_validar_cuenta_almacen_rechaza_almacen_inactivo(
    usuario_almacen, almacen
):
    almacen.activo = False
    almacen.save(update_fields=["activo"])
    with pytest.raises(services.PermisoDenegado):
        services.validar_cuenta_almacen(usuario_almacen)


@pytest.mark.django_db
def test_obtener_solicitud_region_filtra_estado_y_region(
    usuario_admin,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    region,
):
    enviada = _enviada(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    assert (
        services.obtener_solicitud_region(region, enviada.pk).pk
        == enviada.pk
    )

    borrador = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )
    with pytest.raises(services.SolicitudNoExiste):
        services.obtener_solicitud_region(region, borrador.pk)

    cancelada = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )
    cancelar_solicitud(cancelada, usuario_tenant)
    with pytest.raises(services.SolicitudNoExiste):
        services.obtener_solicitud_region(region, cancelada.pk)

    otra = Region.objects.create(
        codigo="OTR", nombre="Otra", creado_por=usuario_admin
    )
    with pytest.raises(services.SolicitudNoExiste):
        services.obtener_solicitud_region(otra, enviada.pk)

    with pytest.raises(services.SolicitudNoExiste):
        services.obtener_solicitud_region(region, enviada.pk + 999)
    assert enviada.estado == EstadoSolicitud.ENVIADA
