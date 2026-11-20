"""Restricciones de base de datos de regiones y almacenes."""

import pytest
from django.db import IntegrityError, transaction

from tenants.models import Almacen, Region


@pytest.mark.django_db
def test_region_con_codigo_vacio_falla(usuario_admin):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Region.objects.create(
                codigo="",
                nombre="Sin código",
                creado_por=usuario_admin,
            )


@pytest.mark.django_db
def test_region_codigo_duplicado_falla(usuario_admin, region):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Region.objects.create(
                codigo=region.codigo,
                nombre="Duplicada",
                creado_por=usuario_admin,
            )


@pytest.mark.django_db
def test_almacen_sin_centro_falla(usuario_admin, region):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Almacen.objects.create(
                region=region,
                centro="",
                codigo_almacen="BE03",
                buzon="almacen@lari.local",
                creado_por=usuario_admin,
            )


@pytest.mark.django_db
def test_almacen_sin_codigo_falla(usuario_admin, region):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Almacen.objects.create(
                region=region,
                centro="PR05",
                codigo_almacen="",
                buzon="almacen@lari.local",
                creado_por=usuario_admin,
            )
