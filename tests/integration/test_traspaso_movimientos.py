"""Saldos por movimientos, idempotencia y cadenas de traspasos."""

from datetime import date

import pytest
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from acceso.models import Rol, Usuario
from materiales.models import Material
from series.models import EstadoSerie, Serie
from stock.models import (
    MovimientoTecnico,
    StockTecnico,
    TipoMovimientoTecnico,
)
from stock.services import obtener_stock_tecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso, SolicitudTraspaso
from traspasos.services import (
    ValidacionTraspaso,
    confirmar_traspaso,
    crear_solicitud_traspaso,
    enviar_solicitud_traspaso,
)


def _tecnico(tenant, usuario, nif, nombre):
    return Tecnico.objects.create(
        tenant=tenant,
        nif=nif,
        nombre=nombre,
        creado_por=usuario,
    )


def _material(usuario, codigo, descripcion="Material"):
    return Material.objects.create(
        codigo=codigo,
        descripcion=descripcion,
        lote="",
        es_seriado=False,
        creado_por=usuario,
    )


def _stock(tenant, tecnico, material, cantidad):
    return StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material,
        cantidad=cantidad,
    )


def _traspaso(tenant, actor, origen, destino, material, cantidad):
    solicitud = crear_solicitud_traspaso(
        tenant,
        date.today(),
        [
            {
                "tecnico_origen_id": origen.pk,
                "tecnico_destino_id": destino.pk,
                "material_id": material.pk,
                "cantidad": cantidad,
            }
        ],
        actor,
    )
    enviar_solicitud_traspaso(solicitud, actor)
    return solicitud


@pytest.mark.django_db
def test_dos_origenes_al_mismo_destino_suman_cinco(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA4001", "Origen B")
    destino = _tecnico(tenant, usuario_tenant, "LA4002", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 2)
    _stock(tenant, origen_b, material_no_seriado, 3)
    _stock(tenant, destino, material_no_seriado, 0)

    for origen, cantidad in ((tecnico, 2), (origen_b, 3)):
        solicitud = _traspaso(
            tenant,
            usuario_tenant,
            origen,
            destino,
            material_no_seriado,
            cantidad,
        )
        confirmar_traspaso(solicitud, usuario_almacen)

    assert obtener_stock_tecnico(destino, material_no_seriado) == 5
    assert (
        MovimientoTecnico.objects.filter(
            tecnico=destino,
            material=material_no_seriado,
            tipo=TipoMovimientoTecnico.TRASPASO_ENTRADA,
        ).aggregate(total=Sum("cantidad"))["total"]
        == 5
    )


@pytest.mark.django_db
def test_cadena_uno_dos_y_dos_uno(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    tecnico_dos = _tecnico(tenant, usuario_tenant, "LA4003", "Técnico 2")
    _stock(tenant, tecnico, material_no_seriado, 2)
    _stock(tenant, tecnico_dos, material_no_seriado, 0)

    primera = _traspaso(
        tenant,
        usuario_tenant,
        tecnico,
        tecnico_dos,
        material_no_seriado,
        2,
    )
    confirmar_traspaso(primera, usuario_almacen)
    segunda = _traspaso(
        tenant,
        usuario_tenant,
        tecnico_dos,
        tecnico,
        material_no_seriado,
        1,
    )
    confirmar_traspaso(segunda, usuario_almacen)

    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 1
    assert obtener_stock_tecnico(tecnico_dos, material_no_seriado) == 1


@pytest.mark.django_db
def test_cadena_uno_dos_tres_uno(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    dos = _tecnico(tenant, usuario_tenant, "LA4004", "Técnico 2")
    tres = _tecnico(tenant, usuario_tenant, "LA4005", "Técnico 3")
    _stock(tenant, tecnico, material_no_seriado, 3)
    _stock(tenant, dos, material_no_seriado, 0)
    _stock(tenant, tres, material_no_seriado, 0)

    for origen, destino, cantidad in (
        (tecnico, dos, 3),
        (dos, tres, 2),
        (tres, tecnico, 1),
    ):
        solicitud = _traspaso(
            tenant,
            usuario_tenant,
            origen,
            destino,
            material_no_seriado,
            cantidad,
        )
        confirmar_traspaso(solicitud, usuario_almacen)

    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 1
    assert obtener_stock_tecnico(dos, material_no_seriado) == 1
    assert obtener_stock_tecnico(tres, material_no_seriado) == 1


@pytest.mark.django_db
def test_serie_movida_una_vez_no_aparece_en_dos_tecnicos(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA4006", "Destino")
    _stock(tenant, tecnico, material_seriado, 1)
    _stock(tenant, destino, material_seriado, 0)
    serie = Serie.objects.create(
        numero="SER000040001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )

    solicitud = crear_solicitud_traspaso(
        tenant,
        date.today(),
        [
            {
                "tecnico_origen_id": tecnico.pk,
                "tecnico_destino_id": destino.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie.pk],
            }
        ],
        usuario_tenant,
    )
    enviar_solicitud_traspaso(solicitud, usuario_tenant)
    confirmar_traspaso(solicitud, usuario_almacen)

    serie.refresh_from_db()
    assert serie.tecnico_id == destino.pk
    assert Serie.objects.filter(pk=serie.pk).count() == 1


@pytest.mark.django_db
def test_traspaso_mayor_al_saldo_no_cambia_nada(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA4007", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 2)

    with pytest.raises(ValidacionTraspaso, match="supera el stock"):
        crear_solicitud_traspaso(
            tenant,
            date.today(),
            [
                {
                    "tecnico_origen_id": tecnico.pk,
                    "tecnico_destino_id": destino.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 3,
                }
            ],
            usuario_tenant,
        )

    assert SolicitudTraspaso.objects.filter(tenant=tenant).count() == 0
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 2
    assert MovimientoTecnico.objects.count() == 0


@pytest.mark.django_db
def test_doble_clic_no_duplica_el_traspaso(
    cliente_tenant,
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA4008", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 10)
    _stock(tenant, destino, material_no_seriado, 0)
    datos = {
        "accion": "enviar",
        "fecha": "2026-11-21",
        "clave_idempotencia": "clave-fija-001",
        "lineas-TOTAL_FORMS": "1",
        "lineas-INITIAL_FORMS": "0",
        "lineas-MIN_NUM_FORMS": "0",
        "lineas-MAX_NUM_FORMS": "1000",
        "lineas-0-tecnico_origen_id": tecnico.pk,
        "lineas-0-tecnico_destino_id": destino.pk,
        "lineas-0-material_id": material_no_seriado.pk,
        "lineas-0-cantidad": 2,
    }

    primera = cliente_tenant.post(reverse("nuevo_traspaso"), datos)
    segunda = cliente_tenant.post(reverse("nuevo_traspaso"), datos)

    assert primera.status_code == 302
    assert segunda.status_code == 302
    solicitudes = SolicitudTraspaso.objects.filter(tenant=tenant)
    assert solicitudes.count() == 1
    solicitud = solicitudes.get()
    assert solicitud.estado == EstadoTraspaso.ENVIADA
    assert solicitud.lineas.count() == 1

    confirmar_traspaso(solicitud, usuario_almacen)
    assert obtener_stock_tecnico(destino, material_no_seriado) == 2


@pytest.mark.django_db
def test_envio_fallido_no_deja_borrador(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    monkeypatch,
):
    from traspasos import services

    destino = _tecnico(tenant, usuario_tenant, "LA4009", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 10)

    def fallar(*args, **kwargs):
        raise ValidacionTraspaso("Fallo forzado del envío")

    monkeypatch.setattr(services, "enviar_solicitud_traspaso", fallar)
    respuesta = cliente_tenant.post(
        reverse("nuevo_traspaso"),
        {
            "accion": "enviar",
            "fecha": "2026-11-21",
            "clave_idempotencia": "clave-fallo-001",
            "lineas-TOTAL_FORMS": "1",
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "0",
            "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-tecnico_origen_id": tecnico.pk,
            "lineas-0-tecnico_destino_id": destino.pk,
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": 2,
        },
    )

    assert respuesta.status_code == 400
    assert SolicitudTraspaso.objects.filter(tenant=tenant).count() == 0
    assert MovimientoTecnico.objects.count() == 0


@pytest.mark.django_db
def test_saldo_historico_sin_movimientos_crea_asiento_inicial(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    _stock(tenant, tecnico, material_no_seriado, 10)
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 10

    from stock.services import decrementar_stock_tecnico

    nuevo = decrementar_stock_tecnico(
        tecnico, material_no_seriado, 4, usuario_tenant
    )
    assert nuevo == 6
    tipos = set(
        MovimientoTecnico.objects.filter(
            tecnico=tecnico, material=material_no_seriado
        ).values_list("tipo", "cantidad")
    )
    assert tipos == {
        (TipoMovimientoTecnico.SALDO_INICIAL.value, 10),
        (TipoMovimientoTecnico.AJUSTE.value, -4),
    }
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 6
