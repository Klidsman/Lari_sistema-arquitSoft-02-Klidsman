from django.urls import path

from . import views

urlpatterns = [
    path("", views.estado_stock_inicial, name="estado_stock_inicial"),
    path(
        "validar-excel/",
        views.validar_excel,
        name="validar_excel_stock_inicial",
    ),
    path(
        "cargar-excel/",
        views.cargar_excel,
        name="cargar_excel_stock_inicial",
    ),
    path(
        "formulario/",
        views.formulario_stock_inicial,
        name="formulario_stock_inicial",
    ),
    path(
        "<int:carga_id>/editar/",
        views.editar_stock_inicial,
        name="editar_stock_inicial",
    ),
    path(
        "<int:carga_id>/",
        views.detalle_stock_inicial,
        name="detalle_stock_inicial",
    ),
]
