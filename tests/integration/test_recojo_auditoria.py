"""Auditoría de recojos y stock."""

from datetime import date

import pytest

from acceso.models import Usuario
from auditoria.models import RegistroCambio
from recojos.services import crear_recojo
from stock.models import StockGeneral
from tenants.models import Tenant


@pytest.mark.django_db
def test_auditoria_de_alta_y_stock(
    usuario_tenant, tenant, material_seriado, material_no_seriado, almacen, registro_cambios
):
    recojo = crear_recojo(
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [
                {"material_id": material_seriado.pk, "series": "ABC123456789"},
                {"material_id": material_no_seriado.pk, "cantidad": 4},
            ],
        },
        usuario_tenant,
    )

    alta = registro_cambios(recojo).get(campo="alta")
    assert "fecha=" in alta.valor_nuevo
    assert "series=1" in alta.valor_nuevo
    assert "cantidad=4" in alta.valor_nuevo

    stock = StockGeneral.objects.get(
        tenant=tenant, material=material_no_seriado
    )
    cambio = registro_cambios(stock, entidad="StockGeneral").get(campo="cantidad")
    assert cambio.valor_anterior == "0"
    assert cambio.valor_nuevo == "4"


@pytest.mark.django_db
def test_auditoria_sin_secretos(
    usuario_tenant, material_no_seriado, almacen
):
    recojo = crear_recojo(
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [{"material_id": material_no_seriado.pk, "cantidad": 1}],
        },
        usuario_tenant,
    )

    prohibidos = ("password", "contraseña", "token", "secreto", "tenant_id")
    for registro in RegistroCambio.objects.filter(entidad__in=["Recojo", "StockGeneral"]):
        texto = " ".join(
            [registro.campo, registro.valor_anterior, registro.valor_nuevo]
        ).lower()
        for prohibido in prohibidos:
            assert prohibido not in texto


@pytest.mark.django_db
def test_auditoria_se_conserva_al_suspender(
    usuario_tenant, tenant, material_no_seriado, almacen
):
    recojo = crear_recojo(
        {
            "nombre": "Recojo de prueba", "fecha": date.today(),
            "lineas": [{"material_id": material_no_seriado.pk, "cantidad": 1}],
        },
        usuario_tenant,
    )
    Usuario.objects.filter(pk=usuario_tenant.pk).update(is_active=False)
    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)

    assert RegistroCambio.objects.filter(
        entidad="Recojo", entidad_id=recojo.pk
    ).exists()
