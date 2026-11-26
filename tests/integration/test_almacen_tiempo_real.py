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

@pytest.mark.django_db
def test_evento_cambio_estado_incluye_estado_y_pendientes(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    from datetime import date

    from asignaciones.models import EstadoSolicitud
    from asignaciones.services import crear_y_enviar_solicitud
    from stock.models import StockGeneral

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )

    evento = notificaciones.evento_cambio_estado(
        solicitud,
        EstadoSolicitud.ENVIADA,
        EstadoSolicitud.CONFIRMADA,
    )
    assert evento["tipo"] == "cambio_estado"
    assert evento["estado_anterior"] == "ENVIADA"
    assert evento["estado"] == "CONFIRMADA"
    assert evento["pendientes"] == 1


@pytest.mark.django_db
def test_confirmar_y_rechazar_publican_cambio_de_estado(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    from datetime import date

    from asignaciones import almacen_services
    from asignaciones.services import crear_y_enviar_solicitud
    from stock.models import StockGeneral

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=20
    )
    publicados = []
    monkeypatch.setattr(
        notificaciones,
        "publicar_cambio_estado",
        lambda solicitud, anterior, nuevo: publicados.append(
            (solicitud.pk, anterior, nuevo)
        ),
    )

    def crear():
        return crear_y_enviar_solicitud(
            tenant,
            date.today(),
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 1,
                }
            ],
            usuario_tenant,
        )

    confirmada = crear()
    with django_capture_on_commit_callbacks(execute=True):
        almacen_services.confirmar_solicitud(confirmada, usuario_almacen)

    rechazada = crear()
    with django_capture_on_commit_callbacks(execute=True):
        almacen_services.rechazar_solicitud(
            rechazada, "No procede", usuario_almacen
        )

    assert publicados == [
        (confirmada.pk, "ENVIADA", "CONFIRMADA"),
        (rechazada.pk, "ENVIADA", "RECHAZADA"),
    ]
