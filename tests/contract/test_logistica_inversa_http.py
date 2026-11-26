"""Contrato HTTP de logística inversa."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from logistica_inversa.models import BajaEquipo, Devolucion
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico
from tecnicos.models import Tecnico


def _serie(tenant, material, estado, usuario, tecnico=None, numero="SER000000001"):
    asignada = estado == EstadoSerie.ASIGNADA
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=estado,
        tecnico=tecnico if asignada else None,
        asignada_en=timezone.now() if asignada else None,
        creado_por=usuario,
    )


@pytest.mark.django_db
def test_flujo_http_devolucion(
    cliente_tenant,
    cliente_autenticado,
    cliente_otro_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    serie = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant, tecnico
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )

    assert cliente_tenant.get(reverse("lista_devoluciones")).status_code == 200
    assert (
        cliente_autenticado.get(reverse("lista_devoluciones")).status_code == 403
    )
    assert (
        cliente_tenant.get(reverse("nueva_devolucion")).status_code == 200
    )

    respuesta = cliente_tenant.post(
        reverse("nueva_devolucion"),
        {
            "tecnico": tecnico.pk,
            "fecha": date.today().isoformat(),
            "series": [serie.pk],
            "observaciones": "Devuelto",
        },
    )
    assert respuesta.status_code == 302
    devolucion = Devolucion.objects.get()
    detalle = reverse("detalle_devolucion", args=[devolucion.pk])
    assert cliente_tenant.get(detalle).status_code == 200
    assert cliente_otro_tenant.get(detalle).status_code == 404

    acta = reverse("acta_devolucion", args=[devolucion.pk])
    respuesta = cliente_tenant.get(acta)
    assert respuesta.status_code == 200
    assert respuesta["Content-Disposition"].endswith(
        f'acta-devolucion-{devolucion.pk}.xlsx"'
    )
    assert b"".join(respuesta.streaming_content)[:2] == b"PK"

    ruta = Path(settings.MEDIA_ROOT) / devolucion.acta_ruta
    ruta.write_bytes(ruta.read_bytes() + b"alterado")
    assert cliente_tenant.get(acta).status_code == 409


@pytest.mark.django_db
def test_fecha_futura_devuelve_400(
    cliente_tenant, tenant, tecnico, material_seriado, almacen
):
    respuesta = cliente_tenant.post(
        reverse("nueva_devolucion"),
        {
            "tecnico": tecnico.pk,
            "fecha": (date.today() + timedelta(days=1)).isoformat(),
            "series": [],
        },
    )
    assert respuesta.status_code == 400


@pytest.mark.django_db
def test_flujo_http_baja(
    cliente_tenant,
    cliente_autenticado,
    cliente_otro_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    serie = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=tecnico, numero="SER000000021",
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    assert cliente_tenant.get(reverse("lista_bajas")).status_code == 200
    assert cliente_autenticado.get(reverse("lista_bajas")).status_code == 403
    assert cliente_tenant.get(reverse("nueva_baja")).status_code == 200

    respuesta = cliente_tenant.post(
        reverse("nueva_baja"),
        {
            "tecnico": tecnico.pk,
            "series": [serie.pk],
            "causa": "AVERIA",
            "observaciones": "",
        },
    )
    assert respuesta.status_code == 302
    baja = BajaEquipo.objects.get()
    detalle = reverse("detalle_baja", args=[baja.pk])
    assert cliente_tenant.get(detalle).status_code == 200
    assert cliente_otro_tenant.get(detalle).status_code == 404

    respuesta = cliente_tenant.post(
        reverse("nueva_baja"),
        {
            "tecnico": tecnico.pk,
            "series": [serie.pk],
            "causa": "",
            "observaciones": "",
        },
    )
    assert respuesta.status_code == 400


@pytest.mark.django_db
def test_devolucion_solo_muestra_series_del_tecnico(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    otro = Tecnico.objects.create(
        tenant=tenant, nif="LA7777", nombre="Otro", creado_por=usuario_tenant
    )
    propia = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=tecnico, numero="SER000000011",
    )
    ajena = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=otro, numero="SER000000012",
    )

    respuesta = cliente_tenant.get(
        reverse("nueva_devolucion"), {"tecnico": tecnico.pk}
    )
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert propia.numero in contenido
    assert ajena.numero not in contenido
    assert material_seriado.codigo in contenido
    assert material_seriado.descripcion in contenido

    fragmento = cliente_tenant.get(
        reverse("series_tecnico_devolucion"), {"tecnico": tecnico.pk}
    )
    assert fragmento.status_code == 200
    assert propia.numero in fragmento.content.decode()
    assert ajena.numero not in fragmento.content.decode()


@pytest.mark.django_db
def test_devolucion_rechaza_serie_de_otro_tecnico(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    otro = Tecnico.objects.create(
        tenant=tenant, nif="LA7778", nombre="Otro", creado_por=usuario_tenant
    )
    ajena = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=otro, numero="SER000000013",
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )

    respuesta = cliente_tenant.post(
        reverse("nueva_devolucion"),
        {
            "tecnico": tecnico.pk,
            "fecha": date.today().isoformat(),
            "series": [ajena.pk],
            "observaciones": "",
        },
    )

    assert respuesta.status_code == 400
    assert not Devolucion.objects.exists()
    ajena.refresh_from_db()
    assert ajena.estado == EstadoSerie.ASIGNADA
    assert ajena.tecnico_id == otro.pk


@pytest.mark.django_db
def test_baja_solo_muestra_series_del_tecnico(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    otro = Tecnico.objects.create(
        tenant=tenant, nif="LA7779", nombre="Otro", creado_por=usuario_tenant
    )
    propia = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=tecnico, numero="SER000000033",
    )
    ajena = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=otro, numero="SER000000034",
    )

    respuesta = cliente_tenant.get(
        reverse("nueva_baja"), {"tecnico": tecnico.pk}
    )
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert propia.numero in contenido
    assert ajena.numero not in contenido
    assert material_seriado.codigo in contenido
    assert material_seriado.descripcion in contenido


@pytest.mark.django_db
def test_baja_rechaza_serie_de_otro_tecnico(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    otro = Tecnico.objects.create(
        tenant=tenant, nif="LA7780", nombre="Otro", creado_por=usuario_tenant
    )
    ajena = _serie(
        tenant, material_seriado, EstadoSerie.ASIGNADA, usuario_tenant,
        tecnico=otro, numero="SER000000035",
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )

    respuesta = cliente_tenant.post(
        reverse("nueva_baja"),
        {
            "tecnico": tecnico.pk,
            "series": [ajena.pk],
            "causa": "AVERIA",
            "observaciones": "",
        },
    )

    assert respuesta.status_code == 400
    assert not BajaEquipo.objects.exists()
    ajena.refresh_from_db()
    assert ajena.estado == EstadoSerie.ASIGNADA
    assert ajena.tecnico_id == otro.pk
