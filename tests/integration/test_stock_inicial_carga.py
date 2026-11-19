"""Carga y validación de stock inicial."""

import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from auditoria.models import RegistroCambio
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral
from stock.services import obtener_stock_tecnico
from stock_inicial.models import CargaStockInicial, LineaStockInicial
from stock_inicial.services import (
    StockInicialYaCargado,
    cargar_desde_excel,
    cargar_desde_formulario,
    validar_filas_stock_inicial,
    validar_formulario_stock_inicial,
)


def _excel(filas):
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append(
        [
            "Material",
            "Lote",
            "Libre utilización",
            "Número de serie",
            "Nº ident.fis.1",
            "Texto breve material",
        ]
    )
    for fila in filas:
        hoja.append(fila)
    buffer = io.BytesIO()
    libro.save(buffer)
    libro.close()
    return SimpleUploadedFile("stock.xlsx", buffer.getvalue())


@pytest.mark.django_db
def test_carga_excel_exitosa(
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
):
    archivo = _excel(
        [
            [
                material_seriado.codigo,
                "IGNORADO",
                99,
                "ABC123456789",
                tecnico.nif,
                "IGNORADA",
            ],
            [
                material_no_seriado.codigo,
                "",
                10,
                "",
                tecnico.nif,
                "",
            ],
        ]
    )

    carga = cargar_desde_excel(tenant, archivo, usuario_tenant)

    tenant.refresh_from_db()
    assert tenant.stock_inicial_cargado is True
    assert tenant.fecha_stock_inicial is not None
    assert CargaStockInicial.objects.count() == 1
    assert LineaStockInicial.objects.count() == 2
    assert Serie.objects.get().estado == EstadoSerie.ASIGNADA
    assert Serie.objects.get().tecnico_id == tecnico.pk
    assert obtener_stock_tecnico(tecnico, material_seriado) == 1
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 10
    assert not StockGeneral.objects.exists()
    assert carga.archivo_nombre == "stock.xlsx"
    assert len(carga.archivo_hash) == 64
    assert RegistroCambio.objects.filter(
        entidad="CargaStockInicial", campo="alta"
    ).exists()


@pytest.mark.django_db
def test_segunda_carga_rechazada(
    usuario_tenant, tenant, tecnico, material_no_seriado
):
    cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 3,
                }
            ]
        },
        usuario_tenant,
    )

    with pytest.raises(
        StockInicialYaCargado,
        match="El stock inicial ya fue cargado para este tenant",
    ):
        cargar_desde_formulario(
            tenant,
            {
                "lineas": [
                    {
                        "tecnico_id": tecnico.pk,
                        "material_id": material_no_seriado.pk,
                        "cantidad": 1,
                    }
                ]
            },
            usuario_tenant,
        )


@pytest.mark.django_db
def test_carga_formulario(
    usuario_tenant, tenant, tecnico, material_no_seriado
):
    carga = cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 7,
                }
            ]
        },
        usuario_tenant,
    )

    assert carga.metodo == CargaStockInicial.METODO_FORMULARIO
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 7
    assert not Serie.objects.exists()


@pytest.mark.django_db
def test_errores_no_escriben(
    tenant, tecnico, material_seriado, material_no_seriado
):
    filas = [
        {
            "numero_fila": 2,
            "material": material_seriado.codigo,
            "serie": "ABC123",
            "nif": tecnico.nif,
            "libre": "",
        },
        {
            "numero_fila": 3,
            "material": "NOEXISTE",
            "serie": "",
            "nif": tecnico.nif,
            "libre": 1,
        },
        {
            "numero_fila": 4,
            "material": material_no_seriado.codigo,
            "serie": "",
            "nif": "LA9999",
            "libre": 1,
        },
    ]

    resultado = validar_filas_stock_inicial(tenant, filas)

    assert resultado.valido is False
    assert len(resultado.errores) == 3
    assert not CargaStockInicial.objects.exists()
    assert not Serie.objects.exists()
    assert not LineaStockInicial.objects.exists()


@pytest.mark.django_db
def test_serie_duplicada_y_existente(
    tenant, tecnico, material_seriado, serie_existente
):
    filas = [
        {
            "numero_fila": 2,
            "material": material_seriado.codigo,
            "serie": "ABC123456789",
            "nif": tecnico.nif,
            "libre": "",
        },
        {
            "numero_fila": 3,
            "material": material_seriado.codigo,
            "serie": "ABC123456789",
            "nif": tecnico.nif,
            "libre": "",
        },
        {
            "numero_fila": 4,
            "material": material_seriado.codigo,
            "serie": serie_existente.numero,
            "nif": tecnico.nif,
            "libre": "",
        },
    ]

    resultado = validar_filas_stock_inicial(tenant, filas)
    mensajes = [error.mensaje for error in resultado.errores]

    assert "La serie está duplicada en la carga" in mensajes
    assert "La serie ya está registrada en el sistema" in mensajes


@pytest.mark.django_db
def test_formulario_series_separadas(
    tenant, tecnico, material_seriado
):
    resultado = validar_formulario_stock_inicial(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_seriado.pk,
                    "series": "ABC123456789, DEF123456789",
                }
            ]
        },
    )

    assert resultado.valido is True
    assert len(resultado.lineas) == 2
    assert {linea.serie for linea in resultado.lineas} == {
        "ABC123456789",
        "DEF123456789",
    }
