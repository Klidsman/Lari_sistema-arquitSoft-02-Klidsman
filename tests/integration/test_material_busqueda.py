"""Integración de búsqueda y datos del material."""

import pytest

from materiales.models import Material
from materiales.services import buscar_materiales, obtener_datos_material


@pytest.mark.django_db
def test_busqueda_por_codigo_o_descripcion(usuario_tenant):
    Material.objects.create(
        codigo="10402520279",
        descripcion="ROSETA",
        lote="FIBERHOME",
        es_seriado=True,
        creado_por=usuario_tenant,
    )
    Material.objects.create(
        codigo="10402520323",
        descripcion="CABLE",
        lote="",
        es_seriado=False,
        creado_por=usuario_tenant,
    )

    assert list(buscar_materiales("ROSETA").values_list("codigo", flat=True)) == [
        "10402520279"
    ]
    assert list(buscar_materiales("10402520323").values_list("codigo", flat=True)) == [
        "10402520323"
    ]


@pytest.mark.django_db
def test_busqueda_vacia_devuelve_todo(usuario_tenant):
    for indice in range(3):
        Material.objects.create(
            codigo=f"1{indice:010d}",
            descripcion=f"Material {indice}",
            lote="",
            es_seriado=False,
            creado_por=usuario_tenant,
        )

    assert buscar_materiales("").count() == 3
    assert list(
        buscar_materiales("").values_list("codigo", flat=True)
    ) == sorted(buscar_materiales("").values_list("codigo", flat=True))


@pytest.mark.django_db
def test_datos_para_autocompletado(material):
    assert obtener_datos_material(material) == {
        "codigo": "10402520279",
        "descripcion": "ROSETA",
        "lote": "FIBERHOME",
        "tipo": "SERIADO",
    }


@pytest.mark.django_db
def test_catalogo_global_sin_filtro_tenant(usuario_tenant, usuario_otro_tenant):
    Material.objects.create(
        codigo="10402520279",
        descripcion="DE OTRO TENANT",
        lote="",
        es_seriado=False,
        creado_por=usuario_otro_tenant,
    )

    assert buscar_materiales("OTRO").count() == 1
