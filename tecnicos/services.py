"""Servicios de técnicos del tenant."""

import re

from django.db import IntegrityError, transaction
from django.db.models import Q

from acceso.models import Rol
from auditoria.services import registrar_cambio
from tenants.models import Tenant

from .models import Tecnico

PATRON_NIF = re.compile(r"^LA[0-9]{4}$")


class ValidacionTecnico(Exception):
    pass


class NifDuplicado(Exception):
    mensaje = "El NIF ya está registrado"

    def __init__(self, mensaje=None):
        super().__init__(mensaje or self.mensaje)


class PermisoDenegado(Exception):
    mensaje = "No tienes permiso para gestionar técnicos"

    def __str__(self):
        return self.mensaje


class NoEncontrado(Exception):
    mensaje = "El técnico no existe"

    def __str__(self):
        return self.mensaje


class TecnicoNoDisponible(Exception):
    mensaje = "El técnico está desactivado"

    def __str__(self):
        return self.mensaje


class TenantSuspendido(Exception):
    mensaje = "El tenant está suspendido"

    def __str__(self):
        return self.mensaje


def normalizar_nif(nif) -> str:
    return (nif or "").strip().upper()


def validar_nif(nif) -> str:
    nif = normalizar_nif(nif)
    if not PATRON_NIF.match(nif):
        raise ValidacionTecnico("El NIF debe tener el formato LAXXXX")
    return nif


def normalizar_nombre(nombre) -> str:
    return " ".join((nombre or "").split())


def validar_nombre(nombre) -> str:
    nombre = normalizar_nombre(nombre)
    if not nombre:
        raise ValidacionTecnico("El nombre es obligatorio")
    if len(nombre) > 100:
        raise ValidacionTecnico("El nombre no puede superar los 100 caracteres")
    return nombre


def validar_cuenta_tenant(actor, tenant=None):
    """Devuelve el tenant del actor y valida rol, actividad y suspensión."""
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol != Rol.USUARIO_TENANT or not actor.tenant_id:
        raise PermisoDenegado

    tenant_actor = actor.tenant
    if tenant is not None and tenant.pk != tenant_actor.pk:
        raise NoEncontrado
    if tenant_actor.estado != Tenant.ESTADO_ACTIVO:
        raise TenantSuspendido
    return tenant_actor


def obtener_tecnico(tenant, tecnico_id) -> Tecnico:
    tecnico = Tecnico.objects.filter(pk=tecnico_id, tenant=tenant).first()
    if tecnico is None:
        raise NoEncontrado
    return tecnico


def obtener_tecnico_por_nif(tenant, nif) -> Tecnico:
    nif = normalizar_nif(nif)
    tecnico = Tecnico.objects.filter(tenant=tenant, nif=nif).first()
    if tecnico is None:
        raise NoEncontrado
    return tecnico


def stock_actual_tecnico(tecnico):
    """Stock por material del técnico; solo lectura y acotado a su tenant."""
    from stock.models import StockTecnico

    return (
        StockTecnico.objects.filter(
            tenant=tecnico.tenant,
            tecnico=tecnico,
        )
        .select_related("material")
        .order_by("material__codigo")
    )


def validar_tecnico_para_operacion(tenant, tecnico_id) -> Tecnico:
    tecnico = obtener_tecnico(tenant, tecnico_id)
    if not tecnico.activo:
        raise TecnicoNoDisponible
    return tecnico


def _estado_texto(activo: bool) -> str:
    return "ACTIVO" if activo else "DESACTIVADO"


def auditar_alta_tecnico(tecnico: Tecnico, actor):
    valor = (
        f"nif={tecnico.nif}; nombre={tecnico.nombre}; "
        f"estado={_estado_texto(tecnico.activo)}"
    )
    return registrar_cambio(
        "Tecnico",
        tecnico.pk,
        "alta",
        "",
        valor,
        actor,
        tenant=tecnico.tenant,
    )


def auditar_cambio_tecnico(tecnico: Tecnico, cambios, actor):
    registros = []
    for campo, anterior, nuevo in cambios:
        if campo == "activo":
            anterior = _estado_texto(anterior)
            nuevo = _estado_texto(nuevo)
        registros.append(
            registrar_cambio(
                "Tecnico",
                tecnico.pk,
                campo,
                anterior,
                nuevo,
                actor,
                tenant=tecnico.tenant,
            )
        )
    return registros


def tecnicos_para_operacion(tenant):
    return Tecnico.objects.filter(tenant=tenant, activo=True).order_by(
        "nombre", "nif"
    )


def tecnicos_para_reporte(tenant, incluir_inactivos=True):
    tecnicos = Tecnico.objects.filter(tenant=tenant)
    if not incluir_inactivos:
        tecnicos = tecnicos.filter(activo=True)
    return tecnicos.order_by("nombre", "nif")


def crear_tecnico(datos, actor) -> Tecnico:
    tenant = validar_cuenta_tenant(actor)

    nif = validar_nif(datos.get("nif"))
    nombre = validar_nombre(datos.get("nombre"))

    existente = Tecnico.objects.filter(nif=nif).first()
    if existente is not None:
        if existente.tenant_id == tenant.pk and not existente.activo:
            raise NifDuplicado(
                "El NIF ya está registrado; reactiva el técnico existente"
            )
        raise NifDuplicado

    try:
        with transaction.atomic():
            tecnico = Tecnico.objects.create(
                tenant=tenant,
                nif=nif,
                nombre=nombre,
                activo=True,
                creado_por=actor,
            )
            auditar_alta_tecnico(tecnico, actor)
    except IntegrityError as exc:
        existente = Tecnico.objects.filter(nif=nif).first()
        if (
            existente is not None
            and existente.tenant_id == tenant.pk
            and not existente.activo
        ):
            raise NifDuplicado(
                "El NIF ya está registrado; reactiva el técnico existente"
            ) from exc
        raise NifDuplicado from exc

    return tecnico


def listar_tecnicos(tenant, estado="todos"):
    tecnicos = Tecnico.objects.filter(tenant=tenant)
    if estado == "activos":
        tecnicos = tecnicos.filter(activo=True)
    elif estado == "desactivados":
        tecnicos = tecnicos.filter(activo=False)
    return tecnicos.order_by("nombre", "nif")


def buscar_tecnicos(tenant, q="", solo_activos=False, estado=None):
    tecnicos = Tecnico.objects.filter(tenant=tenant)

    if estado == "activos":
        tecnicos = tecnicos.filter(activo=True)
    elif estado == "desactivados":
        tecnicos = tecnicos.filter(activo=False)
    if solo_activos:
        tecnicos = tecnicos.filter(activo=True)

    q = (q or "").strip()
    if q:
        tecnicos = tecnicos.filter(
            Q(nif__icontains=q) | Q(nombre__icontains=q)
        )

    return tecnicos.order_by("nombre", "nif")


def obtener_datos_tecnico(tecnico: Tecnico) -> dict:
    return {
        "nif": tecnico.nif,
        "nombre": tecnico.nombre,
        "activo": tecnico.activo,
    }


def actualizar_tecnico(tecnico: Tecnico, cambios, actor) -> Tecnico:
    tenant = validar_cuenta_tenant(actor)

    if tecnico.tenant_id != tenant.pk:
        raise NoEncontrado
    if "nif" in cambios:
        raise ValidacionTecnico("El NIF no se puede cambiar")
    if "tenant" in cambios or "tenant_id" in cambios:
        raise ValidacionTecnico("El tenant del técnico no se puede cambiar")

    nombre = validar_nombre(cambios.get("nombre", tecnico.nombre))

    with transaction.atomic():
        bloqueado = Tecnico.objects.select_for_update().get(
            pk=tecnico.pk,
            tenant=tenant,
        )

        if nombre == bloqueado.nombre:
            return bloqueado

        anterior = bloqueado.nombre
        bloqueado.nombre = nombre
        bloqueado.actualizado_por = actor
        bloqueado.save(
            update_fields=["nombre", "actualizado_por", "actualizado_en"]
        )
        auditar_cambio_tecnico(
            bloqueado,
            [("nombre", anterior, nombre)],
            actor,
        )

    return bloqueado


def _cambiar_estado(tecnico: Tecnico, actor, activo: bool) -> Tecnico:
    tenant = validar_cuenta_tenant(actor)

    if tecnico.tenant_id != tenant.pk:
        raise NoEncontrado

    with transaction.atomic():
        bloqueado = Tecnico.objects.select_for_update().get(
            pk=tecnico.pk,
            tenant=tenant,
        )
        if bloqueado.activo == activo:
            return bloqueado

        anterior = bloqueado.activo
        bloqueado.activo = activo
        bloqueado.actualizado_por = actor
        bloqueado.save(
            update_fields=["activo", "actualizado_por", "actualizado_en"]
        )
        auditar_cambio_tecnico(
            bloqueado,
            [("activo", anterior, activo)],
            actor,
        )

    return bloqueado


def desactivar_tecnico(tecnico: Tecnico, actor) -> Tecnico:
    return _cambiar_estado(tecnico, actor, False)


def reactivar_tecnico(tecnico: Tecnico, actor) -> Tecnico:
    return _cambiar_estado(tecnico, actor, True)
