"""Rendimiento de la carga de conciliaciones."""

import time

import pytest

from conciliaciones.models import EstadoConciliacion
from conciliaciones.services import crear_conciliacion
from tests.reportes import archivo_xlsx, fila_no_seriada


@pytest.mark.django_db
def test_reporte_de_mil_filas_en_menos_de_diez_segundos(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    filas = [
        fila_no_seriada(material_no_seriado, tecnico.nif, 1)
        for _ in range(1000)
    ]
    archivo = archivo_xlsx(filas)

    inicio = time.perf_counter()
    conciliacion = crear_conciliacion(usuario_tenant, archivo)
    duracion = time.perf_counter() - inicio

    assert conciliacion.estado == EstadoConciliacion.EN_REVISION
    assert conciliacion.diferencias_cantidades.count() == 1
    assert duracion < 10
