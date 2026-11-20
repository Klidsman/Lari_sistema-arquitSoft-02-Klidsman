"""Lectura del Excel de conciliación."""

from io import BytesIO
from zipfile import ZipFile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from conciliaciones.excel import (
    CantidadInvalida,
    ColumnasFaltantes,
    FormatoInvalido,
    HojaGeneralAusente,
    leer_reporte,
)
from tests.reportes import archivo_xlsx, crear_xlsx


def test_lee_hoja_general_y_normaliza_encabezados():
    contenido = crear_xlsx(
        [
            ["10402520400", "L1", 5, None, "LA1234", "CABLE"],
            ["10402520323", "L1", None, "SER000000001", "LA1234", "ROSETA"],
        ]
    )
    reporte = leer_reporte(SimpleUploadedFile("reporte.xlsx", contenido))
    assert reporte.total_filas == 2
    assert reporte.filas[0].libre_utilizacion == 5
    assert reporte.filas[0].nif == "LA1234"
    assert reporte.filas[1].numero_serie == "SER000000001"
    assert reporte.filas[1].libre_utilizacion is None


def test_rechaza_extension_distinta():
    with pytest.raises(FormatoInvalido):
        leer_reporte(SimpleUploadedFile("reporte.xls", b"contenido"))


def test_rechaza_archivo_corrupto():
    with pytest.raises(FormatoInvalido):
        leer_reporte(SimpleUploadedFile("reporte.xlsx", b"no es un excel"))


def test_rechaza_sin_hoja_general():
    libro = Workbook()
    libro.active.title = "OTRA"
    buffer = BytesIO()
    libro.save(buffer)
    libro.close()
    with pytest.raises(HojaGeneralAusente):
        leer_reporte(
            SimpleUploadedFile("reporte.xlsx", buffer.getvalue())
        )


def test_rechaza_columnas_faltantes():
    contenido = crear_xlsx(
        [["10402520400", 5, "LA1234"]],
        encabezados=["Material", "Libre utilización", "Nº ident.fis.1"],
    )
    with pytest.raises(ColumnasFaltantes):
        leer_reporte(SimpleUploadedFile("reporte.xlsx", contenido))


def test_rechaza_cantidad_negativa():
    contenido = crear_xlsx(
        [["10402520400", "L1", -1, None, "LA1234", "CABLE"]]
    )
    with pytest.raises(CantidadInvalida):
        leer_reporte(SimpleUploadedFile("reporte.xlsx", contenido))


def test_zip_valido_sin_hoja_general():
    assert ZipFile(BytesIO(crear_xlsx([]))).namelist()
