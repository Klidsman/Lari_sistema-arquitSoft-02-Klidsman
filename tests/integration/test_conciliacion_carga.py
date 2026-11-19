"""Carga y comparación de conciliaciones."""

import pytest
from django.utils import timezone

from conciliaciones.models import (
    DiferenciaCantidad,
    DiferenciaSerie,
    EstadoConciliacion,
    MaterialNoCatalogado,
    TipoDiferenciaSerie,
)
from conciliaciones.services import (
    ConciliacionEnRevision,
    TecnicosFueraRegion,
    alertas_conciliacion,
    crear_conciliacion,
)
from series.models import EstadoSerie, Serie
from stock.models import StockTecnico
from tecnicos.models import Tecnico
from tests.reportes import archivo_xlsx, fila_no_seriada, fila_seriada


def _serie(tenant, material, tecnico, numero, usuario, estado=EstadoSerie.ASIGNADA):
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
        creado_por=usuario,
    )


@pytest.mark.django_db
def test_cargar_reporte_crea_conciliacion_en_revision_sin_tocar_stock(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado, almacen
):
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=10
    )
    archivo = archivo_xlsx(
        [
            fila_no_seriada(material_no_seriado, tecnico.nif, 4),
            fila_seriada(material_seriado, tecnico.nif, "SER000000001"),
        ]
    )
    conciliacion = crear_conciliacion(usuario_tenant, archivo)

    assert conciliacion.estado == EstadoConciliacion.EN_REVISION
    assert conciliacion.archivo_ruta
    assert len(conciliacion.hash_sha256) == 64
    assert (
        StockTecnico.objects.get(
            tecnico=tecnico, material=material_no_seriado
        ).cantidad
        == 10
    )
    diferencia = DiferenciaCantidad.objects.get(conciliacion=conciliacion)
    assert diferencia.cantidad_sistema == 10
    assert diferencia.cantidad_reporte == 4
    assert diferencia.diferencia == -6
    assert DiferenciaSerie.objects.filter(
        conciliacion=conciliacion,
        tipo=TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA,
        numero="SER000000001",
    ).exists()


@pytest.mark.django_db
def test_solo_una_conciliacion_en_revision(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    archivo = archivo_xlsx(
        [fila_no_seriada(material_no_seriado, tecnico.nif, 0)]
    )
    crear_conciliacion(usuario_tenant, archivo)
    with pytest.raises(ConciliacionEnRevision):
        crear_conciliacion(
            usuario_tenant,
            archivo_xlsx([fila_no_seriada(material_no_seriado, tecnico.nif, 1)]),
        )


@pytest.mark.django_db
def test_tecnico_ausente_se_ignora(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    destino = Tecnico.objects.create(
        tenant=tenant, nif="LA2222", nombre="Destino", creado_por=usuario_tenant
    )
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=9
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx([fila_no_seriada(material_no_seriado, destino.nif, 2)]),
    )
    assert not DiferenciaCantidad.objects.filter(
        conciliacion=conciliacion, tecnico=tecnico
    ).exists()
    assert DiferenciaCantidad.objects.filter(
        conciliacion=conciliacion, tecnico=destino
    ).exists()


@pytest.mark.django_db
def test_material_ausente_para_tecnico_presente_se_asume_cero(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado, almacen
):
    StockTecnico.objects.create(
        tenant=tenant, tecnico=tecnico, material=material_no_seriado, cantidad=7
    )
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [fila_seriada(material_seriado, tecnico.nif, "SER000000001")]
        ),
    )
    diferencia = DiferenciaCantidad.objects.get(conciliacion=conciliacion)
    assert diferencia.material_id == material_no_seriado.pk
    assert diferencia.cantidad_sistema == 7
    assert diferencia.cantidad_reporte == 0
    assert diferencia.diferencia == -7


@pytest.mark.django_db
def test_diferencias_de_series_en_dos_grupos(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    _serie(tenant, material_seriado, tecnico, "SER000000001", usuario_tenant)
    _serie(tenant, material_seriado, tecnico, "SER000000003", usuario_tenant)
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_seriada(material_seriado, tecnico.nif, "SER000000001"),
                fila_seriada(material_seriado, tecnico.nif, "SER000000002"),
            ]
        ),
    )
    nuevos = DiferenciaSerie.objects.filter(
        conciliacion=conciliacion,
        tipo=TipoDiferenciaSerie.EN_REPORTE_NO_SISTEMA,
    )
    faltantes = DiferenciaSerie.objects.filter(
        conciliacion=conciliacion,
        tipo=TipoDiferenciaSerie.EN_SISTEMA_NO_REPORTE,
    )
    assert list(nuevos.values_list("numero", flat=True)) == ["SER000000002"]
    assert list(faltantes.values_list("numero", flat=True)) == ["SER000000003"]


@pytest.mark.django_db
def test_alertas_categorizadas(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    _serie(tenant, material_seriado, tecnico, "SER000000003", usuario_tenant)
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_seriada(material_seriado, tecnico.nif, "SER000000002"),
                fila_seriada(material_seriado, tecnico.nif, "SER000000004"),
            ]
        ),
    )
    alertas = alertas_conciliacion(conciliacion)
    assert len(alertas["material_ajeno"]) == 2
    assert len(alertas["series_faltantes"]) == 1
    assert alertas["tecnicos_inconsistentes"][0]["tecnico"] == tecnico


@pytest.mark.django_db
def test_tecnico_de_otro_tenant_de_la_region_se_ignora(
    usuario_tenant, tenant, tecnico_otro_tenant, material_no_seriado, almacen
):
    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_no_seriada(
                    material_no_seriado, tecnico_otro_tenant.nif, 5
                )
            ]
        ),
    )
    assert conciliacion.diferencias_series.count() == 0
    assert conciliacion.diferencias_cantidades.count() == 0


@pytest.mark.django_db
def test_tecnico_desconocido_rechaza_archivo(
    usuario_tenant, material_no_seriado, almacen
):
    with pytest.raises(TecnicosFueraRegion):
        crear_conciliacion(
            usuario_tenant,
            archivo_xlsx(
                [fila_no_seriada(material_no_seriado, "LA7777", 1)]
            ),
        )


@pytest.mark.django_db
def test_material_no_catalogado_se_registra_sin_bloquear_carga(
    usuario_tenant, tecnico, material_no_seriado, almacen
):
    class Ajeno:
        codigo = "99999999999"
        lote = ""
        descripcion = "MATERIAL AJENO"

    conciliacion = crear_conciliacion(
        usuario_tenant,
        archivo_xlsx(
            [
                fila_no_seriada(material_no_seriado, tecnico.nif, 1),
                [
                    Ajeno.codigo,
                    "",
                    1,
                    None,
                    tecnico.nif,
                    Ajeno.descripcion,
                ],
            ]
        ),
    )
    assert MaterialNoCatalogado.objects.filter(
        conciliacion=conciliacion, codigo=Ajeno.codigo
    ).exists()
