"""Servicios de autenticación, cuentas, invitaciones y sesión."""

from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.utils import timezone

from auditoria.services import registrar_cambio
from tenants.models import Tenant

from .models import Invitacion, Rol, TipoInvitacion, Usuario
from .tasks import enviar_correo_invitacion
from .tokens import generar_token, hash_token
from .totp import verificar_codigo

CLAVE_PENDIENTE_2FA = "pendiente_2fa_usuario_id"
CLAVE_VERSION_SESION = "version_sesion"

ROLES_CON_2FA = {Rol.ADMIN_PLATAFORMA, Rol.RESPONSABLE_ALMACEN}


class CredencialesInvalidas(Exception):
    mensaje = "Correo o contraseña incorrectos"


class CuentaDesactivada(Exception):
    mensaje = "La cuenta está desactivada"


class TenantSuspendido(Exception):
    mensaje = "El tenant está suspendido"


class SesionPendienteRequerida(Exception):
    mensaje = "Debes iniciar sesión"


class SegundoFactorRequerido(Exception):
    mensaje = "Debes completar el segundo factor"


def requiere_segundo_factor(usuario) -> bool:
    return usuario.rol in ROLES_CON_2FA


def estado_sesion_pendiente(request) -> bool:
    return bool(request.session.get(CLAVE_PENDIENTE_2FA))


def usuario_pendiente(request):
    usuario_id = request.session.get(CLAVE_PENDIENTE_2FA)
    if not usuario_id:
        return None
    return Usuario.objects.filter(pk=usuario_id, is_active=True).first()


def _dejar_sesion_pendiente(request, usuario) -> None:
    request.session.cycle_key()
    request.session[CLAVE_PENDIENTE_2FA] = usuario.pk
    request.session[CLAVE_VERSION_SESION] = usuario.version_sesion


def _completar_sesion(request, usuario) -> None:
    request.session.pop(CLAVE_PENDIENTE_2FA, None)
    login(request, usuario)
    request.session[CLAVE_VERSION_SESION] = usuario.version_sesion


def iniciar_sesion(request, correo: str, password: str):
    """Autentica y deja la sesión pendiente si el rol exige segundo factor."""
    from django.contrib.auth import authenticate

    usuario = authenticate(request, username=correo, password=password)
    if usuario is None:
        raise CredencialesInvalidas

    if not usuario.is_active:
        raise CuentaDesactivada

    if usuario.tenant_id and usuario.tenant.estado != Tenant.ESTADO_ACTIVO:
        raise TenantSuspendido

    if requiere_segundo_factor(usuario):
        _dejar_sesion_pendiente(request, usuario)
        return usuario

    _completar_sesion(request, usuario)
    return usuario


def verificar_segundo_factor(request, usuario, codigo: str) -> None:
    if not usuario.segundo_factor_habilitado or not usuario.secreto_totp:
        raise SegundoFactorRequerido
    if not verificar_codigo(usuario, codigo):
        raise SegundoFactorRequerido
    _completar_sesion(request, usuario)


def renovar_version_sesion(usuario) -> int:
    """Invalida las sesiones abiertas incrementando la versión."""
    with transaction.atomic():
        bloqueado = Usuario.objects.select_for_update().get(pk=usuario.pk)
        bloqueado.version_sesion += 1
        bloqueado.save(update_fields=["version_sesion"])
        usuario.version_sesion = bloqueado.version_sesion
        return bloqueado.version_sesion


def cuentas_visibles_para(actor):
    """Cuentas que el actor puede consultar según su alcance."""
    if actor is None:
        return Usuario.objects.none()

    if actor.rol == Rol.ADMIN_PLATAFORMA:
        return Usuario.objects.all()
    if actor.rol == Rol.USUARIO_TENANT and actor.tenant_id:
        return Usuario.objects.filter(tenant=actor.tenant)
    if actor.rol == Rol.RESPONSABLE_ALMACEN and actor.region_id:
        return Usuario.objects.filter(region=actor.region)

    return Usuario.objects.none()


def registros_visibles_para(actor):
    """Auditoría que el actor puede consultar; nunca usa datos del cliente."""
    from auditoria.models import RegistroCambio

    if actor is None:
        return RegistroCambio.objects.none()

    if actor.rol == Rol.ADMIN_PLATAFORMA:
        return RegistroCambio.objects.all()
    if actor.rol == Rol.USUARIO_TENANT and actor.tenant_id:
        return RegistroCambio.objects.filter(tenant=actor.tenant)
    if actor.rol == Rol.RESPONSABLE_ALMACEN and actor.region_id:
        return RegistroCambio.objects.filter(tenant__region=actor.region)

    return RegistroCambio.objects.none()


def destino_por_rol(usuario) -> str:
    if usuario.rol == Rol.ADMIN_PLATAFORMA:
        return "/plataforma/regiones/"
    return "/"


class PermisoDenegado(Exception):
    mensaje = "No tienes permiso para administrar esta cuenta"


class CuentaDuplicada(Exception):
    mensaje = "El tenant ya tiene una cuenta"


class CorreoDuplicado(Exception):
    mensaje = "El correo ya está registrado"


class CuentaInvalida(Exception):
    pass


class InvitacionInvalida(Exception):
    mensaje = "La invitación venció o ya fue usada"


class CuentaInactivaRestablecimiento(Exception):
    mensaje = "Reactiva la cuenta antes de restablecer su contraseña"


class CuentaTenantNoCambiaRol(Exception):
    mensaje = "La cuenta del tenant no cambia de rol"


class RolNoPermitido(Exception):
    mensaje = "No puedes asignar ese rol"


class AlcanceInvalido(Exception):
    mensaje = "El alcance de la cuenta no es válido"


def _validar_admin(actor) -> None:
    if actor is None or getattr(actor, "rol", None) != Rol.ADMIN_PLATAFORMA:
        raise PermisoDenegado


def verificar_alcance(actor, objetivo) -> bool:
    """Solo el Administrador de plataforma administra cuentas."""
    _validar_admin(actor)
    if objetivo is None or not isinstance(objetivo, Usuario):
        raise PermisoDenegado
    return True


def desactivar_cuenta(usuario: Usuario, actor) -> Usuario:
    """Desactiva la cuenta sin eliminarla e invalida sus sesiones."""
    verificar_alcance(actor, usuario)

    with transaction.atomic():
        bloqueado = Usuario.objects.select_for_update().get(pk=usuario.pk)
        if not bloqueado.is_active:
            return bloqueado

        bloqueado.is_active = False
        bloqueado.version_sesion += 1
        bloqueado.save(update_fields=["is_active", "version_sesion"])

        registrar_cambio(
            "Usuario",
            bloqueado.pk,
            "is_active",
            True,
            False,
            actor,
            tenant=bloqueado.tenant,
        )

    return bloqueado


def reactivar_cuenta(usuario: Usuario, actor) -> Usuario:
    """Reactiva la cuenta salvo que su tenant esté suspendido."""
    verificar_alcance(actor, usuario)

    with transaction.atomic():
        bloqueado = Usuario.objects.select_for_update().get(pk=usuario.pk)
        if bloqueado.is_active:
            return bloqueado

        if (
            bloqueado.tenant_id
            and bloqueado.tenant.estado != Tenant.ESTADO_ACTIVO
        ):
            raise TenantSuspendido

        bloqueado.is_active = True
        bloqueado.version_sesion += 1
        bloqueado.save(update_fields=["is_active", "version_sesion"])

        registrar_cambio(
            "Usuario",
            bloqueado.pk,
            "is_active",
            False,
            True,
            actor,
            tenant=bloqueado.tenant,
        )

    return bloqueado


def cambiar_rol(usuario: Usuario, nuevo_rol: str, actor) -> Usuario:
    """Cambia el rol de una cuenta administrativa y valida su alcance."""
    verificar_alcance(actor, usuario)

    if usuario.rol == Rol.USUARIO_TENANT:
        raise CuentaTenantNoCambiaRol

    if nuevo_rol not in {Rol.ADMIN_PLATAFORMA, Rol.RESPONSABLE_ALMACEN}:
        raise RolNoPermitido

    with transaction.atomic():
        bloqueado = Usuario.objects.select_for_update().get(pk=usuario.pk)

        if bloqueado.rol == Rol.USUARIO_TENANT:
            raise CuentaTenantNoCambiaRol

        if nuevo_rol == Rol.ADMIN_PLATAFORMA:
            if bloqueado.tenant_id is not None:
                raise AlcanceInvalido
            nueva_region = None
        else:
            nueva_region = bloqueado.region
            if nueva_region is None:
                raise AlcanceInvalido

        anterior = bloqueado.rol
        bloqueado.rol = nuevo_rol
        bloqueado.region = nueva_region
        bloqueado.version_sesion += 1
        bloqueado.save(update_fields=["rol", "region", "version_sesion"])

        if anterior != nuevo_rol:
            registrar_cambio(
                "Usuario",
                bloqueado.pk,
                "rol",
                anterior,
                nuevo_rol,
                actor,
                tenant=bloqueado.tenant,
            )

    return bloqueado


def crear_cuenta_tenant(tenant: Tenant, correo: str, actor) -> Usuario:
    """Crea la cuenta única e inactiva del tenant y su invitación."""
    usuario, _ = crear_cuenta_tenant_con_enlace(tenant, correo, actor)
    return usuario


def crear_cuenta_tenant_con_enlace(
    tenant: Tenant,
    correo: str,
    actor,
) -> tuple[Usuario, str]:
    """Crea la cuenta del tenant y devuelve el token de su invitación."""
    _validar_admin(actor)

    correo = (correo or "").strip().lower()
    if not correo:
        raise CuentaInvalida("El correo no es válido")

    if Usuario.objects.para_tenant(tenant).exists():
        raise CuentaDuplicada
    if Usuario.objects.filter(email__iexact=correo).exists():
        raise CorreoDuplicado

    try:
        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                email=correo,
                password=None,
                rol=Rol.USUARIO_TENANT,
                tenant=tenant,
                is_active=False,
            )
            registrar_cambio(
                "Usuario",
                usuario.pk,
                "alta",
                "",
                f"{usuario.email} ({usuario.rol})",
                actor,
                tenant=tenant,
            )
            _, token = emitir_invitacion(usuario, actor)
    except IntegrityError as exc:
        if Usuario.objects.para_tenant(tenant).exists():
            raise CuentaDuplicada from exc
        if Usuario.objects.filter(email__iexact=correo).exists():
            raise CorreoDuplicado from exc
        raise

    return usuario, token


def crear_cuenta_almacen(region, correo: str, actor) -> Usuario:
    """Crea una cuenta inactiva de Responsable de almacén con invitación."""
    usuario, _ = crear_cuenta_almacen_con_enlace(region, correo, actor)
    return usuario


def crear_cuenta_almacen_con_enlace(
    region,
    correo: str,
    actor,
) -> tuple[Usuario, str]:
    """Crea la cuenta de almacén y devuelve el token de su invitación."""
    _validar_admin(actor)

    correo = (correo or "").strip().lower()
    if region is None or not getattr(region, "activa", False):
        raise CuentaInvalida("El alcance de la cuenta no es válido")
    if not correo:
        raise CuentaInvalida("El correo no es válido")
    if Usuario.objects.filter(email__iexact=correo).exists():
        raise CorreoDuplicado

    try:
        with transaction.atomic():
            usuario = Usuario.objects.create_user(
                email=correo,
                password=None,
                rol=Rol.RESPONSABLE_ALMACEN,
                region=region,
                is_active=False,
            )
            registrar_cambio(
                "Usuario",
                usuario.pk,
                "alta",
                "",
                f"{usuario.email} ({usuario.rol})",
                actor,
            )
            _, token = emitir_invitacion(usuario, actor)
    except IntegrityError as exc:
        if Usuario.objects.filter(email__iexact=correo).exists():
            raise CorreoDuplicado from exc
        raise

    return usuario, token


def emitir_invitacion(
    usuario,
    actor,
    tipo: str = TipoInvitacion.ALTA,
    enviar_correo: bool = True,
) -> tuple[Invitacion, str]:
    """Revoca invitaciones pendientes y emite un token nuevo de un solo uso."""
    ahora = timezone.now()

    with transaction.atomic():
        Invitacion.objects.filter(
            usuario=usuario,
            usada_en__isnull=True,
            revocada_en__isnull=True,
        ).update(revocada_en=ahora)

        token = generar_token()
        invitacion = Invitacion.objects.create(
            usuario=usuario,
            tipo=tipo,
            token_hash=hash_token(token),
            correo=usuario.email,
            expira_en=ahora + timedelta(hours=72),
            creada_por=actor,
        )
        if enviar_correo:
            transaction.on_commit(
                lambda: enviar_correo_invitacion.delay(invitacion.pk, token)
            )

    return invitacion, token


def enviar_invitacion(
    usuario,
    actor,
    tipo: str = TipoInvitacion.ALTA,
) -> Invitacion:
    """Emite una invitación y devuelve el registro persistido."""
    invitacion, _ = emitir_invitacion(usuario, actor, tipo)
    return invitacion


def reenviar_invitacion(usuario, actor) -> tuple[Invitacion, str]:
    """Reenvía la invitación invalidando el token anterior."""
    return emitir_invitacion(usuario, actor)


def solicitar_restablecimiento(
    usuario,
    actor,
    enviar_correo: bool = True,
) -> tuple[Invitacion, str]:
    """Emite un enlace de restablecimiento y cierra las sesiones abiertas."""
    verificar_alcance(actor, usuario)

    with transaction.atomic():
        bloqueado = Usuario.objects.select_for_update().get(pk=usuario.pk)
        if not bloqueado.is_active:
            raise CuentaInactivaRestablecimiento

        invitacion, token = emitir_invitacion(
            bloqueado,
            actor,
            TipoInvitacion.RESTABLECIMIENTO,
            enviar_correo=enviar_correo,
        )

        bloqueado.version_sesion += 1
        bloqueado.save(update_fields=["version_sesion"])
        usuario.version_sesion = bloqueado.version_sesion

        registrar_cambio(
            "Usuario",
            bloqueado.pk,
            "acceso_cuenta",
            "",
            "restablecimiento_solicitado",
            actor,
            tenant=bloqueado.tenant,
        )

    return invitacion, token


def restablecer_segundo_factor(usuario, actor=None) -> Usuario:
    """Borra el secreto TOTP y obliga a configurarlo de nuevo."""
    with transaction.atomic():
        bloqueado = Usuario.objects.select_for_update().get(pk=usuario.pk)
        bloqueado.secreto_totp = ""
        bloqueado.segundo_factor_habilitado = False
        bloqueado.version_sesion += 1
        bloqueado.save(
            update_fields=[
                "secreto_totp",
                "segundo_factor_habilitado",
                "version_sesion",
            ]
        )
        usuario.version_sesion = bloqueado.version_sesion
        usuario.secreto_totp = ""
        usuario.segundo_factor_habilitado = False

        registrar_cambio(
            "Usuario",
            bloqueado.pk,
            "segundo_factor",
            "configurado",
            "reiniciado",
            actor or bloqueado,
            tenant=bloqueado.tenant,
        )

    return bloqueado


def _vigente(invitacion, ahora) -> bool:
    return bool(
        invitacion
        and invitacion.usada_en is None
        and invitacion.revocada_en is None
        and invitacion.expira_en > ahora
    )


def obtener_invitacion_vigente(token: str) -> Invitacion:
    ahora = timezone.now()
    invitacion = (
        Invitacion.objects.select_related("usuario")
        .filter(token_hash=hash_token(token or ""))
        .first()
    )
    if not _vigente(invitacion, ahora):
        raise InvitacionInvalida
    return invitacion


def aceptar_invitacion(token: str, password: str) -> Usuario:
    """Define la contraseña y consume la invitación vigente."""
    ahora = timezone.now()

    with transaction.atomic():
        invitacion = (
            Invitacion.objects.select_for_update()
            .select_related("usuario")
            .filter(token_hash=hash_token(token or ""))
            .first()
        )
        if not _vigente(invitacion, ahora):
            raise InvitacionInvalida

        usuario = invitacion.usuario
        es_alta = invitacion.tipo == TipoInvitacion.ALTA

        if es_alta:
            if usuario.is_active:
                raise InvitacionInvalida
        elif not usuario.is_active:
            raise InvitacionInvalida

        validate_password(password, usuario)

        usuario.set_password(password)
        if es_alta:
            usuario.is_active = True
            usuario.save(update_fields=["password", "is_active"])
        else:
            usuario.version_sesion += 1
            usuario.save(update_fields=["password", "version_sesion"])

        invitacion.usada_en = ahora
        invitacion.save(update_fields=["usada_en"])

        if es_alta:
            registrar_cambio(
                "Usuario",
                usuario.pk,
                "is_active",
                False,
                True,
                usuario,
                tenant=usuario.tenant,
            )
        else:
            registrar_cambio(
                "Usuario",
                usuario.pk,
                "acceso_cuenta",
                "restablecimiento_solicitado",
                "restablecimiento_completado",
                usuario,
                tenant=usuario.tenant,
            )

    return usuario
