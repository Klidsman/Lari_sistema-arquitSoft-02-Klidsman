"""Integración del alta de técnicos."""

import pytest

from acceso.models import Rol, Usuario
from auditoria.models import RegistroCambio
from tecnicos.models import Tecnico
from tecnicos.services import (
    NifDuplicado,
    PermisoDenegado,
    TenantSuspendido,
    ValidacionTecnico,
    crear_tecnico,
)


def _datos(**cambios):
    datos = {"nif": "LA1234", "nombre": "  Juan   Pérez "}
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_alta_toma_tenant_del_actor(usuario_tenant, tenant):
    tecnico = crear_tecnico(_datos(), usuario_tenant)

    assert tecnico.tenant_id == tenant.pk
    assert tecnico.activo is True
    assert tecnico.creado_por_id == usuario_tenant.pk


@pytest.mark.django_db
def test_alta_auditada(usuario_tenant, registro_cambios):
    tecnico = crear_tecnico(_datos(), usuario_tenant)

    registro = registro_cambios(tecnico).get(campo="alta")
    assert "nif=LA1234" in registro.valor_nuevo
    assert "nombre=Juan Pérez" in registro.valor_nuevo
    assert "estado=ACTIVO" in registro.valor_nuevo


@pytest.mark.django_db
def test_normalizacion(usuario_tenant):
    tecnico = crear_tecnico(
        _datos(nif=" la1234 ", nombre="  Juan   Pérez "),
        usuario_tenant,
    )

    assert tecnico.nif == "LA1234"
    assert tecnico.nombre == "Juan Pérez"


@pytest.mark.django_db
def test_nif_duplicado_mismo_y_otro_tenant(
    usuario_tenant, tecnico, tecnico_otro_tenant
):
    with pytest.raises(NifDuplicado, match="El NIF ya está registrado"):
        crear_tecnico(_datos(nif=tecnico.nif), usuario_tenant)

    with pytest.raises(NifDuplicado, match="El NIF ya está registrado"):
        crear_tecnico(_datos(nif=tecnico_otro_tenant.nif), usuario_tenant)


@pytest.mark.django_db
def test_nif_de_desactivado_mismo_tenant(usuario_tenant, tecnico_desactivado):
    with pytest.raises(
        NifDuplicado,
        match="El NIF ya está registrado; reactiva el técnico existente",
    ):
        crear_tecnico(_datos(nif=tecnico_desactivado.nif), usuario_tenant)


@pytest.mark.django_db
def test_nif_de_desactivado_otro_tenant(usuario_tenant, usuario_otro_tenant):
    Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA7777",
        nombre="Ajeno",
        activo=False,
        creado_por=usuario_otro_tenant,
    )

    with pytest.raises(NifDuplicado) as error:
        crear_tecnico(_datos(nif="LA7777"), usuario_tenant)

    assert str(error.value) == "El NIF ya está registrado"


@pytest.mark.django_db
def test_nombre_duplicado_permitido(usuario_tenant, tecnico):
    otro = crear_tecnico(
        _datos(nif="LA5555", nombre=tecnico.nombre),
        usuario_tenant,
    )

    assert otro.nombre == tecnico.nombre


@pytest.mark.django_db
def test_validaciones(usuario_tenant):
    with pytest.raises(ValidacionTecnico, match="El NIF debe tener el formato LAXXXX"):
        crear_tecnico(_datos(nif="LA123"), usuario_tenant)

    with pytest.raises(ValidacionTecnico, match="El nombre es obligatorio"):
        crear_tecnico(_datos(nombre="  "), usuario_tenant)

    with pytest.raises(
        ValidacionTecnico, match="El nombre no puede superar los 100 caracteres"
    ):
        crear_tecnico(_datos(nombre="X" * 101), usuario_tenant)


@pytest.mark.django_db
def test_solo_cuenta_tenant(usuario_admin, usuario_almacen):
    for actor in (usuario_admin, usuario_almacen):
        with pytest.raises(PermisoDenegado):
            crear_tecnico(_datos(), actor)

    assert not Tecnico.objects.filter(nif="LA1234").exists()


@pytest.mark.django_db
def test_tenant_suspendido(tenant, usuario_tenant):
    from tenants.models import Tenant

    Tenant.objects.filter(pk=tenant.pk).update(estado=Tenant.ESTADO_SUSPENDIDO)
    actor = Usuario.objects.get(pk=usuario_tenant.pk)

    with pytest.raises(TenantSuspendido):
        crear_tecnico(_datos(), actor)


@pytest.mark.django_db
def test_fallo_no_audita(usuario_tenant, tecnico):
    antes = RegistroCambio.objects.filter(entidad="Tecnico").count()

    with pytest.raises(NifDuplicado):
        crear_tecnico(_datos(nif=tecnico.nif), usuario_tenant)

    assert RegistroCambio.objects.filter(entidad="Tecnico").count() == antes
