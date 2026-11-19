"""Contrato de consulta de auditoría."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from acceso.models import Rol, Usuario
from auditoria.models import RegistroCambio
from tenants.models import Region, Tenant


@pytest.fixture
def otra_region(db, usuario_admin):
    return Region.objects.create(
        codigo="TRU",
        nombre="Trujillo",
        creado_por=usuario_admin,
    )


@pytest.fixture
def otro_tenant(db, otra_region, usuario_admin):
    return Tenant.objects.create(
        codigo="TEN-002",
        nombre="Otro",
        region=otra_region,
        creado_por=usuario_admin,
    )


def _cliente_con(usuario):
    cliente = Client()
    cliente.force_login(usuario)
    sesion = cliente.session
    sesion["version_sesion"] = usuario.version_sesion
    sesion.save()
    return cliente


def _entrada(tenant, usuario, **cambios):
    datos = {
        "tenant": tenant,
        "entidad": "Tenant",
        "entidad_id": tenant.pk if tenant else 1,
        "campo": "nombre",
        "valor_anterior": "Antes",
        "valor_nuevo": "Después",
        "usuario": usuario,
    }
    datos.update(cambios)
    return RegistroCambio.objects.create(**datos)


@pytest.mark.django_db
def test_admin_ve_toda_la_auditoria(
    cliente_autenticado, tenant, otro_tenant, usuario_admin
):
    propia = _entrada(tenant, usuario_admin)
    ajena = _entrada(otro_tenant, usuario_admin, campo="estado")

    respuesta = cliente_autenticado.get(reverse("auditoria_acceso"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert str(propia.entidad_id) in contenido
    assert str(ajena.entidad_id) in contenido


@pytest.mark.django_db
def test_tenant_solo_ve_su_auditoria(usuario_tenant, otro_tenant, usuario_admin):
    propia = _entrada(usuario_tenant.tenant, usuario_admin)
    ajena = _entrada(
        otro_tenant,
        usuario_admin,
        entidad="TenantAjeno",
        campo="estado",
        valor_nuevo="Ajeno",
    )
    cliente = _cliente_con(usuario_tenant)

    respuesta = cliente.get(reverse("auditoria_acceso"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert propia.valor_nuevo in contenido
    assert "TenantAjeno" not in contenido
    assert "Ajeno" not in contenido


@pytest.mark.django_db
def test_almacen_solo_ve_su_region(
    usuario_almacen, tenant, otro_tenant, usuario_admin
):
    propia = _entrada(tenant, usuario_admin)
    ajena = _entrada(
        otro_tenant,
        usuario_admin,
        entidad="TenantAjeno",
        campo="estado",
        valor_nuevo="Ajeno",
    )
    cliente = _cliente_con(usuario_almacen)

    respuesta = cliente.get(reverse("auditoria_acceso"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert propia.valor_nuevo in contenido
    assert "TenantAjeno" not in contenido
    assert "Ajeno" not in contenido


@pytest.mark.django_db
def test_recurso_ajeno_devuelve_404(otro_tenant, usuario_admin, usuario_tenant):
    ajena = _entrada(otro_tenant, usuario_admin)

    cliente_tenant = _cliente_con(usuario_tenant)

    respuesta = cliente_tenant.get(
        reverse("auditoria_acceso"),
        {"registro_id": ajena.pk},
    )
    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_paginacion_50(cliente_autenticado, tenant, usuario_admin):
    for indice in range(55):
        _entrada(tenant, usuario_admin, entidad_id=indice + 1)

    respuesta = cliente_autenticado.get(reverse("auditoria_acceso"))

    assert respuesta.status_code == 200
    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2


@pytest.mark.django_db
def test_filtros(cliente_autenticado, tenant, usuario_admin):
    entrada = _entrada(
        tenant,
        usuario_admin,
        entidad="Region",
        entidad_id=7,
        campo="nombre",
        valor_nuevo="Filtrada",
    )
    _entrada(tenant, usuario_admin, entidad="Tenant", entidad_id=8)
    ahora = timezone.now()

    respuesta = cliente_autenticado.get(
        reverse("auditoria_acceso"),
        {
            "entidad": "Region",
            "entidad_id": "7",
            "usuario": usuario_admin.email,
            "desde": (ahora - timedelta(days=1)).date().isoformat(),
            "hasta": (ahora + timedelta(days=1)).date().isoformat(),
        },
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert "Filtrada" in contenido
    assert "<td>Tenant</td>" not in contenido

    respuesta = cliente_autenticado.get(
        reverse("auditoria_acceso"),
        {
            "desde": (ahora - timedelta(days=4)).date().isoformat(),
            "hasta": (ahora - timedelta(days=2)).date().isoformat(),
        },
    )
    assert "Filtrada" not in respuesta.content.decode()


@pytest.mark.django_db
def test_administrador_puede_entrar(cliente_autenticado):
    respuesta = cliente_autenticado.get(reverse("auditoria_acceso"))
    assert respuesta.status_code == 200
