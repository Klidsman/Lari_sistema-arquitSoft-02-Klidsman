"""Concurrencia de devoluciones."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.utils import timezone

from acceso.models import Usuario
from logistica_inversa.services import (
    BajaNoEncontrada,
    NoEncontrado,
    obtener_baja,
    obtener_devolucion,
    registrar_baja_equipo,
    registrar_devolucion,
)
from logistica_inversa.models import BajaEquipo, Devolucion
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _devolver(tenant_id, tecnico_id, serie_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        from tecnicos.models import Tecnico
        from tenants.models import Tenant

        tenant = Tenant.objects.get(pk=tenant_id)
        tecnico = Tecnico.objects.get(pk=tecnico_id)
        serie = Serie.objects.get(pk=serie_id)
        actor = Usuario.objects.get(pk=actor_id)
        registrar_devolucion(
            tenant, tecnico, date.today(), [serie], "", actor
        )
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_devoluciones_simultaneas_de_la_misma_serie(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )

    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _devolver(
                    tenant.pk,
                    tecnico.pk,
                    serie.pk,
                    usuario_tenant.pk,
                    barrera,
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["SerieNoEnTecnico", "ok"]
    serie.refresh_from_db()
    general.refresh_from_db()
    assert serie.estado == EstadoSerie.DISPONIBLE
    assert serie.tecnico_id is None
    assert general.cantidad == 1


def _bajar(tenant_id, serie_id, actor_id, barrera):
    close_old_connections()
    barrera.wait()
    try:
        from tenants.models import Tenant

        tenant = Tenant.objects.get(pk=tenant_id)
        serie = Serie.objects.get(pk=serie_id)
        actor = Usuario.objects.get(pk=actor_id)
        registrar_baja_equipo(tenant, serie, "AVERIA", "", actor)
        return "ok"
    except Exception as exc:
        return type(exc).__name__
    finally:
        connection.close()


@pytest.mark.django_db(transaction=True)
def test_dos_bajas_simultaneas_de_la_misma_serie(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    tecnico_stock = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )

    barrera = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(
            executor.map(
                lambda _: _bajar(
                    tenant.pk, serie.pk, usuario_tenant.pk, barrera
                ),
                range(2),
            )
        )

    assert sorted(resultados) == ["SerieYaInactiva", "ok"]
    assert BajaEquipo.objects.count() == 1
    tecnico_stock.refresh_from_db()
    assert tecnico_stock.cantidad == 0


@pytest.mark.django_db
def test_aislamiento_y_rls_de_logistica_inversa(
    usuario_tenant,
    usuario_otro_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
):
    serie = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario_tenant,
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    devolucion = registrar_devolucion(
        tenant, tecnico, date.today(), [serie], "", usuario_tenant
    )
    baja = registrar_baja_equipo(
        tenant,
        Serie.objects.create(
            numero="SER000000002",
            tenant=tenant,
            region=tenant.region,
            material=material_seriado,
            lote=material_seriado.lote,
            estado=EstadoSerie.DISPONIBLE,
            creado_por=usuario_tenant,
        ),
        "AVERIA",
        "",
        usuario_tenant,
    )
    ajeno = usuario_otro_tenant.tenant
    with pytest.raises(NoEncontrado):
        obtener_devolucion(ajeno, devolucion.pk)
    with pytest.raises(BajaNoEncontrada):
        obtener_baja(ajeno, baja.pk)

    with connection.cursor() as cursor:
        for tabla in (
            Devolucion._meta.db_table,
            BajaEquipo._meta.db_table,
        ):
            cursor.execute(
                "SELECT relrowsecurity FROM pg_class WHERE relname = %s",
                [tabla],
            )
            fila = cursor.fetchone()
            assert fila is not None, tabla
            assert fila[0] is True, tabla


@pytest.mark.django_db
def test_devolucion_de_cien_series_en_menos_de_dos_segundos(
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    almacen,
    django_assert_max_num_queries,
):
    import time

    series = [
        Serie.objects.create(
            numero=f"SER{indice:09d}",
            tenant=tenant,
            region=tenant.region,
            material=material_seriado,
            lote=material_seriado.lote,
            estado=EstadoSerie.ASIGNADA,
            tecnico=tecnico,
            asignada_en=timezone.now(),
            creado_por=usuario_tenant,
        )
        for indice in range(100)
    ]
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=100
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )

    inicio = time.perf_counter()
    with django_assert_max_num_queries(800):
        registrar_devolucion(
            tenant, tecnico, date.today(), series, "", usuario_tenant
        )
    duracion = time.perf_counter() - inicio

    general.refresh_from_db()
    assert general.cantidad == 100
    assert duracion < 2
