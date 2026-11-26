"""Contrato HTTP de la bandeja en tiempo real (007)."""

import pytest
from django.urls import reverse

from asignaciones import almacen_views, notificaciones


@pytest.mark.django_db
def test_bandeja_incluye_sse_polling_toast_y_silencio(cliente_almacen, almacen):
    respuesta = cliente_almacen.get(reverse("bandeja_almacen"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert 'data-sse-url="' in contenido
    assert 'data-poll-url="' in contenido
    assert 'data-tabla-url="' in contenido
    assert 'id="toast-alerta"' in contenido
    assert 'id="silenciar-aviso"' in contenido
    assert "EventSource" in contenido
    assert "setInterval" in contenido


@pytest.mark.django_db
def test_sse_usa_la_region_del_almacen_y_devuelve_stream(
    cliente_almacen, region, almacen, monkeypatch
):
    regiones = []

    def generador(region_arg, heartbeat_segundos=None):
        regiones.append(region_arg)
        yield 'event: notificacion\ndata: {"solicitud_id": 1}\n\n'

    monkeypatch.setattr(
        almacen_views.notificaciones, "suscribir_region", generador
    )
    respuesta = cliente_almacen.get(reverse("sse_almacen"))

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"].startswith("text/event-stream")
    assert respuesta["Cache-Control"] == "no-cache"
    cuerpo = b"".join(respuesta.streaming_content).decode()
    assert regiones == [region]
    assert "event: notificacion" in cuerpo
    assert '"solicitud_id": 1' in cuerpo


@pytest.mark.django_db
def test_sse_rechaza_a_tenant_y_anonimo(
    cliente_tenant, cliente_autenticado
):
    assert cliente_tenant.get(reverse("sse_almacen")).status_code == 403
    assert cliente_autenticado.get(reverse("sse_almacen")).status_code == 403


@pytest.mark.django_db
def test_tabla_bandeja_es_un_fragmento_para_refresco(
    cliente_almacen, almacen
):
    respuesta = cliente_almacen.get(reverse("tabla_bandeja_almacen"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "<table" in contenido
    assert "data-solicitud-id" in contenido or "No hay solicitudes" in contenido
    assert "<html" not in contenido
