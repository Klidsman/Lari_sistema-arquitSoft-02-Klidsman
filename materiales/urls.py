from django.urls import path

from . import views

urlpatterns = [
    path("", views.listar_materiales, name="listar_materiales"),
    path(
        "buscar/",
        views.buscar_materiales_htmx,
        name="buscar_materiales_htmx",
    ),
    path("nuevo/", views.crear_material, name="crear_material"),
    path(
        "<int:material_id>/editar/",
        views.editar_material,
        name="editar_material",
    ),
    path(
        "<int:material_id>/baja/",
        views.dar_de_baja_material,
        name="dar_de_baja_material",
    ),
]
