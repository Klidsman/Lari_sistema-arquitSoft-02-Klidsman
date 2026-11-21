"""Días en mano y alerta de cupo de 006 (CA-08 y CA-09)."""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from asignaciones.services import (
    calcular_alerta_cupo,
    dias_en_mano_serie,
    series_en_custodia_tecnico,
)
from series.models import EstadoSerie, Serie


def _serie(tenant, tecnico, material, usuario_tenant, dias=0, estado=EstadoSerie.ASIGNADA):
    base = timezone.make_aware(
        datetime.combine(timezone.localdate(), time(12, 0))
    )
    return Serie.objects.create(
        numero=f"SER{dias:09d}"[-12:],
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=estado,
        tecnico=tecnico if estado == EstadoSerie.ASIGNADA else None,
        asignada_en=(
            base - timedelta(days=dias)
            if estado == EstadoSerie.ASIGNADA
            else None
        ),
        creado_por=usuario_tenant,
    )


@pytest.mark.django_db
def test_dias_en_mano_solo_para_series_asignadas(
    tenant, tecnico, material_seriado, usuario_tenant
):
    asignada = _serie(
        tenant, tecnico, material_seriado, usuario_tenant, dias=10
    )
    disponible = _serie(
        tenant,
        tecnico,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.DISPONIBLE,
    )

    assert dias_en_mano_serie(asignada) == 10
    assert dias_en_mano_serie(disponible) is None
    asignada.asignada_en = None
    assert dias_en_mano_serie(asignada) is None


@pytest.mark.django_db
def test_series_en_custodia_filtra_por_tecnico_y_estado(
    tenant, tecnico, material_seriado, usuario_tenant
):
    propia = _serie(tenant, tecnico, material_seriado, usuario_tenant, dias=5)
    _serie(
        tenant,
        tecnico,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.DISPONIBLE,
    )

    custodia = series_en_custodia_tecnico(tecnico)

    assert [item["serie"].pk for item in custodia] == [propia.pk]
    assert custodia[0]["dias"] == 5


@pytest.mark.django_db
def test_alerta_cupo_se_evalua_por_equipo_y_no_bloquea(
    tenant, tecnico, material_seriado, material_no_seriado, usuario_tenant
):
    _serie(tenant, tecnico, material_seriado, usuario_tenant, dias=19)
    _serie(tenant, tecnico, material_seriado, usuario_tenant, dias=21)

    alerta = calcular_alerta_cupo(tecnico)

    assert alerta is not None
    assert "supera los 20 días en mano" in alerta.mensaje
    assert len(alerta.series) == 1
    assert alerta.series[0]["dias"] == 21


@pytest.mark.django_db
def test_alerta_cupo_no_cuenta_series_de_otro_tenant(
    tenant,
    tecnico,
    material_seriado,
    usuario_tenant,
    usuario_otro_tenant,
):
    _serie(tenant, tecnico, material_seriado, usuario_tenant, dias=5)
    from tecnicos.models import Tecnico

    otro_tenant = usuario_otro_tenant.tenant
    tecnico_ajeno = Tecnico.objects.create(
        tenant=otro_tenant,
        nif="LA7777",
        nombre="Ajeno",
        creado_por=usuario_otro_tenant,
    )
    _serie(
        otro_tenant,
        tecnico_ajeno,
        material_seriado,
        usuario_otro_tenant,
        dias=30,
    )

    assert calcular_alerta_cupo(tecnico) is None
