"""Rechazo de una conciliación sin cambios de stock."""

import pytest

from auditoria.models import RegistroCambio
from conciliaciones.models import EstadoConciliacion
from conciliaciones.services import (
    EstadoConciliacionInvalido,
    MotivoInvalido,
    aprobar_conciliacion,
    crear_conciliacion,
    rechazar_conciliacion,
)
from stock.models import StockGeneral, StockTecnico
from tests.reportes import archivo_xlsx, fila_no_seriada, fila_seriada


@pytest.mark.django_db
def test_rechazo_conserva_motivo_auditoria_y_no_cambia_stock(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado, almacen
):
    stock = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_seriada(material_seriado, tecnico.nif, "ABC123456789"),
                fila_no_seriada(material_no_seriado, tecnico.nif, 2),
            ]
        ),
    )

    rechazar_conciliacion(conciliacion, usuario_tenant, "  Datos inconsistentes  ")

    conciliacion.refresh_from_db()
    stock.refresh_from_db()
    general.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.RECHAZADA
    assert conciliacion.motivo_rechazo == "Datos inconsistentes"
    assert conciliacion.fecha_rechazo is not None
    assert stock.cantidad == 10
    assert general.cantidad == 50
    assert RegistroCambio.objects.filter(
        entidad="Conciliacion",
        entidad_id=conciliacion.pk,
        campo="motivo_rechazo",
        valor_nuevo="Datos inconsistentes",
    ).exists()


@pytest.mark.django_db
def test_no_se_rechaza_dos_veces_ni_fuera_de_revision(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 1)]),
    )
    rechazar_conciliacion(conciliacion, usuario_tenant)
    with pytest.raises(EstadoConciliacionInvalido):
        rechazar_conciliacion(conciliacion, usuario_tenant)

    aprobada = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 3)]),
    )
    aprobar_conciliacion(aprobada, usuario_tenant)
    with pytest.raises(EstadoConciliacionInvalido):
        rechazar_conciliacion(aprobada, usuario_tenant)


@pytest.mark.django_db
def test_motivo_demasiado_largo_se_rechaza(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 1)]),
    )
    with pytest.raises(MotivoInvalido):
        rechazar_conciliacion(conciliacion, usuario_tenant, "x" * 1001)
    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.EN_REVISION
