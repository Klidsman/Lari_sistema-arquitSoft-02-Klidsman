from django.urls import path

from . import views

urlpatterns = [
    path(
        "devoluciones/",
        views.lista_devoluciones,
        name="lista_devoluciones",
    ),
    path(
        "devoluciones/nueva/",
        views.nueva_devolucion,
        name="nueva_devolucion",
    ),
    path(
        "devoluciones/<int:devolucion_id>/acta/",
        views.acta_devolucion,
        name="acta_devolucion",
    ),
    path(
        "devoluciones/<int:devolucion_id>/",
        views.detalle_devolucion,
        name="detalle_devolucion",
    ),
    path("bajas/", views.lista_bajas, name="lista_bajas"),
    path("bajas/nueva/", views.nueva_baja, name="nueva_baja"),
    path("bajas/<int:baja_id>/", views.detalle_baja, name="detalle_baja"),
]
