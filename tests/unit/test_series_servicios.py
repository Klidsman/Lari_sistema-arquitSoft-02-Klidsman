"""Servicios de series y normalización."""

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from series.models import EstadoSerie, Serie
from series.services import (
    SerieInvalida,
    crear_serie,
    extraer_numeros,
    normalizar_numero,
    series_existentes,
    validar_numero,
)
from tecnicos.models import Tecnico


def test_normalizacion_idempotente():
    assert normalizar_numero(" abc 123456789 ") == "ABC123456789"
    assert normalizar_numero("ABC123456789") == "ABC123456789"


def test_formatos_invalidos():
    for numero in ("ABC123", "ABC12345678", "ABC1234567890", "ABC-12345678"):
        with pytest.raises(
            SerieInvalida, match="La serie debe tener 12 caracteres alfanuméricos"
        ):
            validar_numero(numero)


def test_validar_numero_valido():
    assert validar_numero("abc123456789") == "ABC123456789"


def test_extraer_numeros_de_una_fila_con_guiones():
    texto = (
        "7493DA33A8E0 - 2C9682081050 - 7493DA526E40 -\n"
        "7493DA527310 - 2CEADC372510 - 2C96820D47A8-\n"
        "2C96820506D8 - CCEDDC71E958- 2C968256F088-\n"
        "CCD4A1378650 - CCEDDCC25C60"
    )

    assert extraer_numeros(texto) == [
        "7493DA33A8E0",
        "2C9682081050",
        "7493DA526E40",
        "7493DA527310",
        "2CEADC372510",
        "2C96820D47A8",
        "2C96820506D8",
        "CCEDDC71E958",
        "2C968256F088",
        "CCD4A1378650",
        "CCEDDCC25C60",
    ]


def test_extraer_numeros_conserva_invalidos():
    assert extraer_numeros("ABC-12345678") == ["ABC-12345678"]
    assert extraer_numeros("ABC1234567890") == ["ABC1234567890"]
    assert extraer_numeros("abc 123456789") == ["abc 123456789"]


@pytest.mark.django_db
def test_series_existentes_global(serie_existente, tenant, usuario_otro_tenant):
    Serie.objects.create(
        numero="XYZ987654321",
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        material=serie_existente.material,
        creado_por=usuario_otro_tenant,
    )

    assert series_existentes(["ABC123456789", "XYZ987654321", "NUEVA1234567"]) == {
        "ABC123456789",
        "XYZ987654321",
    }


@pytest.mark.django_db
def test_crear_serie_disponible_por_defecto(
    tenant, material_seriado, usuario_tenant
):
    serie = crear_serie(
        tenant,
        tenant.region,
        material_seriado,
        " nueva1234567 ",
        material_seriado.lote,
        usuario_tenant,
    )

    assert serie.numero == "NUEVA1234567"
    assert serie.estado == EstadoSerie.DISPONIBLE
    assert serie.tecnico is None
    assert serie.asignada_en is None


@pytest.mark.django_db
def test_crear_serie_asignada(tenant, material_seriado, usuario_tenant):
    tecnico = Tecnico.objects.create(
        tenant=tenant,
        nif="LA1234",
        nombre="Juan",
        creado_por=usuario_tenant,
    )
    asignada_en = timezone.now()

    serie = crear_serie(
        tenant,
        tenant.region,
        material_seriado,
        "ASIG12345678",
        "",
        usuario_tenant,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=asignada_en,
    )

    assert serie.estado == EstadoSerie.ASIGNADA
    assert serie.tecnico_id == tecnico.pk
    assert serie.asignada_en == asignada_en


@pytest.mark.django_db
def test_crear_serie_incoherente(tenant, material_seriado, usuario_tenant):
    with pytest.raises(SerieInvalida):
        crear_serie(
            tenant,
            tenant.region,
            material_seriado,
            "ASIG12345678",
            "",
            usuario_tenant,
            estado=EstadoSerie.ASIGNADA,
        )


@pytest.mark.django_db
def test_integrity_error_no_se_captura(
    tenant, material_seriado, usuario_tenant, serie_existente
):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            crear_serie(
                tenant,
                tenant.region,
                material_seriado,
                serie_existente.numero,
                "",
                usuario_tenant,
            )
