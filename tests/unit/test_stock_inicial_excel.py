"""Lectura del Excel de stock inicial."""

import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from stock_inicial.excel import FormatoExcelInvalido, leer_excel_stock_inicial


def _archivo(filas, nombre="stock.xlsx"):
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
    return SimpleUploadedFile(
        nombre,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def test_leer_excel_y_hash():
    archivo = _archivo(
        [["10402520279", "X", 2, "ABC123456789", "LA1234", "ROSETA"]]
    )

    filas, nombre, hash_archivo = leer_excel_stock_inicial(archivo)

    assert nombre == "stock.xlsx"
    assert len(hash_archivo) == 64
    assert filas[0]["numero_fila"] == 2
    assert filas[0]["material"] == "10402520279"
    assert filas[0]["nif"] == "LA1234"


def test_rechaza_xls():
    archivo = SimpleUploadedFile("stock.xls", b"datos")
    with pytest.raises(FormatoExcelInvalido, match="El archivo debe ser un Excel .xlsx"):
        leer_excel_stock_inicial(archivo)


def test_columna_faltante():
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append(["Material"])
    buffer = io.BytesIO()
    libro.save(buffer)
    libro.close()
    archivo = SimpleUploadedFile("stock.xlsx", buffer.getvalue())

    with pytest.raises(
        FormatoExcelInvalido,
        match="El archivo no tiene la columna obligatoria: Lote",
    ):
        leer_excel_stock_inicial(archivo)


def test_sin_filas():
    archivo = _archivo([])
    with pytest.raises(
        FormatoExcelInvalido, match="El archivo no contiene filas de datos"
    ):
        leer_excel_stock_inicial(archivo)
