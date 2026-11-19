"""Excel de traspaso entre técnicos."""

import hashlib
import uuid
from pathlib import Path

import openpyxl
from django.conf import settings


def _escribir_hoja(hoja, movimiento, tecnico, solicitud):
    hoja.append(["Movimiento", movimiento])
    hoja.append(["Centro", solicitud.region.almacen.centro])
    hoja.append(["Almacén", solicitud.region.almacen.codigo_almacen])
    hoja.append(["NIF", tecnico.nif])
    hoja.append(["Fecha", solicitud.fecha.isoformat()])
    hoja.append(["Tenant", solicitud.tenant.codigo])
    hoja.append(["Región", solicitud.region.codigo])
    hoja.append(["ID de traspaso", solicitud.pk])
    hoja.append([])

    lineas = list(solicitud.lineas.select_related("material", "serie"))

    hoja.append(["Seriales"])
    hoja.append(["Código", "Descripción", "Lote", "Serie", "Cantidad"])
    for linea in lineas:
        if not linea.serie_id:
            continue
        hoja.append(
            [
                linea.material.codigo,
                linea.material.descripcion,
                linea.lote,
                linea.serie.numero,
                1,
            ]
        )

    hoja.append([])
    hoja.append(["Material menor"])
    hoja.append(["Código", "Descripción", "Lote", "Cantidad"])
    totales = {}
    for linea in lineas:
        if linea.serie_id:
            continue
        clave = linea.material_id
        if clave not in totales:
            totales[clave] = {
                "codigo": linea.material.codigo,
                "descripcion": linea.material.descripcion,
                "lote": linea.lote,
                "cantidad": 0,
            }
        totales[clave]["cantidad"] += linea.cantidad
    for datos in totales.values():
        hoja.append(
            [datos["codigo"], datos["descripcion"], datos["lote"], datos["cantidad"]]
        )


def generar_excel_traspaso(solicitud):
    libro = openpyxl.Workbook()
    desasignacion = libro.active
    desasignacion.title = "Desasignación"
    asignacion = libro.create_sheet("Asignación")

    _escribir_hoja(desasignacion, "Z32", solicitud.tecnico_origen, solicitud)
    _escribir_hoja(asignacion, "Z31", solicitud.tecnico_destino, solicitud)

    nombre = f"{uuid.uuid4().hex}.xlsx"
    relativa = (
        Path(settings.TRASPASOS_EXCEL_DIR)
        / solicitud.tenant.codigo
        / str(solicitud.pk)
        / nombre
    )
    absoluta = Path(settings.MEDIA_ROOT) / relativa
    absoluta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(absoluta)
    libro.close()

    hash_archivo = hashlib.sha256(absoluta.read_bytes()).hexdigest()
    return str(relativa).replace("\\", "/"), hash_archivo
