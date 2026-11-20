"""Lectura del reporte de Lari para la conciliación."""

import unicodedata
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from zipfile import BadZipFile


class FormatoInvalido(Exception):
    mensaje = "El archivo debe ser un Excel .xlsx válido"

    def __str__(self):
        return self.mensaje


class HojaGeneralAusente(Exception):
    mensaje = "El archivo no contiene la hoja GENERAL"

    def __str__(self):
        return self.mensaje


class ColumnasFaltantes(Exception):
    mensaje = "Faltan columnas requeridas en la hoja GENERAL"

    def __str__(self):
        return self.mensaje


class CantidadInvalida(Exception):
    mensaje = (
        "La cantidad no seriada debe ser un entero mayor o igual a 0"
    )

    def __str__(self):
        return self.mensaje


@dataclass(frozen=True)
class FilaReporte:
    material_codigo: str
    lote: str
    libre_utilizacion: int | None
    numero_serie: str | None
    nif: str
    descripcion: str
    fila: int


@dataclass(frozen=True)
class ReporteLeido:
    filas: list
    columnas: list
    total_filas: int
    errores: list = field(default_factory=list)


COLUMNAS = {
    "material": "material",
    "lote": "lote",
    "libre utilizacion": "libre",
    "numero de serie": "serie",
    "no ident fis 1": "nif",
    "texto breve material": "descripcion",
}


def _normalizar_encabezado(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().replace(".", " ")
    return " ".join(texto.split())


def _texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def _entero(valor):
    if valor in (None, ""):
        return 0
    if isinstance(valor, bool):
        raise CantidadInvalida
    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, float) and valor.is_integer():
        numero = int(valor)
    else:
        texto = str(valor).strip()
        if not texto.isdigit():
            raise CantidadInvalida
        numero = int(texto)
    if numero < 0:
        raise CantidadInvalida
    return numero


def leer_reporte(archivo):
    nombre = getattr(archivo, "name", "") or ""
    if Path(nombre).suffix.lower() != ".xlsx":
        raise FormatoInvalido
    contenido = archivo.read()
    if isinstance(contenido, str):
        contenido = contenido.encode()
    if not contenido:
        raise FormatoInvalido

    try:
        libro = openpyxl.load_workbook(
            BytesIO(contenido), read_only=True, data_only=True
        )
    except (InvalidFileException, BadZipFile, KeyError, OSError, ValueError):
        raise FormatoInvalido

    try:
        if "GENERAL" not in libro.sheetnames:
            raise HojaGeneralAusente
        hoja = libro["GENERAL"]
        filas_crudas = hoja.iter_rows(values_only=True)
        try:
            encabezados = next(filas_crudas)
        except StopIteration:
            raise ColumnasFaltantes

        indices = {}
        columnas = []
        for posicion, encabezado in enumerate(encabezados):
            normalizado = _normalizar_encabezado(encabezado)
            columnas.append(normalizado)
            if normalizado in COLUMNAS:
                indices[COLUMNAS[normalizado]] = posicion
        if set(COLUMNAS.values()) - set(indices):
            raise ColumnasFaltantes

        filas = []
        for numero, valores in enumerate(filas_crudas, start=2):
            if not any(valor not in (None, "") for valor in valores):
                continue
            material = _texto(valores[indices["material"]])
            if not material:
                continue
            serie = _texto(valores[indices["serie"]]).upper() or None
            libre = None
            if serie is None:
                libre = _entero(valores[indices["libre"]])
            filas.append(
                FilaReporte(
                    material_codigo=material,
                    lote=_texto(valores[indices["lote"]]),
                    libre_utilizacion=libre,
                    numero_serie=serie,
                    nif=_texto(valores[indices["nif"]]).upper(),
                    descripcion=_texto(valores[indices["descripcion"]]),
                    fila=numero,
                )
            )
    finally:
        libro.close()

    return ReporteLeido(
        filas=filas,
        columnas=columnas,
        total_filas=len(filas),
    )
