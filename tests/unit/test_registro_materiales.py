"""Registro de materiales: validadores, cálculos y restricciones."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from registro_materiales.models import (
    CierreMensual,
    MaterialHabilitado,
    OrdenLiquidacion,
    SaldoInicialPeriodo,
    UsoMaterialOrden,
)
from registro_materiales.services import (
    PeriodoInvalido,
    _cantidad,
    normalizar_numero,
    periodo_actual,
    periodo_anterior,
    periodo_de_fecha,
    saldo_final,
    saldo_inicial_efectivo,
    validar_periodo,
)


# --- T009: validadores y cálculos ---------------------------------------


def test_periodo_de_fecha_y_desplazamiento():
    assert periodo_de_fecha(date(2026, 11, 18)) == "2026-11"
    assert periodo_actual() == date.today().strftime("%Y-%m")
    assert periodo_anterior("2026-01") == "2025-12"
    with pytest.raises(PeriodoInvalido):
        validar_periodo("2026-13")


def test_cantidad_acepta_entero_no_negativo_y_rechaza_resto():
    assert _cantidad(0) == 0
    assert _cantidad("7") == 7
    assert _cantidad(None) == 0
    assert _cantidad("") == 0
    for valor in (-1, "2.5", "abc", True):
        with pytest.raises(Exception):
            _cantidad(valor)


def test_normalizar_numero_orden_conserva_forma():
    assert normalizar_numero("  a1  ") == "A1"
    with pytest.raises(Exception):
        normalizar_numero("A 1")


@pytest.mark.django_db
def test_saldo_inicial_y_final(tenant, usuario_tenant, material_no_seriado):
    assert (
        saldo_inicial_efectivo(
            tenant, material_no_seriado, "2026-11"
        )
        == 0
    )
    assert saldo_final(tenant, material_no_seriado, "2026-11") == 0


# --- T007: restricciones de modelos -------------------------------------


def _habilitar(tenant, material, actor):
    return MaterialHabilitado.objects.create(
        tenant=tenant, material=material, creado_por=actor
    )


def _orden(tenant, tecnico, actor, periodo="2026-11", numero="A1"):
    return OrdenLiquidacion.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        numero_original=numero,
        numero_normalizado=numero,
        periodo=periodo,
        creado_por=actor,
    )


@pytest.mark.django_db
def test_material_habilitado_unico_por_tenant(
    tenant, usuario_tenant, material_no_seriado
):
    _habilitar(tenant, material_no_seriado, usuario_tenant)
    with pytest.raises(IntegrityError), transaction.atomic():
        _habilitar(tenant, material_no_seriado, usuario_tenant)


@pytest.mark.django_db
def test_saldo_inicial_unico_y_periodo_valido(
    tenant, usuario_tenant, material_no_seriado
):
    SaldoInicialPeriodo.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        periodo="2026-11",
        cantidad=10,
        creado_por=usuario_tenant,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        SaldoInicialPeriodo.objects.create(
            tenant=tenant,
            material=material_no_seriado,
            periodo="2026-11",
            cantidad=5,
            creado_por=usuario_tenant,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        SaldoInicialPeriodo.objects.create(
            tenant=tenant,
            material=material_no_seriado,
            periodo="2026-13",
            cantidad=5,
            creado_por=usuario_tenant,
        )


@pytest.mark.django_db
def test_orden_unica_por_tecnico_mes_y_numero(
    tenant, usuario_tenant, tecnico
):
    _orden(tenant, tecnico, usuario_tenant)
    with pytest.raises(IntegrityError), transaction.atomic():
        _orden(tenant, tecnico, usuario_tenant)


@pytest.mark.django_db
def test_orden_rechaza_numero_o_periodo_invalidos(
    tenant, usuario_tenant, tecnico
):
    with pytest.raises(IntegrityError), transaction.atomic():
        _orden(
            tenant, tecnico, usuario_tenant, periodo="2026-11", numero="A 1"
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        _orden(
            tenant, tecnico, usuario_tenant, periodo="2026-13", numero="A1"
        )


@pytest.mark.django_db
def test_uso_unico_por_orden_material_y_cantidad_no_negativa(
    tenant, usuario_tenant, tecnico, material_no_seriado
):
    orden = _orden(tenant, tecnico, usuario_tenant)
    UsoMaterialOrden.objects.create(
        tenant=tenant,
        orden=orden,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=2,
        creado_por=usuario_tenant,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        UsoMaterialOrden.objects.create(
            tenant=tenant,
            orden=orden,
            tecnico=tecnico,
            material=material_no_seriado,
            cantidad=3,
            creado_por=usuario_tenant,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        UsoMaterialOrden.objects.create(
            tenant=tenant,
            orden=orden,
            tecnico=tecnico,
            material=material_no_seriado,
            cantidad=-1,
            creado_por=usuario_tenant,
        )


@pytest.mark.django_db
def test_cierre_unico_y_estado_valido(tenant):
    CierreMensual.objects.create(tenant=tenant, periodo="2026-11")
    with pytest.raises(IntegrityError), transaction.atomic():
        CierreMensual.objects.create(tenant=tenant, periodo="2026-11")
    with pytest.raises(IntegrityError), transaction.atomic():
        CierreMensual.objects.create(
            tenant=tenant, periodo="2026-12", estado="OTRO"
        )
