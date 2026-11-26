"""Comparación de series/cantidades y huella de stock."""

import pytest
from django.utils import timezone

from conciliaciones.excel import FilaReporte
from conciliaciones.services import (
    calcular_huella_stock,
    clasificar_tecnicos,
    comparar_cantidades,
    comparar_series,
    validar_filas,
)
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico
from tecnicos.models import Tecnico


def _fila(material, nif, cantidad=None, serie=None, lote=""):
    return FilaReporte(
        material_codigo=material.codigo,
        lote=lote or material.lote,
        libre_utilizacion=cantidad,
        numero_serie=serie,
        nif=nif,
        descripcion=material.descripcion,
        fila=1,
    )


def _preparar(tenant, filas):
    clasificacion = clasificar_tecnicos(tenant, filas)
    valido = validar_filas(tenant, filas, clasificacion)
    return clasificacion, valido


def _serie(tenant, material, tecnico, numero, estado=EstadoSerie.ASIGNADA):
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
        creado_por=tenant.creado_por,
    )


# --- T010: comparar_series ----------------------------------------------


def test_serie_en_reporte_ausente_en_sistema(
    db, tenant, tecnico, material_seriado, usuario_tenant
):
    filas = [_fila(material_seriado, tecnico.nif, serie="ABC123456789")]
    clasificacion, valido = _preparar(tenant, filas)
    diferencias = comparar_series(tenant, clasificacion, valido)
    assert len(diferencias) == 1
    assert diferencias[0].tipo == "EN_REPORTE_NO_SISTEMA"
    assert diferencias[0].numero == "ABC123456789"


def test_serie_en_sistema_ausente_en_reporte(
    db, tenant, tecnico, material_seriado, material_no_seriado, usuario_tenant
):
    _serie(tenant, material_seriado, tecnico, "ABC123456789")
    # Una fila fungible solo marca al técnico como presente en el reporte.
    filas = [_fila(material_no_seriado, tecnico.nif, cantidad=0)]
    clasificacion, valido = _preparar(tenant, filas)
    diferencias = comparar_series(tenant, clasificacion, valido)
    assert [(d.tipo, d.numero) for d in diferencias] == [
        ("EN_SISTEMA_NO_REPORTE", "ABC123456789")
    ]


def test_serie_en_otro_tecnico(
    db, tenant, tecnico, material_seriado, usuario_tenant
):
    otro = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Otro",
        creado_por=usuario_tenant,
    )
    _serie(tenant, material_seriado, otro, "ABC123456789")
    filas = [_fila(material_seriado, tecnico.nif, serie="ABC123456789")]
    clasificacion, valido = _preparar(tenant, filas)
    diferencias = comparar_series(tenant, clasificacion, valido)
    assert len(diferencias) == 1
    assert diferencias[0].tipo == "EN_OTRO_TECNICO"
    assert diferencias[0].tecnico_sistema.pk == otro.pk


def test_serie_instalada_no_se_reutiliza(
    db, tenant, tecnico, material_seriado, usuario_tenant
):
    _serie(
        tenant,
        material_seriado,
        tecnico,
        "ABC123456789",
        estado=EstadoSerie.INSTALADA,
    )
    from conciliaciones.services import SerieInstalada

    filas = [_fila(material_seriado, tecnico.nif, serie="ABC123456789")]
    clasificacion = clasificar_tecnicos(tenant, filas)
    with pytest.raises(SerieInstalada):
        validar_filas(tenant, filas, clasificacion)


# --- T011: comparar_cantidades ------------------------------------------


def test_diferencia_de_cantidad_por_tecnico_y_material(
    db, tenant, tecnico, material_no_seriado
):
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
    )
    filas = [_fila(material_no_seriado, tecnico.nif, cantidad=4)]
    clasificacion, valido = _preparar(tenant, filas)
    diferencias = comparar_cantidades(tenant, clasificacion, valido)
    assert len(diferencias) == 1
    assert diferencias[0].cantidad_sistema == 10
    assert diferencias[0].cantidad_reporte == 4
    assert diferencias[0].diferencia == -6


def test_material_ausente_para_tecnico_presente_es_cero(
    db, tenant, tecnico, material_no_seriado
):
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
    )
    filas = [_fila(material_no_seriado, tecnico.nif, cantidad=0)]
    clasificacion, valido = _preparar(tenant, filas)
    diferencias = comparar_cantidades(tenant, clasificacion, valido)
    assert diferencias[0].cantidad_reporte == 0


def test_tecnico_ausente_no_genera_diferencia(
    db, tenant, tecnico, material_no_seriado
):
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
    )
    clasificacion, valido = _preparar(tenant, [])
    assert comparar_cantidades(tenant, clasificacion, valido) == []


def test_filas_no_seriadas_se_suman(
    db, tenant, tecnico, material_no_seriado
):
    filas = [
        _fila(material_no_seriado, tecnico.nif, cantidad=3),
        _fila(material_no_seriado, tecnico.nif, cantidad=2),
    ]
    clasificacion, valido = _preparar(tenant, filas)
    diferencias = comparar_cantidades(tenant, clasificacion, valido)
    assert diferencias[0].cantidad_reporte == 5


# --- T012: huella de stock ----------------------------------------------


def test_huella_estable_y_sensible_a_stock_y_series(
    db, tenant, tecnico, material_seriado, material_no_seriado
):
    stock = StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
    )
    serie = _serie(tenant, material_seriado, tecnico, "ABC123456789")

    inicial = calcular_huella_stock(tenant, [tecnico])
    assert inicial == calcular_huella_stock(tenant, [tecnico])

    stock.cantidad = 11
    stock.save(update_fields=["cantidad"])
    tras_stock = calcular_huella_stock(tenant, [tecnico])
    assert tras_stock != inicial

    serie.estado = EstadoSerie.INSTALADA
    serie.tecnico = None
    serie.asignada_en = None
    serie.save(update_fields=["estado", "tecnico", "asignada_en"])
    assert calcular_huella_stock(tenant, [tecnico]) != tras_stock


def test_huella_ignora_stock_general_y_tecnicos_ausentes(
    db, tenant, tecnico, material_no_seriado, usuario_tenant
):
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=100
    )
    antes = calcular_huella_stock(tenant, [tecnico])
    general.cantidad = 50
    general.save(update_fields=["cantidad"])
    assert calcular_huella_stock(tenant, [tecnico]) == antes

    ajeno = Tecnico.objects.create(
        tenant=tenant,
        nif="LA3333",
        nombre="Ausente",
        creado_por=usuario_tenant,
    )
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=ajeno,
        material=material_no_seriado,
        cantidad=99,
    )
    assert calcular_huella_stock(tenant, [tecnico]) == antes
