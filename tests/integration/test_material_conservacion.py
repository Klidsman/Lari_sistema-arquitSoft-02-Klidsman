"""Conservación del material y ausencia de borrado."""

import pytest
from django.urls import reverse

from acceso.models import Usuario
from materiales.models import Material
from materiales.services import actualizar_material


@pytest.mark.django_db
def test_material_se_conserva_si_se_desactiva_creador(
    material, usuario_almacen, usuario_admin
):
    Usuario.objects.filter(pk=usuario_almacen.pk).update(is_active=False, version_sesion=1)

    assert Material.objects.filter(pk=material.pk).exists()

    actualizar_material(
        material,
        {"descripcion": "EDITADA TRAS DESACTIVAR CREADOR"},
        usuario_admin,
    )

    material.refresh_from_db()
    assert material.descripcion == "EDITADA TRAS DESACTIVAR CREADOR"


@pytest.mark.django_db
def test_no_existe_ruta_de_borrado():
    from materiales import urls

    nombres = [patron.name for patron in urls.urlpatterns]

    assert not any(
        "borrar" in nombre or "delete" in nombre or "eliminar" in nombre
        for nombre in nombres
    )


@pytest.mark.django_db
def test_delete_responde_405(cliente_almacen, material):
    rutas = [
        reverse("listar_materiales"),
        reverse("buscar_materiales_htmx"),
        reverse("crear_material"),
        reverse("editar_material", args=[material.pk]),
    ]

    for ruta in rutas:
        assert cliente_almacen.delete(ruta).status_code == 405
