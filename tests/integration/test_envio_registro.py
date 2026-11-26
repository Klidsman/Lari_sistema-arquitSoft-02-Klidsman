"""Restricciones del registro de envíos de correo."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from asignaciones.models import EnvioCorreo, EstadoSolicitud
from asignaciones.services import crear_y_enviar_solicitud
from stock.models import StockGeneral


def _solicitud(usuario_tenant, tenant, tecnico, material):
    StockGeneral.objects.create(
        tenant=tenant, material=material, cantidad=5
    )
    return crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )


def _envio(solicitud, numero=1, **extra):
    datos = {
        "solicitud": solicitud,
        "tenant": solicitud.tenant,
        "region": solicitud.region,
        "numero_intento": numero,
        "destinatario": "almacen@lari.local",
        "archivo": solicitud.excel_ruta,
        "hash_sha256": solicitud.excel_hash,
    }
    datos.update(extra)
    return EnvioCorreo.objects.create(**datos)


@pytest.mark.django_db
def test_envio_correo_valores_por_defecto(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    envio = _envio(solicitud)
    assert envio.estado == EnvioCorreo.ESTADO_REINTENTANDO
    assert envio.error_mensaje == ""
    assert envio.enviado_en is None
    assert solicitud.estado == EstadoSolicitud.ENVIADA


@pytest.mark.django_db
def test_envio_correo_intento_unico(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    _envio(solicitud)
    with pytest.raises(IntegrityError), transaction.atomic():
        _envio(solicitud)


@pytest.mark.django_db
def test_envio_correo_numero_intento_positivo_y_estado_valido(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        _envio(solicitud, numero=0)
    with pytest.raises(IntegrityError), transaction.atomic():
        _envio(solicitud, numero=2, estado="OTRO")


@pytest.mark.django_db
def test_envio_correo_protege_solicitud(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    _envio(solicitud)
    with pytest.raises(ProtectedError):
        solicitud.delete()
