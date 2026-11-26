from django.urls import path

from . import views

urlpatterns = [
    path("", views.menu, name="menu_registro_materiales"),
    path("ordenes/cargar/", views.cargar_ordenes, name="cargar_ordenes"),
    path(
        "ordenes/cargar/preview/",
        views.preview_carga,
        name="preview_carga_ordenes",
    ),
    path(
        "ordenes/cargas/<int:carga_id>/deshacer/",
        views.deshacer_carga,
        name="deshacer_carga_ordenes",
    ),
    path(
        "ordenes/pendientes/",
        views.pendientes,
        name="ordenes_pendientes",
    ),
    path(
        "ordenes/<int:orden_id>/historial/",
        views.historial,
        name="historial_orden",
    ),
    path("materiales/", views.materiales, name="registrar_materiales"),
    path(
        "materiales/contexto/",
        views.contexto_materiales,
        name="contexto_materiales",
    ),
    path(
        "materiales/guardar/",
        views.guardar_materiales,
        name="guardar_materiales",
    ),
    path("dashboard/", views.dashboard, name="dashboard_materiales"),
    path("cierre/", views.cierre, name="cierre_mensual"),
    path("cierre/cerrar/", views.cerrar, name="cerrar_mes"),
    path("cierre/reabrir/", views.reabrir, name="reabrir_mes"),
    path("cierre/justificar/", views.justificar, name="justificar_pendiente"),
    path(
        "advertencias/<int:advertencia_id>/resolver/",
        views.resolver_advertencia,
        name="resolver_advertencia",
    ),
    path(
        "exportar/reporte/",
        views.exportar_reporte,
        name="exportar_reporte_mensual",
    ),
    path(
        "exportar/ordenes/",
        views.exportar_ordenes,
        name="exportar_detalle_ordenes",
    ),
]
