"""Reinicio del stock inicial mediante comando de gestión (005)."""

from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from auditoria.models import RegistroCambio
from series.models import Serie
from stock.services import obtener_stock_tecnico
from stock_inicial.models import CargaStockInicial, LineaStockInicial
from stock_inicial.services import cargar_desde_formulario


def _cargar(
    tenant,
    usuario_tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
):
    return cargar_desde_formulario(
        tenant,
        {
            "lineas": [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 5,
                },
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_seriado.pk,
                    "series": "ABC123456789",
                },
            ]
        },
        usuario_tenant,
    )


def _ejecutar(tenant, usuario, confirmar=True):
    salida = StringIO()
    call_command(
        "reiniciar_stock_inicial",
        tenant=tenant.codigo,
        usuario=usuario.email,
        confirmar=confirmar,
        stdout=salida,
    )
    return salida.getvalue()


@pytest.mark.django_db
def test_reinicio_exitoso_limpia_carga_series_y_stock(
    monkeypatch,
    usuario_tenant,
    usuario_admin,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
):
    monkeypatch.setattr(
        settings, "PERMITIR_REINICIO_STOCK_INICIAL", True
    )
    carga = _cargar(
        tenant,
        usuario_tenant,
        tecnico,
        material_seriado,
        material_no_seriado,
    )
    assert CargaStockInicial.objects.count() == 1
    assert LineaStockInicial.objects.count() == 2
    assert Serie.objects.count() == 1
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 5
    assert obtener_stock_tecnico(tecnico, material_seriado) == 1

    salida = _ejecutar(tenant, usuario_admin, confirmar=True)

    tenant.refresh_from_db()
    assert "reiniciado" in salida.lower()
    assert not CargaStockInicial.objects.filter(pk=carga.pk).exists()
    assert LineaStockInicial.objects.count() == 0
    assert Serie.objects.count() == 0
    assert tenant.stock_inicial_cargado is False
    assert tenant.fecha_stock_inicial is None
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 0
    assert obtener_stock_tecnico(tecnico, material_seriado) == 0
    assert RegistroCambio.objects.filter(
        entidad="Tenant",
        entidad_id=tenant.pk,
        campo="stock_inicial_cargado",
    ).exists()


@pytest.mark.django_db
def test_sin_confirmar_no_cambia_nada(
    monkeypatch,
    usuario_tenant,
    usuario_admin,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
):
    monkeypatch.setattr(
        settings, "PERMITIR_REINICIO_STOCK_INICIAL", True
    )
    _cargar(
        tenant,
        usuario_tenant,
        tecnico,
        material_seriado,
        material_no_seriado,
    )

    salida = _ejecutar(tenant, usuario_admin, confirmar=False)

    assert "falta --confirmar" in salida.lower()
    assert CargaStockInicial.objects.count() == 1
    assert LineaStockInicial.objects.count() == 2
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 5


@pytest.mark.django_db
def test_reinicio_deshabilitado(
    monkeypatch,
    usuario_tenant,
    usuario_admin,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
):
    monkeypatch.setattr(
        settings, "PERMITIR_REINICIO_STOCK_INICIAL", False
    )
    _cargar(
        tenant,
        usuario_tenant,
        tecnico,
        material_seriado,
        material_no_seriado,
    )

    with pytest.raises(CommandError, match="deshabilitado"):
        _ejecutar(tenant, usuario_admin)

    assert CargaStockInicial.objects.count() == 1
    assert obtener_stock_tecnico(tecnico, material_no_seriado) == 5


@pytest.mark.django_db
def test_reinicio_solo_para_administrador(
    monkeypatch,
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
):
    monkeypatch.setattr(
        settings, "PERMITIR_REINICIO_STOCK_INICIAL", True
    )
    _cargar(
        tenant,
        usuario_tenant,
        tecnico,
        material_seriado,
        material_no_seriado,
    )

    with pytest.raises(CommandError, match="permiso"):
        _ejecutar(tenant, usuario_tenant)

    assert CargaStockInicial.objects.count() == 1


@pytest.mark.django_db
def test_reinicio_sin_carga(
    monkeypatch,
    usuario_admin,
    tenant,
):
    monkeypatch.setattr(
        settings, "PERMITIR_REINICIO_STOCK_INICIAL", True
    )

    with pytest.raises(CommandError, match="No hay stock inicial"):
        _ejecutar(tenant, usuario_admin)


@pytest.mark.django_db
def test_reinicio_tenant_o_usuario_inexistente(
    monkeypatch,
    usuario_admin,
    tenant,
):
    monkeypatch.setattr(
        settings, "PERMITIR_REINICIO_STOCK_INICIAL", True
    )

    with pytest.raises(CommandError, match="tenant no existe"):
        call_command(
            "reiniciar_stock_inicial",
            tenant="TEN-999",
            usuario=usuario_admin.email,
            confirmar=True,
            stdout=StringIO(),
        )

    with pytest.raises(CommandError, match="usuario no existe"):
        call_command(
            "reiniciar_stock_inicial",
            tenant=tenant.codigo,
            usuario="nadie@example.com",
            confirmar=True,
            stdout=StringIO(),
        )
