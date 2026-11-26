"""Registro de materiales: órdenes, saldos y cierre."""

from datetime import date

import pytest
from django.utils import timezone

from materiales.models import Material
from registro_materiales.exportacion import (
    exportar_detalle_ordenes,
    exportar_reporte_mensual,
)
from registro_materiales.models import (
    AdvertenciaUso,
    CargaOrdenes,
    CierreMensual,
    DespachoAlmacen,
    MaterialHabilitado,
    OrdenLiquidacion,
    SaldoMensualMaterial,
    UsoMaterialOrden,
    UsoMaterialSerie,
)
from registro_materiales.services import (
    CantidadInvalida,
    CargaNoDeshacible,
    CierreBloqueado,
    MotivoRequerido,
    NumeroOrdenInvalido,
    SaldoInsuficiente,
    buscar_orden,
    cerrar_mes,
    confirmar_carga,
    deshacer_carga,
    guardar_uso,
    historial_orden,
    lista_chequeo,
    obtener_o_crear_orden,
    ordenes_pendientes,
    previsualizar_carga,
    procesar_lista,
    reabrir_mes,
    registrar_saldo_inicial,
    saldo_final,
    saldo_inicial_efectivo,
)
from series.models import EstadoSerie, Serie
from stock.models import MovimientoTecnico, StockGeneral, StockTecnico
from tecnicos.models import Tecnico

PERIODO = "2026-11"


def _habilitar(tenant, material, actor, activo=True):
    return MaterialHabilitado.objects.create(
        tenant=tenant,
        material=material,
        activo=activo,
        creado_por=actor,
    )


def _tecnicos(tenant, actor):
    return Tecnico.objects.create(
        tenant=tenant, nif="LA2222", nombre="Destino", creado_por=actor
    )


def _stock(tenant, tecnico, material, cantidad):
    return StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material,
        cantidad=cantidad,
    )


@pytest.mark.django_db
def test_carga_masiva_idempotente_y_resumen(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    destino = _tecnicos(tenant, usuario_tenant)
    texto = "A1\n a1 \n\nB2\n"
    resumen = previsualizar_carga(tenant, tecnico, PERIODO, texto)
    assert resumen.leidas == 2
    assert resumen.nuevas == 2
    assert resumen.omitidas == 0
    assert resumen.tambien_otro_tecnico == 0

    carga = confirmar_carga(tenant, tecnico, PERIODO, texto, usuario_tenant)
    assert carga.total_nuevas == 2
    assert OrdenLiquidacion.objects.filter(tenant=tenant).count() == 2

    resumen = previsualizar_carga(tenant, tecnico, PERIODO, texto)
    assert resumen.nuevas == 0
    assert resumen.omitidas == 2

    assert buscar_orden(tenant, tecnico, PERIODO, "a1") is not None

    obtener_o_crear_orden(tenant, destino, PERIODO, "C3", usuario_tenant)
    resumen = previsualizar_carga(tenant, tecnico, PERIODO, "C3")
    assert resumen.nuevas == 1
    assert resumen.tambien_otro_tecnico == 1

    deshacer_carga(carga, usuario_tenant, "carga errónea")
    assert OrdenLiquidacion.objects.filter(tenant=tenant).count() == 1


@pytest.mark.django_db
def test_carga_rechaza_lineas_con_mas_de_un_valor(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    lista = procesar_lista("A 1\nB2")
    assert lista.rechazadas == ["A 1"]
    with pytest.raises(NumeroOrdenInvalido):
        confirmar_carga(tenant, tecnico, PERIODO, "A 1\nB2", usuario_tenant)


@pytest.mark.django_db
def test_carga_acepta_ordenes_con_guion(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    carga = confirmar_carga(
        tenant,
        tecnico,
        PERIODO,
        "FE-1133926298\nfe-1133926298\nTT_5960190",
        usuario_tenant,
    )
    assert carga.total_nuevas == 2
    assert OrdenLiquidacion.objects.filter(
        tenant=tenant,
        tecnico=tecnico,
        periodo=PERIODO,
        numero_normalizado="FE-1133926298",
    ).exists()
    assert OrdenLiquidacion.objects.filter(
        tenant=tenant,
        tecnico=tecnico,
        periodo=PERIODO,
        numero_normalizado="TT_5960190",
    ).exists()


@pytest.mark.django_db
def test_carga_rechaza_caracter_invalido_sin_llegar_a_base(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    with pytest.raises(NumeroOrdenInvalido):
        confirmar_carga(
            tenant, tecnico, PERIODO, "FE$1133926298", usuario_tenant
        )
    assert not OrdenLiquidacion.objects.filter(tenant=tenant).exists()


@pytest.mark.django_db
def test_deshacer_bloqueado_si_hay_materiales(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    carga = confirmar_carga(tenant, tecnico, PERIODO, "A1", usuario_tenant)
    orden = OrdenLiquidacion.objects.get(numero_normalizado="A1")
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 10, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 10)
    guardar_uso(orden, date(2026, 11, 10), {material_no_seriado.pk: 2}, usuario_tenant)
    with pytest.raises(CargaNoDeshacible):
        deshacer_carga(carga, usuario_tenant)


@pytest.mark.django_db
def test_guardar_uso_cantidad_cero_e_invalida(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 10, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 10)
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    guardar_uso(orden, date(2026, 11, 10), {material_no_seriado.pk: 0}, usuario_tenant)
    assert (
        UsoMaterialOrden.objects.get(orden=orden).cantidad == 0
    )
    with pytest.raises(CantidadInvalida):
        guardar_uso(
            orden, date(2026, 11, 10), {material_no_seriado.pk: "-2"}, usuario_tenant
        )
    with pytest.raises(CantidadInvalida):
        guardar_uso(
            orden, date(2026, 11, 10), {material_no_seriado.pk: "2.5"}, usuario_tenant
        )


@pytest.mark.django_db
def test_guardar_uso_descuenta_stock_tecnico_y_no_toca_general(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 10, usuario_tenant
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )
    tecnico_stock = _stock(tenant, tecnico, material_no_seriado, 7)
    movimientos_antes = MovimientoTecnico.objects.count()
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )

    guardar_uso(
        orden,
        date(2026, 11, 10),
        {material_no_seriado.pk: 3},
        usuario_tenant,
    )

    general.refresh_from_db()
    tecnico_stock.refresh_from_db()
    assert UsoMaterialOrden.objects.get(orden=orden).cantidad == 3
    assert general.cantidad == 50
    assert tecnico_stock.cantidad == 4
    assert MovimientoTecnico.objects.count() > movimientos_antes
    assert MovimientoTecnico.objects.filter(tipo="CONSUMO").count() == 1


@pytest.mark.django_db
def test_guardar_uso_seriado_descuenta_stock_y_mueve_series(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    _habilitar(tenant, material_seriado, usuario_tenant)
    _stock(tenant, tecnico, material_seriado, 2)
    primera = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    segunda = Serie.objects.create(
        numero="SER000000002",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )

    guardar_uso(
        orden,
        date(2026, 11, 10),
        {},
        usuario_tenant,
        series_por_material={material_seriado.pk: [primera.pk]},
    )

    primera.refresh_from_db()
    segunda.refresh_from_db()
    assert primera.estado == EstadoSerie.INSTALADA
    assert segunda.estado == EstadoSerie.ASIGNADA
    assert UsoMaterialOrden.objects.get(orden=orden).cantidad == 1
    assert UsoMaterialSerie.objects.filter(uso__orden=orden).count() == 1
    assert (
        StockTecnico.objects.get(
            tenant=tenant, tecnico=tecnico, material=material_seriado
        ).cantidad
        == 1
    )

    guardar_uso(
        orden,
        date(2026, 11, 10),
        {},
        usuario_tenant,
        series_por_material={
            material_seriado.pk: [primera.pk, segunda.pk]
        },
    )
    segunda.refresh_from_db()
    assert segunda.estado == EstadoSerie.INSTALADA
    assert UsoMaterialOrden.objects.get(orden=orden).cantidad == 2
    assert (
        StockTecnico.objects.get(
            tenant=tenant, tecnico=tecnico, material=material_seriado
        ).cantidad
        == 0
    )

    guardar_uso(
        orden,
        date(2026, 11, 10),
        {},
        usuario_tenant,
        series_por_material={material_seriado.pk: [primera.pk]},
    )
    segunda.refresh_from_db()
    assert segunda.estado == EstadoSerie.ASIGNADA
    assert segunda.tecnico_id == tecnico.pk
    assert UsoMaterialOrden.objects.get(orden=orden).cantidad == 1
    assert (
        StockTecnico.objects.get(
            tenant=tenant, tecnico=tecnico, material=material_seriado
        ).cantidad
        == 1
    )


@pytest.mark.django_db
def test_bloqueo_de_saldo_negativo(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 45, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 45)
    primera = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    segunda = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A2", usuario_tenant
    )
    guardar_uso(primera, date(2026, 11, 10), {material_no_seriado.pk: 40}, usuario_tenant)
    with pytest.raises(SaldoInsuficiente, match="faltante=5"):
        guardar_uso(
            segunda, date(2026, 11, 10), {material_no_seriado.pk: 10}, usuario_tenant
        )


@pytest.mark.django_db
def test_advertencia_atipica_no_bloquea(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    for periodo in ("2026-08", "2026-09", "2026-10"):
        cierre = CierreMensual.objects.create(
            tenant=tenant, periodo=periodo, estado=CierreMensual.CERRADO
        )
        SaldoMensualMaterial.objects.create(
            cierre=cierre,
            tenant=tenant,
            material=material_no_seriado,
            saldo_inicial=100,
            despachos=0,
            usado=10,
            saldo_final=90,
        )
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 100, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 100)
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    guardar_uso(orden, date(2026, 11, 10), {material_no_seriado.pk: 31}, usuario_tenant)
    advertencia = AdvertenciaUso.objects.get()
    assert "supera" in advertencia.mensaje
    assert advertencia.resuelta is False


@pytest.mark.django_db
def test_saldo_final_herencia_y_manual_y_despachos(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 100, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 100)
    DespachoAlmacen.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        fecha=date(2026, 11, 5),
        cantidad=20,
        creado_por=usuario_tenant,
    )
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    guardar_uso(orden, date(2026, 11, 10), {material_no_seriado.pk: 30}, usuario_tenant)
    assert saldo_final(tenant, material_no_seriado, PERIODO) == 90
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 50, usuario_tenant
    )
    assert saldo_inicial_efectivo(tenant, material_no_seriado, PERIODO) == 50

    cierre = CierreMensual.objects.create(
        tenant=tenant, periodo=PERIODO, estado=CierreMensual.CERRADO
    )
    SaldoMensualMaterial.objects.create(
        cierre=cierre,
        tenant=tenant,
        material=material_no_seriado,
        saldo_inicial=50,
        despachos=20,
        usado=30,
        saldo_final=90,
    )
    assert (
        saldo_inicial_efectivo(tenant, material_no_seriado, "2026-12") == 90
    )


@pytest.mark.django_db
def test_historial_y_pendientes(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 10, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 10)
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    assert list(ordenes_pendientes(tenant, PERIODO)) == [orden]
    guardar_uso(orden, date(2026, 11, 10), {material_no_seriado.pk: 2}, usuario_tenant)
    assert not ordenes_pendientes(tenant, PERIODO).exists()
    historial = historial_orden(tenant, orden.pk)
    assert any(
        r.entidad == "UsoMaterialOrden" and r.campo in ("alta", "cantidad")
        for r in historial
    )
    assert any(
        r.entidad == "OrdenLiquidacion" and r.campo == "alta"
        for r in historial
    )


@pytest.mark.django_db
def test_cierre_bloqueado_por_pendientes(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    obtener_o_crear_orden(tenant, tecnico, PERIODO, "A1", usuario_tenant)
    assert lista_chequeo(tenant, PERIODO)
    with pytest.raises(CierreBloqueado):
        cerrar_mes(tenant, PERIODO, "backups/lari.sql", usuario_tenant)


@pytest.mark.django_db
def test_cierre_traspaso_y_reapertura(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    periodo = "2026-09"
    registrar_saldo_inicial(
        tenant, material_no_seriado, periodo, 100, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 100)
    orden = obtener_o_crear_orden(
        tenant, tecnico, periodo, "A1", usuario_tenant
    )
    guardar_uso(orden, date(2026, 9, 10), {material_no_seriado.pk: 10}, usuario_tenant)
    cierre = cerrar_mes(
        tenant, periodo, "backups/lari.sql", usuario_tenant
    )
    assert cierre.estado == CierreMensual.CERRADO
    assert saldo_inicial_efectivo(
        tenant, material_no_seriado, "2026-10"
    ) == 90

    with pytest.raises(MotivoRequerido):
        reabrir_mes(cierre, "   ", usuario_tenant)
    cierre = reabrir_mes(cierre, "Corrección", usuario_tenant)
    assert cierre.estado == CierreMensual.ABIERTO
    assert cierre.version == 2


@pytest.mark.django_db
def test_exportacion_excel_y_csv(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 10, usuario_tenant
    )
    _stock(tenant, tecnico, material_no_seriado, 10)
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    guardar_uso(orden, date(2026, 11, 10), {material_no_seriado.pk: 2}, usuario_tenant)

    xlsx = exportar_reporte_mensual(tenant, PERIODO, "xlsx")
    assert xlsx.nombre.endswith(".xlsx")
    assert xlsx.contenido[:2] == b"PK"
    csv_file = exportar_detalle_ordenes(tenant, PERIODO, "csv")
    assert csv_file.nombre.endswith(".csv")
    assert material_no_seriado.codigo.encode() in csv_file.contenido
