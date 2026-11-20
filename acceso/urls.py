from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("login/2fa/", views.login_2fa, name="login_2fa"),
    path("logout/", views.logout, name="logout"),
    path("", views.inicio, name="inicio"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/2fa/", views.configurar_2fa, name="configurar_2fa"),
    path(
        "plataforma/tenants/<int:tenant_id>/cuenta/nueva/",
        views.crear_cuenta_tenant,
        name="crear_cuenta_tenant",
    ),
    path(
        "plataforma/cuentas/",
        views.listar_cuentas,
        name="listar_cuentas",
    ),
    path(
        "plataforma/cuentas/nueva-almacen/",
        views.crear_cuenta_almacen,
        name="crear_cuenta_almacen",
    ),
    path(
        "plataforma/cuentas/<int:cuenta_id>/desactivar/",
        views.desactivar_cuenta,
        name="desactivar_cuenta",
    ),
    path(
        "plataforma/cuentas/<int:cuenta_id>/reactivar/",
        views.reactivar_cuenta,
        name="reactivar_cuenta",
    ),
    path(
        "plataforma/cuentas/<int:cuenta_id>/rol/",
        views.cambiar_rol,
        name="cambiar_rol",
    ),
    path(
        "invitacion/<str:token>/",
        views.aceptar_invitacion,
        name="aceptar_invitacion",
    ),
]
