"""Utilidades de prueba para generar reportes de Lari."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

ENCABEZADOS = [
    "Material",
    "Lote",
    "Libre utilización",
    "Número de serie",
    "Nº ident.fis.1",
    "Texto breve material",
]


def crear_xlsx(filas, encabezados=None):
    libro = Workbook()
    hoja = libro.active
    hoja.title = "GENERAL"
    hoja.append(encabezados or ENCABEZADOS)
    for fila in filas:
        hoja.append(fila)
    buffer = BytesIO()
    libro.save(buffer)
    libro.close()
    return buffer.getvalue()


def archivo_xlsx(filas, nombre="reporte.xlsx", encabezados=None):
    return SimpleUploadedFile(
        nombre,
        crear_xlsx(filas, encabezados),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


def fila_no_seriada(material, nif, cantidad, lote="", descripcion=""):
    return [
        material.codigo,
        lote or material.lote,
        cantidad,
        None,
        nif,
        descripcion or material.descripcion,
    ]


def fila_seriada(material, nif, numero, lote="", descripcion=""):
    return [
        material.codigo,
        lote or material.lote,
        None,
        numero,
        nif,
        descripcion or material.descripcion,
    ]
