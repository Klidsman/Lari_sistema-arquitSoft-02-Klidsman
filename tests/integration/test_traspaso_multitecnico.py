"""Traspasos multi-técnico (1→N / N→1) y stock visible."""

import openpyxl
import pytest
from django.urls import reverse

from materiales.models import Material
from stock.models import StockTecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso
from traspasos.services import (
    EstructuraTecnicosInvalida,
    ValidacionTraspaso,
    confirmar_traspaso,
    crear_solicitud_traspaso,
    enviar_solicitud_traspaso,
    stock_tecnico_para_traspaso,
)


def _tecnico(tenant, usuario, nif, nombre):
    return Tecnico.objects.create(
        tenant=tenant,
        nif=nif,
        nombre=nombre,
        creado_por=usuario,
    )


def _material(usuario, codigo, descripcion):
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


def _linea(origen, destino, material, cantidad):
    return {
        "tecnico_origen_id": origen.pk,
        "tecnico_destino_id": destino.pk,
        "material_id": material.pk,
        "cantidad": cantidad,
    }


@pytest.mark.django_db
def test_traspaso_uno_a_varios(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    material_b = _material(usuario_tenant, "10402520501", "ONT")
    destino_b = _tecnico(tenant, usuario_tenant, "LA3001", "Destino B")
    destino_c = _tecnico(tenant, usuario_tenant, "LA3002", "Destino C")
    _stock(tenant, tecnico, material_no_seriado, 10)
    _stock(tenant, tecnico, material_b, 8)

    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [
            _linea(tecnico, destino_b, material_no_seriado, 4),
            _linea(tecnico, destino_c, material_b, 3),
        ],
        usuario_tenant,
    )
    assert solicitud.forma == "1→N"
    assert {t.nif for t in solicitud.origenes} == {tecnico.nif}
    assert {t.nif for t in solicitud.destinos} == {
        destino_b.nif,
        destino_c.nif,
    }

    enviar_solicitud_traspaso(solicitud, usuario_tenant)
    confirmar_traspaso(solicitud, usuario_almacen)

    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 6
    )
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_b
        ).cantidad
        == 5
    )
    assert (
        StockTecnico.objects.get(
            tecnico=destino_b, material=material_no_seriado
        ).cantidad
        == 4
    )
    assert (
        StockTecnico.objects.get(
            tecnico=destino_c, material=material_b
        ).cantidad
        == 3
    )


@pytest.mark.django_db
def test_traspaso_varios_a_uno(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA3003", "Origen B")
    destino = _tecnico(tenant, usuario_tenant, "LA3004", "Destino único")
    _stock(tenant, tecnico, material_no_seriado, 10)
    _stock(tenant, origen_b, material_no_seriado, 6)

    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [
            _linea(tecnico, destino, material_no_seriado, 4),
            _linea(origen_b, destino, material_no_seriado, 2),
        ],
        usuario_tenant,
    )
    assert solicitud.forma == "N→1"
    assert {t.nif for t in solicitud.destinos} == {destino.nif}

    enviar_solicitud_traspaso(solicitud, usuario_tenant)
    confirmar_traspaso(solicitud, usuario_almacen)

    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 6
    )
    assert (
        StockTecnico.objects.get(
            tecnico=origen_b, material=material_no_seriado
        ).cantidad
        == 4
    )
    assert (
        StockTecnico.objects.get(
            tecnico=destino, material=material_no_seriado
        ).cantidad
        == 6
    )


@pytest.mark.django_db
def test_varios_origenes_y_varios_destinos_se_rechaza(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA3005", "Origen B")
    destino_c = _tecnico(tenant, usuario_tenant, "LA3006", "Destino C")
    _stock(tenant, tecnico, material_no_seriado, 10)
    _stock(tenant, origen_b, material_no_seriado, 10)

    with pytest.raises(EstructuraTecnicosInvalida, match="un técnico a varios"):
        crear_solicitud_traspaso(
            tenant,
            "2026-11-21",
            [
                _linea(tecnico, origen_b, material_no_seriado, 1),
                _linea(origen_b, destino_c, material_no_seriado, 1),
            ],
            usuario_tenant,
        )


@pytest.mark.django_db
def test_linea_con_mismo_origen_y_destino_se_rechaza(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    _stock(tenant, tecnico, material_no_seriado, 10)
    with pytest.raises(ValidacionTraspaso, match="no pueden ser el mismo"):
        crear_solicitud_traspaso(
            tenant,
            "2026-11-21",
            [_linea(tecnico, tecnico, material_no_seriado, 1)],
            usuario_tenant,
        )


@pytest.mark.django_db
def test_excel_agrupa_por_tecnico_en_uno_a_varios(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    material_b = _material(usuario_tenant, "10402520502", "ONT")
    destino_b = _tecnico(tenant, usuario_tenant, "LA3007", "Destino B")
    destino_c = _tecnico(tenant, usuario_tenant, "LA3008", "Destino C")
    _stock(tenant, tecnico, material_no_seriado, 10)
    _stock(tenant, tecnico, material_b, 8)

    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [
            _linea(tecnico, destino_b, material_no_seriado, 4),
            _linea(tecnico, destino_c, material_b, 3),
        ],
        usuario_tenant,
    )
    enviar_solicitud_traspaso(solicitud, usuario_tenant)
    solicitud.refresh_from_db()

    from pathlib import Path

    from django.conf import settings

    ruta = Path(settings.MEDIA_ROOT) / solicitud.excel_ruta
    libro = openpyxl.load_workbook(ruta)
    try:
        desasignacion = libro["Desasignación"]
        asignacion = libro["Asignación"]
        valores_desasignacion = [
            celda.value
            for fila in desasignacion.iter_rows()
            for celda in fila
        ]
        valores_asignacion = [
            celda.value
            for fila in asignacion.iter_rows()
            for celda in fila
        ]
        # La hoja de desasignación repite el mismo NIF origen por cada bloque.
        assert valores_desasignacion.count(tecnico.nif) == 1
        assert destino_b.nif in valores_asignacion
        assert destino_c.nif in valores_asignacion
    finally:
        libro.close()


@pytest.mark.django_db
def test_stock_tecnico_para_traspaso_solo_lectura(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    cliente_tenant,
):
    _stock(tenant, tecnico, material_no_seriado, 7)
    material_sin_stock = _material(usuario_tenant, "10402520504", "SIN STOCK")
    _stock(tenant, tecnico, material_sin_stock, 0)

    filas = list(
        stock_tecnico_para_traspaso(tenant, tecnico)
    )
    assert len(filas) == 1
    assert filas[0].cantidad == 7

    respuesta = cliente_tenant.get(
        reverse("stock_tecnico_traspaso"), {"tecnico": tecnico.pk}
    )
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert material_no_seriado.codigo in contenido
    assert "7" in contenido


@pytest.mark.django_db
def test_stock_de_otro_tenant_no_se_expone(
    cliente_tenant,
    usuario_otro_tenant,
    tecnico_otro_tenant,
):
    respuesta = cliente_tenant.get(
        reverse("stock_tecnico_traspaso"),
        {"tecnico": tecnico_otro_tenant.pk},
    )
    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_formulario_muestra_flujo_de_tres_columnas(cliente_tenant):
    respuesta = cliente_tenant.get(reverse("nuevo_traspaso"))
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "Técnico que entrega" in contenido
    assert "Materiales en mano" in contenido
    assert "Técnicos que reciben" in contenido
    assert "Registrar traspaso" in contenido
    assert 'id="tecnicos-entrega"' in contenido
    assert 'id="materiales-panel"' in contenido
    assert 'id="resumen-recibiran"' in contenido


@pytest.mark.django_db
def test_materiales_tecnico_expone_cantidades_y_series(
    cliente_tenant,
    tenant,
    tecnico,
    material_no_seriado,
):
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
    )
    respuesta = cliente_tenant.get(
        reverse("materiales_tecnico_traspaso"), {"tecnico": tecnico.pk}
    )
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert material_no_seriado.codigo in contenido
    assert "en mano" in contenido
    assert "data-agregar-cantidad" in contenido
    assert "data-cantidad-input" in contenido


@pytest.mark.django_db
def test_materiales_tecnico_seriado_muestra_series(
    cliente_tenant,
    tenant,
    tecnico,
    material_seriado,
    usuario_tenant,
):
    from django.utils import timezone

    from series.models import EstadoSerie, Serie

    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_seriado,
        cantidad=1,
    )
    serie = Serie.objects.create(
        numero="SER000048213",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    respuesta = cliente_tenant.get(
        reverse("materiales_tecnico_traspaso"), {"tecnico": tecnico.pk}
    )
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert serie.numero in contenido
    assert "data-agregar-series" in contenido


@pytest.mark.django_db
def test_formulario_envia_lineas_por_cada_receptor(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    material_b = _material(usuario_tenant, "10402520503", "ONT")
    destino_b = _tecnico(tenant, usuario_tenant, "LA3010", "Destino B")
    destino_c = _tecnico(tenant, usuario_tenant, "LA3011", "Destino C")
    _stock(tenant, tecnico, material_no_seriado, 10)
    _stock(tenant, tecnico, material_b, 8)

    respuesta = cliente_tenant.post(
        reverse("nuevo_traspaso"),
        {
            "accion": "enviar",
            "fecha": "2026-11-21",
            "lineas-TOTAL_FORMS": "2",
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "0",
            "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-tecnico_origen_id": tecnico.pk,
            "lineas-0-tecnico_destino_id": destino_b.pk,
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": 4,
            "lineas-1-tecnico_origen_id": tecnico.pk,
            "lineas-1-tecnico_destino_id": destino_c.pk,
            "lineas-1-material_id": material_b.pk,
            "lineas-1-cantidad": 3,
        },
    )

    assert respuesta.status_code == 302
    from traspasos.models import SolicitudTraspaso

    solicitud = SolicitudTraspaso.objects.get()
    assert solicitud.estado == EstadoTraspaso.ENVIADA
    assert solicitud.forma == "1→N"
    assert {t.nif for t in solicitud.destinos} == {
        destino_b.nif,
        destino_c.nif,
    }


@pytest.mark.django_db
def test_materiales_de_otro_tenant_no_se_exponen(
    cliente_tenant, tecnico_otro_tenant
):
    respuesta = cliente_tenant.get(
        reverse("materiales_tecnico_traspaso"),
        {"tecnico": tecnico_otro_tenant.pk},
    )
    assert respuesta.status_code == 404
