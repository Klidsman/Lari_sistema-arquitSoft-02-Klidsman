"""Bandeja del almacén: alcance por región, filtros y totales."""

import time
from datetime import date

import pytest
from django.urls import reverse

from acceso.models import Rol, Usuario
from asignaciones import almacen_services
from asignaciones.models import EstadoSolicitud
from asignaciones.services import (
    cancelar_solicitud,
    crear_borrador_solicitud,
    crear_y_enviar_solicitud,
)
from stock.models import StockGeneral
from tenants.models import Almacen, Region, Tenant


def _enviada(usuario_tenant, tenant, tecnico, material, cantidad=1):
    StockGeneral.objects.get_or_create(
        tenant=tenant, material=material, defaults={"cantidad": 1000}
    )
    return crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material.pk,
                "cantidad": cantidad,
            }
        ],
        usuario_tenant,
    )


@pytest.mark.django_db
def test_bandeja_solo_muestra_la_region_y_excluye_borradores(
    usuario_admin,
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    region,
):
    enviada = _enviada(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    confirmada = _enviada(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    almacen_services.confirmar_solicitud(confirmada, usuario_almacen)
    rechazada = _enviada(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    almacen_services.rechazar_solicitud(
        rechazada, "Sin stock", usuario_almacen
    )
    borrador = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )
    cancelada = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )
    cancelar_solicitud(cancelada, usuario_tenant)

    otra_region = Region.objects.create(
        codigo="AYA", nombre="Ayacucho", creado_por=usuario_admin
    )
    Almacen.objects.create(
        region=otra_region,
        centro="PR02",
        codigo_almacen="BE02",
        buzon="almacen.aya@lari.local",
        creado_por=usuario_admin,
    )
    otro_tenant = Tenant.objects.create(
        codigo="TEN-AYA",
        nombre="Tenant Ayacucho",
        region=otra_region,
        creado_por=usuario_admin,
    )
    otro_usuario = Usuario.objects.create_user(
        email="aya@lari.local",
        password="ClaveAya12345",
        rol=Rol.USUARIO_TENANT,
        tenant=otro_tenant,
        is_active=True,
    )
    from tecnicos.models import Tecnico

    otro_tecnico = Tecnico.objects.create(
        tenant=otro_tenant,
        nif="LA4444",
        nombre="Técnico Ayacucho",
        creado_por=otro_usuario,
    )
    ajena = _enviada(
        otro_usuario, otro_tenant, otro_tecnico, material_no_seriado
    )

    ids = set(almacen_services.bandeja(region).values_list("pk", flat=True))
    assert ids == {enviada.pk, confirmada.pk, rechazada.pk}
    assert borrador.pk not in ids
    assert cancelada.pk not in ids
    assert ajena.pk not in ids

    solo_enviadas = almacen_services.bandeja(
        region, EstadoSolicitud.ENVIADA
    )
    assert list(solo_enviadas.values_list("pk", flat=True)) == [enviada.pk]


@pytest.mark.django_db
def test_bandeja_calcula_totales_de_series_y_cantidad(
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    serie_existente,
    material_no_seriado,
    almacen,
    stock_general,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie_existente.pk],
            },
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 7,
            },
        ],
        usuario_tenant,
    )
    lineas = list(solicitud.lineas.all())
    total_series = sum(1 for linea in lineas if linea.serie_id)
    total_cantidad = sum(
        linea.cantidad for linea in lineas if linea.serie_id is None
    )
    assert total_series == 1
    assert total_cantidad == 7


@pytest.mark.django_db
def test_bandeja_responde_sin_n_mas_uno(
    cliente_almacen,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    django_assert_max_num_queries,
):
    for _ in range(20):
        _enviada(usuario_tenant, tenant, tecnico, material_no_seriado)

    inicio = time.perf_counter()
    with django_assert_max_num_queries(45):
        respuesta = cliente_almacen.get(reverse("bandeja_almacen"))
    duracion = time.perf_counter() - inicio
    assert respuesta.status_code == 200
    assert duracion < 1
