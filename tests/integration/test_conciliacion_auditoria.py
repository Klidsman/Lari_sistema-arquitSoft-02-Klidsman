"""Auditoría de la carga y los ajustes de conciliación."""

import pytest

from auditoria.models import RegistroCambio
from conciliaciones.services import aprobar_conciliacion, crear_conciliacion
from tests.reportes import archivo_xlsx, fila_no_seriada, fila_seriada


@pytest.mark.django_db
def test_auditoria_de_la_carga(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_no_seriada(material_no_seriado, tecnico.nif, 3)]
        ),
    )

    alta = RegistroCambio.objects.get(
        entidad="Conciliacion",
        entidad_id=conciliacion.pk,
        campo="alta",
    )
    assert conciliacion.hash_sha256 in alta.valor_nuevo
    assert conciliacion.archivo_nombre in alta.valor_nuevo
    assert alta.usuario_id == usuario_tenant.pk
    assert alta.tenant_id == tenant.pk

    archivo = RegistroCambio.objects.get(
        entidad="Conciliacion",
        entidad_id=conciliacion.pk,
        campo="archivo",
    )
    assert archivo.valor_nuevo == conciliacion.archivo_ruta
    assert not archivo.valor_nuevo.startswith("/")
    assert "\x00" not in archivo.valor_nuevo


@pytest.mark.django_db
def test_auditoria_de_ajustes_de_series_y_stock(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado, almacen
):
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_seriada(material_seriado, tecnico.nif, "ABC123456789"),
                fila_no_seriada(material_no_seriado, tecnico.nif, 2),
            ]
        ),
    )
    aprobar_conciliacion(conciliacion, usuario_tenant)

    serie_alta = RegistroCambio.objects.filter(
        entidad="Serie", campo="alta"
    )
    assert serie_alta.exists()
    stock = RegistroCambio.objects.filter(
        entidad="StockTecnico", campo="cantidad"
    ).order_by("id")
    assert stock.exists()
    ultimo = stock.last()
    assert ultimo.valor_anterior != ultimo.valor_nuevo
