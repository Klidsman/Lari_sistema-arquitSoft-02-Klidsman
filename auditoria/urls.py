from django.urls import path

from . import views

urlpatterns = [
    path("auditoria/acceso/", views.auditoria_acceso, name="auditoria_acceso"),
]
