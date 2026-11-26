"""Auditoría de la confirmación y el rechazo en el almacén."""

from datetime import date

import pytest
from django.conf import settings

from asignaciones import almacen_services
from asignaciones.services import crear_y_enviar_solicitud
from auditoria.models import RegistroCambio
from stock.models import StockGeneral, StockTecnico


def _enviada(usuario_tenant, tenant, tecnico, material, serie=None, cantidad=None):
    linea = {"tecnico_id": tecnico.pk, "material_id": material.pk}
    if serie is not None:
        linea["serie_ids"] = [serie.pk]
    else:
        linea["cantidad"] = cantidad
    return crear_y_enviar_solicitud(
        tenant, date.today(), [linea], usuario_tenant
    )


@pytest.mark.django_db
def test_auditoria_de_confirmacion(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    almacen_services.confirmar_solicitud(solicitud, usuario_almacen)

    estado = RegistroCambio.objects.get(
        entidad="SolicitudAsignacion",
        entidad_id=solicitud.pk,
        campo="estado",
        valor_nuevo="CONFIRMADA",
    )
    assert estado.valor_anterior == "ENVIADA"
    assert estado.usuario_id == usuario_almacen.pk

    assert (
        RegistroCambio.objects.filter(
            entidad="Serie",
            entidad_id=serie_existente.pk,
            campo="estado",
            valor_nuevo="ASIGNADA",
        ).count()
        == 1
    )
    assert (
        RegistroCambio.objects.filter(
            entidad="StockGeneral", campo="cantidad"
        ).count()
        == 1
    )
    assert (
        RegistroCambio.objects.filter(
            entidad="StockTecnico", campo="cantidad"
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_auditoria_de_rechazo(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    almacen,
    stock_general,
):
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_seriado, serie_existente
    )
    almacen_services.rechazar_solicitud(
        solicitud, "No hay unidad", usuario_almacen
    )

    estado = RegistroCambio.objects.get(
        entidad="SolicitudAsignacion",
        entidad_id=solicitud.pk,
        campo="estado",
        valor_nuevo="RECHAZADA",
    )
    assert RegistroCambio.objects.filter(
        entidad="Serie",
        entidad_id=serie_existente.pk,
        campo="estado",
        valor_anterior="RESERVADA",
        valor_nuevo="DISPONIBLE",
    ).exists()


@pytest.mark.django_db
def test_auditoria_del_almacen_sin_secretos_ni_rutas_absolutas(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    solicitud = _enviada(
        usuario_tenant, tenant, tecnico, material_no_seriado, cantidad=1
    )
    almacen_services.confirmar_solicitud(solicitud, usuario_almacen)

    texto = " ".join(
        f"{campo} {anterior} {nuevo}"
        for campo, anterior, nuevo in RegistroCambio.objects.values_list(
            "campo", "valor_anterior", "valor_nuevo"
        )
    ).lower()
    for prohibido in ("password", "token", "secret", "smtp"):
        assert prohibido not in texto
    for _, anterior, nuevo in RegistroCambio.objects.values_list(
        "campo", "valor_anterior", "valor_nuevo"
    ):
        assert str(settings.MEDIA_ROOT) not in anterior
        assert str(settings.MEDIA_ROOT) not in nuevo
        assert "\x00" not in anterior
        assert "\x00" not in nuevo
    assert StockTecnico.objects.filter(
        tecnico=tecnico, material=material_no_seriado
    ).exists()
