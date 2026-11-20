"""Lectura del Excel de stock inicial."""

import hashlib
import io
from pathlib import Path

import openpyxl
from django.core.exceptions import ValidationError

COLUMNAS = {
    "material": "Material",
    "lote": "Lote",
    "libre": "Libre utilización",
    "serie": "Número de serie",
    "nif": "Nº ident.fis.1",
    "descripcion": "Texto breve material",
}


class FormatoExcelInvalido(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


def _cabecera(valor):
    return str(valor or "").strip().casefold()


def leer_excel_stock_inicial(archivo):
    nombre = Path(getattr(archivo, "name", "") or "").name
    if not nombre.lower().endswith(".xlsx"):
        raise FormatoExcelInvalido("El archivo debe ser un Excel .xlsx")

    contenido = archivo.read()
    hash_archivo = hashlib.sha256(contenido).hexdigest()

    try:
        libro = openpyxl.load_workbook(
            io.BytesIO(contenido),
            read_only=True,
            data_only=True,
        )
        hoja = libro.worksheets[0]
    except Exception as exc:
        raise FormatoExcelInvalido(
            "El archivo no se pudo leer como Excel"
        ) from exc

    filas_crudas = hoja.iter_rows(values_only=True)
    try:
        cabecera = next(filas_crudas)
    except StopIteration as exc:
        raise FormatoExcelInvalido(
            "El archivo no contiene filas de datos"
        ) from exc

    indices = {}
    for clave, titulo in COLUMNAS.items():
        buscado = titulo.strip().casefold()
        for posicion, valor in enumerate(cabecera):
            if _cabecera(valor) == buscado:
                indices[clave] = posicion
                break
        else:
            raise FormatoExcelInvalido(
                f"El archivo no tiene la columna obligatoria: {titulo}"
            )

    filas = []
    for numero, valores in enumerate(filas_crudas, start=2):
        if not any(valor not in (None, "") for valor in valores):
            continue
        fila = {"numero_fila": numero}
        for clave, posicion in indices.items():
            valor = valores[posicion] if posicion < len(valores) else None
            fila[clave] = valor
        filas.append(fila)

    libro.close()

    if not filas:
        raise FormatoExcelInvalido("El archivo no contiene filas de datos")

    return filas, nombre, hash_archivo
