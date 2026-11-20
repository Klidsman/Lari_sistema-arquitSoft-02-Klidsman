"""Separación de funciones entre actores."""

import pytest
from django.test import Client
from django.urls import reverse

from acceso.models import Rol, Usuario
from tenants.models import Tenant


def _cliente_con(usuario):
    cliente = Client()
    cliente.force_login(usuario)
    sesion = cliente.session
    sesion["version_sesion"] = usuario.version_sesion
    sesion.save()
    return cliente


@pytest.mark.django_db
def test_tenant_solo_tiene_rol_de_tenant(tenant, usuario_tenant):
    cuentas = Usuario.objects.filter(tenant=tenant)

    assert list(cuentas.values_list("rol", flat=True)) == [Rol.USUARIO_TENANT]
    assert not Usuario.objects.filter(
        tenant=tenant,
        rol__in=[Rol.ADMIN_PLATAFORMA, Rol.RESPONSABLE_ALMACEN],
    ).exists()


@pytest.mark.django_db
def test_tenant_puede_operar_su_propio_alcance(usuario_tenant):
    assert usuario_tenant.is_active is True
    assert usuario_tenant.tenant.estado == Tenant.ESTADO_ACTIVO
    assert usuario_tenant.tenant.tiene_cuenta_activa() is True


@pytest.mark.django_db
def test_tenant_no_accede_a_rutas_de_plataforma(usuario_tenant):
    cliente = _cliente_con(usuario_tenant)

    for nombre in ("listar_regiones", "listar_tenants", "listar_cuentas"):
        respuesta = cliente.get(reverse(nombre))
        assert respuesta.status_code == 403


@pytest.mark.django_db
def test_admin_no_accede_a_rutas_de_inventario(cliente_autenticado):
    rutas_inexistentes = [
        "/inventario/",
    ]

    for ruta in rutas_inexistentes:
        assert cliente_autenticado.get(ruta).status_code == 404

    respuesta = cliente_autenticado.get("/asignaciones/")
    assert respuesta.status_code == 403
    assert "No tienes permiso para crear asignaciones" in respuesta.content.decode()

    # Recojos ya existe y el administrador no tiene permiso para operarlo.
    respuesta = cliente_autenticado.get("/recojos/")
    assert respuesta.status_code == 403
    assert "No tienes permiso para registrar recojos" in respuesta.content.decode()

    # Traspasos ya existe y el administrador no tiene permiso para operarlo.
    respuesta = cliente_autenticado.get("/traspasos/")
    assert respuesta.status_code == 403
    assert "No tienes permiso para crear traspasos" in respuesta.content.decode()

    # Conciliaciones ya existe y el administrador no tiene permiso para operarlas.
    respuesta = cliente_autenticado.get("/conciliaciones/")
    assert respuesta.status_code == 403
    assert "No tienes permiso para cargar conciliaciones" in respuesta.content.decode()
