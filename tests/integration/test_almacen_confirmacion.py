"""Confirmación y rechazo desde el almacén."""

from datetime import date

import pytest

from acceso.models import Rol, Usuario
from asignaciones.almacen_services import (
    EstadoSolicitudInvalido,
    SolicitudNoExiste,
    confirmar_solicitud,
    rechazar_solicitud,
)
from asignaciones.models import EstadoSolicitud
from asignaciones.services import crear_y_enviar_solicitud
from tenants.models import Almacen, Region
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _enviada(usuario_tenant, tenant, tecnico, material, serie=None, cantidad=None):
    linea = {"tecnico_id": tecnico.pk, "material_id": material.pk}
    if serie is not None:
        linea["serie_ids"] = [serie.pk]
    else:
        linea["cantidad"] = cantidad
    return crear_y_enviar_solicitud(
        tenant, date.today(), [linea], usuario_tenant
    )


@pytest.mark.django_db
def test_confirmar_mueve_stock_y_series(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )

    confirmar_solicitud(solicitud, usuario_almacen)

    solicitud.refresh_from_db()
    serie_existente.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.CONFIRMADA
    assert solicitud.confirmada_en is not None
    assert serie_existente.estado == EstadoSerie.ASIGNADA
    assert serie_existente.tecnico_id == tecnico.pk
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 99
    assert StockTecnico.objects.get(
        tecnico=tecnico, material=material_seriado
    ).cantidad == 1


@pytest.mark.django_db
def test_confirmar_no_seriado(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_no_seriado, cantidad=10
    )

    confirmar_solicitud(solicitud, usuario_almacen)

    assert StockGeneral.objects.get(
        tenant=tenant, material=material_no_seriado
    ).cantidad == 40
    assert StockTecnico.objects.get(
        tecnico=tecnico, material=material_no_seriado
    ).cantidad == 10


@pytest.mark.django_db
def test_rechazar_libera_series_y_pide_motivo(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )

    rechazar_solicitud(solicitud, "No hay unidad disponible", usuario_almacen)

    solicitud.refresh_from_db()
    serie_existente.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.RECHAZADA
    assert solicitud.motivo_rechazo == "No hay unidad disponible"
    assert solicitud.rechazada_en is not None
    assert serie_existente.estado == EstadoSerie.DISPONIBLE


@pytest.mark.django_db
def test_confirmar_rechaza_solicitud_de_otra_region(
    usuario_admin,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=5
    )
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_no_seriado, cantidad=1
    )

    otra = Region.objects.create(
        codigo="ARE", nombre="Arequipa", creado_por=usuario_admin
    )
    Almacen.objects.create(
        region=otra,
        centro="PR01",
        codigo_almacen="BE01",
        buzon="almacen.are@lari.local",
        creado_por=usuario_admin,
    )
    actor_ajeno = Usuario.objects.create_user(
        email="almacen.are@lari.local",
        password="ClaveAre12345",
        rol=Rol.RESPONSABLE_ALMACEN,
        region=otra,
        is_active=True,
    )
    with pytest.raises(SolicitudNoExiste):
        confirmar_solicitud(solicitud, actor_ajeno)
    with pytest.raises(SolicitudNoExiste):
        rechazar_solicitud(solicitud, "Sin stock", actor_ajeno)


@pytest.mark.django_db
def test_confirmacion_revierte_si_falta_stock(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    StockGeneral.objects.filter(pk=stock_general.pk).update(cantidad=0)

    with pytest.raises(EstadoSolicitudInvalido):
        confirmar_solicitud(solicitud, usuario_almacen)

    solicitud.refresh_from_db()
    serie_existente.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.ENVIADA
    assert solicitud.confirmada_en is None
    assert serie_existente.estado == EstadoSerie.RESERVADA
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 0
    assert not StockTecnico.objects.filter(tecnico=tecnico).exists()
