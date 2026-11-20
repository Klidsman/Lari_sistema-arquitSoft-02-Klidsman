"""Contrato de anulación lógica de recojos."""

from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from auditoria.models import RegistroCambio
from recojos.models import EstadoRecojo, Recojo
from recojos.services import crear_recojo
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral
from tecnicos.models import Tecnico


def _recojo_con_stock(usuario_tenant, material, almacen, **datos):
    return crear_recojo(
        {
            "nombre": "Recojo anulable",
            "fecha": date.today(),
            "lineas": [
                {
                    "material_id": material.pk,
                    "series": "ABC123456789",
                }
            ],
            **datos,
        },
        usuario_tenant,
    )


@pytest.mark.django_db
def test_anular_recojo(
    cliente_tenant, usuario_tenant, tenant, material_seriado, almacen
):
    recojo = _recojo_con_stock(usuario_tenant, material_seriado, almacen)

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]),
        {"motivo": "Error de carga"},
    )

    assert respuesta.status_code == 302
    recojo.refresh_from_db()
    assert recojo.estado == EstadoRecojo.ANULADO
    assert recojo.motivo_anulacion == "Error de carga"
    assert recojo.anulado_por_id == usuario_tenant.pk
    assert recojo.anulado_en is not None

    assert StockGeneral.objects.get(
        tenant=tenant, material=material_seriado
    ).cantidad == 0
    assert Serie.objects.get().estado == EstadoSerie.DISPONIBLE
    assert RegistroCambio.objects.filter(
        entidad="Recojo", entidad_id=recojo.pk, campo="estado"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="Serie", campo="reactivada"
    ).exists()


@pytest.mark.django_db
def test_motivo_obligatorio(
    cliente_tenant, usuario_tenant, material_seriado, almacen
):
    recojo = _recojo_con_stock(usuario_tenant, material_seriado, almacen)

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]),
        {"motivo": "   "},
    )

    assert respuesta.status_code == 400
    assert "El motivo de anulación es obligatorio" in respuesta.content.decode()
    recojo.refresh_from_db()
    assert recojo.estado == EstadoRecojo.REGISTRADO


@pytest.mark.django_db
def test_motivo_demasiado_largo(
    cliente_tenant, usuario_tenant, material_seriado, almacen
):
    recojo = _recojo_con_stock(usuario_tenant, material_seriado, almacen)

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]),
        {"motivo": "X" * 501},
    )

    assert respuesta.status_code == 400
    assert "El motivo no puede superar los 500 caracteres" in respuesta.content.decode()


@pytest.mark.django_db
def test_plazo_de_24_horas_vencido(
    cliente_tenant, usuario_tenant, material_seriado, almacen
):
    recojo = _recojo_con_stock(usuario_tenant, material_seriado, almacen)
    Recojo.objects.filter(pk=recojo.pk).update(
        creado_en=timezone.now() - timedelta(hours=25)
    )
    recojo.refresh_from_db()

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]),
        {"motivo": "Tarde"},
    )

    assert respuesta.status_code == 409
    assert "El plazo de 24 horas para anular este recojo venció" in respuesta.content.decode()
    recojo.refresh_from_db()
    assert recojo.estado == EstadoRecojo.REGISTRADO


@pytest.mark.django_db
def test_serie_utilizada_bloquea(
    cliente_tenant, usuario_tenant, tenant, material_seriado, almacen
):
    recojo = _recojo_con_stock(usuario_tenant, material_seriado, almacen)
    tecnico = Tecnico.objects.create(
        tenant=tenant,
        nif="LA1234",
        nombre="Juan",
        creado_por=usuario_tenant,
    )
    serie = Serie.objects.get()
    Serie.objects.filter(pk=serie.pk).update(
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
    )

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]),
        {"motivo": "Error"},
    )

    assert respuesta.status_code == 409
    assert "una serie ya fue utilizada" in respuesta.content.decode()


@pytest.mark.django_db
def test_stock_insuficiente_bloquea(
    cliente_tenant, usuario_tenant, tenant, material_seriado, almacen
):
    recojo = _recojo_con_stock(usuario_tenant, material_seriado, almacen)
    StockGeneral.objects.filter(tenant=tenant, material=material_seriado).update(
        cantidad=0
    )

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]),
        {"motivo": "Error"},
    )

    assert respuesta.status_code == 409
    assert "el stock del material ya fue utilizado" in respuesta.content.decode()


@pytest.mark.django_db
def test_recojo_ajeno_404(cliente_tenant, usuario_otro_tenant):
    ajeno = Recojo.objects.create(
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        nombre="Ajeno",
        fecha=date.today(),
        creado_por=usuario_otro_tenant,
    )

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[ajeno.pk]),
        {"motivo": "No"},
    )

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_admin_y_almacen_403(cliente_autenticado, cliente_almacen, recojo):
    for cliente in (cliente_autenticado, cliente_almacen):
        respuesta = cliente.post(
            reverse("anular_recojo", args=[recojo.pk]),
            {"motivo": "No"},
        )
        assert respuesta.status_code == 403


@pytest.mark.django_db
def test_get_y_delete_405(cliente_tenant, recojo):
    assert (
        cliente_tenant.get(reverse("anular_recojo", args=[recojo.pk])).status_code
        == 405
    )
    assert (
        cliente_tenant.delete(reverse("anular_recojo", args=[recojo.pk])).status_code
        == 405
    )


@pytest.mark.django_db
def test_doble_anulacion_no_duplica_auditoria(
    cliente_tenant, usuario_tenant, material_seriado, almacen
):
    recojo = _recojo_con_stock(usuario_tenant, material_seriado, almacen)
    cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]), {"motivo": "Error"}
    )
    antes = RegistroCambio.objects.filter(
        entidad="Recojo", entidad_id=recojo.pk
    ).count()

    respuesta = cliente_tenant.post(
        reverse("anular_recojo", args=[recojo.pk]), {"motivo": "Otra vez"}
    )

    assert respuesta.status_code == 302
    assert (
        RegistroCambio.objects.filter(
            entidad="Recojo", entidad_id=recojo.pk
        ).count()
        == antes
    )
