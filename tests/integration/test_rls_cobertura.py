"""Cobertura de políticas RLS en las tablas de 009–013."""

import pytest
from django.db import connection

TABLAS = [
    "traspasos_solicitudtraspaso",
    "traspasos_lineatraspaso",
    "conciliaciones_conciliacion",
    "conciliaciones_diferenciaserie",
    "conciliaciones_diferenciacantidad",
    "conciliaciones_materialnocatalogado",
    "logistica_inversa_devolucion",
    "logistica_inversa_lineadevolucion",
    "logistica_inversa_bajaequipo",
    "registro_materiales_materialhabilitado",
    "registro_materiales_saldoinicialperiodo",
    "registro_materiales_despachoalmacen",
    "registro_materiales_cargaordenes",
    "registro_materiales_ordenliquidacion",
    "registro_materiales_usomaterialorden",
    "registro_materiales_advertenciauso",
    "registro_materiales_cierremensual",
    "registro_materiales_saldomensualmaterial",
    "registro_materiales_justificacioncierre",
    "reportes_cortemensual",
]


@pytest.mark.django_db
def test_tablas_nuevas_tienen_rls_y_politica():
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename, rowsecurity
            FROM pg_tables
            WHERE schemaname = 'public' AND tablename = ANY(%s)
            """,
            [TABLAS],
        )
        estado = dict(cursor.fetchall())
        assert set(TABLAS) <= set(estado)
        assert all(estado[tabla] for tabla in TABLAS)

        cursor.execute(
            """
            SELECT tablename, COUNT(*)
            FROM pg_policies
            WHERE schemaname = 'public' AND tablename = ANY(%s)
            GROUP BY tablename
            """,
            [TABLAS],
        )
        politicas = dict(cursor.fetchall())
    assert set(TABLAS) <= set(politicas)
    assert all(politicas[tabla] >= 1 for tabla in TABLAS)
