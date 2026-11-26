"""Contrato HTTP del registro de materiales."""

import pytest
from django.urls import reverse
from django.utils import timezone

from registro_materiales.models import (
    MaterialHabilitado,
    OrdenLiquidacion,
    UsoMaterialSerie,
)
from registro_materiales.services import (
    obtener_o_crear_orden,
    registrar_saldo_inicial,
)
from series.models import EstadoSerie, Serie
from stock.models import StockTecnico
from tecnicos.models import Tecnico

PERIODO = "2026-11"


@pytest.mark.django_db
def test_menu_y_permisos(cliente_tenant, cliente_autenticado):
    assert (
        cliente_tenant.get(reverse("menu_registro_materiales")).status_code
        == 200
    )
    assert (
        cliente_autenticado.get(
            reverse("menu_registro_materiales")
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_flujo_http_carga_materiales_y_exportacion(
    cliente_tenant,
    cliente_otro_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    MaterialHabilitado.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        creado_por=usuario_tenant,
    )
    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 10, usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad=10,
    )

    assert cliente_tenant.get(reverse("cargar_ordenes")).status_code == 200
    respuesta = cliente_tenant.post(
        reverse("preview_carga_ordenes"),
        {"tecnico": tecnico.pk, "periodo": PERIODO, "texto": "A1\nB2"},
    )
    assert respuesta.status_code == 200
    assert "Nuevas: 2" in respuesta.content.decode()

    respuesta = cliente_tenant.post(
        reverse("cargar_ordenes"),
        {"tecnico": tecnico.pk, "periodo": PERIODO, "texto": "A1\nB2"},
    )
    assert respuesta.status_code == 302
    assert OrdenLiquidacion.objects.count() == 2

    otro = Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Otro técnico",
        creado_por=usuario_tenant,
    )
    OrdenLiquidacion.objects.create(
        tenant=tenant,
        tecnico=otro,
        numero_original="OTRA1",
        numero_normalizado="OTRA1",
        periodo=PERIODO,
        creado_por=usuario_tenant,
    )

    listado = cliente_tenant.get(
        reverse("registrar_materiales"),
        {"tecnico": tecnico.pk, "periodo": PERIODO},
    )
    contenido_listado = listado.content.decode()
    assert listado.status_code == 200
    assert "Órdenes por cargar" in contenido_listado
    assert "A1" in contenido_listado
    assert "B2" in contenido_listado
    assert "OTRA1" not in contenido_listado
    assert "Guardar materiales" not in contenido_listado

    assert (
        cliente_tenant.get(
            reverse("ordenes_pendientes"), {"periodo": PERIODO}
        ).status_code
        == 200
    )
    assert (
        cliente_tenant.get(
            reverse("registrar_materiales"),
            {
                "tecnico": tecnico.pk,
                "periodo": PERIODO,
                "numero_orden": "A1",
            },
        ).status_code
        == 200
    )

    respuesta = cliente_tenant.post(
        reverse("guardar_materiales"),
        {
            "tecnico": tecnico.pk,
            "periodo": PERIODO,
            "numero_orden": "A1",
            "fecha_instalacion": "2026-11-10",
            f"cantidades[{material_no_seriado.pk}]": "2",
        },
    )
    assert respuesta.status_code == 302

    assert (
        cliente_tenant.get(
            reverse("entradas_materiales"), {"periodo": PERIODO}
        ).status_code
        == 200
    )
    assert (
        cliente_tenant.get(
            reverse("dashboard_materiales"), {"periodo": PERIODO}
        ).status_code
        == 200
    )
    assert (
        cliente_tenant.get(
            reverse("cierre_mensual"), {"periodo": PERIODO}
        ).status_code
        == 200
    )

    respuesta = cliente_tenant.get(
        reverse("exportar_reporte_mensual"),
        {"periodo": PERIODO, "formato": "xlsx"},
    )
    assert respuesta.status_code == 200
    assert respuesta.content[:2] == b"PK"

    respuesta = cliente_tenant.get(
        reverse("exportar_detalle_ordenes"),
        {"periodo": PERIODO, "formato": "csv"},
    )
    assert respuesta.status_code == 200
    assert b"A1" in respuesta.content

    orden = OrdenLiquidacion.objects.get(numero_normalizado="A1")
    assert (
        cliente_tenant.get(
            reverse("historial_orden", args=[orden.pk])
        ).status_code
        == 200
    )
    assert (
        cliente_otro_tenant.get(
            reverse("historial_orden", args=[orden.pk])
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_acciones_no_aceptan_get(cliente_tenant, usuario_tenant, tenant, almacen):
    for nombre in (
        "cerrar_mes",
        "reabrir_mes",
        "justificar_pendiente",
        "guardar_saldo_inicial",
        "guardar_materiales",
    ):
        assert cliente_tenant.get(reverse(nombre)).status_code == 405


@pytest.mark.django_db
def test_guardar_material_seriado_desde_http(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    MaterialHabilitado.objects.create(
        tenant=tenant,
        material=material_seriado,
        creado_por=usuario_tenant,
    )
    StockTecnico.objects.create(
        tenant=tenant,
        tecnico=tecnico,
        material=material_seriado,
        cantidad=1,
    )
    serie = Serie.objects.create(
        numero="SER000000099",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )

    respuesta = cliente_tenant.post(
        reverse("guardar_materiales"),
        {
            "tecnico": tecnico.pk,
            "periodo": PERIODO,
            "numero_orden": orden.numero_normalizado,
            "fecha_instalacion": "2026-11-10",
            f"series[{material_seriado.pk}]": str(serie.pk),
        },
    )

    assert respuesta.status_code == 302
    serie.refresh_from_db()
    assert serie.estado == EstadoSerie.INSTALADA
    assert serie.tecnico_id is None
    assert (
        StockTecnico.objects.get(
            tenant=tenant, tecnico=tecnico, material=material_seriado
        ).cantidad
        == 0
    )
    assert UsoMaterialSerie.objects.filter(uso__orden=orden).exists()


@pytest.mark.django_db
def test_catalogo_habilitado_http(
    cliente_tenant, usuario_tenant, tenant, material_no_seriado, almacen
):
    respuesta = cliente_tenant.post(
        reverse("catalogo_materiales"),
        {"material": material_no_seriado.pk, "activo": "1", "orden": "1"},
    )
    assert respuesta.status_code == 302
    assert MaterialHabilitado.objects.filter(
        tenant=tenant, material=material_no_seriado, activo=True
    ).exists()
