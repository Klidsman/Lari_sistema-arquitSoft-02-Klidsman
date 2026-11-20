"""Restricciones de base de datos del catálogo."""

import pytest
from django.db import DatabaseError, transaction

from materiales.models import Material


def _crear(usuario, **cambios):
    datos = {
        "codigo": "10402520279",
        "descripcion": "ROSETA",
        "lote": "",
        "es_seriado": True,
        "creado_por": usuario,
    }
    datos.update(cambios)
    return Material.objects.create(**datos)


@pytest.mark.django_db
def test_codigo_de_10_digitos_falla(usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(usuario_tenant, codigo="1040252027")


@pytest.mark.django_db
def test_codigo_de_12_digitos_falla(usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(usuario_tenant, codigo="104025202791")


@pytest.mark.django_db
def test_codigo_con_letras_falla(usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(usuario_tenant, codigo="1040252027A")


@pytest.mark.django_db
def test_descripcion_vacia_falla(usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(usuario_tenant, descripcion="")


@pytest.mark.django_db
def test_codigo_duplicado_falla(usuario_tenant, material):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _crear(usuario_tenant, codigo=material.codigo)
