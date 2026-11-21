"""Contrato del listado de asignaciones (006, US4)."""

from datetime import date

import pytest
from django.urls import reverse

from asignaciones.models import EstadoSolicitud, SolicitudAsignacion
from asignaciones.services import crear_borrador_solicitud
from stock.models import StockGeneral


def _crear(usuario_tenant, tenant, tecnico, material):
    StockGeneral.objects.create(
        tenant=tenant, material=material, cantidad=10
    )
    return crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material.pk,
                "cantidad": 2,
            }
        ],
        usuario_tenant,
    )


@pytest.mark.django_db
def test_lista_muestra_solo_solicitudes_del_tenant_y_filtra(
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    usuario_otro_tenant,
):
    propia = _crear(usuario_tenant, tenant, tecnico, material_no_seriado)
    SolicitudAsignacion.objects.create(
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        fecha=date.today(),
        creado_por=usuario_otro_tenant,
    )

    respuesta = cliente_tenant.get(reverse("lista_asignaciones"))
    contenido = respuesta.content.decode()
    detalle = reverse("detalle_asignacion", args=[propia.pk])

    assert respuesta.status_code == 200
    assert detalle in contenido
    assert usuario_otro_tenant.tenant.codigo not in contenido
    assert "BORRADOR" in contenido or "Borrador" in contenido

    respuesta = cliente_tenant.get(
        reverse("lista_asignaciones"), {"estado": EstadoSolicitud.ENVIADA}
    )
    assert detalle not in respuesta.content.decode()


@pytest.mark.django_db
def test_permisos_y_metodos_del_listado(
    cliente_autenticado, cliente_almacen, cliente_tenant
):
    for cliente in (cliente_autenticado, cliente_almacen):
        assert cliente.get(reverse("lista_asignaciones")).status_code == 403

    assert cliente_tenant.delete(reverse("lista_asignaciones")).status_code == 405
