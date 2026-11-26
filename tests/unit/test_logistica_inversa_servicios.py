"""Restricciones y validadores de logística inversa."""

from datetime import date, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from logistica_inversa import services
from logistica_inversa.models import BajaEquipo, Devolucion, LineaDevolucion
from series.models import EstadoSerie, Serie


def _devolucion(tenant, tecnico, actor, **extra):
    datos = {
        "tenant": tenant,
        "region": tenant.region,
        "tecnico": tecnico,
        "fecha": date.today(),
        "creado_por": actor,
    }
    datos.update(extra)
    return Devolucion.objects.create(**datos)


def _serie(
    tenant,
    material,
    actor,
    estado=EstadoSerie.ASIGNADA,
    tecnico=None,
    numero="SER000000001",
):
    asignada = estado == EstadoSerie.ASIGNADA
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=estado,
        tecnico=tecnico if asignada else None,
        asignada_en=timezone.now() if asignada else None,
        creado_por=actor,
    )


# --- T006: restricciones de modelos -------------------------------------


@pytest.mark.django_db
def test_devolucion_exige_tenant_region_tecnico_y_fecha(
    tenant, tecnico, usuario_tenant
):
    with pytest.raises(IntegrityError), transaction.atomic():
        Devolucion.objects.create(creado_por=usuario_tenant)


@pytest.mark.django_db
def test_linea_devolucion_unica_por_serie(
    tenant, tecnico, material_seriado, usuario_tenant
):
    devolucion = _devolucion(tenant, tecnico, usuario_tenant)
    serie = _serie(tenant, material_seriado, usuario_tenant, tecnico=tecnico)
    LineaDevolucion.objects.create(
        tenant=tenant,
        devolucion=devolucion,
        serie=serie,
        material=material_seriado,
        descripcion=material_seriado.descripcion,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        LineaDevolucion.objects.create(
            tenant=tenant,
            devolucion=devolucion,
            serie=serie,
            material=material_seriado,
            descripcion=material_seriado.descripcion,
        )


@pytest.mark.django_db
def test_borrar_devolucion_arrastra_lineas(
    tenant, tecnico, material_seriado, usuario_tenant
):
    devolucion = _devolucion(tenant, tecnico, usuario_tenant)
    LineaDevolucion.objects.create(
        tenant=tenant,
        devolucion=devolucion,
        serie=_serie(tenant, material_seriado, usuario_tenant, tecnico=tecnico),
        material=material_seriado,
        descripcion=material_seriado.descripcion,
    )
    devolucion.delete()
    assert not LineaDevolucion.objects.exists()


@pytest.mark.django_db
def test_baja_es_una_por_serie_y_causa_valida(
    tenant, material_seriado, usuario_tenant
):
    serie = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.INACTIVA,
    )
    BajaEquipo.objects.create(
        tenant=tenant,
        region=tenant.region,
        serie=serie,
        material=material_seriado,
        causa="AVERIA",
        creado_por=usuario_tenant,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        BajaEquipo.objects.create(
            tenant=tenant,
            region=tenant.region,
            serie=serie,
            material=material_seriado,
            causa="MIGRACION",
            creado_por=usuario_tenant,
        )
    otra = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.INACTIVA,
        numero="SER000000002",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        BajaEquipo.objects.create(
            tenant=tenant,
            region=tenant.region,
            serie=otra,
            material=material_seriado,
            causa="ROBO",
            creado_por=usuario_tenant,
        )


# --- T009: validadores --------------------------------------------------


@pytest.mark.django_db
def test_validar_cuenta_tenant(
    usuario_admin, usuario_otro_tenant, usuario_tenant, tenant
):
    with pytest.raises(services.PermisoDenegado):
        services.validar_cuenta_tenant(usuario_admin)
    with pytest.raises(services.PermisoDenegado):
        services.validar_cuenta_tenant(usuario_otro_tenant, tenant)
    assert services.validar_cuenta_tenant(usuario_tenant).pk == tenant.pk


@pytest.mark.django_db
def test_validar_tecnico_rechaza_otro_tenant(
    tenant, tecnico, tecnico_otro_tenant
):
    assert services.validar_tecnico(tenant, tecnico).pk == tecnico.pk
    with pytest.raises(services.TecnicoNoExiste):
        services.validar_tecnico(tenant, tecnico_otro_tenant)


def test_validar_fecha_devolucion():
    assert services.validar_fecha_devolucion(date.today()) == date.today()
    assert services.validar_fecha_devolucion(
        date.today().isoformat()
    ) == date.today()
    with pytest.raises(services.FechaInvalida):
        services.validar_fecha_devolucion(
            date.today() + timedelta(days=1)
        )
    with pytest.raises(services.FechaInvalida):
        services.validar_fecha_devolucion("no-es-fecha")


@pytest.mark.django_db
def test_validar_serie_para_devolucion(
    tenant, tecnico, material_seriado, usuario_tenant
):
    propia = _serie(
        tenant, material_seriado, usuario_tenant, tecnico=tecnico
    )
    assert services.validar_serie_para_devolucion(propia, tecnico).pk == propia.pk

    otra = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.DISPONIBLE,
        numero="SER000000002",
    )
    with pytest.raises(services.SerieNoEnTecnico):
        services.validar_serie_para_devolucion(otra, tecnico)

    reservada = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.RESERVADA,
        numero="SER000000003",
    )
    with pytest.raises(services.SerieReservada):
        services.validar_serie_para_devolucion(reservada, tecnico)

    instalada = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.INSTALADA,
        numero="SER000000004",
    )
    with pytest.raises(services.SerieInstalada):
        services.validar_serie_para_devolucion(instalada, tecnico)

    inactiva = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.INACTIVA,
        numero="SER000000005",
    )
    with pytest.raises(services.SerieYaInactiva):
        services.validar_serie_para_devolucion(inactiva, tecnico)


@pytest.mark.django_db
def test_validar_serie_para_baja(
    tenant, material_seriado, usuario_tenant
):
    disponible = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.DISPONIBLE,
    )
    assert services.validar_serie_para_baja(disponible, tenant).pk == disponible.pk

    inactiva = _serie(
        tenant,
        material_seriado,
        usuario_tenant,
        estado=EstadoSerie.INACTIVA,
        numero="SER000000002",
    )
    with pytest.raises(services.SerieYaInactiva):
        services.validar_serie_para_baja(inactiva, tenant)


@pytest.mark.django_db
def test_resolver_series_deduplica_y_rechaza_vacias(
    tenant, tecnico, material_seriado, usuario_tenant
):
    serie = _serie(
        tenant, material_seriado, usuario_tenant, tecnico=tecnico
    )
    assert services._resolver_series(tenant, [serie, serie]) == [serie]
    with pytest.raises(services.SinSeries):
        services._resolver_series(tenant, [])
    with pytest.raises(services.SerieFueraTenant):
        services._resolver_series(tenant, [999999])
