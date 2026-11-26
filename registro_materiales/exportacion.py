"""Exportación del registro de materiales."""

import csv
from dataclasses import dataclass
from io import BytesIO, StringIO

import openpyxl

from .models import UsoMaterialOrden
from .services import dashboard_mensual, validar_periodo


@dataclass(frozen=True)
class ArchivoReporte:
    nombre: str
    contenido: bytes
    content_type: str


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV = "text/csv; charset=utf-8"


def _xlsx(nombre, encabezados, filas):
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = nombre
    hoja.append(encabezados)
    for fila in filas:
        hoja.append(fila)
    buffer = BytesIO()
    libro.save(buffer)
    libro.close()
    return ArchivoReporte(
        nombre=f"{nombre}.xlsx", contenido=buffer.getvalue(), content_type=XLSX
    )


def _csv(nombre, encabezados, filas):
    buffer = StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return ArchivoReporte(
        nombre=f"{nombre}.csv",
        contenido=buffer.getvalue().encode("utf-8-sig"),
        content_type=CSV,
    )


def _salida(nombre, encabezados, filas, formato):
    if formato not in ("xlsx", "csv"):
        raise ValueError("El formato debe ser xlsx o csv")
    if formato == "xlsx":
        return _xlsx(nombre, encabezados, filas)
    return _csv(nombre, encabezados, filas)


def exportar_reporte_mensual(tenant, periodo, formato):
    validar_periodo(periodo)
    datos = dashboard_mensual(tenant, periodo)
    filas = [
        [
            periodo,
            fila["material"].codigo,
            fila["material"].descripcion,
            fila["inicial"],
            fila["asignaciones_confirmadas"],
            fila["usado"],
            fila["final"],
        ]
        for fila in datos["filas"]
    ]
    return _salida(
        f"reporte-{periodo}",
        [
            "Periodo",
            "Código",
            "Descripción",
            "Inicial",
            "Asignaciones confirmadas",
            "Usado",
            "Final",
        ],
        filas,
        formato,
    )


def exportar_detalle_ordenes(tenant, periodo, formato):
    validar_periodo(periodo)
    usos = (
        UsoMaterialOrden.objects.filter(
            tenant=tenant, orden__periodo=periodo, cantidad__gt=0
        )
        .select_related("tecnico", "orden", "material")
        .order_by("tecnico__nif", "orden__numero_normalizado", "material__codigo")
    )
    filas = [
        [
            uso.tecnico.nif,
            uso.orden.numero_normalizado,
            (
                uso.orden.fecha_instalacion.isoformat()
                if uso.orden.fecha_instalacion
                else ""
            ),
            uso.material.codigo,
            uso.material.descripcion,
            uso.cantidad,
        ]
        for uso in usos
    ]
    return _salida(
        f"ordenes-{periodo}",
        ["Técnico", "Orden", "Fecha", "Material", "Descripción", "Cantidad"],
        filas,
        formato,
    )
