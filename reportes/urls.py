from django.urls import path

from . import views

urlpatterns = [
    path("cortes/", views.lista_cortes, name="lista_cortes"),
    path("cortes/generar/", views.generar_corte, name="generar_corte"),
    path(
        "cortes/<int:corte_id>/regenerar/",
        views.regenerar_corte,
        name="regenerar_corte",
    ),
    path(
        "cortes/<int:corte_id>/exportar/auditoria/",
        views.exportar_auditoria,
        name="exportar_auditoria",
    ),
    path(
        "cortes/<int:corte_id>/exportar/conciliacion/",
        views.exportar_conciliacion,
        name="exportar_conciliacion",
    ),
    path(
        "cortes/<int:corte_id>/",
        views.detalle_corte,
        name="detalle_corte",
    ),
]
