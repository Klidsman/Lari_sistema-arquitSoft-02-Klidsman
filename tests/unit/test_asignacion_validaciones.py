"""Validaciones unitarias de líneas de asignación."""

from datetime import date

import pytest

from asignaciones.services import (
    CantidadInvalida,
    MaterialDuplicado,
    SerieDuplicada,
    SerieNoDisponible,
    TecnicoNoDisponible,
    ValidacionAsignacion,
    normalizar_lineas_solicitud,
)
from series.models import EstadoSerie, Serie
from tecnicos.models import Tecnico


@pytest.mark.django_db
def test_material_seriado_expande_series_y_copia_lote(
    tenant, tecnico, material_seriado, serie_existente
):
    lineas = normalizar_lineas_solicitud(
        tenant,
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie_existente.pk],
            }
        ],
    )

    assert len(lineas) == 1
    assert lineas[0].serie == serie_existente
    assert lineas[0].cantidad == 1
    assert lineas[0].lote == material_seriado.lote
    assert lineas[0].tecnico == tecnico


@pytest.mark.django_db
def test_seriado_sin_serie_se_rechaza(
    tenant, tecnico, material_seriado
):
    with pytest.raises(ValidacionAsignacion, match="al menos una serie"):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_seriado.pk,
                    "serie_ids": [],
                }
            ],
        )


@pytest.mark.django_db
def test_no_seriado_con_series_se_rechaza(
    tenant, tecnico, material_no_seriado, serie_existente
):
    with pytest.raises(ValidacionAsignacion, match="no admite series"):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "serie_ids": [serie_existente.pk],
                }
            ],
        )


@pytest.mark.django_db
@pytest.mark.parametrize("cantidad", [0, -1, "dos", 1.5])
def test_cantidad_invalida(
    tenant, tecnico, material_no_seriado, cantidad
):
    with pytest.raises(CantidadInvalida):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": cantidad,
                }
            ],
        )


@pytest.mark.django_db
def test_serie_duplicada_en_la_solicitud(
    tenant, tecnico, material_seriado, serie_existente, usuario_tenant
):
    segundo = Tecnico.objects.create(
        tenant=tenant,
        nif="LA3333",
        nombre="Segundo",
        creado_por=usuario_tenant,
    )
    with pytest.raises(SerieDuplicada):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_seriado.pk,
                    "serie_ids": [serie_existente.pk],
                },
                {
                    "tecnico_id": segundo.pk,
                    "material_id": material_seriado.pk,
                    "serie_ids": [serie_existente.pk],
                },
            ],
        )


@pytest.mark.django_db
def test_serie_no_disponible(
    tenant, tecnico, material_seriado, serie_existente
):
    serie_existente.estado = EstadoSerie.RESERVADA
    serie_existente.save(update_fields=["estado"])

    with pytest.raises(SerieNoDisponible):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_seriado.pk,
                    "serie_ids": [serie_existente.pk],
                }
            ],
        )


@pytest.mark.django_db
def test_tecnico_inactivo_y_ajeno(
    tenant, tecnico_desactivado, usuario_otro_tenant, material_no_seriado
):
    with pytest.raises(TecnicoNoDisponible, match="desactivado"):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": tecnico_desactivado.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 1,
                }
            ],
        )

    ajeno = Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA8888",
        nombre="Ajeno",
        creado_por=usuario_otro_tenant,
    )
    with pytest.raises(TecnicoNoDisponible, match="no existe"):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": ajeno.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 1,
                }
            ],
        )


@pytest.mark.django_db
def test_material_duplicado_para_el_mismo_tecnico(
    tenant, tecnico, material_no_seriado
):
    with pytest.raises(MaterialDuplicado):
        normalizar_lineas_solicitud(
            tenant,
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 1,
                },
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 2,
                },
            ],
        )
