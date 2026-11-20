"""Integración de tenants."""

import pytest
from django.db import IntegrityError, transaction

from auditoria.models import RegistroCambio
from tenants.models import Tenant
from tenants.services import (
    TenantDuplicado,
    TenantInvalido,
    actualizar_tenant,
    crear_tenant,
)


@pytest.mark.django_db
def test_crear_tenant_guarda_y_audita(usuario_admin, region):
    tenant = crear_tenant(
        {"codigo": "ten-100", "nombre": "Nuevo tenant", "region": region.pk},
        usuario_admin,
    )

    assert tenant.codigo == "TEN-100"
    assert tenant.estado == Tenant.ESTADO_ACTIVO
    assert tenant.region_id == region.pk
    assert RegistroCambio.objects.filter(
        entidad="Tenant", entidad_id=tenant.pk, campo="alta"
    ).count() == 1


@pytest.mark.django_db
def test_crear_tenant_es_atomico(usuario_admin, region, monkeypatch):
    def auditoria_que_falla(*args, **kwargs):
        raise RuntimeError("falla de auditoría")

    monkeypatch.setattr("tenants.services.registrar_cambio", auditoria_que_falla)

    with pytest.raises(RuntimeError):
        crear_tenant(
            {"codigo": "TEN-100", "nombre": "Nuevo", "region": region.pk},
            usuario_admin,
        )

    assert not Tenant.objects.filter(codigo="TEN-100").exists()


@pytest.mark.django_db
def test_crear_tenant_sin_region(usuario_admin):
    with pytest.raises(TenantInvalido, match="El tenant debe pertenecer a una región"):
        crear_tenant({"codigo": "TEN-100", "nombre": "Sin región"}, usuario_admin)


@pytest.mark.django_db
def test_crear_tenant_region_inactiva(usuario_admin, region):
    region.activa = False
    region.save(update_fields=["activa"])

    with pytest.raises(
        TenantInvalido, match="La región seleccionada no está disponible"
    ):
        crear_tenant(
            {"codigo": "TEN-100", "nombre": "Nuevo", "region": region.pk},
            usuario_admin,
        )


@pytest.mark.django_db
def test_crear_tenant_codigo_duplicado(usuario_admin, tenant):
    with pytest.raises(TenantDuplicado):
        crear_tenant(
            {"codigo": "TEN-001", "nombre": "Duplicado", "region": tenant.region_id},
            usuario_admin,
        )


@pytest.mark.django_db
def test_codigo_duplicado_falla_por_restriccion_unica(usuario_admin, tenant):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Tenant.objects.create(
                codigo=tenant.codigo,
                nombre="Duplicado",
                region=tenant.region,
                creado_por=usuario_admin,
            )


@pytest.mark.django_db
def test_actualizar_tenant_no_permite_cambiar_region(usuario_admin, tenant, region):
    from tenants.models import Region

    otra = Region.objects.create(
        codigo="TRU",
        nombre="Trujillo",
        creado_por=usuario_admin,
    )

    with pytest.raises(
        TenantInvalido, match="La región del tenant no se puede cambiar"
    ):
        actualizar_tenant(tenant, {"region": otra.pk}, usuario_admin)

    tenant.refresh_from_db()
    assert tenant.region_id == region.pk


def test_formulario_edicion_no_expone_region():
    from tenants.forms import TenantEdicionForm

    assert "region" not in TenantEdicionForm().fields


@pytest.mark.django_db
def test_actualizar_tenant_audita_campos_modificados(usuario_admin, tenant):
    actualizar_tenant(tenant, {"nombre": "Tenant renombrado"}, usuario_admin)

    tenant.refresh_from_db()
    assert tenant.nombre == "Tenant renombrado"

    registro = RegistroCambio.objects.get(
        entidad="Tenant", entidad_id=tenant.pk, campo="nombre"
    )
    assert registro.valor_anterior == "Tenant de prueba"
    assert registro.valor_nuevo == "Tenant renombrado"
