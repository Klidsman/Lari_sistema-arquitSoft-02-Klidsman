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
def test_varios_materiales_y_series_agregan_por_material(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    from tecnicos.models import Tecnico
    from series.models import Serie

    segundo = Tecnico.objects.create(
        tenant=tenant,
        nif="LA3333",
        nombre="Segundo",
        creado_por=usuario_tenant,
    )
    segunda_serie = Serie.objects.create(
        numero="OTRA00000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.DISPONIBLE,
        creado_por=usuario_tenant,
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie_existente.pk],
            },
            {
                "tecnico_id": segundo.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [segunda_serie.pk],
            },
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 2,
            },
        ],
        usuario_tenant,
    )

    resultado = actualizar_stock_confirmacion_asignacion(
        solicitud, usuario_almacen
    )

    assert resultado.total_series == 2
    assert resultado.total_cantidad == 2
    assert StockTecnico.objects.filter(material=material_seriado).count() == 2
    assert StockTecnico.objects.filter(material=material_no_seriado).count() == 1
    assert RegistroCambio.objects.filter(
        entidad="StockGeneral", campo="cantidad"
    ).count() >= 2


@pytest.mark.django_db
def test_segunda_confirmacion_no_mueve_stock(
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

    actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)
    with pytest.raises(SerieNoReservada):
        actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)

    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 99
    assert StockTecnico.objects.get(
        tecnico=tecnico, material=material_seriado
    ).cantidad == 1


@pytest.mark.django_db
def test_dias_en_mano_inician_en_asignada_en(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    from datetime import timedelta

    from asignaciones.services import dias_en_mano_serie

    solicitud = _enviada(
        usuario_tenant,
        tenant,
        tecnico,
        material_seriado,
        serie=serie_existente,
    )
    actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)
    serie_existente.refresh_from_db()

    assert serie_existente.asignada_en is not None
    assert dias_en_mano_serie(
        serie_existente,
        hoy=serie_existente.asignada_en.date() + timedelta(days=1),
    ) == 1
    assert not hasattr(serie_existente, "dias_en_mano")


@pytest.mark.django_db
def test_serie_de_otro_material_no_se_acepta(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
    almacen,
    stock_general,
):
    from asignaciones.models import EstadoSolicitud, LineaAsignacion, SolicitudAsignacion
    from series.models import Serie

    serie_otro_material = Serie.objects.create(
        numero="MATER0000001",
        tenant=tenant,
        region=tenant.region,
        material=material_no_seriado,
        lote=material_no_seriado.lote,
        estado=EstadoSerie.RESERVADA,
        creado_por=usuario_tenant,
    )
    solicitud = SolicitudAsignacion.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        estado=EstadoSolicitud.ENVIADA,
        creado_por=usuario_tenant,
    )
    LineaAsignacion.objects.create(
        tenant=tenant,
        solicitud=solicitud,
        tecnico=tecnico,
        material=material_seriado,
        lote=material_seriado.lote,
        serie=serie_otro_material,
        cantidad=1,
    )

    with pytest.raises(SerieNoReservada):
        actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)

    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 100


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
def test_no_modifica_stock_de_otro_tenant(
    usuario_tenant,
    usuario_almacen,
    usuario_otro_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    from tecnicos.models import Tecnico

    otro_tenant = usuario_otro_tenant.tenant
    otro_tecnico = Tecnico.objects.create(
        tenant=otro_tenant,
        nif="LA6666",
        nombre="Otro",
        creado_por=usuario_otro_tenant,
    )
    otro_general = StockGeneral.objects.create(
        tenant=otro_tenant,
        material=material_seriado,
        cantidad=7,
    )
    otro_tecnico_stock = StockTecnico.objects.create(
        tenant=otro_tenant,
        tecnico=otro_tecnico,
        material=material_seriado,
        cantidad=3,
    )
    solicitud = _enviada(
        usuario_tenant,
        tenant,
        tecnico,
        material_seriado,
        serie=serie_existente,
    )

    actualizar_stock_confirmacion_asignacion(solicitud, usuario_almacen)

    otro_general.refresh_from_db()
    otro_tecnico_stock.refresh_from_db()
    assert otro_general.cantidad == 7
    assert otro_tecnico_stock.cantidad == 3


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
