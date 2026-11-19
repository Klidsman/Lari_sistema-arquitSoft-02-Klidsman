"""Servicios de regiones, almacenes y tenants."""

from django.db import IntegrityError, transaction
from django.db.models import F

from auditoria.services import registrar_cambio
from acceso.models import Rol, Usuario

from .models import Almacen, Region, Tenant


class PermisoDenegado(Exception):
    mensaje = "No tienes permiso para administrar esta cuenta"


class RegionDuplicada(Exception):
    mensaje = "El código de región ya existe"


class RegionNoExiste(Exception):
    mensaje = "La región no existe"


class RegionInvalida(Exception):
    pass


class TenantInvalido(Exception):
    pass


class TenantDuplicado(Exception):
    mensaje = "El código de tenant ya existe"


def _validar_admin(actor) -> None:
    if actor is None or getattr(actor, "rol", None) != Rol.ADMIN_PLATAFORMA:
        raise PermisoDenegado


def _texto(datos, clave, defecto=""):
    return str(datos.get(clave, defecto)).strip()


def crear_region(datos, actor) -> Region:
    _validar_admin(actor)

    codigo = _texto(datos, "codigo").upper()
    nombre = _texto(datos, "nombre")
    centro = _texto(datos, "centro")
    codigo_almacen = _texto(datos, "codigo_almacen") or _texto(datos, "almacen")
    buzon = _texto(datos, "buzon")

    if not codigo:
        raise RegionInvalida("El código de región es obligatorio")
    if not nombre:
        raise RegionInvalida("El nombre es obligatorio")
    if not centro or not codigo_almacen:
        raise RegionInvalida("Centro y Almacén son obligatorios")

    try:
        with transaction.atomic():
            region = Region.objects.create(
                codigo=codigo,
                nombre=nombre,
                activa=True,
                creado_por=actor,
            )
            almacen = Almacen.objects.create(
                region=region,
                centro=centro,
                codigo_almacen=codigo_almacen,
                buzon=buzon,
                creado_por=actor,
            )
            registrar_cambio(
                "Region",
                region.pk,
                "alta",
                "",
                f"{region.codigo} - {region.nombre}",
                actor,
            )
            registrar_cambio(
                "Almacen",
                almacen.pk,
                "alta",
                "",
                f"{almacen.centro}/{almacen.codigo_almacen}",
                actor,
            )
    except IntegrityError as exc:
        if Region.objects.filter(codigo=codigo).exists():
            raise RegionDuplicada from exc
        raise

    return region


def actualizar_region(region: Region, datos, actor) -> Region:
    _validar_admin(actor)

    codigo = _texto(datos, "codigo")
    if codigo and codigo.upper() != region.codigo:
        raise RegionInvalida("El código de región no se puede cambiar")

    with transaction.atomic():
        region = Region.objects.select_for_update().get(pk=region.pk)
        almacen = Almacen.objects.select_for_update().get(region=region)

        nombre = _texto(datos, "nombre", region.nombre)
        centro = _texto(datos, "centro", almacen.centro)
        codigo_almacen = (
            _texto(datos, "codigo_almacen")
            or _texto(datos, "almacen")
            or almacen.codigo_almacen
        )
        buzon = _texto(datos, "buzon", almacen.buzon)
        activa = datos.get("activa", region.activa)
        if isinstance(activa, str):
            activa = activa.lower() in {"1", "true", "on", "yes"}

        if not nombre:
            raise RegionInvalida("El nombre es obligatorio")
        if not centro or not codigo_almacen:
            raise RegionInvalida("Centro y Almacén son obligatorios")

        cambios = [
            ("Region", region.pk, "nombre", region.nombre, nombre),
            ("Region", region.pk, "activa", region.activa, activa),
            ("Almacen", almacen.pk, "centro", almacen.centro, centro),
            (
                "Almacen",
                almacen.pk,
                "codigo_almacen",
                almacen.codigo_almacen,
                codigo_almacen,
            ),
            ("Almacen", almacen.pk, "buzon", almacen.buzon, buzon),
            ("Almacen", almacen.pk, "activo", almacen.activo, activa),
        ]

        region.nombre = nombre
        region.activa = activa
        region.actualizado_por = actor
        region.save(update_fields=["nombre", "activa", "actualizado_por", "actualizado_en"])

        almacen.centro = centro
        almacen.codigo_almacen = codigo_almacen
        almacen.buzon = buzon
        almacen.activo = activa
        almacen.actualizado_por = actor
        almacen.save(
            update_fields=[
                "centro",
                "codigo_almacen",
                "buzon",
                "activo",
                "actualizado_por",
                "actualizado_en",
            ]
        )

        for entidad, entidad_id, campo, anterior, nuevo in cambios:
            if anterior != nuevo:
                registrar_cambio(entidad, entidad_id, campo, anterior, nuevo, actor)

    return region


def crear_tenant(datos, actor) -> Tenant:
    _validar_admin(actor)

    codigo = _texto(datos, "codigo").upper()
    nombre = _texto(datos, "nombre")
    region = datos.get("region")

    if region is None or region == "":
        raise TenantInvalido("El tenant debe pertenecer a una región")

    if isinstance(region, (int, str)):
        region = Region.objects.filter(pk=region).first()

    if region is None or not Region.objects.filter(
        pk=region.pk, activa=True
    ).exists():
        raise TenantInvalido("La región seleccionada no está disponible")

    if not codigo:
        raise TenantInvalido("El código de tenant es obligatorio")
    if not nombre:
        raise TenantInvalido("El nombre es obligatorio")

    try:
        with transaction.atomic():
            tenant = Tenant.objects.create(
                codigo=codigo,
                nombre=nombre,
                region=region,
                estado=Tenant.ESTADO_ACTIVO,
                creado_por=actor,
            )
            registrar_cambio(
                "Tenant",
                tenant.pk,
                "alta",
                "",
                f"{tenant.codigo} - {tenant.nombre}",
                actor,
                tenant=tenant,
            )
    except IntegrityError as exc:
        if Tenant.objects.filter(codigo=codigo).exists():
            raise TenantDuplicado from exc
        raise

    return tenant


def actualizar_tenant(tenant: Tenant, datos, actor) -> Tenant:
    _validar_admin(actor)

    region = datos.get("region")
    if region not in (None, "", tenant.region_id) and getattr(
        region, "pk", region
    ) != tenant.region_id:
        raise TenantInvalido("La región del tenant no se puede cambiar")

    with transaction.atomic():
        tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)

        codigo = _texto(datos, "codigo", tenant.codigo).upper()
        nombre = _texto(datos, "nombre", tenant.nombre)
        estado = _texto(datos, "estado", tenant.estado)

        if not codigo:
            raise TenantInvalido("El código de tenant es obligatorio")
        if not nombre:
            raise TenantInvalido("El nombre es obligatorio")
        if estado not in {Tenant.ESTADO_ACTIVO, Tenant.ESTADO_SUSPENDIDO}:
            raise TenantInvalido("El estado del tenant no es válido")

        cambios = [
            ("codigo", tenant.codigo, codigo),
            ("nombre", tenant.nombre, nombre),
            ("estado", tenant.estado, estado),
        ]

        tenant.codigo = codigo
        tenant.nombre = nombre
        tenant.estado = estado
        tenant.actualizado_por = actor
        tenant.save(
            update_fields=[
                "codigo",
                "nombre",
                "estado",
                "actualizado_por",
                "actualizado_en",
            ]
        )

        for campo, anterior, nuevo in cambios:
            if anterior != nuevo:
                registrar_cambio(
                    "Tenant",
                    tenant.pk,
                    campo,
                    anterior,
                    nuevo,
                    actor,
                    tenant=tenant,
                )

    return tenant


def _invalidar_sesiones_del_tenant(tenant) -> None:
    Usuario.objects.filter(
        tenant=tenant,
        rol=Rol.USUARIO_TENANT,
    ).update(version_sesion=F("version_sesion") + 1)


def suspender_tenant(tenant: Tenant, actor) -> Tenant:
    """Suspende el tenant sin tocar sus datos ni su stock."""
    _validar_admin(actor)

    with transaction.atomic():
        bloqueado = Tenant.objects.select_for_update().get(pk=tenant.pk)
        if bloqueado.estado == Tenant.ESTADO_SUSPENDIDO:
            return bloqueado

        anterior = bloqueado.estado
        bloqueado.estado = Tenant.ESTADO_SUSPENDIDO
        bloqueado.actualizado_por = actor
        bloqueado.save(
            update_fields=["estado", "actualizado_por", "actualizado_en"]
        )

        _invalidar_sesiones_del_tenant(bloqueado)

        registrar_cambio(
            "Tenant",
            bloqueado.pk,
            "estado",
            anterior,
            bloqueado.estado,
            actor,
            tenant=bloqueado,
        )

    return bloqueado


def activar_tenant(tenant: Tenant, actor) -> Tenant:
    """Reactiva el tenant e invalida las sesiones previas de su cuenta."""
    _validar_admin(actor)

    with transaction.atomic():
        bloqueado = Tenant.objects.select_for_update().get(pk=tenant.pk)
        if bloqueado.estado == Tenant.ESTADO_ACTIVO:
            return bloqueado

        anterior = bloqueado.estado
        bloqueado.estado = Tenant.ESTADO_ACTIVO
        bloqueado.actualizado_por = actor
        bloqueado.save(
            update_fields=["estado", "actualizado_por", "actualizado_en"]
        )

        _invalidar_sesiones_del_tenant(bloqueado)

        registrar_cambio(
            "Tenant",
            bloqueado.pk,
            "estado",
            anterior,
            bloqueado.estado,
            actor,
            tenant=bloqueado,
        )

    return bloqueado
