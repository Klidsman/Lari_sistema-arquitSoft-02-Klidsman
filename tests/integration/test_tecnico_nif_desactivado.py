"""NIF de técnicos desactivados y validación para operaciones."""

import pytest

from tecnicos.models import Tecnico
from tecnicos.services import (
    NifDuplicado,
    TecnicoNoDisponible,
    crear_tecnico,
    validar_tecnico_para_operacion,
)


@pytest.mark.django_db
def test_crear_con_nif_de_desactivado_mismo_tenant(
    usuario_tenant, tecnico_desactivado
):
    with pytest.raises(
        NifDuplicado,
        match="El NIF ya está registrado; reactiva el técnico existente",
    ):
        crear_tecnico(
            {"nif": tecnico_desactivado.nif, "nombre": "Nuevo"},
            usuario_tenant,
        )


@pytest.mark.django_db
def test_crear_con_nif_de_desactivado_otro_tenant(
    usuario_tenant, usuario_otro_tenant
):
    Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA7777",
        nombre="Ajeno",
        activo=False,
        creado_por=usuario_otro_tenant,
    )

    with pytest.raises(NifDuplicado) as error:
        crear_tecnico({"nif": "LA7777", "nombre": "Nuevo"}, usuario_tenant)

    assert str(error.value) == "El NIF ya está registrado"


@pytest.mark.django_db
def test_formulario_viejo_con_desactivado(tenant, tecnico_desactivado):
    with pytest.raises(TecnicoNoDisponible, match="El técnico está desactivado"):
        validar_tecnico_para_operacion(tenant, tecnico_desactivado.pk)


@pytest.mark.django_db
def test_operacion_con_otro_tenant(tenant, tecnico_otro_tenant):
    from tecnicos.services import NoEncontrado

    with pytest.raises(NoEncontrado, match="El técnico no existe"):
        validar_tecnico_para_operacion(tenant, tecnico_otro_tenant.pk)
