from django.urls import path

from . import almacen_views as views

urlpatterns = [
    path("", views.bandeja, name="bandeja_traspasos"),
    path(
        "<int:traspaso_id>/excel/",
        views.excel,
        name="excel_traspaso_almacen",
    ),
    path(
        "<int:traspaso_id>/confirmar/",
        views.confirmar,
        name="confirmar_traspaso_almacen",
    ),
    path(
        "<int:traspaso_id>/rechazar/",
        views.rechazar,
        name="rechazar_traspaso_almacen",
    ),
    path(
        "<int:traspaso_id>/",
        views.detalle,
        name="detalle_traspaso_almacen",
    ),
]
