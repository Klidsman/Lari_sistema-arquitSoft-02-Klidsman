"""Integración de la baja lógica."""

import pytest

from acceso.models import Rol, Usuario
from auditoria.models import RegistroCambio
from materiales.models import Material
from materiales.services import (
    PermisoDenegado,
    ValidacionMaterial,
    buscar_materiales,
    crear_material,
    dar_de_baja_material,
    listar_materiales,
)


@pytest.mark.django_db
def test_baja_marca_inactivo_y_audita(material, usuario_almacen):
    dar_de_baja_material(material, usuario_almacen)

    material.refresh_from_db()
    assert material.activo is False
    assert material.actualizado_por_id == usuario_almacen.pk

    registro = RegistroCambio.objects.get(
        entidad="Material", entidad_id=material.pk, campo="activo"
    )
    assert registro.valor_anterior == "True"
    assert registro.valor_nuevo == "False"


@pytest.mark.django_db
def test_baja_no_borra_la_fila(material, usuario_almacen):
    dar_de_baja_material(material, usuario_almacen)

    assert Material.objects.filter(pk=material.pk).exists()


@pytest.mark.django_db
def test_material_de_baja_sale_del_catalogo(material, usuario_almacen):
    dar_de_baja_material(material, usuario_almacen)

    assert not listar_materiales().filter(pk=material.pk).exists()
    assert not buscar_materiales(material.codigo).filter(pk=material.pk).exists()


@pytest.mark.django_db
def test_cualquier_almacen_puede_dar_de_baja(material, region):
    otro_almacen = Usuario.objects.create_user(
        email="almacen2@lari.local",
        password="ClaveAlmacen12345",
        rol=Rol.RESPONSABLE_ALMACEN,
        region=region,
        is_active=True,
    )

    dar_de_baja_material(material, otro_almacen)

    material.refresh_from_db()
    assert material.activo is False


@pytest.mark.django_db
def test_tenant_no_puede_dar_de_baja(material, usuario_tenant):
    with pytest.raises(PermisoDenegado):
        dar_de_baja_material(material, usuario_tenant)


@pytest.mark.django_db
def test_admin_no_puede_dar_de_baja(material, usuario_admin):
    with pytest.raises(PermisoDenegado):
        dar_de_baja_material(material, usuario_admin)


@pytest.mark.django_db
def test_crear_con_codigo_de_baja_reactiva(usuario_almacen):
    material = Material.objects.create(
        codigo="10402520999",
        descripcion="VIEJA",
        lote="",
        es_seriado=True,
        activo=False,
        creado_por=usuario_almacen,
    )

    reactivado = crear_material(
        {
            "codigo": "10402520999",
            "descripcion": "NUEVA",
            "lote": "lote nuevo",
            "tipo": "NO_SERIADO",
        },
        usuario_almacen,
    )

    assert reactivado.pk == material.pk
    material.refresh_from_db()
    assert material.activo is True
    assert material.descripcion == "NUEVA"
    assert material.lote == "LOTE NUEVO"
    assert material.es_seriado is False

    registro = RegistroCambio.objects.get(
        entidad="Material", entidad_id=material.pk, campo="activo"
    )
    assert registro.valor_anterior == "False"
    assert registro.valor_nuevo == "True"
    assert RegistroCambio.objects.filter(
        entidad="Material", entidad_id=material.pk, campo="descripcion"
    ).exists()


@pytest.mark.django_db
def test_reactivacion_bloqueada_por_movimientos(
    usuario_almacen, verificacion_movimientos
):
    Material.objects.create(
        codigo="10402520998",
        descripcion="VIEJA",
        lote="",
        es_seriado=True,
        activo=False,
        creado_por=usuario_almacen,
    )
    verificacion_movimientos(lambda material: True)

    with pytest.raises(
        ValidacionMaterial,
        match="El tipo no se puede cambiar: el material tiene movimientos",
    ):
        crear_material(
            {
                "codigo": "10402520998",
                "descripcion": "NUEVA",
                "lote": "",
                "tipo": "NO_SERIADO",
            },
            usuario_almacen,
        )

    assert not Material.objects.get(codigo="10402520998").activo


@pytest.mark.django_db
def test_codigo_activo_sigue_siendo_duplicado(usuario_almacen, material):
    from materiales.services import MaterialDuplicado

    with pytest.raises(MaterialDuplicado):
        crear_material(
            {
                "codigo": material.codigo,
                "descripcion": "OTRA",
                "lote": "",
                "tipo": "SERIADO",
            },
            usuario_almacen,
        )


@pytest.mark.django_db
def test_baja_idempotente_sin_auditoria_extra(material, usuario_almacen):
    dar_de_baja_material(material, usuario_almacen)
    antes = RegistroCambio.objects.filter(
        entidad="Material", entidad_id=material.pk, campo="activo"
    ).count()

    dar_de_baja_material(material, usuario_almacen)

    assert (
        RegistroCambio.objects.filter(
            entidad="Material", entidad_id=material.pk, campo="activo"
        ).count()
        == antes
    )
