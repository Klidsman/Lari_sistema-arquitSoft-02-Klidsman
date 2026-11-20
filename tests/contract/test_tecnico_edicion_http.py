"""Contrato de edición de técnicos."""

import pytest
from django.urls import reverse

from tecnicos.models import Tecnico


@pytest.mark.django_db
def test_editar_nombre(cliente_tenant, tecnico):
    respuesta = cliente_tenant.post(
        reverse("editar_tecnico", args=[tecnico.pk]),
        {"nombre": "Juan Pérez Actualizado"},
    )

    assert respuesta.status_code == 302
    tecnico.refresh_from_db()
    assert tecnico.nombre == "Juan Pérez Actualizado"


@pytest.mark.django_db
def test_nif_no_editable(cliente_tenant, tecnico):
    respuesta = cliente_tenant.post(
        reverse("editar_tecnico", args=[tecnico.pk]),
        {"nif": "LA9999", "nombre": tecnico.nombre},
    )

    assert respuesta.status_code == 400
    assert "El NIF no se puede cambiar" in respuesta.content.decode()
    tecnico.refresh_from_db()
    assert tecnico.nif == "LA1234"


@pytest.mark.django_db
def test_tenant_no_editable(cliente_tenant, tecnico, usuario_otro_tenant):
    respuesta = cliente_tenant.post(
        reverse("editar_tecnico", args=[tecnico.pk]),
        {"tenant_id": usuario_otro_tenant.tenant_id, "nombre": tecnico.nombre},
    )

    assert respuesta.status_code == 400
    assert "El tenant del técnico no se puede cambiar" in respuesta.content.decode()


@pytest.mark.django_db
def test_nombre_invalido(cliente_tenant, tecnico):
    respuesta = cliente_tenant.post(
        reverse("editar_tecnico", args=[tecnico.pk]),
        {"nombre": "   "},
    )

    assert respuesta.status_code == 400
    assert "El nombre es obligatorio" in respuesta.content.decode()

    respuesta = cliente_tenant.post(
        reverse("editar_tecnico", args=[tecnico.pk]),
        {"nombre": "X" * 101},
    )
    assert respuesta.status_code == 400
    assert "El nombre no puede superar los 100 caracteres" in respuesta.content.decode()


@pytest.mark.django_db
def test_tecnico_de_otro_tenant_404(cliente_tenant, tecnico_otro_tenant):
    respuesta = cliente_tenant.get(
        reverse("editar_tecnico", args=[tecnico_otro_tenant.pk])
    )

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_admin_y_almacen_no_editan(cliente_autenticado, cliente_almacen, tecnico):
    for cliente in (cliente_autenticado, cliente_almacen):
        respuesta = cliente.post(
            reverse("editar_tecnico", args=[tecnico.pk]),
            {"nombre": "No permitido"},
        )
        assert respuesta.status_code == 403


@pytest.mark.django_db
def test_editar_desactivado_permitido(cliente_tenant, tecnico_desactivado):
    respuesta = cliente_tenant.post(
        reverse("editar_tecnico", args=[tecnico_desactivado.pk]),
        {"nombre": "Ana Editada"},
    )

    assert respuesta.status_code == 302
    tecnico_desactivado.refresh_from_db()
    assert tecnico_desactivado.nombre == "Ana Editada"
    assert tecnico_desactivado.activo is False


@pytest.mark.django_db
def test_delete_no_permitido(cliente_tenant, tecnico):
    respuesta = cliente_tenant.delete(
        reverse("editar_tecnico", args=[tecnico.pk])
    )

    assert respuesta.status_code == 405
