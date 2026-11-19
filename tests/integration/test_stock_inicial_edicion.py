"""Edición transaccional del stock inicial."""

import pytest

from series.models import Serie
from stock.services import obtener_stock_tecnico
from stock_inicial.models import LineaStockInicial
from stock_inicial.services import (
    EdicionInvalida,
    cargar_desde_formulario,
)


@pytest.mark.django_db
def test_agregar_serie(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado
):
    carga = cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 5,
                }
            ]
        },
        usuario_tenant,
    )

    from stock_inicial.services import aplicar_edicion_stock_inicial

    aplicar_edicion_stock_inicial(
        carga,
        [
            {
                "tipo": "AGREGAR",
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "series": "ABC123456789",
            }
        ],
        usuario_tenant,
    )

    assert Serie.objects.get().estado == "ASIGNADA"
    assert obtener_stock_tecnico(tecnico, material_seriado) == 1
    assert LineaStockInicial.objects.filter(serie__isnull=False).count() == 1


@pytest.mark.django_db
def test_modificar_cantidad_no_seriada(
    usuario_tenant, tenant, tecnico, material_no_seriado
):
    carga = cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 5,
                }
            ]
        },
        usuario_tenant,
    )
    linea = LineaStockInicial.objects.get()

    from stock_inicial.services import aplicar_edicion_stock_inicial

    aplicar_edicion_stock_inicial(
        carga,
        [{"tipo": "MODIFICAR", "linea_id": linea.pk, "cantidad": "8"}],
        usuario_tenant,
    )

    linea.refresh_from_db()
    assert linea.cantidad == 8
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 8


@pytest.mark.django_db
def test_eliminar_serie(
    usuario_tenant, tenant, tecnico, material_seriado
):
    carga = cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_seriado.pk,
                    "series": "ABC123456789",
                }
            ]
        },
        usuario_tenant,
    )
    linea = LineaStockInicial.objects.get()

    from stock_inicial.services import aplicar_edicion_stock_inicial

    aplicar_edicion_stock_inicial(
        carga,
        [{"tipo": "ELIMINAR", "linea_id": linea.pk}],
        usuario_tenant,
    )

    assert not LineaStockInicial.objects.exists()
    assert not Serie.objects.exists()
    assert obtener_stock_tecnico(tecnico, material_seriado) == 0


@pytest.mark.django_db
def test_lote_vacio_es_error(
    usuario_tenant, tenant, tecnico, material_no_seriado
):
    carga = cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 5,
                }
            ]
        },
        usuario_tenant,
    )

    from stock_inicial.services import aplicar_edicion_stock_inicial

    with pytest.raises(EdicionInvalida, match="No se enviaron cambios"):
        aplicar_edicion_stock_inicial(carga, [], usuario_tenant)
