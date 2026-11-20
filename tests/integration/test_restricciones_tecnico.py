"""Restricciones de base de datos de técnicos."""

import pytest
from django.db import DatabaseError, transaction

from tecnicos.models import Tecnico


def _crear(tenant, usuario, **cambios):
    datos = {
        "tenant": tenant,
        "nif": "LA1234",
        "nombre": "Juan Pérez",
        "activo": True,
        "creado_por": usuario,
    }
    datos.update(cambios)
    return Tecnico.objects.create(**datos)


@pytest.mark.django_db
def test_nif_de_3_digitos_falla(tenant, usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(tenant, usuario_tenant, nif="LA123")


@pytest.mark.django_db
def test_nif_de_5_digitos_falla(tenant, usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(tenant, usuario_tenant, nif="LA12345")


@pytest.mark.django_db
def test_nif_con_letras_falla(tenant, usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(tenant, usuario_tenant, nif="LA12A4")


@pytest.mark.django_db
def test_nif_con_espacio_interno_falla(tenant, usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(tenant, usuario_tenant, nif="LA 123")


@pytest.mark.django_db
def test_nif_duplicado_falla(tenant, usuario_tenant, tecnico):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(tenant, usuario_tenant, nif=tecnico.nif)


@pytest.mark.django_db
def test_nombre_vacio_falla(tenant, usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(tenant, usuario_tenant, nombre="")
