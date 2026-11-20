"""Contrato de traspasos."""

from datetime import date
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from series.models import EstadoSerie
from stock.models import StockTecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso, SolicitudTraspaso
from traspasos.services import crear_borrador_traspaso, enviar_traspaso


def _datos(tecnico, destino, material, cantidad):
    return {
        "tecnico_origen": tecnico.pk,
        "tecnico_destino": destino.pk,
        "fecha": date.today().isoformat(),
        "accion": "enviar",
        "lineas-TOTAL_FORMS": "1",
        "lineas-INITIAL_FORMS": "0",
        "lineas-MIN_NUM_FORMS": "0",
        "lineas-MAX_NUM_FORMS": "1000",
        "lineas-0-material_id": material.pk,
        "lineas-0-cantidad": cantidad,
    }


@pytest.mark.django_db
def test_flujo_http_y_permisos(
    cliente_tenant,
    cliente_almacen,
    cliente_autenticado,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Destino",
        creado_por=tecnico.creado_por,
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )

    respuesta = cliente_tenant.post(
        reverse("nuevo_traspaso"),
        _datos(tecnico, destino, material_no_seriado, 4),
    )
    assert respuesta.status_code == 302
    traspaso = SolicitudTraspaso.objects.get()
    assert traspaso.estado == EstadoTraspaso.ENVIADA

    assert cliente_tenant.get(reverse("lista_traspasos")).status_code == 200
    assert cliente_tenant.get(reverse("detalle_traspaso", args=[traspaso.pk])).status_code == 200
    assert cliente_autenticado.get(reverse("lista_traspasos")).status_code == 403

    respuesta = cliente_almacen.post(
        reverse("confirmar_traspaso_almacen", args=[traspaso.pk])
    )
    assert respuesta.status_code == 302
    traspaso.refresh_from_db()
    assert traspaso.estado == EstadoTraspaso.CONFIRMADA


@pytest.mark.django_db
def test_contrato_acciones_y_aislamiento(
    cliente_tenant,
    cliente_otro_tenant,
    cliente_almacen,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Destino",
        creado_por=tecnico.creado_por,
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    traspaso.refresh_from_db()

    # Editar una solicitud enviada devuelve 409.
    assert (
        cliente_tenant.get(
            reverse("editar_traspaso", args=[traspaso.pk])
        ).status_code
        == 409
    )

    # Otro tenant no ve el traspaso.
    assert (
        cliente_otro_tenant.get(
            reverse("detalle_traspaso", args=[traspaso.pk])
        ).status_code
        == 404
    )

    # Descarga del Excel correcta y sin exponer la ruta física.
    respuesta = cliente_tenant.get(reverse("excel_traspaso", args=[traspaso.pk]))
    assert respuesta.status_code == 200
    assert respuesta["Content-Disposition"].endswith('.xlsx"')
    contenido = b"".join(respuesta.streaming_content)
    assert contenido[:2] == b"PK"

    # Las acciones del almacén no aceptan GET.
    assert (
        cliente_almacen.get(
            reverse("confirmar_traspaso_almacen", args=[traspaso.pk])
        ).status_code
        == 405
    )

    # Rechazar sin motivo devuelve 400.
    assert (
        cliente_almacen.post(
            reverse("rechazar_traspaso_almacen", args=[traspaso.pk]), {}
        ).status_code
        == 400
    )

    # Bandeja del almacén: solo el responsable de almacén.
    assert cliente_almacen.get(reverse("bandeja_traspasos")).status_code == 200
    assert cliente_tenant.get(reverse("bandeja_traspasos")).status_code == 403

    # Un Excel alterado bloquea la descarga con 409.
    ruta = Path(settings.MEDIA_ROOT) / traspaso.excel_ruta
    ruta.write_bytes(ruta.read_bytes() + b"alterado")
    assert (
        cliente_tenant.get(reverse("excel_traspaso", args=[traspaso.pk])).status_code
        == 409
    )
