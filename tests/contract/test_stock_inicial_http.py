"""Contrato HTTP de stock inicial."""

import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from stock_inicial.models import CargaStockInicial
from stock_inicial.services import cargar_desde_formulario


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


@pytest.mark.django_db
def test_estado_sin_carga(cliente_tenant):
    respuesta = cliente_tenant.get(reverse("estado_stock_inicial"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "se carga una sola vez" in contenido
    assert "formulario" in contenido.lower()


@pytest.mark.django_db
def test_admin_y_almacen_403(cliente_autenticado, cliente_almacen):
    for cliente in (cliente_autenticado, cliente_almacen):
        respuesta = cliente.get(reverse("estado_stock_inicial"))
        assert respuesta.status_code == 403
        assert "No tienes permiso para cargar stock inicial" in respuesta.content.decode()


@pytest.mark.django_db
def test_carga_por_formulario_http(
    cliente_tenant, tenant, tecnico, material_no_seriado
):
    respuesta = cliente_tenant.post(
        reverse("formulario_stock_inicial"),
        {
            "lineas-TOTAL_FORMS": "1",
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "0",
            "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-tecnico_id": tecnico.pk,
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": "7",
        },
    )

    assert respuesta.status_code == 302
    carga = CargaStockInicial.objects.get()
    assert respuesta.url == reverse("detalle_stock_inicial", args=[carga.pk])
    tenant.refresh_from_db()
    assert tenant.stock_inicial_cargado is True


@pytest.mark.django_db
def test_detalle_y_aislamiento(
    cliente_tenant, cliente_otro_tenant, usuario_tenant, tenant, tecnico, material_no_seriado
):
    carga = cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 2,
                }
            ]
        },
        usuario_tenant,
    )

    respuesta = cliente_tenant.get(
        reverse("detalle_stock_inicial", args=[carga.pk])
    )
    assert respuesta.status_code == 200
    assert tecnico.nif in respuesta.content.decode()

    respuesta = cliente_otro_tenant.get(
        reverse("detalle_stock_inicial", args=[carga.pk])
    )
    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_validar_excel_http(
    cliente_tenant, tecnico, material_no_seriado
):
    archivo = _excel(
        [[material_no_seriado.codigo, "", 5, "", tecnico.nif, ""]]
    )

    respuesta = cliente_tenant.post(
        reverse("validar_excel_stock_inicial"),
        {"archivo": archivo},
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert 'data-valido="true"' in contenido
    assert 'data-total-cantidad="5"' in contenido
    assert not CargaStockInicial.objects.exists()


@pytest.mark.django_db
def test_cargar_excel_y_segunda_carga(
    cliente_tenant, tenant, tecnico, material_no_seriado
):
    def archivo():
        return _excel(
            [[material_no_seriado.codigo, "", 5, "", tecnico.nif, ""]]
        )

    respuesta = cliente_tenant.post(
        reverse("cargar_excel_stock_inicial"),
        {"archivo": archivo()},
    )
    assert respuesta.status_code == 302
    tenant.refresh_from_db()
    assert tenant.stock_inicial_cargado is True

    respuesta = cliente_tenant.post(
        reverse("cargar_excel_stock_inicial"),
        {"archivo": archivo()},
    )
    assert respuesta.status_code == 409
    assert "El stock inicial ya fue cargado" in respuesta.content.decode()


@pytest.mark.django_db
def test_metodos_no_permitidos(cliente_tenant):
    respuesta = cliente_tenant.delete(reverse("estado_stock_inicial"))
    assert respuesta.status_code == 405
