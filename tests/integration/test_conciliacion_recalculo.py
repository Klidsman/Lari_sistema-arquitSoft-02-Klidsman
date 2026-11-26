"""Recálculo de diferencias cuando cambió el stock."""

import pytest

from auditoria.models import RegistroCambio
from conciliaciones.models import EstadoConciliacion
from conciliaciones.services import (
    EstadoConciliacionInvalido,
    aprobar_conciliacion,
    crear_conciliacion,
    rechazar_conciliacion,
    recalcular_diferencias,
)
from stock.models import StockGeneral, StockTecnico
from tests.reportes import archivo_xlsx, fila_no_seriada


@pytest.mark.django_db
def test_recalculo_reemplaza_diferencias_sin_tocar_stock(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    stock = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=100
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 4)]),
    )
    StockTecnico.objects.filter(pk=stock.pk).update(cantidad=7)

    recalcular_diferencias(conciliacion, usuario_tenant)

    conciliacion.refresh_from_db()
    stock.refresh_from_db()
    general.refresh_from_db()
    diferencia = conciliacion.diferencias_cantidades.get()
    assert diferencia.cantidad_sistema == 7
    assert diferencia.cantidad_reporte == 4
    assert conciliacion.requiere_revision is True
    assert stock.cantidad == 7
    assert general.cantidad == 100
    assert RegistroCambio.objects.filter(
        entidad="Conciliacion",
        entidad_id=conciliacion.pk,
        campo="recalculo",
    ).exists()


@pytest.mark.django_db
def test_tras_recalcular_la_aprobacion_aplica_datos_frescos(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    stock = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 4)]),
    )
    StockTecnico.objects.filter(pk=stock.pk).update(cantidad=7)

    recalcular_diferencias(conciliacion, usuario_tenant)
    aprobar_conciliacion(conciliacion, usuario_tenant)

    conciliacion.refresh_from_db()
    stock.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.APROBADA
    assert conciliacion.requiere_revision is False
    assert stock.cantidad == 4


@pytest.mark.django_db
def test_no_se_recalcula_una_conciliacion_cerrada(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    aprobada = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 1)]),
    )
    aprobar_conciliacion(aprobada, usuario_tenant)
    with pytest.raises(EstadoConciliacionInvalido):
        recalcular_diferencias(aprobada, usuario_tenant)

    rechazada = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 2)]),
    )
    rechazar_conciliacion(rechazada, usuario_tenant, "no procede")
    with pytest.raises(EstadoConciliacionInvalido):
        recalcular_diferencias(rechazada, usuario_tenant)
