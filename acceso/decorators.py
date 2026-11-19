"""Decoradores de alcance y rol."""

from functools import wraps

from django.http import HttpResponseForbidden

MENSAJE_SIN_PERMISO = "No tienes permiso para administrar esta cuenta"


def _denegar():
    return HttpResponseForbidden(MENSAJE_SIN_PERMISO)


def requiere_rol(*roles):
    """Exige que el usuario autenticado tenga uno de los roles indicados."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            usuario = getattr(request, "usuario", None)
            if usuario is None or usuario.rol not in roles:
                return _denegar()
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


def requiere_tenant(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if getattr(request, "tenant", None) is None:
            return _denegar()
        return vista(request, *args, **kwargs)

    return envoltura


def requiere_region(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if getattr(request, "region", None) is None:
            return _denegar()
        return vista(request, *args, **kwargs)

    return envoltura
