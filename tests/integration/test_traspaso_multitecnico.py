"""Traspasos multi-técnico (1→N / N→1) y stock visible."""

import openpyxl
import pytest
from django.urls import reverse

from materiales.models import Material
from stock.models import StockTecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso
from traspasos.services import (
    ValidacionTraspaso,
    actualizar_lineas_borrador,
    calcular_disponible,
    cancelar_traspaso,
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
def test_tecnico_puede_entregar_y_recibir_materiales(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA3005", "Origen B")
    _stock(tenant, tecnico, material_no_seriado, 5)
    _stock(tenant, origen_b, material_no_seriado, 5)

    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [
            _linea(tecnico, origen_b, material_no_seriado, 2),
            _linea(origen_b, tecnico, material_no_seriado, 1),
        ],
        usuario_tenant,
    )
    assert solicitud.forma == "MIXTA"

    enviar_solicitud_traspaso(solicitud, usuario_tenant)
    confirmar_traspaso(solicitud, usuario_almacen)

    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 4
    )
    assert (
        StockTecnico.objects.get(
            tecnico=origen_b, material=material_no_seriado
        ).cantidad
        == 6
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
        nifs_desasignacion = [
            desasignacion.cell(fila, 7).value
            for fila in range(2, desasignacion.max_row + 1)
        ]
        nifs_asignacion = [
            asignacion.cell(fila, 7).value
            for fila in range(2, asignacion.max_row + 1)
        ]
        assert nifs_desasignacion.count(tecnico.nif) == 2
        assert set(nifs_asignacion) == {destino_b.nif, destino_c.nif}
        assert desasignacion["A2"].value == "Z32"
        assert asignacion["A2"].value == "Z31"
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
    assert filas[0].disponible == 7
    assert filas[0].stock == 7

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
    assert "data-stock-texto" in contenido
    assert "data-accion-cantidad" in contenido


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
    assert "data-serie-id" in contenido
    assert "data-series-count" in contenido


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
def test_editar_borrador_precarga_el_carrito(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA3012", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 10)
    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [_linea(tecnico, destino, material_no_seriado, 4)],
        usuario_tenant,
    )

    respuesta = cliente_tenant.get(
        reverse("editar_traspaso", args=[solicitud.pk])
    )
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "Guardar cambios" in contenido

    import json
    import re

    coincidencia = re.search(
        r'<script id="datos-iniciales" type="application/json">(.*?)</script>',
        contenido,
        re.S,
    )
    assert coincidencia is not None
    datos = json.loads(coincidencia.group(1))
    assert datos["origen"] == tecnico.pk
    assert datos["destinos"] == [destino.pk]
    assert datos["items"][0]["materialId"] == str(material_no_seriado.pk)
    assert datos["items"][0]["cantidad"] == 4
    assert datos["items"][0]["origenId"] == str(tecnico.pk)
    assert datos["items"][0]["origenNif"] == tecnico.nif
    assert datos["bloqueado"] is False


@pytest.mark.django_db
def test_editar_borrador_n_a_uno_precarga_varios_origenes(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA3016", "Origen B")
    destino = _tecnico(tenant, usuario_tenant, "LA3017", "Destino")
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

    respuesta = cliente_tenant.get(
        reverse("editar_traspaso", args=[solicitud.pk])
    )
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert "Guardar cambios" in contenido

    import json
    import re

    coincidencia = re.search(
        r'<script id="datos-iniciales" type="application/json">(.*?)</script>',
        contenido,
        re.S,
    )
    datos = json.loads(coincidencia.group(1))
    assert datos["bloqueado"] is False
    assert datos["destinos"] == [destino.pk]
    assert {item["origenId"] for item in datos["items"]} == {
        str(tecnico.pk),
        str(origen_b.pk),
    }


@pytest.mark.django_db
def test_enviar_revalida_stock_actual(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA3013", "Destino")
    fila = _stock(tenant, tecnico, material_no_seriado, 10)
    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [_linea(tecnico, destino, material_no_seriado, 4)],
        usuario_tenant,
    )
    fila.cantidad = 2
    fila.save(update_fields=["cantidad"])

    with pytest.raises(ValidacionTraspaso, match="supera el stock"):
        enviar_solicitud_traspaso(solicitud, usuario_tenant)


@pytest.mark.django_db
def test_enviar_revalida_serie_en_el_origen(
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    from django.utils import timezone

    from series.models import EstadoSerie, Serie

    destino = _tecnico(tenant, usuario_tenant, "LA3014", "Destino")
    otro = _tecnico(tenant, usuario_tenant, "LA3015", "Otro")
    serie = Serie.objects.create(
        numero="SER000099999",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    _stock(tenant, tecnico, material_seriado, 1)
    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
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
    serie.tecnico = otro
    serie.save(update_fields=["tecnico"])

    with pytest.raises(ValidacionTraspaso, match="no está asignada"):
        enviar_solicitud_traspaso(solicitud, usuario_tenant)


@pytest.mark.django_db
def test_materiales_de_otro_tenant_no_se_exponen(
    cliente_tenant, tecnico_otro_tenant
):
    respuesta = cliente_tenant.get(
        reverse("materiales_tecnico_traspaso"),
        {"tecnico": tecnico_otro_tenant.pk},
    )
    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_borrador_descuenta_stock_disponible_y_lo_muestra(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA3020", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 10)
    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [_linea(tecnico, destino, material_no_seriado, 4)],
        usuario_tenant,
    )

    assert calcular_disponible(tecnico, material_no_seriado) == 6
    filas = list(stock_tecnico_para_traspaso(tenant, tecnico))
    assert filas[0].stock == 10
    assert filas[0].reservado == 4
    assert filas[0].disponible == 6

    respuesta = cliente_tenant.get(
        reverse("materiales_tecnico_traspaso"), {"tecnico": tecnico.pk}
    )
    assert "6 disponible de 10 en mano" in respuesta.content.decode()

    cancelar_traspaso(solicitud, usuario_tenant)
    assert calcular_disponible(tecnico, material_no_seriado) == 10


@pytest.mark.django_db
def test_editar_borrador_no_descuenta_su_propia_reserva(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA3021", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 10)
    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [_linea(tecnico, destino, material_no_seriado, 4)],
        usuario_tenant,
    )

    actualizar_lineas_borrador(
        solicitud,
        "2026-11-21",
        [_linea(tecnico, destino, material_no_seriado, 4)],
        usuario_tenant,
    )
    assert calcular_disponible(tecnico, material_no_seriado) == 6


@pytest.mark.django_db
def test_dos_origenes_mismo_material_suman_en_el_destino(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA3022", "Origen B")
    destino = _tecnico(tenant, usuario_tenant, "LA3023", "Destino único")
    _stock(tenant, tecnico, material_no_seriado, 2)
    _stock(tenant, origen_b, material_no_seriado, 2)

    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [
            _linea(tecnico, destino, material_no_seriado, 2),
            _linea(origen_b, destino, material_no_seriado, 2),
        ],
        usuario_tenant,
    )
    enviar_solicitud_traspaso(solicitud, usuario_tenant)
    confirmar_traspaso(solicitud, usuario_almacen)

    assert (
        StockTecnico.objects.get(
            tecnico=destino, material=material_no_seriado
        ).cantidad
        == 4
    )
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 0
    )
    assert (
        StockTecnico.objects.get(
            tecnico=origen_b, material=material_no_seriado
        ).cantidad
        == 0
    )


@pytest.mark.django_db
def test_excel_asignacion_suma_mismo_material_de_varios_origenes(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA3024", "Origen B")
    destino = _tecnico(tenant, usuario_tenant, "LA3025", "Destino único")
    _stock(tenant, tecnico, material_no_seriado, 2)
    _stock(tenant, origen_b, material_no_seriado, 2)
    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [
            _linea(tecnico, destino, material_no_seriado, 2),
            _linea(origen_b, destino, material_no_seriado, 2),
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

        filas_desasignacion = [
            (
                desasignacion.cell(fila, 6).value,
                desasignacion.cell(fila, 7).value,
            )
            for fila in range(2, desasignacion.max_row + 1)
        ]
        assert filas_desasignacion == [(2, tecnico.nif), (2, origen_b.nif)]

        filas_asignacion = [
            (
                asignacion.cell(fila, 4).value,
                asignacion.cell(fila, 6).value,
                asignacion.cell(fila, 7).value,
            )
            for fila in range(2, asignacion.max_row + 1)
        ]
        assert filas_asignacion == [
            (material_no_seriado.codigo, 4, destino.nif)
        ]
    finally:
        libro.close()


@pytest.mark.django_db
def test_excel_desasignacion_agrupa_mismo_material_para_varios_destinos(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino_b = _tecnico(tenant, usuario_tenant, "LA3026", "Destino B")
    destino_c = _tecnico(tenant, usuario_tenant, "LA3027", "Destino C")
    _stock(tenant, tecnico, material_no_seriado, 4)
    solicitud = crear_solicitud_traspaso(
        tenant,
        "2026-11-21",
        [
            _linea(tecnico, destino_b, material_no_seriado, 2),
            _linea(tecnico, destino_c, material_no_seriado, 2),
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

        filas_desasignacion = [
            (
                desasignacion.cell(fila, 4).value,
                desasignacion.cell(fila, 6).value,
                desasignacion.cell(fila, 7).value,
            )
            for fila in range(2, desasignacion.max_row + 1)
        ]
        assert filas_desasignacion == [
            (material_no_seriado.codigo, 4, tecnico.nif)
        ]

        filas_asignacion = [
            (
                asignacion.cell(fila, 6).value,
                asignacion.cell(fila, 7).value,
            )
            for fila in range(2, asignacion.max_row + 1)
        ]
        assert sorted(filas_asignacion) == [
            (2, destino_b.nif),
            (2, destino_c.nif),
        ]
    finally:
        libro.close()


@pytest.mark.django_db
def test_formulario_registra_varios_materiales_y_origenes(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    origen_b = _tecnico(tenant, usuario_tenant, "LA3030", "Origen B")
    destino_c = _tecnico(tenant, usuario_tenant, "LA3031", "Destino C")
    material_b = _material(usuario_tenant, "10402520600", "ONT")
    _stock(tenant, tecnico, material_no_seriado, 10)
    _stock(tenant, origen_b, material_b, 10)

    respuesta = cliente_tenant.post(
        reverse("nuevo_traspaso"),
        {
            "accion": "enviar",
            "fecha": "2026-11-21",
            "lineas-TOTAL_FORMS": "4",
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "0",
            "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-tecnico_origen_id": tecnico.pk,
            "lineas-0-tecnico_destino_id": origen_b.pk,
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": 2,
            "lineas-1-tecnico_origen_id": tecnico.pk,
            "lineas-1-tecnico_destino_id": destino_c.pk,
            "lineas-1-material_id": material_no_seriado.pk,
            "lineas-1-cantidad": 2,
            "lineas-2-tecnico_origen_id": origen_b.pk,
            "lineas-2-tecnico_destino_id": tecnico.pk,
            "lineas-2-material_id": material_b.pk,
            "lineas-2-cantidad": 1,
            "lineas-3-tecnico_origen_id": origen_b.pk,
            "lineas-3-tecnico_destino_id": destino_c.pk,
            "lineas-3-material_id": material_b.pk,
            "lineas-3-cantidad": 1,
        },
    )

    assert respuesta.status_code == 302
    from traspasos.models import SolicitudTraspaso

    solicitud = SolicitudTraspaso.objects.get()
    assert solicitud.forma == "MIXTA"
    assert solicitud.lineas.count() == 4
    assert {linea.material_id for linea in solicitud.lineas.all()} == {
        material_no_seriado.pk,
        material_b.pk,
    }


@pytest.mark.django_db
def test_error_de_validacion_conserva_el_carrito(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    destino = _tecnico(tenant, usuario_tenant, "LA3032", "Destino")
    _stock(tenant, tecnico, material_no_seriado, 10)

    respuesta = cliente_tenant.post(
        reverse("nuevo_traspaso"),
        {
            "accion": "enviar",
            "fecha": "2026-11-21",
            "lineas-TOTAL_FORMS": "1",
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "0",
            "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-tecnico_origen_id": tecnico.pk,
            "lineas-0-tecnico_destino_id": destino.pk,
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": 99,
        },
    )

    assert respuesta.status_code == 400
    contenido = respuesta.content.decode()
    assert "supera el stock" in contenido

    import json
    import re

    coincidencia = re.search(
        r'<script id="datos-iniciales" type="application/json">(.*?)</script>',
        contenido,
        re.S,
    )
    assert coincidencia is not None
    datos = json.loads(coincidencia.group(1))
    assert datos["origen"] == tecnico.pk
    assert datos["destinos"] == [destino.pk]
    assert datos["items"][0]["materialId"] == str(material_no_seriado.pk)
    assert datos["items"][0]["cantidad"] == 99
