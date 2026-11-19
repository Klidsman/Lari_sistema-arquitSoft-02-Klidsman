"""Integración de la edición de materiales."""

import pytest

from acceso.models import Usuario
from auditoria.models import RegistroCambio
from materiales.models import Material
from materiales.services import (
    PermisoDenegado,
    ValidacionMaterial,
    actualizar_material,
)


@pytest.mark.django_db
def test_creador_actualiza_descripcion(material, usuario_almacen):
    actualizar_material(
        material,
        {"descripcion": "ROSETA ÓPTICA"},
        usuario_almacen,
    )

    material.refresh_from_db()
    assert material.descripcion == "ROSETA ÓPTICA"
    assert material.actualizado_por_id == usuario_almacen.pk


@pytest.mark.django_db
def test_admin_actualiza_lote(material, usuario_admin):
    actualizar_material(material, {"lote": "NUEVO LOTE"}, usuario_admin)

    material.refresh_from_db()
    assert material.lote == "NUEVO LOTE"


@pytest.mark.django_db
def test_auditoria_por_campo(material, usuario_almacen):
    actualizar_material(
        material,
        {"descripcion": "ROSETA ÓPTICA", "lote": "OTRO LOTE"},
        usuario_almacen,
    )

    descripcion = RegistroCambio.objects.get(
        entidad="Material", entidad_id=material.pk, campo="descripcion"
    )
    lote = RegistroCambio.objects.get(
        entidad="Material", entidad_id=material.pk, campo="lote"
    )

    assert descripcion.valor_anterior == "ROSETA"
    assert descripcion.valor_nuevo == "ROSETA ÓPTICA"
    assert lote.valor_anterior == "FIBERHOME"
    assert lote.valor_nuevo == "OTRO LOTE"


@pytest.mark.django_db
def test_edicion_sin_cambios_no_audita(material, usuario_almacen):
    antes = RegistroCambio.objects.filter(
        entidad="Material", entidad_id=material.pk
    ).count()

    actualizar_material(
        material,
        {
            "descripcion": material.descripcion,
            "lote": material.lote,
            "tipo": material.tipo,
        },
        usuario_almacen,
    )

    assert (
        RegistroCambio.objects.filter(
            entidad="Material", entidad_id=material.pk
        ).count()
        == antes
    )


@pytest.mark.django_db
def test_codigo_rechazado(material, usuario_almacen):
    with pytest.raises(ValidacionMaterial, match="El código no se puede cambiar"):
        actualizar_material(material, {"codigo": "99999999999"}, usuario_almacen)


@pytest.mark.django_db
def test_otra_cuenta_rechazada(material, usuario_otro_tenant):
    with pytest.raises(PermisoDenegado):
        actualizar_material(
            material,
            {"descripcion": "NO PERMITIDO"},
            usuario_otro_tenant,
        )


@pytest.mark.django_db
def test_almacen_edita_material_creado_por_tenant(usuario_tenant, usuario_almacen):
    material = Material.objects.create(
        codigo="10402520001",
        descripcion="LEGADO",
        lote="",
        es_seriado=True,
        creado_por=usuario_tenant,
    )

    actualizar_material(
        material,
        {"descripcion": "EDITADO POR ALMACEN"},
        usuario_almacen,
    )

    material.refresh_from_db()
    assert material.descripcion == "EDITADO POR ALMACEN"
    assert material.creado_por_id == usuario_tenant.pk
    assert material.actualizado_por_id == usuario_almacen.pk


@pytest.mark.django_db
def test_creador_tenant_ya_no_edita(usuario_tenant):
    material = Material.objects.create(
        codigo="10402520002",
        descripcion="LEGADO",
        lote="",
        es_seriado=True,
        creado_por=usuario_tenant,
    )

    with pytest.raises(PermisoDenegado):
        actualizar_material(
            material,
            {"descripcion": "INTENTO"},
            usuario_tenant,
        )


@pytest.mark.django_db
def test_actualizado_por_y_fecha(material, usuario_admin):
    anterior = material.actualizado_en

    actualizado = actualizar_material(
        material,
        {"descripcion": "CAMBIADA"},
        usuario_admin,
    )

    assert actualizado.actualizado_por_id == usuario_admin.pk
    assert actualizado.actualizado_en >= anterior
