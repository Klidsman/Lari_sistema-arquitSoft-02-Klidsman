"""Acta de devolución en Excel."""

import hashlib
import uuid
from pathlib import Path

import openpyxl
from django.conf import settings
from django.utils import timezone


def generar_acta(devolucion):
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Devolución"

    hoja.append(["Tenant", devolucion.tenant.codigo])
    hoja.append(["Región", devolucion.region.codigo])
    hoja.append(
        ["Fecha de generación", timezone.now().isoformat(timespec="seconds")]
    )
    hoja.append(["ID de devolución", devolucion.pk])
    hoja.append([])
    hoja.append(
        ["NIF", "Material", "Descripción", "Serie", "Fecha de devolución"]
    )
    lineas = devolucion.lineas.select_related(
        "material", "serie"
    ).order_by("serie__numero")
    for linea in lineas:
        hoja.append(
            [
                devolucion.tecnico.nif,
                linea.material.codigo,
                linea.descripcion,
                linea.serie.numero,
                devolucion.fecha.isoformat(),
            ]
        )

    nombre = f"{uuid.uuid4().hex}.xlsx"
    relativa = (
        Path(settings.ACTAS_DIR)
        / str(devolucion.tenant_id)
        / f"devolucion-{devolucion.pk}-{nombre}"
    )
    absoluta = Path(settings.MEDIA_ROOT) / relativa
    absoluta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(absoluta)
    libro.close()

    hash_archivo = hashlib.sha256(absoluta.read_bytes()).hexdigest()
    return str(relativa).replace("\\", "/"), hash_archivo
