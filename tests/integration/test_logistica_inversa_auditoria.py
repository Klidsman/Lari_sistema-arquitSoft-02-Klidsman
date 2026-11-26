"""Auditoría de devoluciones y bajas."""

from datetime import date

import pytest
from django.conf import settings
from django.utils import timezone

from auditoria.models import RegistroCambio
from logistica_inversa.services import registrar_baja_equipo, registrar_devolucion
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico


def _serie(
    tenant,
    material,
    actor,
    tecnico=None,
    estado=EstadoSerie.ASIGNADA,
    numero="SER000000001",
):
    asignada = estado == EstadoSerie.ASIGNADA
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=estado,
        tecnico=tecnico if asignada else None,
        asignada_en=timezone.now() if asignada else None,
        creado_por=actor,
    )


@pytest.mark.django_db
def test_auditoria_de_devolucion_completa(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    primera = _serie(
        tenant, material_seriado, usuario_tenant, tecnico, numero="SER000000001"
    )
    segunda = _serie(
        tenant, material_seriado, usuario_tenant, tecnico, numero="SER000000002"
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=2
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=10
    )
    devolucion = registrar_devolucion(
        tenant, tecnico, date.today(), [primera, segunda], "", usuario_tenant
    )

    assert RegistroCambio.objects.filter(
        entidad="Devolucion", entidad_id=devolucion.pk, campo="alta"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="Devolucion", entidad_id=devolucion.pk, campo="acta"
    ).exists()
    assert (
        RegistroCambio.objects.filter(
            entidad="LineaDevolucion", campo="alta"
        ).count()
        == 2
    )
    for serie in (primera, segunda):
        assert RegistroCambio.objects.filter(
            entidad="Serie",
            entidad_id=serie.pk,
            campo="estado",
            valor_anterior="ASIGNADA",
            valor_nuevo="DISPONIBLE",
        ).exists()
        assert RegistroCambio.objects.filter(
            entidad="Serie", entidad_id=serie.pk, campo="tecnico"
        ).exists()
        assert RegistroCambio.objects.filter(
            entidad="Serie", entidad_id=serie.pk, campo="asignada_en"
        ).exists()

    tecnico_evento = RegistroCambio.objects.get(
        entidad="StockTecnico", campo="cantidad"
    )
    general_evento = RegistroCambio.objects.get(
        entidad="StockGeneral", campo="cantidad"
    )
    assert tecnico_evento.valor_anterior == "2"
    assert tecnico_evento.valor_nuevo == "0"
    assert general_evento.valor_anterior == "10"
    assert general_evento.valor_nuevo == "12"


@pytest.mark.django_db
def test_auditoria_de_baja_solo_toca_el_nivel_correcto(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    asignada = _serie(
        tenant, material_seriado, usuario_tenant, tecnico, numero="SER000000001"
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=3
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=10
    )
    baja = registrar_baja_equipo(
        tenant, asignada, "AVERIA", "dañada", usuario_tenant
    )
    assert RegistroCambio.objects.filter(
        entidad="BajaEquipo", entidad_id=baja.pk, campo="alta"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="Serie",
        entidad_id=asignada.pk,
        campo="estado",
        valor_nuevo="INACTIVA",
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="StockTecnico", campo="cantidad"
    ).exists()
    assert not RegistroCambio.objects.filter(
        entidad="StockGeneral", campo="cantidad"
    ).exists()


@pytest.mark.django_db
def test_auditoria_sin_secretos_binarios_ni_rutas_absolutas(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, usuario_tenant, tecnico
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_seriado, cantidad=1
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_seriado, cantidad=0
    )
    devolucion = registrar_devolucion(
        tenant, tecnico, date.today(), [serie], "", usuario_tenant
    )

    valores = list(
        RegistroCambio.objects.values_list(
            "campo", "valor_anterior", "valor_nuevo"
        )
    )
    texto = " ".join(
        f"{campo} {anterior} {nuevo}"
        for campo, anterior, nuevo in valores
    ).lower()
    for prohibido in ("password", "token", "secret", "clave"):
        assert prohibido not in texto
    for _, anterior, nuevo in valores:
        for valor in (anterior, nuevo):
            assert "\x00" not in valor
            assert str(settings.MEDIA_ROOT) not in valor
    assert devolucion.acta_ruta.startswith(settings.ACTAS_DIR)
    assert not devolucion.acta_ruta.startswith("/")
