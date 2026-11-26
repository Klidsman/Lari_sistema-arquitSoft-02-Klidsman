"""Descarga segura del acta de devolución."""

from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from logistica_inversa.services import (
    ArchivoNoDisponible,
    registrar_devolucion,
    verificar_hash_acta,
)
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _devolucion(usuario_tenant, tenant, tecnico, material):
    serie = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material, cantidad=0
    )
    return registrar_devolucion(
        tenant,
        tecnico,
        timezone.localdate(),
        [serie],
        "",
        usuario_tenant,
    )


@pytest.mark.django_db
def test_acta_ausente_devuelve_404(
    cliente_tenant, usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    devolucion = _devolucion(
        usuario_tenant, tenant, tecnico, material_seriado
    )
    ruta = Path(settings.MEDIA_ROOT) / devolucion.acta_ruta
    ruta.unlink()

    respuesta = cliente_tenant.get(
        reverse("acta_devolucion", args=[devolucion.pk])
    )
    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_acta_no_expone_rutas_fuera_del_directorio(
    cliente_tenant, usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    devolucion = _devolucion(
        usuario_tenant, tenant, tecnico, material_seriado
    )
    devolucion.acta_ruta = "../fuera.xlsx"
    devolucion.save(update_fields=["acta_ruta"])

    with pytest.raises(ArchivoNoDisponible):
        verificar_hash_acta(devolucion)
    respuesta = cliente_tenant.get(
        reverse("acta_devolucion", args=[devolucion.pk])
    )
    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_acta_solo_acepta_get(
    cliente_tenant, usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    devolucion = _devolucion(
        usuario_tenant, tenant, tecnico, material_seriado
    )
    url = reverse("acta_devolucion", args=[devolucion.pk])
    assert cliente_tenant.post(url).status_code == 405


@pytest.mark.django_db
def test_acta_de_otro_tenant_devuelve_404(
    cliente_otro_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    devolucion = _devolucion(
        usuario_tenant, tenant, tecnico, material_seriado
    )
    respuesta = cliente_otro_tenant.get(
        reverse("acta_devolucion", args=[devolucion.pk])
    )
    assert respuesta.status_code == 404
