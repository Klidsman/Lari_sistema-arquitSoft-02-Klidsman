"""Integración del estado del técnico."""

import pytest

from acceso.models import Usuario
from tenants.models import Tenant
from tecnicos.models import Tecnico
from tecnicos.services import (
    TenantSuspendido,
    desactivar_tecnico,
    reactivar_tecnico,
    tecnicos_para_operacion,
    tecnicos_para_reporte,
)


@pytest.mark.django_db
def test_desactivar_audita(tecnico, usuario_tenant, registro_cambios):
    desactivar_tecnico(tecnico, usuario_tenant)

    registro = registro_cambios(tecnico).get(campo="activo")
    assert registro.valor_anterior == "ACTIVO"
    assert registro.valor_nuevo == "DESACTIVADO"


@pytest.mark.django_db
def test_reactivar_audita(tecnico_desactivado, usuario_tenant, registro_cambios):
    reactivar_tecnico(tecnico_desactivado, usuario_tenant)

    registro = registro_cambios(tecnico_desactivado).get(campo="activo")
    assert registro.valor_anterior == "DESACTIVADO"
    assert registro.valor_nuevo == "ACTIVO"


@pytest.mark.django_db
def test_idempotencia_sin_auditoria(tecnico, tecnico_desactivado, usuario_tenant):
    desactivar_tecnico(tecnico, usuario_tenant)
    desactivar_tecnico(tecnico, usuario_tenant)
    reactivar_tecnico(tecnico_desactivado, usuario_tenant)
    reactivar_tecnico(tecnico_desactivado, usuario_tenant)

    assert (
        Tecnico.objects.filter(pk=tecnico.pk, activo=False).exists()
        and Tecnico.objects.filter(pk=tecnico_desactivado.pk, activo=True).exists()
    )


@pytest.mark.django_db
def test_selectores_de_operacion(tenant, tecnico, tecnico_desactivado):
    activos = list(tecnicos_para_operacion(tenant))
    reporte = list(tecnicos_para_reporte(tenant))

    assert tecnico in activos
    assert tecnico_desactivado not in activos
    assert tecnico_desactivado in reporte


@pytest.mark.django_db
def test_no_borra_el_registro(tecnico, usuario_tenant, monkeypatch):
    def prohibido(*args, **kwargs):
        raise AssertionError("no debe llamarse delete()")

    monkeypatch.setattr(Tecnico, "delete", prohibido)

    desactivar_tecnico(tecnico, usuario_tenant)

    assert Tecnico.objects.filter(pk=tecnico.pk).exists()


@pytest.mark.django_db
def test_tenant_suspendido_no_cambia_estado(tenant, tecnico, usuario_tenant):
    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)
    actor = Usuario.objects.get(pk=usuario_tenant.pk)

    with pytest.raises(TenantSuspendido):
        desactivar_tecnico(tecnico, actor)
