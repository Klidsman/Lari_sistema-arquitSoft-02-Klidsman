"""Concurrencia y reversión del envío de asignaciones."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from django.db import connections

from asignaciones.models import EstadoSolicitud, LineaAsignacion, SolicitudAsignacion
from asignaciones.services import crear_y_enviar_solicitud, generar_excel_solicitud
from series.models import EstadoSerie


class _Resultado:
    def __init__(self, valor=None, error=None):
        self.valor = valor
        self.error = error


def _enviar(tenant, tecnico, material, serie, usuario):
    connections.close_all()
    try:
        solicitud = crear_y_enviar_solicitud(
            tenant,
            date.today(),
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material.pk,
                    "serie_ids": [serie.pk],
                }
            ],
            usuario,
        )
        return _Resultado(valor=solicitud)
    except Exception as exc:  # noqa: BLE001 - se inspecciona en el test
        return _Resultado(error=exc)
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_dos_envios_de_la_misma_serie_reservan_una_sola(
    tenant, tecnico, material_seriado, serie_existente, usuario_tenant, almacen
):
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(
            ejecutor.map(
                lambda _: _enviar(
                    tenant,
                    tecnico,
                    material_seriado,
                    serie_existente,
                    usuario_tenant,
                ),
                range(2),
            )
        )

    exitos = [r for r in resultados if r.valor is not None]
    fallos = [r for r in resultados if r.error is not None]

    assert len(exitos) == 1
    assert len(fallos) == 1
    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.RESERVADA
    assert SolicitudAsignacion.objects.filter(estado=EstadoSolicitud.ENVIADA).count() == 1


@pytest.mark.django_db
def test_fallo_de_excel_revierte_solicitud_y_lineas(
    monkeypatch,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    usuario_tenant,
    almacen,
):
    monkeypatch.setattr(
        "asignaciones.services.generar_excel_solicitud",
        lambda solicitud: (_ for _ in ()).throw(RuntimeError("excel roto")),
    )

    with pytest.raises(RuntimeError, match="excel roto"):
        crear_y_enviar_solicitud(
            tenant,
            date.today(),
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_seriado.pk,
                    "serie_ids": [serie_existente.pk],
                }
            ],
            usuario_tenant,
        )

    assert not SolicitudAsignacion.objects.exists()
    assert not LineaAsignacion.objects.exists()
    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.DISPONIBLE
