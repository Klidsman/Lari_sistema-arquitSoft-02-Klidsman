"""Integración de la edición de técnicos."""

import pytest

from auditoria.models import RegistroCambio
from tecnicos.services import ValidacionTecnico, actualizar_tecnico


@pytest.mark.django_db
def test_actualizar_nombre_audita(tecnico, usuario_tenant, registro_cambios):
    actualizar_tecnico(tecnico, {"nombre": "Juan Actualizado"}, usuario_tenant)

    tecnico.refresh_from_db()
    assert tecnico.nombre == "Juan Actualizado"

    registro = registro_cambios(tecnico).get(campo="nombre")
    assert registro.valor_anterior == "Juan Pérez"
    assert registro.valor_nuevo == "Juan Actualizado"


@pytest.mark.django_db
def test_edicion_sin_cambios_no_audita_ni_actualiza(tecnico, usuario_tenant, registro_cambios):
    antes = registro_cambios(tecnico).count()
    actualizado_antes = tecnico.actualizado_en

    actualizar_tecnico(tecnico, {"nombre": tecnico.nombre}, usuario_tenant)

    tecnico.refresh_from_db()
    assert registro_cambios(tecnico).count() == antes
    assert tecnico.actualizado_en == actualizado_antes


@pytest.mark.django_db
def test_metadatos_de_actualizacion(tecnico, usuario_tenant):
    actualizado = actualizar_tecnico(
        tecnico,
        {"nombre": "Otro Nombre"},
        usuario_tenant,
    )

    assert actualizado.actualizado_por_id == usuario_tenant.pk
    assert actualizado.actualizado_en >= tecnico.creado_en


@pytest.mark.django_db
def test_nif_y_tenant_inmutables(tecnico, usuario_tenant, registro_cambios):
    antes = registro_cambios(tecnico).count()

    with pytest.raises(ValidacionTecnico, match="El NIF no se puede cambiar"):
        actualizar_tecnico(tecnico, {"nif": "LA9999"}, usuario_tenant)

    with pytest.raises(
        ValidacionTecnico, match="El tenant del técnico no se puede cambiar"
    ):
        actualizar_tecnico(tecnico, {"tenant_id": 999}, usuario_tenant)

    assert registro_cambios(tecnico).count() == antes


@pytest.mark.django_db
def test_intento_rechazado_no_audita(tecnico, usuario_tenant, registro_cambios):
    antes = RegistroCambio.objects.count()

    with pytest.raises(ValidacionTecnico):
        actualizar_tecnico(tecnico, {"nombre": "   "}, usuario_tenant)

    assert RegistroCambio.objects.count() == antes
