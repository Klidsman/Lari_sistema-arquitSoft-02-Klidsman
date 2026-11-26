"""Concurrencia de la aprobación de conciliaciones."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection

from acceso.models import Usuario
from conciliaciones.models import Conciliacion, EstadoConciliacion
from conciliaciones.services import aprobar_conciliacion, crear_conciliacion
from stock.models import StockTecnico
from tests.reportes import archivo_xlsx, fila_no_seriada


def _aprobar(conciliacion_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        conciliacion = Conciliacion.objects.get(pk=conciliacion_id)
        actor = Usuario.objects.get(pk=actor_id)
        aprobar_conciliacion(conciliacion, actor)
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


def _cargar(usuario_id, tecnico_nif, material_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        from materiales.models import Material
        from tecnicos.models import Tecnico

        actor = Usuario.objects.get(pk=usuario_id)
        tecnico = Tecnico.objects.get(nif=tecnico_nif)
        material = Material.objects.get(pk=material_id)
        crear_conciliacion(
            actor,
            archivo_xlsx(
                [fila_no_seriada(material, tecnico.nif, 1)]
            ),
        )
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_cargas_simultaneas_dejan_una_sola_en_revision(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _cargar(
                    usuario_tenant.pk,
                    tecnico.nif,
                    material_no_seriado.pk,
                    barrera,
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["ConciliacionEnRevision", "ok"]
    assert (
        Conciliacion.objects.filter(
            tenant=tenant, estado=EstadoConciliacion.EN_REVISION
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_dos_aprobaciones_simultaneas_aplican_una_sola_vez(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_no_seriada(material_no_seriado, tecnico.nif, 4)]
        ),
    )
    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _aprobar(
                    conciliacion.pk, usuario_tenant.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["EstadoConciliacionInvalido", "ok"]
    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.APROBADA
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 4
    )
