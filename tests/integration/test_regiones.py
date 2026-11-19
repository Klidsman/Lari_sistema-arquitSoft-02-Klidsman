"""Integración de regiones, almacenes y auditoría."""

import pytest
from django.db import IntegrityError, transaction

from acceso.models import Rol, Usuario
from auditoria.models import RegistroCambio
from tenants.models import Almacen, Region
from tenants.services import (
    RegionDuplicada,
    RegionInvalida,
    TenantInvalido,
    actualizar_region,
    crear_region,
    crear_tenant,
)


def _datos(**cambios):
    datos = {
        "codigo": "ARE",
        "nombre": "Arequipa",
        "centro": "PR05",
        "almacen": "BE03",
        "buzon": "almacen.are@lari.local",
    }
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_crear_region_guarda_region_almacen_y_auditoria(usuario_admin):
    region = crear_region(_datos(), usuario_admin)

    assert Region.objects.filter(pk=region.pk).exists()
    assert Almacen.objects.filter(region=region).count() == 1
    assert RegistroCambio.objects.filter(
        entidad="Region", entidad_id=region.pk, campo="alta"
    ).count() == 1
    almacen = region.almacen
    assert RegistroCambio.objects.filter(
        entidad="Almacen", entidad_id=almacen.pk, campo="alta"
    ).count() == 1


@pytest.mark.django_db
def test_crear_region_es_atomico(usuario_admin, monkeypatch):
    def auditoria_que_falla(*args, **kwargs):
        raise RuntimeError("falla de auditoría")

    monkeypatch.setattr("tenants.services.registrar_cambio", auditoria_que_falla)

    with pytest.raises(RuntimeError):
        crear_region(_datos(), usuario_admin)

    assert not Region.objects.filter(codigo="ARE").exists()
    assert not Almacen.objects.filter(codigo_almacen="BE03").exists()


@pytest.mark.django_db
def test_crear_region_codigo_duplicado(usuario_admin, region):
    with pytest.raises(RegionDuplicada):
        crear_region(_datos(codigo="LIM"), usuario_admin)


@pytest.mark.django_db
def test_codigo_duplicado_falla_por_restriccion_unica(usuario_admin, region):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Region.objects.create(
                codigo="LIM",
                nombre="Otra Lima",
                creado_por=usuario_admin,
            )


@pytest.mark.django_db
def test_actualizar_region_audita_cada_campo(usuario_admin, region, almacen):
    actualizar_region(
        region,
        {
            "nombre": "Lima Norte",
            "centro": "PR09",
            "almacen": "BE09",
            "buzon": "nuevo.lim@lari.local",
            "activa": False,
        },
        usuario_admin,
    )

    region.refresh_from_db()
    almacen.refresh_from_db()

    assert region.nombre == "Lima Norte"
    assert region.activa is False
    assert almacen.centro == "PR09"
    assert almacen.codigo_almacen == "BE09"
    assert almacen.activo is False

    esperados = {
        "nombre": ("Lima", "Lima Norte"),
        "activa": ("True", "False"),
    }
    for campo, (anterior, nuevo) in esperados.items():
        registro = RegistroCambio.objects.get(
            entidad="Region", entidad_id=region.pk, campo=campo
        )
        assert registro.valor_anterior == anterior
        assert registro.valor_nuevo == nuevo

    registro = RegistroCambio.objects.get(
        entidad="Almacen", entidad_id=almacen.pk, campo="centro"
    )
    assert registro.valor_anterior == "PR05"
    assert registro.valor_nuevo == "PR09"


@pytest.mark.django_db
def test_actualizar_region_no_cambia_codigo(usuario_admin, region):
    with pytest.raises(RegionInvalida):
        actualizar_region(region, {"codigo": "OTRO"}, usuario_admin)


@pytest.mark.django_db
def test_region_inactiva_impide_nuevos_tenants(usuario_admin, region, almacen):
    actualizar_region(
        region,
        {
            "nombre": region.nombre,
            "centro": region.almacen.centro,
            "almacen": region.almacen.codigo_almacen,
            "buzon": region.almacen.buzon,
            "activa": False,
        },
        usuario_admin,
    )

    with pytest.raises(TenantInvalido, match="La región seleccionada no está disponible"):
        crear_tenant(
            {"codigo": "TEN-002", "nombre": "Nuevo", "region": region},
            usuario_admin,
        )


@pytest.mark.django_db
def test_solo_admin_plataforma_crea_region(usuario_tenant, region):
    with pytest.raises(Exception):
        crear_region(_datos(), usuario_tenant)
