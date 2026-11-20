"""Contrato del alta de técnicos."""

import pytest
from django.urls import reverse

from acceso.models import Rol, Usuario
from tecnicos.models import Tecnico


def _datos(**cambios):
    datos = {"nif": "LA1234", "nombre": "Juan Pérez"}
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_alta_tecnico(cliente_tenant, tenant):
    respuesta = cliente_tenant.post(reverse("crear_tecnico"), _datos())

    assert respuesta.status_code == 302
    tecnico = Tecnico.objects.get(nif="LA1234")
    assert tecnico.tenant_id == tenant.pk
    assert tecnico.activo is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "nif",
    ["LA123", "LA12345", "A1234", "LA12A4", "LA 1234", "LA-1234"],
)
def test_nif_invalido(cliente_tenant, nif):
    respuesta = cliente_tenant.post(reverse("crear_tecnico"), _datos(nif=nif))

    assert respuesta.status_code == 400
    assert "El NIF debe tener el formato LAXXXX" in respuesta.content.decode()


@pytest.mark.django_db
def test_nif_se_normaliza(cliente_tenant):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        _datos(nif=" la1234 "),
    )

    assert respuesta.status_code == 302
    assert Tecnico.objects.filter(nif="LA1234").exists()


@pytest.mark.django_db
def test_nif_duplicado_mismo_tenant(cliente_tenant, tecnico):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        _datos(nif=tecnico.nif),
    )

    assert respuesta.status_code == 409
    assert "El NIF ya está registrado" in respuesta.content.decode()


@pytest.mark.django_db
def test_nif_duplicado_otro_tenant(cliente_tenant, tecnico_otro_tenant):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        _datos(nif=tecnico_otro_tenant.nif),
    )

    assert respuesta.status_code == 409
    assert "El NIF ya está registrado" in respuesta.content.decode()
    assert tecnico_otro_tenant.tenant.codigo not in respuesta.content.decode()


@pytest.mark.django_db
def test_nif_de_desactivado_mismo_tenant(cliente_tenant, tecnico_desactivado):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        _datos(nif=tecnico_desactivado.nif),
    )

    assert respuesta.status_code == 409
    assert (
        "El NIF ya está registrado; reactiva el técnico existente"
        in respuesta.content.decode()
    )


@pytest.mark.django_db
def test_nif_de_desactivado_otro_tenant(cliente_tenant, usuario_otro_tenant):
    Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA7777",
        nombre="Ajeno desactivado",
        activo=False,
        creado_por=usuario_otro_tenant,
    )

    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        _datos(nif="LA7777"),
    )

    assert respuesta.status_code == 409
    assert respuesta.content.decode().count("El NIF ya está registrado") == 1
    assert "reactiva" not in respuesta.content.decode()


@pytest.mark.django_db
def test_nombre_invalido(cliente_tenant):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        _datos(nombre="   "),
    )

    assert respuesta.status_code == 400
    assert "El nombre es obligatorio" in respuesta.content.decode()


@pytest.mark.django_db
def test_nombre_demasiado_largo(cliente_tenant):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        _datos(nombre="X" * 101),
    )

    assert respuesta.status_code == 400
    assert "El nombre no puede superar los 100 caracteres" in respuesta.content.decode()


@pytest.mark.django_db
def test_tenant_id_forzado_se_ignora(cliente_tenant, tenant, usuario_otro_tenant):
    respuesta = cliente_tenant.post(
        reverse("crear_tecnico"),
        {**_datos(), "tenant_id": usuario_otro_tenant.tenant_id},
    )

    assert respuesta.status_code == 302
    assert Tecnico.objects.get(nif="LA1234").tenant_id == tenant.pk


@pytest.mark.django_db
def test_admin_y_almacen_no_crean(cliente_autenticado, cliente_almacen):
    for cliente in (cliente_autenticado, cliente_almacen):
        respuesta = cliente.post(reverse("crear_tecnico"), _datos())
        assert respuesta.status_code == 403
        assert "No tienes permiso para gestionar técnicos" in respuesta.content.decode()

    assert not Tecnico.objects.filter(nif="LA1234").exists()


@pytest.mark.django_db
def test_delete_no_permitido(cliente_tenant):
    respuesta = cliente_tenant.delete(reverse("crear_tecnico"))

    assert respuesta.status_code == 405
