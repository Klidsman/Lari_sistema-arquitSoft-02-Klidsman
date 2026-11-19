"""Restricciones de base de series y recojos."""

from datetime import date

import pytest
from django.db import DatabaseError, transaction

from recojos.models import LineaRecojo, Recojo
from series.models import Serie


def _serie(tenant, material, usuario, **cambios):
    datos = {
        "numero": "ABC123456789",
        "tenant": tenant,
        "region": tenant.region,
        "material": material,
        "creado_por": usuario,
    }
    datos.update(cambios)
    return Serie.objects.create(**datos)


@pytest.mark.django_db
def test_serie_formato_invalido(tenant, material_seriado, usuario_tenant):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _serie(tenant, material_seriado, usuario_tenant, numero="ABC123")


@pytest.mark.django_db
def test_serie_duplicada(tenant, material_seriado, usuario_tenant, serie_existente):
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            _serie(
                tenant,
                material_seriado,
                usuario_tenant,
                numero=serie_existente.numero,
            )


@pytest.mark.django_db
def test_linea_sin_serie_ni_cantidad(tenant, usuario_tenant, material_no_seriado):
    recojo = Recojo.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        creado_por=usuario_tenant,
    )

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            LineaRecojo.objects.create(
                tenant=tenant,
                recojo=recojo,
                material=material_no_seriado,
                serie=None,
                cantidad=0,
            )


@pytest.mark.django_db
def test_linea_seriada_cantidad_distinta_de_uno(
    tenant, usuario_tenant, material_seriado, serie_existente
):
    recojo = Recojo.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        creado_por=usuario_tenant,
    )

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            LineaRecojo.objects.create(
                tenant=tenant,
                recojo=recojo,
                material=material_seriado,
                serie=serie_existente,
                cantidad=2,
            )


@pytest.mark.django_db
def test_cantidad_negativa(tenant, usuario_tenant, material_no_seriado):
    recojo = Recojo.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        creado_por=usuario_tenant,
    )

    with pytest.raises(DatabaseError):
        with transaction.atomic():
            LineaRecojo.objects.create(
                tenant=tenant,
                recojo=recojo,
                material=material_no_seriado,
                serie=None,
                cantidad=-1,
            )
