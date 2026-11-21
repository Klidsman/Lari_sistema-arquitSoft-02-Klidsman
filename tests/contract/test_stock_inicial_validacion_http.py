"""Contrato de validación y carga de Excel de stock inicial."""

import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from stock_inicial.models import CargaStockInicial


def _excel(filas):
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
    return SimpleUploadedFile("stock.xlsx", buffer.getvalue())


def _validar(cliente, filas):
    return cliente.post(
        reverse("validar_excel_stock_inicial"),
        {"archivo": _excel(filas)},
    )


@pytest.mark.django_db
def test_validacion_valida_muestra_resumen_y_totales(
    cliente_tenant, tecnico, material_no_seriado
):
    respuesta = _validar(
        cliente_tenant,
        [[material_no_seriado.codigo, "", 5, "", tecnico.nif, ""]],
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert 'data-valido="true"' in contenido
    assert 'data-filas-error="0"' in contenido
    assert 'data-total-cantidad="5"' in contenido
    assert "El archivo es válido y se puede cargar" in contenido
    assert not CargaStockInicial.objects.exists()


@pytest.mark.django_db
def test_validacion_material_inexistente_indica_fila_campo_y_mensaje(
    cliente_tenant, tecnico
):
    respuesta = _validar(
        cliente_tenant,
        [["99999999999", "", 1, "", tecnico.nif, ""]],
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert 'data-valido="false"' in contenido
    assert 'data-filas-error="1"' in contenido
    assert 'data-fila="2"' in contenido
    assert 'data-campo="material"' in contenido
    assert 'data-mensaje="El material no existe en el catálogo"' in contenido
    assert "El archivo tiene 1 fila" in contenido
    assert "99999999999" not in contenido


@pytest.mark.django_db
def test_validacion_varios_errores_cuenta_filas_no_errores(
    cliente_tenant, tecnico
):
    respuesta = _validar(
        cliente_tenant,
        [
            ["99999999999", "", 1, "", tecnico.nif, ""],
            ["88888888888", "", 1, "", tecnico.nif, ""],
        ],
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert 'data-filas-error="2"' in contenido
    assert contenido.count('data-campo="material"') == 2
    assert "El archivo tiene 2 filas" in contenido


@pytest.mark.django_db
def test_validacion_errores_de_tipo_serie_y_cantidad(
    cliente_tenant, tecnico, material_seriado, material_no_seriado
):
    respuesta = _validar(
        cliente_tenant,
        [
            [material_seriado.codigo, "", "", "", tecnico.nif, ""],
            [material_no_seriado.codigo, "", "", "ABC123456789", tecnico.nif, ""],
            [material_no_seriado.codigo, "", 0, "", tecnico.nif, ""],
        ],
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert contenido.count('data-campo="tipo"') == 2
    assert 'data-campo="cantidad"' in contenido
    assert "El material es seriado y requiere número de serie" in contenido
    assert "El material no es seriado y no admite número de serie" in contenido
    assert "La cantidad debe ser mayor a 0" in contenido


@pytest.mark.django_db
def test_validacion_archivo_ausente_indica_error_de_archivo(cliente_tenant):
    respuesta = cliente_tenant.post(reverse("validar_excel_stock_inicial"), {})

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 400
    assert 'data-fila="0"' in contenido
    assert 'data-campo="archivo"' in contenido
    assert "Debes seleccionar un archivo Excel" in contenido


@pytest.mark.django_db
def test_cargar_excel_invalido_devuelve_tabla_de_errores(
    cliente_tenant, tecnico
):
    respuesta = cliente_tenant.post(
        reverse("cargar_excel_stock_inicial"),
        {"archivo": _excel([["99999999999", "", 1, "", tecnico.nif, ""]])},
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 400
    assert 'data-valido="false"' in contenido
    assert 'data-fila="2"' in contenido
    assert 'data-campo="material"' in contenido
    assert 'data-mensaje="El material no existe en el catálogo"' in contenido
    assert 'id="resultado-validacion"' in contenido
    assert "Cargar stock inicial" in contenido
    assert not CargaStockInicial.objects.exists()


@pytest.mark.django_db
def test_cargar_archivo_no_xlsx_muestra_pagina_con_error(cliente_tenant):
    respuesta = cliente_tenant.post(
        reverse("cargar_excel_stock_inicial"),
        {"archivo": SimpleUploadedFile("stock.xls", b"no-es-excel")},
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 400
    assert "El archivo debe ser un Excel .xlsx" in contenido
    assert "Cargar stock inicial" in contenido


@pytest.mark.django_db
def test_estado_incluye_htmx(cliente_tenant):
    respuesta = cliente_tenant.get(reverse("estado_stock_inicial"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "htmx.min.js" in contenido
    assert 'hx-post="' in contenido
    assert 'id="resultado-validacion"' in contenido
    assert 'id="boton-cargar-stock" disabled' in contenido
