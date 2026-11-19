"""Middleware que publica el contexto del usuario autenticado."""

from django.conf import settings
from django.contrib.auth import logout
from django.db import connection
from django.shortcuts import redirect

from tenants.models import Tenant

from .services import CLAVE_PENDIENTE_2FA

RUTAS_SIN_BD = ("/static/", "/media/")


def _fijar_variables_bd(tenant=None, region=None, rol=None) -> None:
    """Publica el alcance en variables de sesión de PostgreSQL para RLS."""
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.tenant_id', %s, false)",
            [str(tenant.pk) if tenant else ""],
        )
        cursor.execute(
            "SELECT set_config('app.region_id', %s, false)",
            [str(region.pk) if region else ""],
        )
        cursor.execute(
            "SELECT set_config('app.rol', %s, false)",
            [rol or ""],
        )


class ContextoUsuarioMiddleware:
    """Deriva tenant, región y rol solo de la cuenta autenticada."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.usuario = None
        request.rol = None
        request.tenant = None
        request.region = None

        if request.path.startswith(RUTAS_SIN_BD):
            return self.get_response(request)

        if request.session.get(CLAVE_PENDIENTE_2FA):
            ruta = request.path
            permitidas = (
                ruta.startswith("/login/2fa/"),
                ruta.startswith("/logout/"),
            )
            if not any(permitidas):
                _fijar_variables_bd()
                return redirect("login_2fa")

        usuario = getattr(request, "user", None)
        if usuario is None or not usuario.is_authenticated:
            _fijar_variables_bd()
            return self.get_response(request)

        request.usuario = usuario
        request.rol = usuario.rol

        if not usuario.is_active:
            logout(request)
            _fijar_variables_bd()
            return redirect(settings.LOGIN_URL)

        if usuario.tenant_id:
            tenant = usuario.tenant
            if tenant.estado != Tenant.ESTADO_ACTIVO:
                logout(request)
                _fijar_variables_bd()
                return redirect(settings.LOGIN_URL)
            request.tenant = tenant
            request.region = tenant.region
        elif usuario.region_id:
            request.region = usuario.region

        version_sesion = request.session.get("version_sesion")
        if version_sesion is None:
            request.session["version_sesion"] = usuario.version_sesion
        elif version_sesion != usuario.version_sesion:
            logout(request)
            _fijar_variables_bd()
            return redirect(settings.LOGIN_URL)

        _fijar_variables_bd(request.tenant, request.region, request.rol)
        return self.get_response(request)
