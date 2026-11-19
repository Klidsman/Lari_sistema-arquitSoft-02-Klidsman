"""Registro de devoluciones."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from auditoria.models import RegistroCambio
from logistica_inversa.models import Devolucion
from logistica_inversa.services import (
    FechaInvalida,
    NoEncontrado,
    SerieFueraTenant,
    SerieNoEnTecnico,
    SerieReservada,
    SinSeries,
    obtener_devolucion,
    registrar_devolucion,
)
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso, LineaTraspaso, SolicitudTraspaso


def _serie(
    tenant,
    material,
    tecnico,
    numero,
    usuario,
    estado=EstadoSerie.ASIGNADA,
):
    asignada = estado == EstadoSerie.ASIGNADA
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=estado,
        tecnico=tecnico if asignada else None,
        asignada_en=timezone.now() if asignada else None,
        creado_por=usuario,
    )


@pytest.mark.django_db
def test_devolucion_libera_custodia_y_mueve_stock(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    primera = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    segunda = _serie(
        tenant, material_seriado, tecnico, "SER000000002", usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=2
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=10
    )

    devolucion = registrar_devolucion(
        tenant,
        tecnico,
        date.today(),
        [primera, segunda],
        "  Devuelto en buen estado  ",
        usuario_tenant,
    )

    primera.refresh_from_db()
    segunda.refresh_from_db()
    general.refresh_from_db()
    assert devolucion.observaciones == "Devuelto en buen estado"
    assert devolucion.lineas.count() == 2
    assert devolucion.acta_ruta
    assert devolucion.acta_generada_en is not None
    for serie in (primera, segunda):
        assert serie.estado == EstadoSerie.DISPONIBLE
        assert serie.tecnico_id is None
        assert serie.asignada_en is None
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_seriado
        ).cantidad
        == 0
    )
    assert general.cantidad == 12


@pytest.mark.django_db
def test_serie_devuelta_puede_reasignarse(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    registrar_devolucion(
        tenant, tecnico, date.today(), [serie], "", usuario_tenant
    )
    serie.refresh_from_db()
    destino = Tecnico.objects.create(
        tenant=tenant, nif="LA2222", nombre="Destino", creado_por=usuario_tenant
    )
    # La serie queda elegible para una nueva asignación.
    serie.estado = EstadoSerie.ASIGNADA
    serie.tecnico = destino
    serie.asignada_en = timezone.now()
    serie.save(update_fields=["estado", "tecnico", "asignada_en"])
    serie.refresh_from_db()
    assert serie.tecnico_id == destino.pk


@pytest.mark.django_db
def test_auditoria_completa_de_devolucion(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    devolucion = registrar_devolucion(
        tenant, tecnico, date.today(), [serie], "", usuario_tenant
    )
    assert RegistroCambio.objects.filter(
        entidad="Devolucion", entidad_id=devolucion.pk, campo="alta"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="LineaDevolucion", campo="alta"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="Serie", entidad_id=serie.pk, campo="estado"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="StockTecnico", campo="cantidad"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="StockGeneral", campo="cantidad"
    ).exists()


@pytest.mark.django_db
def test_validaciones_de_devolucion(
    usuario_tenant,
    usuario_otro_tenant,
    tenant,
    tecnico,
    tecnico_otro_tenant,
    material_seriado,
    almacen,
):
    serie = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    otro = Tecnico.objects.create(
        tenant=tenant, nif="LA2222", nombre="Otro", creado_por=usuario_tenant
    )
    with pytest.raises(SinSeries):
        registrar_devolucion(
            tenant, tecnico, date.today(), [], "", usuario_tenant
        )
    with pytest.raises(FechaInvalida):
        registrar_devolucion(
            tenant,
            tecnico,
            date.today() + timedelta(days=1),
            [serie],
            "",
            usuario_tenant,
        )
    with pytest.raises(SerieNoEnTecnico):
        registrar_devolucion(
            tenant, otro, date.today(), [serie], "", usuario_tenant
        )
    with pytest.raises(SerieFueraTenant):
        registrar_devolucion(
            usuario_otro_tenant.tenant,
            tecnico_otro_tenant,
            date.today(),
            [serie],
            "",
            usuario_otro_tenant,
        )
    with pytest.raises(NoEncontrado):
        obtener_devolucion(usuario_otro_tenant.tenant, 999)


@pytest.mark.django_db
def test_serie_reservada_en_traspaso_no_se_devuelve(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    destino = Tecnico.objects.create(
        tenant=tenant, nif="LA2222", nombre="Destino", creado_por=usuario_tenant
    )
    solicitud = SolicitudTraspaso.objects.create(
        tenant=tenant,
        region=tenant.region,
        tecnico_origen=tecnico,
        tecnico_destino=destino,
        fecha=date.today(),
        estado=EstadoTraspaso.ENVIADA,
        creado_por=usuario_tenant,
    )
    LineaTraspaso.objects.create(
        tenant=tenant,
        solicitud=solicitud,
        material=material_seriado,
        serie=serie,
        cantidad=1,
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    with pytest.raises(SerieReservada):
        registrar_devolucion(
            tenant, tecnico, date.today(), [serie], "", usuario_tenant
        )
