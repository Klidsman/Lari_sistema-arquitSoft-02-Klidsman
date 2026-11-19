"""Traspasos: creación, envío y confirmación."""

import hashlib
from datetime import date, timedelta
from pathlib import Path

import openpyxl
import pytest
from django.conf import settings
from django.utils import timezone

from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico
from tecnicos.models import Tecnico
from traspasos.models import EstadoTraspaso
from traspasos.services import (
    ArchivoAlterado,
    EstadoTraspasoInvalido,
    TraspasoNoExiste,
    ValidacionTraspaso,
    calcular_disponible,
    cancelar_traspaso,
    confirmar_traspaso,
    crear_borrador_traspaso,
    enviar_traspaso,
    obtener_traspaso,
    rechazar_traspaso,
    verificar_excel,
)


def _destino(tenant, usuario_tenant):
    return Tecnico.objects.create(
        tenant=tenant,
        nif="LA2222",
        nombre="Destino",
        creado_por=usuario_tenant,
    )


def _serie_asignada(tenant, material, tecnico, usuario_tenant):
    return Serie.objects.create(
        numero="TRAS12345678",
        tenant=tenant,
        region=tenant.region,
        material=material,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now() - timedelta(days=30),
        creado_por=usuario_tenant,
    )


@pytest.mark.django_db
def test_traspaso_seriado_confirma(
    usuario_tenant, usuario_almacen, tenant, tecnico, material_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    serie = _serie_asignada(tenant, material_seriado, tecnico, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=5
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=destino, material=material_seriado, cantidad=0
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_seriado.pk, "serie_ids": [serie.pk]}],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    confirmar_traspaso(traspaso, usuario_almacen)

    traspaso.refresh_from_db()
    serie.refresh_from_db()
    assert traspaso.estado == EstadoTraspaso.CONFIRMADA
    assert serie.tecnico_id == destino.pk
    assert serie.estado == EstadoSerie.ASIGNADA
    assert StockTecnico.objects.get(tecnico=tecnico, material=material_seriado).cantidad == 4
    assert StockTecnico.objects.get(tecnico=destino, material=material_seriado).cantidad == 1


@pytest.mark.django_db
def test_traspaso_no_seriado_confirma(
    usuario_tenant, usuario_almacen, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=destino, material=material_no_seriado, cantidad=0
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    confirmar_traspaso(traspaso, usuario_almacen)

    assert StockTecnico.objects.get(tecnico=tecnico, material=material_no_seriado).cantidad == 6
    assert StockTecnico.objects.get(tecnico=destino, material=material_no_seriado).cantidad == 4


@pytest.mark.django_db
def test_rechazo_no_mueve_stock(
    usuario_tenant, usuario_almacen, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    rechazar_traspaso(traspaso, "No procede", usuario_almacen)

    traspaso.refresh_from_db()
    assert traspaso.estado == EstadoTraspaso.RECHAZADA
    assert StockTecnico.objects.get(tecnico=tecnico, material=material_no_seriado).cantidad == 10


@pytest.mark.django_db
def test_destino_inactivo_rechazado(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    destino.activo = False
    destino.save(update_fields=["activo"])
    from traspasos.services import ValidacionTraspaso

    with pytest.raises(ValidacionTraspaso, match="no está activo"):
        crear_borrador_traspaso(
            tenant,
            tecnico.pk,
            destino.pk,
            date.today(),
            [{"material_id": material_no_seriado.pk, "cantidad": 1}],
            usuario_tenant,
        )


@pytest.mark.django_db
def test_origen_y_destino_iguales_se_rechaza(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    with pytest.raises(ValidacionTraspaso, match="no pueden ser el mismo"):
        crear_borrador_traspaso(
            tenant,
            tecnico.pk,
            tecnico.pk,
            date.today(),
            [{"material_id": material_no_seriado.pk, "cantidad": 1}],
            usuario_tenant,
        )


@pytest.mark.django_db
def test_cantidad_supera_stock_del_tecnico(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    with pytest.raises(ValidacionTraspaso, match="supera el stock del técnico"):
        crear_borrador_traspaso(
            tenant,
            tecnico.pk,
            destino.pk,
            date.today(),
            [{"material_id": material_no_seriado.pk, "cantidad": 15}],
            usuario_tenant,
        )


@pytest.mark.django_db
def test_envio_genera_excel_dos_hojas_con_hash(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    assert traspaso.excel_ruta == ""
    enviar_traspaso(traspaso, usuario_tenant)
    traspaso.refresh_from_db()

    ruta = Path(settings.MEDIA_ROOT) / traspaso.excel_ruta
    assert ruta.exists()
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == traspaso.excel_hash

    libro = openpyxl.load_workbook(ruta)
    try:
        assert libro.sheetnames == ["Desasignación", "Asignación"]
        salida, entrada = libro["Desasignación"], libro["Asignación"]
        assert salida["B1"].value == "Z32"
        assert entrada["B1"].value == "Z31"
        assert salida["B4"].value == tecnico.nif
        assert entrada["B4"].value == destino.nif
        assert salida["B6"].value == tenant.codigo
        assert salida["B7"].value == tenant.region.codigo
        assert salida["A10"].value == "Seriales"
        assert salida["A13"].value == "Material menor"
        assert salida["A14"].value == "Código"
        assert salida["A15"].value == material_no_seriado.codigo
        assert salida["D15"].value == 4
        assert entrada["D15"].value == 4
    finally:
        libro.close()


@pytest.mark.django_db
def test_borrador_no_reserva_ni_mueve_stock(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    assert calcular_disponible(tecnico, material_no_seriado) == 10
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    assert calcular_disponible(tecnico, material_no_seriado) == 10
    assert not traspaso.excel_ruta
    assert StockTecnico.objects.get(tecnico=tecnico, material=material_no_seriado).cantidad == 10

    enviar_traspaso(traspaso, usuario_tenant)
    assert calcular_disponible(tecnico, material_no_seriado) == 6
    assert StockTecnico.objects.get(tecnico=tecnico, material=material_no_seriado).cantidad == 10


@pytest.mark.django_db
def test_rechazo_libera_reserva(
    usuario_tenant, usuario_almacen, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    assert calcular_disponible(tecnico, material_no_seriado) == 6
    rechazar_traspaso(traspaso, "No procede", usuario_almacen)
    assert calcular_disponible(tecnico, material_no_seriado) == 10


@pytest.mark.django_db
def test_confirmar_reinicia_asignada_en_y_no_toca_stock_general(
    usuario_tenant, usuario_almacen, tenant, tecnico, material_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    serie = _serie_asignada(tenant, material_seriado, tecnico, usuario_tenant)
    asignada_antes = timezone.now() - timedelta(days=10)
    Serie.objects.filter(pk=serie.pk).update(asignada_en=asignada_antes)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=destino, material=material_seriado, cantidad=0
    )
    stock_general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=100
    )

    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_seriado.pk, "serie_ids": [serie.pk]}],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    confirmar_traspaso(traspaso, usuario_almacen)

    serie.refresh_from_db()
    stock_general.refresh_from_db()
    assert serie.tecnico_id == destino.pk
    assert serie.estado == EstadoSerie.ASIGNADA
    assert serie.asignada_en > asignada_antes
    assert stock_general.cantidad == 100


@pytest.mark.django_db
def test_cancelar_borrador_no_genera_reserva(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    cancelar_traspaso(traspaso, usuario_tenant)
    traspaso.refresh_from_db()
    assert traspaso.estado == EstadoTraspaso.CANCELADA
    assert calcular_disponible(tecnico, material_no_seriado) == 10

    with pytest.raises(EstadoTraspasoInvalido):
        enviar_traspaso(traspaso, usuario_tenant)


@pytest.mark.django_db
def test_hash_alterado_bloquea_la_descarga(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    enviar_traspaso(traspaso, usuario_tenant)
    traspaso.refresh_from_db()
    ruta = Path(settings.MEDIA_ROOT) / traspaso.excel_ruta
    ruta.write_bytes(ruta.read_bytes() + b"alterado")

    with pytest.raises(ArchivoAlterado):
        verificar_excel(traspaso)


@pytest.mark.django_db
def test_tenant_ajeno_no_accede_al_traspaso(
    usuario_tenant, usuario_otro_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    traspaso = crear_borrador_traspaso(
        tenant,
        tecnico.pk,
        destino.pk,
        date.today(),
        [{"material_id": material_no_seriado.pk, "cantidad": 4}],
        usuario_tenant,
    )
    with pytest.raises(TraspasoNoExiste):
        obtener_traspaso(usuario_otro_tenant.tenant, traspaso.pk)

