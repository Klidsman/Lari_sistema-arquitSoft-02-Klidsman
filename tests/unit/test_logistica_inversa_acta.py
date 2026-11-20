"""Acta de devolución."""

from pathlib import Path

import openpyxl
import pytest
from django.conf import settings
from django.utils import timezone

from logistica_inversa.models import Devolucion, LineaDevolucion
from logistica_inversa.services import (
    HashNoCoincide,
    registrar_devolucion,
    verificar_hash_acta,
)
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _serie(tenant, material, tecnico, numero, usuario):
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario,
    )


@pytest.mark.django_db
def test_acta_una_hoja_y_tabla(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    devolucion = registrar_devolucion(
        tenant, tecnico, timezone.localdate(), [serie], "", usuario_tenant
    )
    ruta = Path(settings.MEDIA_ROOT) / devolucion.acta_ruta
    libro = openpyxl.load_workbook(ruta)
    try:
        assert libro.sheetnames == ["Devolución"]
        hoja = libro["Devolución"]
        assert hoja["A1"].value == "Tenant"
        assert hoja["B1"].value == tenant.codigo
        assert hoja["A2"].value == "Región"
        assert hoja["A4"].value == "ID de devolución"
        assert hoja["B4"].value == devolucion.pk
        assert hoja["A6"].value == "NIF"
        assert hoja["A7"].value == tecnico.nif
        assert hoja["B7"].value == material_seriado.codigo
        assert hoja["D7"].value == "SER000000001"
        assert hoja["E7"].value == devolucion.fecha.isoformat()
        assert len(devolucion.acta_hash) == 64
    finally:
        libro.close()


@pytest.mark.django_db
def test_hash_alterado_bloquea_descarga(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    devolucion = registrar_devolucion(
        tenant, tecnico, timezone.localdate(), [serie], "", usuario_tenant
    )
    ruta = Path(settings.MEDIA_ROOT) / devolucion.acta_ruta
    contenido = ruta.read_bytes()
    ruta.write_bytes(contenido + b"alterado")
    with pytest.raises(HashNoCoincide):
        verificar_hash_acta(devolucion)
