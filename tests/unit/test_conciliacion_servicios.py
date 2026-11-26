"""Restricciones de modelos y clasificación de técnicos de conciliación."""

from datetime import date
from types import SimpleNamespace

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from acceso.models import Usuario
from conciliaciones import services
from conciliaciones.models import (
    Conciliacion,
    DiferenciaCantidad,
    DiferenciaSerie,
    EstadoConciliacion,
    MaterialNoCatalogado,
    TipoDiferenciaSerie,
)
from series.models import EstadoSerie, Serie
from tenants.models import Region, Tenant


def _conciliacion(tenant, usuario, **extra):
    datos = {
        "tenant": tenant,
        "region": tenant.region,
        "archivo_nombre": "reporte.xlsx",
        "hash_sha256": "a" * 64,
        "huella_stock": "b" * 64,
        "creado_por": usuario,
    }
    datos.update(extra)
    return Conciliacion.objects.create(**datos)


def _fila(nif):
    return SimpleNamespace(nif=nif)


# --- T006: restricciones de modelos -------------------------------------


@pytest.mark.django_db
def test_una_sola_conciliacion_en_revision_por_tenant(
    tenant, usuario_tenant
):
    _conciliacion(tenant, usuario_tenant)
    with pytest.raises(IntegrityError), transaction.atomic():
        _conciliacion(tenant, usuario_tenant)


@pytest.mark.django_db
def test_conciliacion_exige_estado_valido(tenant, usuario_tenant):
    with pytest.raises(IntegrityError), transaction.atomic():
        _conciliacion(tenant, usuario_tenant, estado="OTRO")


@pytest.mark.django_db
def test_conciliacion_exige_tenant_y_region(usuario_tenant):
    with pytest.raises(IntegrityError), transaction.atomic():
        Conciliacion.objects.create(
            archivo_nombre="x.xlsx",
            hash_sha256="a" * 64,
            huella_stock="b" * 64,
            creado_por=usuario_tenant,
        )


@pytest.mark.django_db
def test_diferencia_serie_unica_y_formato(
    tenant, usuario_tenant, tecnico, material_seriado
):
    conciliacion = _conciliacion(tenant, usuario_tenant)
    DiferenciaSerie.objects.create(
        tenant=tenant,
        conciliacion=conciliacion,
        tecnico=tecnico,
        material=material_seriado,
        numero="ABC123456789",
        tipo=TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        DiferenciaSerie.objects.create(
            tenant=tenant,
            conciliacion=conciliacion,
            tecnico=tecnico,
            material=material_seriado,
            numero="ABC123456789",
            tipo=TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        DiferenciaSerie.objects.create(
            tenant=tenant,
            conciliacion=conciliacion,
            tecnico=tecnico,
            material=material_seriado,
            numero="corto",
            tipo=TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA,
        )


@pytest.mark.django_db
def test_diferencia_serie_otro_tecnico_exige_tecnico_sistema(
    tenant, usuario_tenant, tecnico, material_seriado
):
    conciliacion = _conciliacion(tenant, usuario_tenant)
    with pytest.raises(IntegrityError), transaction.atomic():
        DiferenciaSerie.objects.create(
            tenant=tenant,
            conciliacion=conciliacion,
            tecnico=tecnico,
            material=material_seriado,
            numero="ABC123456789",
            tipo=TipoDiferenciaSerie.EN_OTRO_TECNICO,
        )


@pytest.mark.django_db
def test_diferencia_cantidad_no_negativa_y_calculada(
    tenant, usuario_tenant, tecnico, material_no_seriado
):
    conciliacion = _conciliacion(tenant, usuario_tenant)
    with pytest.raises(IntegrityError), transaction.atomic():
        DiferenciaCantidad.objects.create(
            tenant=tenant,
            conciliacion=conciliacion,
            tecnico=tecnico,
            material=material_no_seriado,
            cantidad_sistema=-1,
            cantidad_reporte=0,
            diferencia=1,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        DiferenciaCantidad.objects.create(
            tenant=tenant,
            conciliacion=conciliacion,
            tecnico=tecnico,
            material=material_no_seriado,
            cantidad_sistema=5,
            cantidad_reporte=10,
            diferencia=1,
        )


@pytest.mark.django_db
def test_material_no_catalogado_unico_por_conciliacion(
    tenant, usuario_tenant
):
    conciliacion = _conciliacion(tenant, usuario_tenant)
    MaterialNoCatalogado.objects.create(
        tenant=tenant, conciliacion=conciliacion, codigo="999"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        MaterialNoCatalogado.objects.create(
            tenant=tenant, conciliacion=conciliacion, codigo="999"
        )


@pytest.mark.django_db
def test_borrar_conciliacion_arrastra_diferencias(
    tenant, usuario_tenant, tecnico, material_no_seriado
):
    conciliacion = _conciliacion(tenant, usuario_tenant)
    DiferenciaCantidad.objects.create(
        tenant=tenant,
        conciliacion=conciliacion,
        tecnico=tecnico,
        material=material_no_seriado,
        cantidad_sistema=0,
        cantidad_reporte=1,
        diferencia=1,
    )
    conciliacion.delete()
    assert not DiferenciaCantidad.objects.exists()


# --- T009: clasificar_tecnicos ------------------------------------------


@pytest.mark.django_db
def test_clasificar_tecnicos_separa_presentes_e_ignorados(
    tenant, tecnico, usuario_otro_tenant
):
    from tecnicos.models import Tecnico

    tecnico_ajeno = Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA7777",
        nombre="Ajeno misma región",
        creado_por=usuario_otro_tenant,
    )
    clasificacion = services.clasificar_tecnicos(
        tenant, [_fila(tecnico.nif), _fila(tecnico_ajeno.nif)]
    )
    assert [t.pk for t in clasificacion.presentes] == [tecnico.pk]
    assert clasificacion.ignorados == {tecnico_ajeno.nif}


@pytest.mark.django_db
def test_clasificar_tecnicos_rechaza_nif_invalido(tenant):
    with pytest.raises(services.TecnicoFormatoInvalido):
        services.clasificar_tecnicos(tenant, [_fila("XX1")])


@pytest.mark.django_db
def test_clasificar_tecnicos_rechaza_desconocido(tenant):
    with pytest.raises(services.TecnicosFueraRegion):
        services.clasificar_tecnicos(tenant, [_fila("LA8888")])


@pytest.mark.django_db
def test_clasificar_tecnicos_rechaza_otra_region(
    tenant, usuario_admin
):
    otra = Region.objects.create(
        codigo="ARE", nombre="Arequipa", creado_por=usuario_admin
    )
    otro_tenant = Tenant.objects.create(
        codigo="TEN-ARE",
        nombre="Tenant Arequipa",
        region=otra,
        creado_por=usuario_admin,
    )
    Usuario.objects.create_user(
        email="are@lari.local",
        password="ClaveAre12345",
        rol="USUARIO_TENANT",
        tenant=otro_tenant,
        is_active=True,
    )
    from tecnicos.models import Tecnico

    Tecnico.objects.create(
        tenant=otro_tenant,
        nif="LA6666",
        nombre="Técnico Arequipa",
        creado_por=usuario_admin,
    )
    with pytest.raises(services.TecnicosFueraRegion):
        services.clasificar_tecnicos(tenant, [_fila("LA6666")])


# --- T013: contrato de excepciones --------------------------------------


def test_excepciones_de_conciliacion_heredan_del_error_base():
    nombres = [
        "PermisoDenegado",
        "ConciliacionEnRevision",
        "TecnicosFueraRegion",
        "TecnicoFormatoInvalido",
        "MaterialNoExiste",
        "SerieFormatoInvalido",
        "SerieDuplicada",
        "SerieInstalada",
        "SerieFueraTenant",
        "EstadoConciliacionInvalido",
        "AprobacionBloqueada",
        "HuboCambios",
        "NoEncontrado",
        "ArchivoNoDisponible",
        "MotivoInvalido",
    ]
    for nombre in nombres:
        clase = getattr(services, nombre)
        assert issubclass(clase, services.ErrorConciliacion), nombre
