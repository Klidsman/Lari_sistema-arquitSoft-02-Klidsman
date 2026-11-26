"""Vistas de autenticación y sesión."""

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods

from acceso.decorators import requiere_rol
from tenants.models import Tenant

from . import services as acceso_servicios
from .forms import (
    ConfigurarTotpForm,
    CuentaAlmacenForm,
    CuentaTenantForm,
    InvitacionPasswordForm,
    LoginForm,
    SegundoFactorForm,
)
from .models import Rol, Usuario
from .services import (
    CLAVE_VERSION_SESION,
    CredencialesInvalidas,
    CuentaDesactivada,
    SegundoFactorRequerido,
    SesionPendienteRequerida,
    TenantSuspendido,
    destino_por_rol,
    estado_sesion_pendiente,
    iniciar_sesion,
    usuario_pendiente,
    verificar_segundo_factor,
)
from .totp import cifrar_secreto, contexto_configuracion, verificar_codigo


def _render_error(request, plantilla, mensaje, status, contexto=None):
    return render(
        request,
        plantilla,
        {"error": mensaje, **(contexto or {})},
        status=status,
    )


def _primer_error(formulario) -> str:
    for errores in formulario.errors.values():
        if errores:
            return errores[0]
    return "Revisa los datos ingresados"


def _pagina_enlace(request, usuario, token, titulo, descripcion=""):
    """Muestra una sola vez el enlace de invitación o restablecimiento."""
    enlace = request.build_absolute_uri(
        reverse("aceptar_invitacion", args=[token])
    )
    return render(
        request,
        "acceso/enlace_generado.html",
        {
            "titulo": titulo,
            "descripcion": descripcion,
            "enlace": enlace,
            "correo": usuario.email,
        },
    )


def login(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            try:
                usuario = iniciar_sesion(
                    request,
                    form.cleaned_data["email"],
                    form.cleaned_data["password"],
                )
            except CredencialesInvalidas:
                return _render_error(
                    request,
                    "acceso/login.html",
                    CredencialesInvalidas.mensaje,
                    400,
                )
            except CuentaDesactivada:
                return _render_error(
                    request,
                    "acceso/login.html",
                    CuentaDesactivada.mensaje,
                    403,
                )
            except TenantSuspendido:
                return _render_error(
                    request,
                    "acceso/login.html",
                    TenantSuspendido.mensaje,
                    403,
                )

            if estado_sesion_pendiente(request):
                return redirect("login_2fa")
            return redirect(destino_por_rol(usuario))
    else:
        form = LoginForm()

    return render(request, "acceso/login.html", {"form": form})


@never_cache
def login_2fa(request):
    usuario = usuario_pendiente(request)
    if usuario is None:
        return _render_error(
            request,
            "acceso/login_2fa.html",
            SesionPendienteRequerida.mensaje,
            403,
        )

    configurando = not usuario.segundo_factor_habilitado
    if configurando and not usuario.secreto_totp:
        import pyotp

        usuario.secreto_totp = cifrar_secreto(pyotp.random_base32())
        usuario.save(update_fields=["secreto_totp"])

    alta = contexto_configuracion(usuario) if configurando else {}
    contexto = {"usuario": usuario, "configurando": configurando, **alta}

    if request.method == "POST":
        form = ConfigurarTotpForm(request.POST) if configurando else SegundoFactorForm(request.POST)
        if form.is_valid():
            if configurando:
                if not verificar_codigo(usuario, form.cleaned_data["codigo"]):
                    return _render_error(
                        request,
                        "acceso/login_2fa.html",
                        SegundoFactorRequerido.mensaje,
                        400,
                        {**contexto, "form": form},
                    )
                usuario.segundo_factor_habilitado = True
                usuario.save(update_fields=["segundo_factor_habilitado"])

            try:
                verificar_segundo_factor(
                    request,
                    usuario,
                    form.cleaned_data["codigo"],
                )
            except SegundoFactorRequerido:
                return _render_error(
                    request,
                    "acceso/login_2fa.html",
                    SegundoFactorRequerido.mensaje,
                    400,
                    {**contexto, "form": form},
                )
            return redirect(destino_por_rol(usuario))
    else:
        form = ConfigurarTotpForm() if configurando else SegundoFactorForm()

    return render(
        request,
        "acceso/login_2fa.html",
        {"form": form, **contexto},
    )


@require_POST
def logout(request):
    auth_logout(request)
    return redirect("login")


@login_required
def inicio(request):
    return render(request, "inicio.html")


@login_required
def perfil(request):
    return render(request, "acceso/perfil.html")


@login_required
@never_cache
def configurar_2fa(request):
    usuario = request.user

    if request.method == "POST":
        form = ConfigurarTotpForm(request.POST)
        if form.is_valid():
            if not usuario.secreto_totp:
                return redirect("configurar_2fa")
            if not verificar_codigo(usuario, form.cleaned_data["codigo"]):
                return _render_error(
                    request,
                    "acceso/configurar_2fa.html",
                    "Debes completar el segundo factor",
                    400,
                    {
                        "form": form,
                        "usuario": usuario,
                        **contexto_configuracion(usuario),
                    },
                )
            usuario.segundo_factor_habilitado = True
            usuario.save(update_fields=["segundo_factor_habilitado"])
            request.session[CLAVE_VERSION_SESION] = usuario.version_sesion
            messages.success(request, "Segundo factor configurado")
            return redirect("perfil")
    else:
        form = ConfigurarTotpForm()
        if not usuario.secreto_totp:
            import pyotp

            secreto = pyotp.random_base32()
            usuario.secreto_totp = cifrar_secreto(secreto)
            usuario.save(update_fields=["secreto_totp"])

    return render(
        request,
        "acceso/configurar_2fa.html",
        {
            "form": form,
            "usuario": usuario,
            **contexto_configuracion(usuario),
        },
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET", "POST"])
@never_cache
def crear_cuenta_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)

    if request.method == "POST":
        formulario = CuentaTenantForm(request.POST)
        contexto = {"form": formulario, "tenant": tenant}

        if formulario.is_valid():
            try:
                usuario, token = acceso_servicios.crear_cuenta_tenant_con_enlace(
                    tenant,
                    formulario.cleaned_data["email"],
                    request.usuario,
                )
            except acceso_servicios.PermisoDenegado:
                return _render_error(
                    request,
                    "acceso/cuenta_form.html",
                    acceso_servicios.PermisoDenegado.mensaje,
                    403,
                    contexto,
                )
            except acceso_servicios.CuentaDuplicada:
                return _render_error(
                    request,
                    "acceso/cuenta_form.html",
                    acceso_servicios.CuentaDuplicada.mensaje,
                    409,
                    contexto,
                )
            except acceso_servicios.CorreoDuplicado:
                return _render_error(
                    request,
                    "acceso/cuenta_form.html",
                    acceso_servicios.CorreoDuplicado.mensaje,
                    409,
                    contexto,
                )

            return _pagina_enlace(
                request,
                usuario,
                token,
                "Cuenta del tenant creada",
                "Comparte este enlace con la cuenta del tenant. Se muestra una sola vez.",
            )

        return _render_error(
            request,
            "acceso/cuenta_form.html",
            _primer_error(formulario),
            400,
            contexto,
        )

    return render(
        request,
        "acceso/cuenta_form.html",
        {"form": CuentaTenantForm(), "tenant": tenant},
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET", "POST"])
@never_cache
def crear_cuenta_almacen(request):
    if request.method == "POST":
        formulario = CuentaAlmacenForm(request.POST)
        contexto = {"form": formulario}

        if formulario.is_valid():
            try:
                usuario, token = acceso_servicios.crear_cuenta_almacen_con_enlace(
                    formulario.cleaned_data["region"],
                    formulario.cleaned_data["email"],
                    request.usuario,
                )
            except acceso_servicios.PermisoDenegado:
                return _render_error(
                    request,
                    "acceso/cuenta_form.html",
                    acceso_servicios.PermisoDenegado.mensaje,
                    403,
                    contexto,
                )
            except acceso_servicios.CorreoDuplicado:
                return _render_error(
                    request,
                    "acceso/cuenta_form.html",
                    acceso_servicios.CorreoDuplicado.mensaje,
                    409,
                    contexto,
                )
            except acceso_servicios.CuentaInvalida as exc:
                return _render_error(
                    request,
                    "acceso/cuenta_form.html",
                    str(exc),
                    400,
                    contexto,
                )

            return _pagina_enlace(
                request,
                usuario,
                token,
                "Cuenta de almacén creada",
                "Comparte este enlace con el Responsable de almacén. Se muestra una sola vez.",
            )

        return _render_error(
            request,
            "acceso/cuenta_form.html",
            _primer_error(formulario),
            400,
            contexto,
        )

    return render(
        request,
        "acceso/cuenta_form.html",
        {"form": CuentaAlmacenForm()},
    )


def _contexto_cuentas(request):
    cuentas = Usuario.objects.select_related("tenant", "region").order_by("email")
    pagina = Paginator(cuentas, 50).get_page(request.GET.get("page"))
    return {"pagina": pagina, "cuentas": pagina.object_list}


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET"])
def listar_cuentas(request):
    return render(
        request,
        "acceso/cuentas_lista.html",
        _contexto_cuentas(request),
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_POST
def desactivar_cuenta(request, cuenta_id):
    usuario = get_object_or_404(Usuario, pk=cuenta_id)

    if not usuario.is_active:
        return render(
            request,
            "acceso/cuentas_lista.html",
            _contexto_cuentas(request),
        )

    acceso_servicios.desactivar_cuenta(usuario, request.usuario)
    messages.success(request, "Cuenta desactivada")
    return redirect("listar_cuentas")


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_POST
def reactivar_cuenta(request, cuenta_id):
    usuario = get_object_or_404(Usuario, pk=cuenta_id)

    if usuario.is_active:
        return render(
            request,
            "acceso/cuentas_lista.html",
            _contexto_cuentas(request),
        )

    try:
        acceso_servicios.reactivar_cuenta(usuario, request.usuario)
    except acceso_servicios.TenantSuspendido:
        return _render_error(
            request,
            "acceso/cuentas_lista.html",
            acceso_servicios.TenantSuspendido.mensaje,
            409,
            _contexto_cuentas(request),
        )

    messages.success(request, "Cuenta reactivada")
    return redirect("listar_cuentas")


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_POST
def cambiar_rol(request, cuenta_id):
    usuario = get_object_or_404(Usuario, pk=cuenta_id)

    try:
        acceso_servicios.cambiar_rol(
            usuario,
            request.POST.get("rol", ""),
            request.usuario,
        )
    except acceso_servicios.CuentaTenantNoCambiaRol:
        return _render_error(
            request,
            "acceso/cuentas_lista.html",
            acceso_servicios.CuentaTenantNoCambiaRol.mensaje,
            409,
            _contexto_cuentas(request),
        )
    except acceso_servicios.RolNoPermitido:
        return _render_error(
            request,
            "acceso/cuentas_lista.html",
            acceso_servicios.RolNoPermitido.mensaje,
            400,
            _contexto_cuentas(request),
        )
    except acceso_servicios.AlcanceInvalido:
        return _render_error(
            request,
            "acceso/cuentas_lista.html",
            acceso_servicios.AlcanceInvalido.mensaje,
            400,
            _contexto_cuentas(request),
        )

    messages.success(request, "Rol actualizado")
    return redirect("listar_cuentas")


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_POST
@never_cache
def restablecer_password(request, cuenta_id):
    usuario = get_object_or_404(Usuario, pk=cuenta_id)

    if usuario.pk == request.usuario.pk:
        return _render_error(
            request,
            "acceso/cuentas_lista.html",
            "Usa el comando de consola para restablecer tu propia contraseña",
            400,
            _contexto_cuentas(request),
        )

    try:
        _, token = acceso_servicios.solicitar_restablecimiento(
            usuario,
            request.usuario,
        )
    except acceso_servicios.CuentaInactivaRestablecimiento:
        return _render_error(
            request,
            "acceso/cuentas_lista.html",
            acceso_servicios.CuentaInactivaRestablecimiento.mensaje,
            409,
            _contexto_cuentas(request),
        )

    return _pagina_enlace(
        request,
        usuario,
        token,
        "Restablecer contraseña",
        (
            "Comparte este enlace con la cuenta. Al usarlo se cerrarán sus "
            "sesiones abiertas. Se muestra una sola vez."
        ),
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_POST
@never_cache
def reenviar_invitacion_cuenta(request, cuenta_id):
    usuario = get_object_or_404(Usuario, pk=cuenta_id)

    if usuario.is_active:
        return _render_error(
            request,
            "acceso/cuentas_lista.html",
            "La cuenta ya está activa; usa «Restablecer contraseña»",
            409,
            _contexto_cuentas(request),
        )

    _, token = acceso_servicios.reenviar_invitacion(
        usuario,
        request.usuario,
    )

    return _pagina_enlace(
        request,
        usuario,
        token,
        "Invitación reenviada",
        (
            "Comparte este enlace con la cuenta. El enlace anterior quedó "
            "invalidado. Se muestra una sola vez."
        ),
    )


@require_http_methods(["GET", "POST"])
def aceptar_invitacion(request, token):
    if request.method == "POST":
        formulario = InvitacionPasswordForm(request.POST)
        contexto = {"form": formulario}

        if formulario.is_valid():
            try:
                acceso_servicios.aceptar_invitacion(
                    token,
                    formulario.cleaned_data["password"],
                )
            except acceso_servicios.InvitacionInvalida:
                return _render_error(
                    request,
                    "acceso/invitacion_form.html",
                    acceso_servicios.InvitacionInvalida.mensaje,
                    410,
                    contexto,
                )
            except ValidationError as exc:
                return _render_error(
                    request,
                    "acceso/invitacion_form.html",
                    " ".join(exc.messages),
                    400,
                    contexto,
                )

            messages.success(request, "Contraseña definida")
            return redirect("login")

        return _render_error(
            request,
            "acceso/invitacion_form.html",
            _primer_error(formulario),
            400,
            contexto,
        )

    try:
        acceso_servicios.obtener_invitacion_vigente(token)
    except acceso_servicios.InvitacionInvalida:
        return _render_error(
            request,
            "acceso/invitacion_form.html",
            acceso_servicios.InvitacionInvalida.mensaje,
            410,
        )

    return render(
        request,
        "acceso/invitacion_form.html",
        {"form": InvitacionPasswordForm()},
    )
