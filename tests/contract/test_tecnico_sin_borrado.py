"""Contrato de no eliminación de técnicos."""

import pytest
from django.urls import reverse

from tecnicos.models import Tecnico


@pytest.mark.django_db
def test_no_hay_url_de_borrado():
    from tecnicos import urls

    nombres = [patron.name for patron in urls.urlpatterns]

    assert not any(
        "borrar" in nombre or "delete" in nombre or "eliminar" in nombre
        for nombre in nombres
    )


@pytest.mark.django_db
def test_delete_responde_405(cliente_tenant, tecnico):
    rutas = [
        reverse("detalle_tecnico", args=[tecnico.pk]),
        reverse("editar_tecnico", args=[tecnico.pk]),
        reverse("desactivar_tecnico", args=[tecnico.pk]),
        reverse("reactivar_tecnico", args=[tecnico.pk]),
    ]

    for ruta in rutas:
        assert cliente_tenant.delete(ruta).status_code == 405


@pytest.mark.django_db
def test_desactivar_conserva_fila_y_auditoria(cliente_tenant, tecnico):
    cliente_tenant.post(reverse("desactivar_tecnico", args=[tecnico.pk]))

    assert Tecnico.objects.filter(pk=tecnico.pk).exists()
    assert Tecnico.objects.get(pk=tecnico.pk).activo is False
