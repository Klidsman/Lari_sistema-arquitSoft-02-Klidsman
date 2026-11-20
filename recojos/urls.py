from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_recojos, name="lista_recojos"),
    path("nuevo/", views.crear_recojo, name="crear_recojo"),
    path(
        "validar-series/",
        views.validar_series,
        name="validar_series",
    ),
    path(
        "<int:recojo_id>/anular/",
        views.anular_recojo,
        name="anular_recojo",
    ),
    path(
        "<int:recojo_id>/",
        views.detalle_recojo,
        name="detalle_recojo",
    ),
]
