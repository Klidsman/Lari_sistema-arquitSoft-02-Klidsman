from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_conciliaciones, name="lista_conciliaciones"),
    path("cargar/", views.cargar_conciliacion, name="cargar_conciliacion"),
    path(
        "<int:conciliacion_id>/recalcular/",
        views.recalcular_conciliacion,
        name="recalcular_conciliacion",
    ),
    path(
        "<int:conciliacion_id>/aprobar/",
        views.aprobar_conciliacion,
        name="aprobar_conciliacion",
    ),
    path(
        "<int:conciliacion_id>/rechazar/",
        views.rechazar_conciliacion,
        name="rechazar_conciliacion",
    ),
    path(
        "<int:conciliacion_id>/",
        views.detalle_conciliacion,
        name="detalle_conciliacion",
    ),
]
