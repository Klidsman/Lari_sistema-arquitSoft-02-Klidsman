"""Generación del Excel de asignación."""

import hashlib
import uuid
from pathlib import Path

import openpyxl
from django.conf import settings
from django.utils import timezone

ENCABEZADOS = [
    "Movimiento",
    "Centro",
    "Almacén",
    "Material",
    "Descripcion de materiales",
    "Cantidad",
    "NIF Técnico",
    "Lote",
    "Serie",
]


class ExcelAsignacionInvalido(Exception):
    def __init__(self, mensaje="No se pudo generar el Excel de asignación"):
        super().__init__(mensaje)

    def __str__(self):
        return self.args[0]


def generar_excel_solicitud(solicitud):
    region = solicitud.region
    almacen = getattr(region, "almacen", None)
    if almacen is None or not almacen.centro or not almacen.codigo_almacen:
        raise ExcelAsignacionInvalido()

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Asignacion"
    hoja.append(ENCABEZADOS)

    lineas = solicitud.lineas.select_related("material", "serie", "tecnico").order_by("id")
    for linea in lineas:
        hoja.append(
            [
                settings.MOVIMIENTO_ASIGNACION,
                almacen.centro,
                almacen.codigo_almacen,
                linea.material.codigo,
                linea.material.descripcion,
                linea.cantidad,
                linea.tecnico.nif,
                linea.lote,
                linea.serie.numero if linea.serie else "",
            ]
        )

    nombre = f"{uuid.uuid4().hex}.xlsx"
    relativa = (
        Path(settings.ASIGNACIONES_EXCEL_DIR)
        / solicitud.tenant.codigo
        / str(solicitud.pk)
        / nombre
    )
    absoluta = Path(settings.MEDIA_ROOT) / relativa
    absoluta.parent.mkdir(parents=True, exist_ok=True)

    try:
        libro.save(absoluta)
    except Exception as exc:
        raise ExcelAsignacionInvalido() from exc
    finally:
        libro.close()

    contenido = absoluta.read_bytes()
    hash_archivo = hashlib.sha256(contenido).hexdigest()

    return str(relativa).replace("\\", "/"), hash_archivo, timezone.now()
