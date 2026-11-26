"""Publicación del evento de nueva solicitud al almacén (007)."""

from datetime import date

import pytest

from asignaciones import notificaciones
from asignaciones.services import crear_y_enviar_solicitud
from stock.models import StockGeneral


@pytest.mark.django_db
def test_enviar_solicitud_publica_evento_en_on_commit(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    publicados = []

    def publicar(solicitud):
        publicados.append(solicitud.pk)
        return True

    monkeypatch.setattr(
        notificaciones, "publicar_solicitud_enviada", publicar
    )

    with django_capture_on_commit_callbacks(execute=True):
        solicitud = crear_y_enviar_solicitud(
            tenant,
            date.today(),
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 2,
                }
            ],
            usuario_tenant,
        )

    assert publicados == [solicitud.pk]
