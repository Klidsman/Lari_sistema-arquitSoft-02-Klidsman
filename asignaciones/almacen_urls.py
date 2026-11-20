from django.urls import path

from . import almacen_views as views

urlpatterns = [
    path("bandeja/", views.bandeja, name="bandeja_almacen"),
    path(
        "solicitudes/<int:solicitud_id>/previsualizar/",
        views.previsualizar_solicitud,
        name="previsualizar_almacen",
    ),
    path(
        "solicitudes/<int:solicitud_id>/confirmar/",
        views.confirmar_solicitud,
        name="confirmar_almacen",
    ),
    path(
        "solicitudes/<int:solicitud_id>/rechazar/",
        views.rechazar_solicitud,
        name="rechazar_almacen",
    ),
    path(
        "solicitudes/<int:solicitud_id>/descargar-excel/",
        views.descargar_excel,
        name="descargar_excel_almacen",
    ),
    path(
        "solicitudes/<int:solicitud_id>/",
        views.detalle_solicitud,
        name="detalle_almacen",
    ),
    path(
        "excels-historicos/",
        views.historicos,
        name="historicos_almacen",
    ),
    path(
        "excels-historicos/<int:solicitud_id>/descargar/",
        views.descargar_historico,
        name="descargar_historico_almacen",
    ),
    path(
        "notificaciones/pendientes/",
        views.pendientes,
        name="pendientes_almacen",
    ),
    path(
        "notificaciones/sse/",
        views.sse,
        name="sse_almacen",
    ),
]
