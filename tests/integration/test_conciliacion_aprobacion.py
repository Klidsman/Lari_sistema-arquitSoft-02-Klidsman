"""Aprobación, rechazo y recálculo de conciliaciones."""

import pytest
from django.utils import timezone

from auditoria.models import RegistroCambio
from conciliaciones.models import (
    DiferenciaSerie,
    EstadoConciliacion,
    TipoDiferenciaSerie,
)
from conciliaciones.services import (
    AprobacionBloqueada,
    HuboCambios,
    SerieInactiva,
    aprobar_conciliacion,
    crear_conciliacion,
    rechazar_conciliacion,
)
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico
from tecnicos.models import Tecnico
from tests.reportes import archivo_xlsx, fila_no_seriada, fila_seriada


def _serie(tenant, material, tecnico, numero, usuario):
    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=tenant.region,
        material=material,
        lote=material.lote,
        estado=EstadoSerie.ASIGNADA,
        tecnico=tecnico,
        asignada_en=timezone.now(),
        creado_por=usuario,
    )


def _destino(tenant, usuario_tenant):
    return Tecnico.objects.create(
        tenant=tenant, nif="LA2222", nombre="Destino", creado_por=usuario_tenant
    )


@pytest.mark.django_db
def test_ajustes_al_aprobar(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    reasignar = _serie(
        tenant, material_seriado, tecnico, "SER000000001", usuario_tenant
    )
    instalar = _serie(
        tenant, material_seriado, tecnico, "SER000000003", usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=50
    )
    general = StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=100
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_seriada(material_seriado, destino.nif, "SER000000001"),
                fila_seriada(material_seriado, destino.nif, "SER000000002"),
                fila_no_seriada(material_no_seriado, tecnico.nif, 40),
            ]
        ),
    )
    resultado = aprobar_conciliacion(conciliacion, usuario_tenant)

    conciliacion.refresh_from_db()
    reasignar.refresh_from_db()
    instalar.refresh_from_db()
    general.refresh_from_db()
    creada = Serie.objects.get(numero="SER000000002")

    assert conciliacion.estado == EstadoConciliacion.APROBADA
    assert conciliacion.aprobado_por_id == usuario_tenant.pk
    assert conciliacion.ajustes_aplicados >= 4
    assert reasignar.tecnico_id == destino.pk
    assert reasignar.estado == EstadoSerie.ASIGNADA
    assert creada.tecnico_id == destino.pk
    assert creada.estado == EstadoSerie.ASIGNADA
    assert instalar.estado == EstadoSerie.INSTALADA
    assert instalar.tecnico_id is None
    assert instalar.asignada_en is None
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 40
    )
    assert (
        StockTecnico.objects.get(
            tecnico=destino, material=material_seriado
        ).cantidad
        == 2
    )
    assert general.cantidad == 100
    assert len(resultado.series_creadas) == 1
    assert len(resultado.series_reasignadas) == 1
    assert len(resultado.series_instaladas) == 1


@pytest.mark.django_db
def test_auditoria_de_ajustes(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    _serie(tenant, material_seriado, tecnico, "SER000000003", usuario_tenant)
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_seriada(material_seriado, destino.nif, "SER000000001"),
                fila_no_seriada(material_no_seriado, tecnico.nif, 4),
            ]
        ),
    )
    aprobar_conciliacion(conciliacion, usuario_tenant)

    eventos = set(
        RegistroCambio.objects.filter(entidad="Conciliacion").values_list(
            "campo", flat=True
        )
    )
    assert {"alta", "archivo", "estado"} <= eventos
    serie_estado = RegistroCambio.objects.filter(
        entidad="Serie", campo="estado", valor_nuevo="INSTALADA"
    )
    assert serie_estado.exists()
    stock = RegistroCambio.objects.filter(
        entidad="StockTecnico", campo="cantidad"
    ).order_by("id")
    assert stock.exists()
    ultimo = stock.last()
    assert ultimo.valor_anterior != ultimo.valor_nuevo


@pytest.mark.django_db
def test_aprobacion_bloqueada_por_material_no_catalogado(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_no_seriada(material_no_seriado, tecnico.nif, 1),
                ["99999999999", "", 2, None, tecnico.nif, "AJENO"],
            ]
        ),
    )
    with pytest.raises(AprobacionBloqueada):
        aprobar_conciliacion(conciliacion, usuario_tenant)
    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.EN_REVISION


@pytest.mark.django_db
def test_recalculo_si_hubo_cambios(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    fila = StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 4)]),
    )
    StockTecnico.objects.filter(pk=fila.pk).update(cantidad=7)

    with pytest.raises(HuboCambios):
        aprobar_conciliacion(conciliacion, usuario_tenant)

    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.EN_REVISION
    assert conciliacion.requiere_revision is True
    assert (
        StockTecnico.objects.get(pk=fila.pk).cantidad == 7
    )
    diferencia = conciliacion.diferencias_cantidades.get()
    assert diferencia.cantidad_sistema == 7

    aprobar_conciliacion(conciliacion, usuario_tenant)
    assert StockTecnico.objects.get(pk=fila.pk).cantidad == 4


@pytest.mark.django_db
def test_aprobacion_todo_o_nada(
    usuario_tenant,
    tenant,
    tecnico,
    material_seriado,
    material_no_seriado,
    almacen,
    monkeypatch,
):
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=0
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_seriada(material_seriado, tecnico.nif, "SER000000001"),
                fila_no_seriada(material_no_seriado, tecnico.nif, 5),
            ]
        ),
    )

    def _fallar(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(
        "conciliaciones.services.incrementar_stock_tecnico", _fallar
    )
    with pytest.raises(RuntimeError):
        aprobar_conciliacion(conciliacion, usuario_tenant)

    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.EN_REVISION
    assert not Serie.objects.filter(numero="SER000000001").exists()
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 0
    )


@pytest.mark.django_db
def test_aprobar_serie_disponible_la_asigna_al_tecnico(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.DISPONIBLE,
        creado_por=usuario_tenant,
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_seriada(material_seriado, tecnico.nif, "SER000000001")]
        ),
    )
    diferencia = conciliacion.diferencias_series.get()
    assert (
        diferencia.tipo == TipoDiferenciaSerie.EN_SISTEMA_SIN_TECNICO
    )
    assert diferencia.tecnico_sistema_id is None

    aprobar_conciliacion(conciliacion, usuario_tenant)

    serie.refresh_from_db()
    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.APROBADA
    assert serie.estado == EstadoSerie.ASIGNADA
    assert serie.tecnico_id == tecnico.pk
    assert serie.asignada_en is not None


@pytest.mark.django_db
def test_serie_inactiva_aparece_despues_de_cargar_no_rompe_la_aprobacion(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    destino = _destino(tenant, usuario_tenant)
    serie = _serie(
        tenant, material_seriado, destino, "SER000000001", usuario_tenant
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_seriada(material_seriado, tecnico.nif, "SER000000001")]
        ),
    )
    assert conciliacion.diferencias_series.get().tipo == (
        TipoDiferenciaSerie.EN_OTRO_TECNICO
    )

    Serie.objects.filter(pk=serie.pk).update(
        estado=EstadoSerie.INACTIVA,
        tecnico=None,
        asignada_en=None,
    )
    with pytest.raises(SerieInactiva):
        aprobar_conciliacion(conciliacion, usuario_tenant)

    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.EN_REVISION
    serie.refresh_from_db()
    assert serie.estado == EstadoSerie.INACTIVA


@pytest.mark.django_db
def test_rechazar_no_cambia_nada(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    serie = _serie(
        tenant, material_seriado, tecnico, "SER000000003", usuario_tenant
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_seriada(material_seriado, tecnico.nif, "SER000000001")]
        ),
    )
    rechazar_conciliacion(conciliacion, usuario_tenant, "  No procede  ")
    conciliacion.refresh_from_db()
    serie.refresh_from_db()

    assert conciliacion.estado == EstadoConciliacion.RECHAZADA
    assert conciliacion.motivo_rechazo == "No procede"
    assert serie.estado == EstadoSerie.ASIGNADA
    assert serie.tecnico_id == tecnico.pk
    assert not Serie.objects.filter(numero="SER000000001").exists()
