"""Restricciones de base de solicitudes y líneas de asignación."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from asignaciones.models import LineaAsignacion, SolicitudAsignacion


def _solicitud(tenant, usuario_tenant):
    return SolicitudAsignacion.objects.create(
        tenant=tenant,
        region=tenant.region,
        fecha=date.today(),
        creado_por=usuario_tenant,
    )


def _linea(solicitud, material, tecnico, **kwargs):
    return LineaAsignacion.objects.create(
        tenant=solicitud.tenant,
        solicitud=solicitud,
        tecnico=tecnico,
        material=material,
        lote=material.lote,
        **kwargs,
    )


@pytest.mark.django_db
def test_serie_exige_cantidad_uno(
    tenant, usuario_tenant, tecnico, material_seriado, serie_existente
):
    solicitud = _solicitud(tenant, usuario_tenant)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _linea(
                solicitud,
                material_seriado,
                tecnico,
                serie=serie_existente,
                cantidad=2,
            )


@pytest.mark.django_db
@pytest.mark.parametrize("cantidad", [0, -1])
def test_no_seriado_exige_cantidad_positiva(
    tenant, usuario_tenant, tecnico, material_no_seriado, cantidad
):
    solicitud = _solicitud(tenant, usuario_tenant)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _linea(solicitud, material_no_seriado, tecnico, cantidad=cantidad)


@pytest.mark.django_db
def test_serie_no_puede_repetirse_en_la_solicitud(
    tenant, usuario_tenant, tecnico, material_seriado, serie_existente
):
    solicitud = _solicitud(tenant, usuario_tenant)
    _linea(solicitud, material_seriado, tecnico, serie=serie_existente, cantidad=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _linea(
                solicitud,
                material_seriado,
                tecnico,
                serie=serie_existente,
                cantidad=1,
            )


@pytest.mark.django_db
def test_no_seriado_no_puede_repetirse_en_la_solicitud(
    tenant, usuario_tenant, tecnico, material_no_seriado
):
    solicitud = _solicitud(tenant, usuario_tenant)
    _linea(solicitud, material_no_seriado, tecnico, cantidad=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _linea(solicitud, material_no_seriado, tecnico, cantidad=2)


@pytest.mark.django_db
def test_estado_fuera_del_conjunto_falla(tenant, usuario_tenant):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SolicitudAsignacion.objects.create(
                tenant=tenant,
                region=tenant.region,
                fecha=date.today(),
                estado="INVALIDO",
                creado_por=usuario_tenant,
            )
