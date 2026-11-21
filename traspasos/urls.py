from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_traspasos, name="lista_traspasos"),
    path("nuevo/", views.nuevo_traspaso, name="nuevo_traspaso"),
    path(
        "series-tecnico/",
        views.series_tecnico,
        name="series_tecnico",
    ),
    path(
        "stock-tecnico/",
        views.stock_tecnico,
        name="stock_tecnico_traspaso",
    ),
    path(
        "materiales-tecnico/",
        views.materiales_tecnico,
        name="materiales_tecnico_traspaso",
    ),
    path(
        "validar-disponibilidad/",
        views.validar_disponibilidad,
        name="validar_disponibilidad_traspaso",
    ),
    path(
        "<int:traspaso_id>/editar/",
        views.editar_traspaso,
        name="editar_traspaso",
    ),
    path(
        "<int:traspaso_id>/enviar/",
        views.enviar_traspaso,
        name="enviar_traspaso",
    ),
    path(
        "<int:traspaso_id>/cancelar/",
        views.cancelar_traspaso,
        name="cancelar_traspaso",
    ),
    path(
        "<int:traspaso_id>/excel/",
        views.excel_traspaso,
        name="excel_traspaso",
    ),
    path(
        "<int:traspaso_id>/",
        views.detalle_traspaso,
        name="detalle_traspaso",
    ),
]
