"""Integración del alta de materiales."""

import pytest

from acceso.models import Rol, Usuario
from auditoria.models import RegistroCambio
from materiales.models import Material
from materiales.services import (
    MaterialDuplicado,
    PermisoDenegado,
    ValidacionMaterial,
    crear_material,
)


def _datos(**cambios):
    datos = {
        "codigo": "10402520279",
        "descripcion": "ROSETA",
        "lote": "fiberhome",
        "tipo": "SERIADO",
    }
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_crear_material_registra_creador_y_fecha(usuario_almacen):
    material = crear_material(_datos(), usuario_almacen)

    assert material.creado_por_id == usuario_almacen.pk
    assert material.creado_en is not None
    assert material.tipo == "SERIADO"


@pytest.mark.django_db
def test_alta_auditada(usuario_almacen):
    material = crear_material(_datos(), usuario_almacen)

    registro = RegistroCambio.objects.get(
        entidad="Material",
        entidad_id=material.pk,
        campo="alta",
    )
    assert "codigo=10402520279" in registro.valor_nuevo
    assert "descripcion=ROSETA" in registro.valor_nuevo
    assert "lote=FIBERHOME" in registro.valor_nuevo
    assert "tipo=SERIADO" in registro.valor_nuevo


@pytest.mark.django_db
def test_normalizacion(usuario_almacen):
    material = crear_material(
        _datos(
            codigo=" 10402520279 ",
            descripcion="  ROSETA   ÓPTICA ",
            lote=" fiberhome   x ",
        ),
        usuario_almacen,
    )

    assert material.codigo == "10402520279"
    assert material.descripcion == "ROSETA ÓPTICA"
    assert material.lote == "FIBERHOME X"


@pytest.mark.django_db
def test_material_sin_lote(usuario_almacen):
    material = crear_material(_datos(lote=""), usuario_almacen)

    assert material.lote == ""


@pytest.mark.django_db
def test_doble_envio_no_crea_duplicado(usuario_almacen):
    crear_material(_datos(), usuario_almacen)

    with pytest.raises(MaterialDuplicado):
        crear_material(_datos(), usuario_almacen)

    assert Material.objects.filter(codigo="10402520279").count() == 1


@pytest.mark.django_db
def test_codigo_duplicado_por_integridad(usuario_almacen):
    Material.objects.create(
        codigo="10402520279",
        descripcion="Existente",
        lote="",
        es_seriado=False,
        creado_por=usuario_almacen,
    )

    with pytest.raises(MaterialDuplicado):
        crear_material(_datos(), usuario_almacen)


@pytest.mark.django_db
def test_validaciones_de_codigo(usuario_almacen):
    for codigo in ("1040252027", "104025202791", "1040252027A", "1040 2520279"):
        with pytest.raises(
            ValidacionMaterial, match="El código debe tener 11 dígitos"
        ):
            crear_material(_datos(codigo=codigo), usuario_almacen)


@pytest.mark.django_db
def test_descripcion_vacia(usuario_almacen):
    with pytest.raises(ValidacionMaterial, match="La descripción es obligatoria"):
        crear_material(_datos(descripcion="   "), usuario_almacen)


@pytest.mark.django_db
def test_lote_largo(usuario_almacen):
    with pytest.raises(
        ValidacionMaterial, match="El lote no puede superar los 50 caracteres"
    ):
        crear_material(_datos(lote="X" * 51), usuario_almacen)


@pytest.mark.django_db
def test_tipo_obligatorio(usuario_almacen):
    datos = _datos()
    datos.pop("tipo")

    with pytest.raises(ValidacionMaterial, match="El tipo es obligatorio"):
        crear_material(datos, usuario_almacen)


@pytest.mark.django_db
def test_cuenta_inactiva_no_crea(usuario_almacen):
    Usuario.objects.filter(pk=usuario_almacen.pk).update(is_active=False)
    usuario_almacen.refresh_from_db()

    with pytest.raises(PermisoDenegado):
        crear_material(_datos(), usuario_almacen)
