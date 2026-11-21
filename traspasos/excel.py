"""Excel de traspaso entre técnicos con el formato Z32/Z31."""

import hashlib
import uuid
from pathlib import Path

import openpyxl
from django.conf import settings
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

COLUMNAS = [
    "Movimiento",
    "Centro",
    "Almacén",
    "Material",
    "Descripción de materiales",
    "Cantidad",
    "NIF Técnico",
    "Lote",
    "Serie",
]

ANCHOS = [11, 9, 10, 17, 46, 10, 14, 20, 24]

RELLENO_CABECERA_OPERATIVA = PatternFill("solid", fgColor="1F4E79")
RELLENO_CABECERA_DATOS = PatternFill("solid", fgColor="FFC000")
RELLENO_FILA = PatternFill("solid", fgColor="D9E2F3")
BORDE = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)


def _lineas_ordenadas(solicitud):
    return solicitud.lineas.select_related(
        "material", "serie", "tecnico_origen", "tecnico_destino"
    ).order_by("material__codigo", "serie__numero", "id")


def _fila(solicitud, movimiento, tecnico, material, cantidad, lote, serie):
    return [
        movimiento,
        solicitud.region.almacen.centro,
        solicitud.region.almacen.codigo_almacen,
        material.codigo,
        material.descripcion,
        cantidad,
        tecnico.nif,
        lote,
        serie or "",
    ]


def _filas_por_tecnico(solicitud, movimiento, campo_tecnico):
    """Agrupa por técnico y material; las series quedan una por fila."""
    agrupadas = {}
    sueltas = []
    for linea in _lineas_ordenadas(solicitud):
        tecnico = getattr(linea, campo_tecnico)
        if linea.serie_id:
            clave = (
                linea.material.codigo,
                linea.serie.numero,
                tecnico.nif,
            )
            sueltas.append(
                (
                    clave,
                    _fila(
                        solicitud,
                        movimiento,
                        tecnico,
                        linea.material,
                        1,
                        linea.lote,
                        linea.serie.numero,
                    ),
                )
            )
            continue

        clave = (tecnico.pk, linea.material_id, linea.lote)
        grupo = agrupadas.setdefault(
            clave,
            {
                "orden": (
                    linea.material.codigo,
                    "",
                    tecnico.nif,
                ),
                "tecnico": tecnico,
                "material": linea.material,
                "lote": linea.lote,
                "cantidad": 0,
            },
        )
        grupo["cantidad"] += linea.cantidad

    filas = list(sueltas)
    for grupo in agrupadas.values():
        filas.append(
            (
                grupo["orden"],
                _fila(
                    solicitud,
                    movimiento,
                    grupo["tecnico"],
                    grupo["material"],
                    grupo["cantidad"],
                    grupo["lote"],
                    "",
                ),
            )
        )

    filas.sort(key=lambda par: par[0])
    return [fila for _, fila in filas]


def _filas_desasignacion(solicitud):
    return _filas_por_tecnico(solicitud, "Z32", "tecnico_origen")


def _filas_asignacion(solicitud):
    return _filas_por_tecnico(solicitud, "Z31", "tecnico_destino")


def _escribir_hoja(hoja, filas):
    hoja.append(COLUMNAS)

    for indice, titulo in enumerate(COLUMNAS, start=1):
        celda = hoja.cell(row=1, column=indice)
        celda.value = titulo
        if indice <= 3:
            celda.fill = RELLENO_CABECERA_OPERATIVA
            celda.font = Font(bold=True, color="FFFFFF")
        else:
            celda.fill = RELLENO_CABECERA_DATOS
            celda.font = Font(bold=True, color="1F2933")
        celda.alignment = Alignment(horizontal="center", vertical="center")
        celda.border = BORDE

    for datos in filas:
        hoja.append(datos)
        fila = hoja.max_row
        for indice in range(1, len(COLUMNAS) + 1):
            celda = hoja.cell(row=fila, column=indice)
            celda.fill = RELLENO_FILA
            celda.border = BORDE
            celda.alignment = Alignment(
                vertical="center",
                wrap_text=indice == 5,
            )

    for indice, ancho in enumerate(ANCHOS, start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho

    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = f"A1:I{max(hoja.max_row, 1)}"
    hoja.row_dimensions[1].height = 22


def generar_excel_traspaso(solicitud):
    libro = openpyxl.Workbook()
    desasignacion = libro.active
    desasignacion.title = "Desasignación"
    asignacion = libro.create_sheet("Asignación")

    _escribir_hoja(desasignacion, _filas_desasignacion(solicitud))
    _escribir_hoja(asignacion, _filas_asignacion(solicitud))

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
