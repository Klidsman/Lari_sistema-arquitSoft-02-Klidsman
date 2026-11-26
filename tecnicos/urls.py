from django.urls import path

from . import views

urlpatterns = [
    path("", views.listar_tecnicos, name="listar_tecnicos"),
    path(
        "stock/",
        views.stock_actual_tecnicos,
        name="stock_actual_tecnicos",
    ),
    path(
        "buscar/",
        views.buscar_tecnicos_htmx,
        name="buscar_tecnicos_htmx",
    ),
    path("nuevo/", views.crear_tecnico, name="crear_tecnico"),
    path(
        "<int:tecnico_id>/",
        views.detalle_tecnico,
        name="detalle_tecnico",
    ),
    path(
        "<int:tecnico_id>/editar/",
        views.editar_tecnico,
        name="editar_tecnico",
    ),
    path(
        "<int:tecnico_id>/desactivar/",
        views.desactivar_tecnico,
        name="desactivar_tecnico",
    ),
    path(
        "<int:tecnico_id>/reactivar/",
        views.reactivar_tecnico,
        name="reactivar_tecnico",
    ),
]
