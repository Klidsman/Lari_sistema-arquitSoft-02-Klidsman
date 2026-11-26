"""Contrato del almacén (007)."""

from datetime import date

import pytest
from django.urls import reverse

from asignaciones.models import EstadoSolicitud
from asignaciones.services import crear_y_enviar_solicitud
from series.models import EstadoSerie


def _solicitud(usuario_tenant, tenant, tecnico, material, serie, almacen):
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
def test_bandeja_y_confirmacion_http(
    cliente_almacen,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente, almacen
    )

    respuesta = cliente_almacen.get(reverse("bandeja_almacen"))
    assert respuesta.status_code == 200
    assert str(solicitud.pk) in respuesta.content.decode()

    respuesta = cliente_almacen.post(
        reverse("confirmar_almacen", args=[solicitud.pk])
    )
    assert respuesta.status_code == 302
    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.CONFIRMADA
    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.ASIGNADA


@pytest.mark.django_db
def test_rechazo_http(
    cliente_almacen,
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente, almacen
    )

    respuesta = cliente_almacen.post(
        reverse("rechazar_almacen", args=[solicitud.pk]),
        {"motivo": ""},
    )
    assert respuesta.status_code == 400

    respuesta = cliente_almacen.post(
        reverse("rechazar_almacen", args=[solicitud.pk]),
        {"motivo": "Sin stock"},
    )
    assert respuesta.status_code == 302
    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.RECHAZADA

    detalle_tenant = cliente_tenant.get(
        reverse("detalle_asignacion", args=[solicitud.pk])
    )
    contenido = detalle_tenant.content.decode()
    assert detalle_tenant.status_code == 200
    assert "Solicitud rechazada" in contenido
    assert "Sin stock" in contenido


@pytest.mark.django_db
def test_descarga_verifica_hash(
    cliente_almacen,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente, almacen
    )

    respuesta = cliente_almacen.get(
        reverse("descargar_excel_almacen", args=[solicitud.pk])
    )
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith(
        "application/vnd.openxmlformats"
    )


@pytest.mark.django_db
def test_tenant_y_admin_no_operan_bandeja(cliente_tenant, cliente_autenticado):
    assert cliente_tenant.get(reverse("bandeja_almacen")).status_code == 403
    assert cliente_autenticado.get(reverse("bandeja_almacen")).status_code == 403
