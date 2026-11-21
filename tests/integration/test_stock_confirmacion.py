"""Confirmación de stock de 008 sobre solicitudes ENVIADA."""

from datetime import date

import pytest

from asignaciones.services import crear_y_enviar_solicitud
from auditoria.models import RegistroCambio
from series.models import EstadoSerie
from stock.models import StockGeneral, StockTecnico
from stock.services import (
    ConfirmacionStockInvalida,
    SerieNoReservada,
    StockInsuficiente,
    actualizar_stock_confirmacion_asignacion,
)


def _enviada(usuario_tenant, tenant, tecnico, material, cantidad=None, serie=None):
    linea = {"tecnico_id": tecnico.pk, "material_id": material.pk}
    if serie is not None:
        linea["serie_ids"] = [serie.pk]
    else:
        linea["cantidad"] = cantidad
    return crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [linea],
        usuario_tenant,
    )


@pytest.mark.django_db
def test_series_y_stock_se_mueven_una_sola_vez(
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
        usuario_tenant,
        tenant,
        tecnico,
        material_seriado,
        serie=serie_existente,
    )

    resultado = actualizar_stock_confirmacion_asignacion(
        solicitud, usuario_almacen
    )

    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.ASIGNADA
    assert serie_existente.tecnico_id == tecnico.pk
    assert serie_existente.asignada_en is not None
    assert resultado.series_actualizadas == [serie_existente.pk]
    assert resultado.total_series == 1
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 99
    assert StockTecnico.objects.get(
        tecnico=tecnico, material=material_seriado
    ).cantidad == 1
    solicitud.refresh_from_db()
    assert solicitud.estado == "ENVIADA"
    assert solicitud.confirmada_en is None


@pytest.mark.django_db
def test_no_seriados_actualizan_cantidad_agregada(
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
        usuario_tenant,
        tenant,
        tecnico,
        material_no_seriado,
        cantidad=5,
    )

    resultado = actualizar_stock_confirmacion_asignacion(
        solicitud, usuario_almacen
    )

    assert resultado.total_cantidad == 5
    assert StockGeneral.objects.get(
        tenant=tenant, material=material_no_seriado
    ).cantidad == 45
    assert StockTecnico.objects.get(
        tecnico=tecnico, material=material_no_seriado
    ).cantidad == 5


@pytest.mark.django_db
def test_stock_insuficiente_no_modifica_nada(
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
        usuario_tenant,
        tenant,
        tecnico,
        material_seriado,
        serie=serie_existente,
    )
    StockGeneral.objects.filter(pk=stock_general.pk).update(cantidad=0)

    with pytest.raises(StockInsuficiente):
        actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)

    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.RESERVADA
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 0
    assert not StockTecnico.objects.exists()


@pytest.mark.django_db
def test_serie_no_reservada_no_modifica_nada(
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
        usuario_tenant,
        tenant,
        tecnico,
        material_seriado,
        serie=serie_existente,
    )
    serie_existente.estado = EstadoSerie.DISPONIBLE
    serie_existente.save(update_fields=["estado"])

    with pytest.raises(SerieNoReservada):
        actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)

    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 100
    assert not StockTecnico.objects.exists()


@pytest.mark.django_db
def test_solicitud_sin_lineas_es_invalida(
    usuario_tenant, usuario_almacen, tenant
):
    from asignaciones.models import EstadoSolicitud, SolicitudAsignacion

    solicitud = SolicitudAsignacion.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        estado=EstadoSolicitud.ENVIADA,
        creado_por=usuario_tenant,
    )

    with pytest.raises(ConfirmacionStockInvalida):
        actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)


@pytest.mark.django_db
def test_auditoria_de_series_y_stock(
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
        usuario_tenant,
        tenant,
        tecnico,
        material_seriado,
        serie=serie_existente,
    )
    auditoria_solicitud = RegistroCambio.objects.filter(
        entidad="SolicitudAsignacion", entidad_id=solicitud.pk
    ).count()

    actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)

    propios = RegistroCambio.objects.filter(tenant=tenant)
    assert propios.filter(
        entidad="Serie",
        entidad_id=serie_existente.pk,
        campo="estado",
        valor_nuevo=EstadoSerie.ASIGNADA,
    ).count() == 1
    assert propios.filter(entidad="Serie", campo="tecnico").count() == 1
    assert propios.filter(entidad="Serie", campo="asignada_en").count() == 1
    assert propios.filter(entidad="StockGeneral", campo="cantidad").count() == 1
    assert propios.filter(entidad="StockTecnico", campo="cantidad").count() == 1
    assert RegistroCambio.objects.filter(
        entidad="SolicitudAsignacion", entidad_id=solicitud.pk
    ).count() == auditoria_solicitud
    eventos = [
        propios.get(
            entidad="Serie",
            campo="estado",
            valor_nuevo=EstadoSerie.ASIGNADA,
        ),
        propios.get(entidad="Serie", campo="tecnico"),
        propios.get(entidad="Serie", campo="asignada_en"),
        propios.get(entidad="StockGeneral", campo="cantidad"),
        propios.get(entidad="StockTecnico", campo="cantidad"),
    ]
    assert all(evento.usuario_id == usuario_almacen.pk for evento in eventos)
