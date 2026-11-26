"""Búsqueda y descarga de Excels históricos."""

from datetime import date
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from acceso.models import Rol, Usuario
from asignaciones import almacen_services
from asignaciones.models import EnvioCorreo
from asignaciones.services import crear_y_enviar_solicitud
from stock.models import StockGeneral
from tenants.models import Almacen, Region, Tenant


def _solicitud(usuario, tenant, tecnico, material):
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
                "cantidad": 1,
            }
        ],
        usuario,
    )


def _envio(solicitud, numero):
    return EnvioCorreo.objects.create(
        solicitud=solicitud,
        tenant=solicitud.tenant,
        region=solicitud.region,
        numero_intento=numero,
        destinatario="almacen@lari.local",
        archivo=solicitud.excel_ruta,
        hash_sha256=solicitud.excel_hash,
    )


@pytest.mark.django_db
def test_historicos_filtra_y_no_duplica_intentos(
    usuario_admin,
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    region,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    _envio(solicitud, 1)
    ultimo = _envio(solicitud, 2)
    ultimo.estado = EnvioCorreo.ESTADO_FALLIDO
    ultimo.save(update_fields=["estado"])

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
    ajena = _solicitud(
        otro_usuario, otro_tenant, otro_tecnico, material_no_seriado
    )

    propias = list(
        almacen_services.historicos(usuario_almacen, {}).values_list(
            "pk", flat=True
        )
    )
    assert propias == [solicitud.pk]

    globales = set(
        almacen_services.historicos(usuario_admin, {}).values_list(
            "pk", flat=True
        )
    )
    assert globales == {solicitud.pk, ajena.pk}

    por_tenant = almacen_services.historicos(
        usuario_admin, {"tenant": tenant.pk}
    )
    assert list(por_tenant.values_list("pk", flat=True)) == [solicitud.pk]

    por_tecnico = almacen_services.historicos(
        usuario_admin, {"tecnico": tecnico.pk}
    )
    assert list(por_tecnico.values_list("pk", flat=True)) == [solicitud.pk]

    por_estado = almacen_services.historicos(
        usuario_admin, {"estado": "ENVIADA"}
    )
    assert {s.pk for s in por_estado} == {solicitud.pk, ajena.pk}

    hoy = date.today().isoformat()
    por_fecha = almacen_services.historicos(
        usuario_admin, {"fecha_desde": hoy, "fecha_hasta": hoy}
    )
    assert {s.pk for s in por_fecha} == {solicitud.pk, ajena.pk}
    futura = (date.today().replace(year=date.today().year + 1)).isoformat()
    assert almacen_services.historicos(
        usuario_admin, {"fecha_desde": futura}
    ).count() == 0

    fila = almacen_services.historicos(
        usuario_admin, {"tenant": tenant.pk}
    ).get()
    assert fila.ultimo_envio_estado == EnvioCorreo.ESTADO_FALLIDO


@pytest.mark.django_db
def test_historicos_excluye_solicitudes_sin_excel(
    usuario_tenant,
    usuario_almacen,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    from asignaciones.services import crear_borrador_solicitud

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    crear_borrador_solicitud(
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
    assert almacen_services.historicos(usuario_almacen, {}).count() == 0


@pytest.mark.django_db
def test_descarga_historica_por_rol_y_region(
    cliente_almacen,
    cliente_autenticado,
    cliente_tenant,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    guardada = Path(settings.MEDIA_ROOT) / solicitud.excel_ruta
    contenido = guardada.read_bytes()

    url = reverse("descargar_historico_almacen", args=[solicitud.pk])
    respuesta = cliente_almacen.get(url)
    assert respuesta.status_code == 200
    assert b"".join(respuesta.streaming_content) == contenido

    respuesta = cliente_autenticado.get(url)
    assert respuesta.status_code == 200
    assert b"".join(respuesta.streaming_content) == contenido

    assert cliente_tenant.get(url).status_code == 403

    guardada.write_bytes(contenido + b"alterado")
    assert cliente_almacen.get(url).status_code == 409

    guardada.write_bytes(contenido)
    assert cliente_almacen.get(
        reverse("descargar_historico_almacen", args=[solicitud.pk + 999])
    ).status_code == 404


@pytest.mark.django_db
def test_historicos_responde_sin_n_mas_uno(
    cliente_almacen,
    usuario_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
    django_assert_max_num_queries,
):
    for _ in range(10):
        _solicitud(usuario_tenant, tenant, tecnico, material_no_seriado)

    with django_assert_max_num_queries(45):
        respuesta = cliente_almacen.get(reverse("historicos_almacen"))
    assert respuesta.status_code == 200
