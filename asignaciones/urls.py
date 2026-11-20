from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_asignaciones, name="lista_asignaciones"),
    path("nueva/", views.nueva_asignacion, name="nueva_asignacion"),
    path(
        "series-disponibles/",
        views.series_disponibles,
        name="series_disponibles",
    ),
    path(
        "validar-disponibilidad/",
        views.validar_disponibilidad,
        name="validar_disponibilidad_asignacion",
    ),
    path(
        "sobrante/",
        views.sobrante_asignacion,
        name="sobrante_asignacion",
    ),
    path(
        "<int:solicitud_id>/excel/",
        views.descargar_excel_asignacion,
        name="excel_asignacion",
    ),
    path(
        "<int:solicitud_id>/enviar/",
        views.enviar_asignacion,
        name="enviar_asignacion",
    ),
    path(
        "<int:solicitud_id>/cancelar/",
        views.cancelar_asignacion,
        name="cancelar_asignacion",
    ),
    path(
        "<int:solicitud_id>/",
        views.detalle_asignacion,
        name="detalle_asignacion",
    ),
]
