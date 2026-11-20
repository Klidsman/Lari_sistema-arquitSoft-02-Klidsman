"""Integración de búsqueda de técnicos."""

import pytest

from tecnicos.models import Tecnico
from tecnicos.services import (
    buscar_tecnicos,
    obtener_datos_tecnico,
    tecnicos_para_operacion,
)


@pytest.mark.django_db
def test_busqueda_por_nif_o_nombre(tenant, usuario_tenant):
    Tecnico.objects.create(
        tenant=tenant, nif="LA1111", nombre="Carlos", creado_por=usuario_tenant
    )
    Tecnico.objects.create(
        tenant=tenant, nif="LA2222", nombre="Beatriz", creado_por=usuario_tenant
    )

    assert list(buscar_tecnicos(tenant, "LA1111").values_list("nif", flat=True)) == [
        "LA1111"
    ]
    assert list(buscar_tecnicos(tenant, "Beatriz").values_list("nif", flat=True)) == [
        "LA2222"
    ]


@pytest.mark.django_db
def test_busqueda_vacia(tenant, usuario_tenant):
    for indice in range(3):
        Tecnico.objects.create(
            tenant=tenant,
            nif=f"LA{indice:04d}",
            nombre=f"Tecnico {indice}",
            creado_por=usuario_tenant,
        )

    assert buscar_tecnicos(tenant).count() == 3
    assert list(buscar_tecnicos(tenant).values_list("nombre", flat=True)) == sorted(
        buscar_tecnicos(tenant).values_list("nombre", flat=True)
    )


@pytest.mark.django_db
def test_filtro_tenant(tenant, usuario_tenant, usuario_otro_tenant):
    Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA9999",
        nombre="Ajeno",
        creado_por=usuario_otro_tenant,
    )

    assert buscar_tecnicos(tenant, "LA9999").count() == 0


@pytest.mark.django_db
def test_filtros_de_estado(tenant, tecnico, tecnico_desactivado):
    assert list(
        buscar_tecnicos(tenant, estado="activos").values_list("nif", flat=True)
    ) == [tecnico.nif]
    assert list(
        buscar_tecnicos(tenant, estado="desactivados").values_list("nif", flat=True)
    ) == [tecnico_desactivado.nif]
    assert (
        buscar_tecnicos(tenant, solo_activos=True).filter(pk=tecnico_desactivado.pk).exists()
        is False
    )


@pytest.mark.django_db
def test_datos_para_consumidores(tecnico):
    assert obtener_datos_tecnico(tecnico) == {
        "nif": "LA1234",
        "nombre": "Juan Pérez",
        "activo": True,
    }


@pytest.mark.django_db
def test_operacion_solo_activos(tenant, tecnico, tecnico_desactivado):
    assert list(tecnicos_para_operacion(tenant).values_list("nif", flat=True)) == [
        tecnico.nif
    ]
