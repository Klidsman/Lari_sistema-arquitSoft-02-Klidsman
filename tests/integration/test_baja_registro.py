"""Registro de bajas de equipos."""

import pytest
from django.utils import timezone

from logistica_inversa.models import BajaEquipo, CausaBaja
from logistica_inversa.services import (
    CausaInvalida,
    CausaRequerida,
    SerieInstalada,
    SerieYaInactiva,
    registrar_baja_equipo,
)
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _serie(tenant, material, estado, usuario, tecnico=None, numero="SER000000001"):
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
def test_baja_de_serie_asignada_descuenta_stock_tecnico(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant, tecnico
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=5
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=10
    )
    baja = registrar_baja_equipo(
        tenant, serie, "AVERIA", "  Equipo dañado  ", usuario_tenant
    )
    serie.refresh_from_db()
    general.refresh_from_db()
    assert baja.causa == CausaBaja.AVERIA
    assert baja.observaciones == "Equipo dañado"
    assert serie.estado == EstadoSerie.INACTIVA
    assert serie.tecnico_id is None
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_seriado
        ).cantidad
        == 4
    )
    assert general.cantidad == 10


@pytest.mark.django_db
def test_baja_de_serie_disponible_descuenta_stock_general(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, EstadoSerie.DISPONIBLE, usuario_tenant
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=10
    )
    baja = registrar_baja_equipo(
        tenant, serie, "MIGRACION", "", usuario_tenant
    )
    serie.refresh_from_db()
    general.refresh_from_db()
    assert baja.causa == CausaBaja.MIGRACION
    assert serie.estado == EstadoSerie.INACTIVA
    assert general.cantidad == 9


@pytest.mark.django_db
def test_causa_obligatoria_y_valida(
    usuario_tenant, tenant, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, EstadoSerie.DISPONIBLE, usuario_tenant
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=1
    )
    with pytest.raises(CausaRequerida):
        registrar_baja_equipo(tenant, serie, "  ", "", usuario_tenant)
    with pytest.raises(CausaInvalida):
        registrar_baja_equipo(tenant, serie, "ROBO", "", usuario_tenant)
    assert not BajaEquipo.objects.exists()


@pytest.mark.django_db
def test_estados_no_admitidos_para_baja(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    reservada = _serie(
        tenant,
        material_seriado,
        EstadoSerie.RESERVADA,
        usuario_tenant,
        numero="SER000000001",
    )
    from logistica_inversa.services import SerieReservada

    with pytest.raises(SerieReservada):
        registrar_baja_equipo(tenant, reservada, "AVERIA", "", usuario_tenant)

    instalada = _serie(
        tenant,
        material_seriado,
        EstadoSerie.INSTALADA,
        usuario_tenant,
        numero="SER000000002",
    )
    with pytest.raises(SerieInstalada):
        registrar_baja_equipo(tenant, instalada, "AVERIA", "", usuario_tenant)

    inactiva = _serie(
        tenant,
        material_seriado,
        EstadoSerie.INACTIVA,
        usuario_tenant,
        numero="SER000000003",
    )
    with pytest.raises(SerieYaInactiva):
        registrar_baja_equipo(tenant, inactiva, "AVERIA", "", usuario_tenant)

@pytest.mark.django_db
def test_baja_multiple_series_del_tecnico(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    primera = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=tecnico, numero="SER000000031",
    )
    segunda = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=tecnico, numero="SER000000032",
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=2
    )

    from logistica_inversa.services import registrar_bajas_equipo

    bajas = registrar_bajas_equipo(
        tenant,
        tecnico,
        [primera, segunda],
        "AVERIA",
        "Lote dañado",
        usuario_tenant,
    )

    assert len(bajas) == 2
    primera.refresh_from_db()
    segunda.refresh_from_db()
    assert primera.estado == EstadoSerie.INACTIVA
    assert segunda.estado == EstadoSerie.INACTIVA
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_seriado
        ).cantidad
        == 0
    )
