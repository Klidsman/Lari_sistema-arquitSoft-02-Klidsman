"""Contrato de detalle, acciones e históricos del almacén."""

from datetime import date
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from asignaciones import almacen_services
from asignaciones.models import EstadoSolicitud
from asignaciones.services import crear_y_enviar_solicitud
from stock.models import StockGeneral


def _solicitud(usuario_tenant, tenant, tecnico, material, serie):
    StockGeneral.objects.create(
        tenant=tenant, material=material, cantidad=100
    )
    return crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material.pk,
                "serie_ids": [serie.pk],
            }
        ],
        usuario_tenant,
    )


@pytest.mark.django_db
def test_detalle_previsualizacion_y_descarga(
    cliente_almacen,
    cliente_tenant,
    cliente_autenticado,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    detalle = reverse("detalle_almacen", args=[solicitud.pk])
    assert cliente_almacen.get(detalle).status_code == 200
    assert cliente_tenant.get(detalle).status_code == 403
    assert cliente_autenticado.get(detalle).status_code == 403

    preview = reverse("previsualizar_almacen", args=[solicitud.pk])
    respuesta = cliente_almacen.get(preview)
    assert respuesta.status_code == 200
    assert "<html" not in respuesta.content.decode().lower()

    descarga = reverse("descargar_excel_almacen", args=[solicitud.pk])
    respuesta = cliente_almacen.get(descarga)
    assert respuesta.status_code == 200
    assert "private" in respuesta["Cache-Control"]
    assert "no-store" in respuesta["Cache-Control"]
    assert (
        f'filename="asignacion-{solicitud.pk}.xlsx"'
        in respuesta["Content-Disposition"]
    )


@pytest.mark.django_db
def test_descarga_hash_alterado_y_archivo_ausente(
    cliente_almacen,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    descarga = reverse("descargar_excel_almacen", args=[solicitud.pk])
    ruta = Path(settings.MEDIA_ROOT) / solicitud.excel_ruta
    contenido = ruta.read_bytes()
    ruta.write_bytes(contenido + b"alterado")
    assert cliente_almacen.get(descarga).status_code == 409

    solicitud.excel_ruta = "asignaciones/inexistente.xlsx"
    solicitud.save(update_fields=["excel_ruta"])
    assert cliente_almacen.get(descarga).status_code == 404


@pytest.mark.django_db
def test_detalle_de_otra_region_devuelve_404(
    usuario_admin,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    cliente_almacen,
):
    from acceso.models import Rol, Usuario
    from tenants.models import Almacen, Region

    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    otra = Region.objects.create(
        codigo="ARE", nombre="Arequipa", creado_por=usuario_admin
    )
    Almacen.objects.create(
        region=otra,
        centro="PR01",
        codigo_almacen="BE01",
        buzon="almacen.are@lari.local",
        creado_por=usuario_admin,
    )
    actor_ajeno = Usuario.objects.create_user(
        email="almacen.are@lari.local",
        password="ClaveAre12345",
        rol=Rol.RESPONSABLE_ALMACEN,
        region=otra,
        is_active=True,
    )
    from django.test import Client

    ajeno = Client()
    ajeno.force_login(actor_ajeno)
    assert ajeno.get(
        reverse("detalle_almacen", args=[solicitud.pk])
    ).status_code == 404


@pytest.mark.django_db
def test_acciones_solo_aceptan_post_y_limites_de_motivo(
    cliente_almacen,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    for nombre in ("confirmar_almacen", "rechazar_almacen"):
        assert (
            cliente_almacen.get(reverse(nombre, args=[solicitud.pk])).status_code
            == 405
        )

    respuesta = cliente_almacen.post(
        reverse("rechazar_almacen", args=[solicitud.pk]),
        {"motivo": "x" * 1001},
    )
    assert respuesta.status_code == 400
    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.ENVIADA


@pytest.mark.django_db
def test_confirmar_desde_otro_estado_devuelve_409(
    cliente_almacen,
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    almacen_services.confirmar_solicitud(solicitud, usuario_almacen)
    respuesta = cliente_almacen.post(
        reverse("confirmar_almacen", args=[solicitud.pk])
    )
    assert respuesta.status_code == 409
    assert (
        "Solo se pueden confirmar solicitudes enviadas"
        in respuesta.content.decode()
    )


@pytest.mark.django_db
def test_historicos_permisos_y_descarga(
    cliente_almacen,
    cliente_autenticado,
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    assert cliente_almacen.get(reverse("historicos_almacen")).status_code == 200
    assert cliente_autenticado.get(reverse("historicos_almacen")).status_code == 200
    assert cliente_tenant.get(reverse("historicos_almacen")).status_code == 403
