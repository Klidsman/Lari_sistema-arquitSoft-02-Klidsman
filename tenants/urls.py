from django.urls import path

from . import views

urlpatterns = [
    path(
        "plataforma/regiones/",
        views.listar_regiones,
        name="listar_regiones",
    ),
    path(
        "plataforma/regiones/nueva/",
        views.crear_region,
        name="crear_region",
    ),
    path(
        "plataforma/regiones/<int:region_id>/editar/",
        views.editar_region,
        name="editar_region",
    ),
    path(
        "plataforma/tenants/",
        views.listar_tenants,
        name="listar_tenants",
    ),
    path(
        "plataforma/tenants/nuevo/",
        views.crear_tenant,
        name="crear_tenant",
    ),
    path(
        "plataforma/tenants/<int:tenant_id>/",
        views.detalle_tenant,
        name="detalle_tenant",
    ),
    path(
        "plataforma/tenants/<int:tenant_id>/suspender/",
        views.suspender_tenant,
        name="suspender_tenant",
    ),
    path(
        "plataforma/tenants/<int:tenant_id>/activar/",
        views.activar_tenant,
        name="activar_tenant",
    ),
]
