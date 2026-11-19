"""Auditoría de técnicos."""

import pytest

from acceso.models import Usuario
from auditoria.models import RegistroCambio
from tenants.models import Tenant
from tecnicos.models import Tecnico
from tecnicos.services import (
    actualizar_tecnico,
    crear_tecnico,
    desactivar_tecnico,
    reactivar_tecnico,
)


def _eventos(tecnico):
    return RegistroCambio.objects.filter(
        entidad="Tecnico", entidad_id=tecnico.pk
    )


@pytest.mark.django_db
def test_eventos_de_alta_nombre_y_estado(usuario_tenant):
    tecnico = crear_tecnico({"nif": "LA1234", "nombre": "Juan"}, usuario_tenant)
    assert _eventos(tecnico).filter(campo="alta").exists()

    actualizar_tecnico(tecnico, {"nombre": "Juan Pérez"}, usuario_tenant)
    assert _eventos(tecnico).filter(campo="nombre").exists()

    desactivar_tecnico(tecnico, usuario_tenant)
    desactivar_tecnico(tecnico, usuario_tenant)
    reactivar_tecnico(tecnico, usuario_tenant)

    activo = list(_eventos(tecnico).filter(campo="activo").order_by("id"))
    assert [(r.valor_anterior, r.valor_nuevo) for r in activo] == [
        ("ACTIVO", "DESACTIVADO"),
        ("DESACTIVADO", "ACTIVO"),
    ]


@pytest.mark.django_db
def test_auditoria_sin_secretos_ni_tenant_id(usuario_tenant):
    tecnico = crear_tecnico({"nif": "LA1234", "nombre": "Juan"}, usuario_tenant)
    actualizar_tecnico(tecnico, {"nombre": "Juan Pérez"}, usuario_tenant)
    desactivar_tecnico(tecnico, usuario_tenant)

    prohibidos = ("password", "contraseña", "token", "secreto", "tenant_id")
    for registro in _eventos(tecnico):
        texto = " ".join(
            [registro.campo, registro.valor_anterior, registro.valor_nuevo]
        ).lower()
        for prohibido in prohibidos:
            assert prohibido not in texto


@pytest.mark.django_db
def test_alta_es_atomica(usuario_tenant, monkeypatch):
    def auditoria_que_falla(*args, **kwargs):
        raise RuntimeError("falla de auditoría")

    monkeypatch.setattr("tecnicos.services.registrar_cambio", auditoria_que_falla)

    with pytest.raises(RuntimeError):
        crear_tecnico({"nif": "LA1234", "nombre": "Juan"}, usuario_tenant)

    assert not Tecnico_objects_exists("LA1234")


def Tecnico_objects_exists(nif):
    from tecnicos.models import Tecnico

    return Tecnico.objects.filter(nif=nif).exists()


@pytest.mark.django_db
def test_auditoria_se_conserva_al_desactivar_cuenta(tenant, tecnico, usuario_tenant):
    from django.test import Client

    desactivar_tecnico(tecnico, usuario_tenant)
    Usuario.objects.filter(pk=usuario_tenant.pk).update(
        is_active=False, version_sesion=1
    )
    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)

    assert _eventos(tecnico).exists()
    assert Tecnico.objects.filter(pk=tecnico.pk).exists()
