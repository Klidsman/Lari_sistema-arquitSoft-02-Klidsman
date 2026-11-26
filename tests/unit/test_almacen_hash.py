"""Ruta segura y verificación de hash del Excel de asignación."""

from datetime import date
from pathlib import Path

import pytest
from django.conf import settings

from asignaciones import almacen_services as services
from asignaciones.services import crear_y_enviar_solicitud
from stock.models import StockGeneral


def _solicitud(usuario_tenant, tenant, tecnico, material):
    StockGeneral.objects.create(
        tenant=tenant, material=material, cantidad=5
    )
    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )
    return solicitud


@pytest.mark.django_db
def test_verificar_archivo_correcto(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    ruta = services.verificar_archivo(solicitud)
    assert ruta.exists()
    assert ruta.is_relative_to(Path(settings.MEDIA_ROOT))


@pytest.mark.django_db
def test_archivo_alterado_se_bloquea(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    ruta = services.verificar_archivo(solicitud)
    ruta.write_bytes(ruta.read_bytes() + b"alterado")
    with pytest.raises(services.ArchivoAlterado):
        services.verificar_archivo(solicitud)


@pytest.mark.django_db
def test_archivo_ausente_no_esta_disponible(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    ruta = services.verificar_archivo(solicitud)
    ruta.unlink()
    with pytest.raises(services.SolicitudNoExiste):
        services.verificar_archivo(solicitud)


@pytest.mark.django_db
def test_ruta_con_travesia_se_rechaza(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    solicitud.excel_ruta = "../fuera.xlsx"
    solicitud.save(update_fields=["excel_ruta"])
    with pytest.raises(services.SolicitudNoExiste):
        services.ruta_absoluta_solicitud(solicitud)


@pytest.mark.django_db
def test_ruta_absoluta_se_rechaza(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    solicitud.excel_ruta = str(
        Path(settings.MEDIA_ROOT) / "otra" / "archivo.xlsx"
    )
    solicitud.save(update_fields=["excel_ruta"])
    with pytest.raises(services.SolicitudNoExiste):
        services.ruta_absoluta_solicitud(solicitud)


@pytest.mark.django_db
def test_sin_excel_no_hay_ruta(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    solicitud = _solicitud(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    solicitud.excel_ruta = ""
    solicitud.save(update_fields=["excel_ruta"])
    with pytest.raises(services.SolicitudNoExiste):
        services.ruta_absoluta_solicitud(solicitud)
