"""Reintentos y registro del envío de asignaciones al almacén (007)."""

from datetime import date
from pathlib import Path

import pytest
from django.conf import settings
from django.core import mail
from django.urls import reverse

from asignaciones import almacen_services
from asignaciones.models import EnvioCorreo, EstadoSolicitud
from asignaciones.services import crear_y_enviar_solicitud
from stock.models import StockGeneral


def _solicitud(usuario_tenant, tenant, tecnico, material_no_seriado, cantidad=2):
    StockGeneral.objects.create(
        tenant=tenant,
        material=material_no_seriado,
        cantidad=10,
    )
    return crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": cantidad,
            }
        ],
        usuario_tenant,
    )


@pytest.mark.django_db
def test_tarea_programar_envia_en_eager(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    mail.outbox.clear()

    from asignaciones import tasks

    tasks.programar_envio_solicitud.delay(solicitud.pk)

    envio = EnvioCorreo.objects.get(solicitud=solicitud, numero_intento=1)
    assert envio.estado == EnvioCorreo.ESTADO_EXITOSO
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_programar_crea_intento_1_con_destinatario_archivo_y_hash(
    monkeypatch,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    programados = []
    monkeypatch.setattr(
        "asignaciones.tasks.enviar_excel_solicitud.apply_async",
        lambda *args, **kwargs: programados.append((args, kwargs)),
    )

    envio = almacen_services.programar_envio_solicitud(solicitud.pk)

    assert envio.numero_intento == 1
    assert envio.estado == EnvioCorreo.ESTADO_REINTENTANDO
    assert envio.destinatario == almacen.buzon
    assert envio.archivo == solicitud.excel_ruta
    assert envio.hash_sha256 == solicitud.excel_hash
    assert programados


@pytest.mark.django_db
def test_envio_exitoso_adjunta_excel_y_cierra_intento(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    mail.outbox.clear()

    envio = almacen_services.procesar_envio_solicitud(solicitud.pk, 1)

    assert envio.estado == EnvioCorreo.ESTADO_EXITOSO
    assert len(mail.outbox) == 1
    assert mail.outbox[0].attachments[0][0] == f"asignacion-{solicitud.pk}.xlsx"
    assert mail.outbox[0].to == [almacen.buzon]


@pytest.mark.django_db
def test_fallo_programa_intento_2_con_intervalo(
    monkeypatch,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    programados = []
    monkeypatch.setattr(
        "asignaciones.tasks.enviar_excel_solicitud.apply_async",
        lambda *args, **kwargs: programados.append((args, kwargs)),
    )
    monkeypatch.setattr(
        almacen_services,
        "_enviar_correo",
        lambda *args: (_ for _ in ()).throw(RuntimeError("smtp caido")),
    )

    envio = almacen_services.procesar_envio_solicitud(solicitud.pk, 1)

    assert envio.estado == EnvioCorreo.ESTADO_FALLIDO
    assert "smtp caido" in envio.error_mensaje
    siguiente = EnvioCorreo.objects.get(
        solicitud=solicitud, numero_intento=2
    )
    assert siguiente.estado == EnvioCorreo.ESTADO_REINTENTANDO
    assert programados[-1][1]["countdown"] == (
        settings.ENVIOS_INTERVALO_REINTENTO_SEGUNDOS
    )
    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.ENVIADA


@pytest.mark.django_db
def test_cuarto_fallo_es_definitivo_y_notifica_al_tenant(
    monkeypatch,
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    monkeypatch.setattr(
        "asignaciones.tasks.enviar_excel_solicitud.apply_async",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        almacen_services,
        "_enviar_correo",
        lambda *args: (_ for _ in ()).throw(RuntimeError("smtp caido")),
    )
    mail.outbox.clear()

    for intento in range(1, settings.ENVIOS_MAX_INTENTOS + 1):
        almacen_services.procesar_envio_solicitud(solicitud.pk, intento)

    assert EnvioCorreo.objects.filter(solicitud=solicitud).count() == 4
    assert not EnvioCorreo.objects.filter(
        solicitud=solicitud,
        estado=EnvioCorreo.ESTADO_REINTENTANDO,
    ).exists()
    assert almacen_services.envio_definitivo_fallido(solicitud)
    assert any(
        "No se pudo enviar la solicitud" in mensaje.subject
        for mensaje in mail.outbox
    )

    respuesta = cliente_tenant.get(
        reverse("detalle_asignacion", args=[solicitud.pk])
    )
    assert "No se pudo enviar el correo al almacén" in respuesta.content.decode()


@pytest.mark.django_db
def test_sin_archivo_registra_fallo_y_notifica(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    solicitud.excel_ruta = ""
    solicitud.excel_hash = ""
    solicitud.save(update_fields=["excel_ruta", "excel_hash"])
    mail.outbox.clear()

    envio = almacen_services.programar_envio_solicitud(solicitud.pk)

    assert envio.estado == EnvioCorreo.ESTADO_FALLIDO
    assert (
        envio.error_mensaje
        == "El archivo del Excel no está disponible o fue modificado"
    )
    assert any(
        "No se pudo enviar la solicitud" in mensaje.subject
        for mensaje in mail.outbox
    )


@pytest.mark.django_db
def test_broker_caido_deja_intento_fallido(
    monkeypatch,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    monkeypatch.setattr(
        "asignaciones.tasks.programar_envio_solicitud.delay",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("broker")),
    )

    almacen_services.encolar_envio_solicitud(solicitud.pk)

    envio = EnvioCorreo.objects.get(solicitud=solicitud, numero_intento=1)
    assert envio.estado == EnvioCorreo.ESTADO_FALLIDO
    assert envio.error_mensaje == "No se pudo programar el envío del correo"


@pytest.mark.django_db
def test_reenviar_un_intento_cerrado_no_duplica_correo(
    monkeypatch,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    mail.outbox.clear()

    almacen_services.procesar_envio_solicitud(solicitud.pk, 1)
    almacen_services.procesar_envio_solicitud(solicitud.pk, 1)

    assert EnvioCorreo.objects.filter(solicitud=solicitud).count() == 1
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_hash_alterado_bloquea_el_envio(
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    ruta = Path(settings.MEDIA_ROOT) / solicitud.excel_ruta
    ruta.write_bytes(b"alterado")

    envio = almacen_services.procesar_envio_solicitud(solicitud.pk, 1)

    assert envio.estado == EnvioCorreo.ESTADO_FALLIDO
    assert (
        envio.error_mensaje
        == "El archivo del Excel no está disponible o fue modificado"
    )
