"""Cambio de tipo permitido y bloqueado por movimientos."""

import pytest
from django.urls import reverse

from auditoria.models import RegistroCambio
from materiales.models import Material


@pytest.mark.django_db
def test_cambio_de_tipo_permitido_y_auditado(cliente_almacen, material):
    respuesta = cliente_almacen.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": material.descripcion, "lote": material.lote, "tipo": "NO_SERIADO"},
    )

    assert respuesta.status_code == 302
    material.refresh_from_db()
    assert material.es_seriado is False

    registro = RegistroCambio.objects.get(
        entidad="Material", entidad_id=material.pk, campo="tipo"
    )
    assert registro.valor_anterior == "SERIADO"
    assert registro.valor_nuevo == "NO_SERIADO"


@pytest.mark.django_db
def test_cambio_de_tipo_rechazado_si_hay_movimientos(
    cliente_almacen, material, verificacion_movimientos
):
    verificacion_movimientos(lambda material: True)
    antes = RegistroCambio.objects.filter(
        entidad="Material", entidad_id=material.pk, campo="tipo"
    ).count()

    respuesta = cliente_almacen.post(
        reverse("editar_material", args=[material.pk]),
        {"descripcion": material.descripcion, "lote": material.lote, "tipo": "NO_SERIADO"},
    )

    assert respuesta.status_code == 400
    assert (
        "El tipo no se puede cambiar: el material tiene movimientos"
        in respuesta.content.decode()
    )

    material.refresh_from_db()
    assert material.es_seriado is True
    assert (
        RegistroCambio.objects.filter(
            entidad="Material", entidad_id=material.pk, campo="tipo"
        ).count()
        == antes
    )


@pytest.mark.django_db
def test_tipo_visible_deshabilitado_si_hay_movimientos(
    cliente_almacen, material, verificacion_movimientos
):
    verificacion_movimientos(lambda material: True)

    respuesta = cliente_almacen.get(
        reverse("editar_material", args=[material.pk])
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert 'name="tipo"' in contenido
    assert "disabled" in contenido
    assert "El tipo no se puede cambiar" in contenido
