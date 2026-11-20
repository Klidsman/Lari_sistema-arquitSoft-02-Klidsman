"""Registro de verificaciones de movimientos para el tipo."""

import pytest

from materiales import services


@pytest.mark.django_db
def test_sin_verificaciones_permite_cambio(material):
    assert services.puede_cambiar_tipo(material) is True


@pytest.mark.django_db
def test_verificacion_con_movimientos_bloquea(material, verificacion_movimientos):
    verificacion_movimientos(lambda material: True)

    assert services.puede_cambiar_tipo(material) is False


@pytest.mark.django_db
def test_se_puede_desregistrar(material):
    baja = services.registrar_verificacion_movimientos(lambda material: True)
    assert services.puede_cambiar_tipo(material) is False

    baja()
    assert services.puede_cambiar_tipo(material) is True


@pytest.mark.django_db
def test_fallo_seguro_ante_excepcion(material, verificacion_movimientos):
    def verificacion_rota(material):
        raise RuntimeError("tabla no disponible")

    verificacion_movimientos(verificacion_rota)

    assert services.puede_cambiar_tipo(material) is False


@pytest.mark.django_db
def test_evalua_todas_las_verificaciones(material, verificacion_movimientos):
    llamadas = []

    verificacion_movimientos(
        lambda material: llamadas.append("primera") or False
    )
    verificacion_movimientos(
        lambda material: llamadas.append("segunda") or True
    )

    assert services.puede_cambiar_tipo(material) is False
    assert llamadas == ["primera", "segunda"]
