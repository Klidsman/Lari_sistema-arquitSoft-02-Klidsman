"""Contrato transversal: materiales sin borrado."""

import pytest
from django.urls import reverse

from materiales.models import Material


@pytest.mark.django_db
def test_todas_las_rutas_rechazan_delete(cliente_almacen, material):
    rutas = [
        reverse("listar_materiales"),
        reverse("buscar_materiales_htmx"),
        reverse("crear_material"),
        reverse("editar_material", args=[material.pk]),
    ]

    for ruta in rutas:
        respuesta = cliente_almacen.delete(ruta)
        assert respuesta.status_code == 405


@pytest.mark.django_db
def test_no_hay_url_de_borrado():
    from materiales import urls

    for patron in urls.urlpatterns:
        assert "delete" not in str(patron.pattern)
        assert "borrar" not in str(patron.pattern)


@pytest.mark.django_db
def test_el_material_persiste_tras_intentos_de_delete(
    cliente_almacen, material
):
    cliente_almacen.delete(reverse("editar_material", args=[material.pk]))

    assert Material.objects.filter(pk=material.pk).exists()
