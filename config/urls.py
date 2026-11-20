"""Rutas raíz del proyecto."""

from django.urls import include, path

urlpatterns = [
    path("", include("acceso.urls")),
    path("", include("tenants.urls")),
    path("", include("auditoria.urls")),
    path("materiales/", include("materiales.urls")),
    path("tecnicos/", include("tecnicos.urls")),
    path("recojos/", include("recojos.urls")),
    path("stock-inicial/", include("stock_inicial.urls")),
    path("asignaciones/", include("asignaciones.urls")),
    path("almacen/", include("asignaciones.almacen_urls")),
    path("traspasos/", include("traspasos.urls")),
    path("almacen/traspasos/", include("traspasos.almacen_urls")),
    path("conciliaciones/", include("conciliaciones.urls")),
    path("logistica-inversa/", include("logistica_inversa.urls")),
    path("registro-materiales/", include("registro_materiales.urls")),
    path("reportes/", include("reportes.urls")),
]
