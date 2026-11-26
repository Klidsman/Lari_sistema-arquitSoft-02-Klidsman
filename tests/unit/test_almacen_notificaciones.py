"""Notificaciones del almacén: canal, publicación y evento."""

import json

import pytest

from asignaciones import notificaciones


class _ClienteFalso:
    def __init__(self):
        self.publicados = []
        self.cerrado = False

    def publish(self, canal, datos):
        self.publicados.append((canal, datos))

    def close(self):
        self.cerrado = True


def test_canal_region_usa_prefijo_configurado(region):
    assert notificaciones.canal_region(region) == f"almacen:region:{region.pk}"


def test_publicar_evento_region(monkeypatch, region):
    cliente = _ClienteFalso()
    monkeypatch.setattr(
        notificaciones, "cliente_redis", lambda: cliente
    )

    resultado = notificaciones.publicar_evento_region(
        region, {"tipo": "solicitud_enviada", "solicitud_id": 7}
    )

    assert resultado is True
    assert cliente.cerrado is True
    assert len(cliente.publicados) == 1
    canal, datos = cliente.publicados[0]
    assert canal == f"almacen:region:{region.pk}"
    assert json.loads(datos)["solicitud_id"] == 7


def test_publicar_no_revienta_si_redis_falla(monkeypatch, region):
    def fallar():
        raise RuntimeError("Redis caído")

    monkeypatch.setattr(notificaciones, "cliente_redis", fallar)
    assert (
        notificaciones.publicar_evento_region(region, {"x": 1}) is False
    )


@pytest.mark.django_db
def test_evento_solicitud_enviada_incluye_totales_y_pendientes(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    from datetime import date

    from stock.models import StockGeneral
    from asignaciones.services import crear_y_enviar_solicitud

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
                "cantidad": 3,
            }
        ],
        usuario_tenant,
    )

    evento = notificaciones.evento_solicitud_enviada(solicitud)
    assert evento["solicitud_id"] == solicitud.pk
    assert evento["tenant"] == tenant.codigo
    assert evento["tecnicos"] == [tecnico.nif]
    assert evento["total_lineas"] == 1
    assert evento["total_cantidad"] == 3
    assert evento["pendientes"] == 1
    assert evento["url"] == f"/almacen/solicitudes/{solicitud.pk}/"
