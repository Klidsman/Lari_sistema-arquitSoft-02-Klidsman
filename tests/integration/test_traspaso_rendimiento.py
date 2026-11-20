"""Rendimiento de la confirmación de traspasos."""

import time
from datetime import date

import pytest
from django.utils import timezone

from series.models import EstadoSerie, Serie
from stock.models import StockTecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso
from traspasos.services import (
    confirmar_traspaso,
    crear_borrador_traspaso,
    enviar_traspaso,
)


@pytest.mark.django_db
def test_traspaso_de_cien_series_en_menos_de_diez_segundos(
    usuario_tenant, usuario_almacen, tenant, tecnico, material_seriado, almacen
):
    destino = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Destino",
        creado_por=usuario_tenant,
    )
    ahora = timezone.now()
    series = Serie.objects.bulk_create(
        [
            Serie(
                numero=f"P{indice:011d}",
                tenant=tenant,
                region=tenant.region,
                material=material_seriado,
                lote=material_seriado.lote,
                estado=EstadoSerie.ASIGNADA,
                tecnico=tecnico,
                asignada_en=ahora,
                creado_por=usuario_tenant,
            )
            for indice in range(100)
        ]
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=100
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=destino, material=material_seriado, cantidad=0
    )

    inicio = time.perf_counter()
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [
            {
                "material_id": material_seriado.pk,
                "serie_ids": [serie.pk for serie in series],
            }
        ],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    confirmar_traspaso(traspaso, usuario_almacen)
    duracion = time.perf_counter() - inicio

    traspaso.refresh_from_db()
    assert traspaso.estado == EstadoTraspaso.CONFIRMADA
    assert (
        StockTecnico.objects.get(
            tecnico=destino, material=material_seriado
        ).cantidad
        == 100
    )
    assert duracion < 10
