"""Aislamiento por tenant y RLS de conciliaciones."""

import pytest
from django.db import connection

from conciliaciones.services import (
    NoEncontrado,
    crear_conciliacion,
    listar_conciliaciones,
    obtener_conciliacion,
)
from tests.reportes import archivo_xlsx, fila_no_seriada


@pytest.mark.django_db
def test_otro_tenant_no_ve_ni_abre_la_conciliacion(
    usuario_tenant, usuario_otro_tenant, tecnico, material_no_seriado, almacen
):
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 1)]),
    )
    ajeno = usuario_otro_tenant.tenant

    with pytest.raises(NoEncontrado):
        obtener_conciliacion(ajeno, conciliacion.pk)
    assert listar_conciliaciones(ajeno).count() == 0
    assert listar_conciliaciones(usuario_tenant.tenant).count() == 1


@pytest.mark.django_db
def test_filas_de_otro_tenant_de_la_region_se_ignoran(
    usuario_tenant,
    usuario_otro_tenant,
    material_no_seriado,
    almacen,
):
    from tecnicos.models import Tecnico

    ajeno = Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA5555",
        nombre="Técnico ajeno",
        creado_por=usuario_otro_tenant,
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_no_seriada(material_no_seriado, ajeno.nif, 1)]
        ),
    )
    assert conciliacion.diferencias_series.count() == 0
    assert conciliacion.diferencias_cantidades.count() == 0


@pytest.mark.django_db
def test_rls_activa_en_conciliaciones():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relrowsecurity FROM pg_class "
            "WHERE relname = 'conciliaciones_conciliacion'"
        )
        fila = cursor.fetchone()
    assert fila is not None
    assert fila[0] is True
