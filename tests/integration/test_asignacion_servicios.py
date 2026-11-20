"""Servicios de solicitudes de asignación."""

from datetime import date
from pathlib import Path

import openpyxl
import pytest
from django.conf import settings

from asignaciones.models import EstadoSolicitud, LineaAsignacion
from asignaciones.services import (
    ArchivoAlterado,
    CantidadExcedeDisponible,
    EstadoSolicitudInvalido,
    MaterialDuplicado,
    actualizar_borrador_solicitud,
    calcular_disponible,
    calcular_reservado,
    calcular_sobrante,
    cancelar_solicitud,
    crear_borrador_solicitud,
    crear_y_enviar_solicitud,
    datos_iniciales_solicitud,
    enviar_solicitud,
    materiales_disponibles_para_asignacion,
    verificar_excel_solicitud,
)
from auditoria.models import RegistroCambio
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral, StockTecnico
from tecnicos.models import Tecnico


@pytest.fixture
def segundo_tecnico(db, tenant, usuario_tenant):
    return Tecnico.objects.create(
        tenant=tenant,
        nif="LA3333",
        nombre="Segundo",
        creado_por=usuario_tenant,
    )


def _leer_excel(solicitud):
    ruta = Path(settings.MEDIA_ROOT) / solicitud.excel_ruta
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas = [list(fila) for fila in libro.active.iter_rows(values_only=True)]
    libro.close()
    return filas


@pytest.mark.django_db
def test_crear_y_enviar_seriado_genera_tabla_z31(
    usuario_tenant, tenant, tecnico, material_seriado, serie_existente, almacen, stock_general
):
    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie_existente.pk],
            }
        ],
        usuario_tenant,
    )

    assert solicitud.estado == EstadoSolicitud.ENVIADA
    assert solicitud.excel_ruta
    assert len(solicitud.excel_hash) == 64

    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.RESERVADA
    assert StockGeneral.objects.get(pk=stock_general.pk).cantidad == 100
    assert not StockTecnico.objects.exists()

    filas = _leer_excel(solicitud)
    assert filas[0] == [
        "Movimiento",
        "Centro",
        "Almacén",
        "Material",
        "Descripcion de materiales",
        "Cantidad",
        "NIF Técnico",
        "Lote",
        "Serie",
    ]
    assert filas[1] == [
        "Z31",
        almacen.centro,
        almacen.codigo_almacen,
        material_seriado.codigo,
        material_seriado.descripcion,
        1,
        tecnico.nif,
        material_seriado.lote,
        serie_existente.numero,
    ]


@pytest.mark.django_db
def test_varios_tecnicos_en_una_solicitud_mantienen_orden_de_captura(
    usuario_tenant,
    tenant,
    tecnico,
    segundo_tecnico,
    material_seriado,
    material_no_seriado,
    almacen,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )
    serie = Serie.objects.create(
        numero="SER000000001",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.DISPONIBLE,
        creado_por=usuario_tenant,
    )
    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [
            {"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 4},
            {"tecnico_id": segundo_tecnico.pk, "material_id": material_seriado.pk, "serie_ids": [serie.pk]},
            {"tecnico_id": segundo_tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 6},
        ],
        usuario_tenant,
    )

    assert solicitud.nifs_tecnicos == f"{tecnico.nif}, {segundo_tecnico.nif}"
    filas = _leer_excel(solicitud)
    assert [fila[6] for fila in filas[1:]] == [tecnico.nif, segundo_tecnico.nif, segundo_tecnico.nif]
    assert [fila[5] for fila in filas[1:]] == [4, 1, 6]
    assert LineaAsignacion.objects.filter(solicitud=solicitud).count() == 3


@pytest.mark.django_db
def test_no_seriado_suma_entre_tecnicos_y_no_supera_disponible(
    usuario_tenant, tenant, tecnico, segundo_tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    with pytest.raises(CantidadExcedeDisponible):
        crear_y_enviar_solicitud(
            tenant,
            date.today(),
            [
                {"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 6},
                {"tecnico_id": segundo_tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 6},
            ],
            usuario_tenant,
        )
    assert not LineaAsignacion.objects.exists()


@pytest.mark.django_db
def test_dos_unidades_solo_permiten_una_al_segundo_tecnico(
    usuario_tenant, tenant, tecnico, segundo_tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=2
    )
    with pytest.raises(CantidadExcedeDisponible, match="solo quedan 2"):
        crear_y_enviar_solicitud(
            tenant,
            date.today(),
            [
                {"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 1},
                {"tecnico_id": segundo_tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 2},
            ],
            usuario_tenant,
        )
    assert not LineaAsignacion.objects.exists()


@pytest.mark.django_db
def test_sobrante_refleja_el_exceso_entre_tecnicos(
    usuario_tenant, tenant, tecnico, segundo_tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=2
    )
    resumen = calcular_sobrante(
        tenant,
        [
            {"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": "1"},
            {"tecnico_id": segundo_tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": "2"},
        ],
    )
    fila = next(
        item
        for item in resumen
        if item.material.pk == material_no_seriado.pk
    )
    assert fila.disponible == 2
    assert fila.solicitado == 3
    assert fila.sobrante == -1


@pytest.mark.django_db
def test_borrador_no_reserva_y_envio_reserva(
    usuario_tenant, tenant, tecnico, material_seriado, serie_existente, almacen, stock_general
):
    solicitud = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie_existente.pk],
            }
        ],
        usuario_tenant,
    )
    serie_existente.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.BORRADOR
    assert serie_existente.estado == EstadoSerie.DISPONIBLE

    enviar_solicitud(solicitud, usuario_tenant)

    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.RESERVADA


@pytest.mark.django_db
def test_no_seriado_disponible_y_reservado(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )

    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [{"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 10}],
        usuario_tenant,
    )

    assert solicitud.estado == EstadoSolicitud.ENVIADA
    assert calcular_reservado(tenant, material_no_seriado) == 10
    assert calcular_disponible(tenant, material_no_seriado) == 40
    assert LineaAsignacion.objects.filter(serie__isnull=True).count() == 1


@pytest.mark.django_db
def test_cantidad_excede_disponible(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )

    with pytest.raises(CantidadExcedeDisponible, match="supera el stock disponible"):
        crear_y_enviar_solicitud(
            tenant,
            date.today(),
            [{"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 60}],
            usuario_tenant,
        )


@pytest.mark.django_db
def test_sobrante_por_material_seriado_y_no_seriado(
    usuario_tenant, tenant, tecnico, material_seriado, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )
    series = [
        Serie.objects.create(
            numero=f"SER00000000{indice}",
            tenant=tenant,
            region=tenant.region,
            material=material_seriado,
            lote=material_seriado.lote,
            estado=EstadoSerie.DISPONIBLE,
            creado_por=usuario_tenant,
        )
        for indice in range(1, 4)
    ]
    resumen = calcular_sobrante(
        tenant,
        [
            {"tecnico_id": tecnico.pk, "material_id": material_seriado.pk, "serie_ids": [series[0].pk]},
            {"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": "12"},
        ],
    )
    por_codigo = {fila.material.codigo: fila for fila in resumen}
    assert por_codigo[material_seriado.codigo].disponible == 3
    assert por_codigo[material_seriado.codigo].sobrante == 2
    assert por_codigo[material_no_seriado.codigo].disponible == 50
    assert por_codigo[material_no_seriado.codigo].sobrante == 38


@pytest.mark.django_db
def test_materiales_disponibles_solo_con_existencias(
    usuario_tenant,
    tenant,
    material_seriado,
    material_no_seriado,
    almacen,
):
    from materiales.models import Material

    sin_stock = Material.objects.create(
        codigo="10402520999",
        descripcion="SIN STOCK",
        es_seriado=False,
        creado_por=usuario_tenant,
    )
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=5
    )
    Serie.objects.create(
        numero="SER000000010",
        tenant=tenant,
        region=tenant.region,
        material=material_seriado,
        lote=material_seriado.lote,
        estado=EstadoSerie.DISPONIBLE,
        creado_por=usuario_tenant,
    )

    disponibles = {
        fila.material.codigo: fila
        for fila in materiales_disponibles_para_asignacion(tenant)
    }
    assert disponibles[material_no_seriado.codigo].disponible == 5
    assert disponibles[material_no_seriado.codigo].seriado is False
    assert disponibles[material_seriado.codigo].disponible == 1
    assert disponibles[material_seriado.codigo].seriado is True
    assert sin_stock.codigo not in disponibles


@pytest.mark.django_db
def test_verificar_excel_bloquea_si_se_altera(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=50
    )
    solicitud = crear_y_enviar_solicitud(
        tenant,
        date.today(),
        [{"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": 2}],
        usuario_tenant,
    )
    assert verificar_excel_solicitud(solicitud).exists()

    ruta = Path(settings.MEDIA_ROOT) / solicitud.excel_ruta
    ruta.write_bytes(ruta.read_bytes() + b"alterado")
    with pytest.raises(ArchivoAlterado):
        verificar_excel_solicitud(solicitud)


@pytest.mark.django_db
def test_cancelar_borrador(
    usuario_tenant, tenant, tecnico, material_seriado, serie_existente, almacen
):
    solicitud = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie_existente.pk],
            }
        ],
        usuario_tenant,
    )
    cancelar_solicitud(solicitud, usuario_tenant)

    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.CANCELADA

    with pytest.raises(EstadoSolicitudInvalido):
        enviar_solicitud(solicitud, usuario_tenant)


@pytest.mark.django_db
def test_material_repetido_para_el_mismo_tecnico_se_rechaza(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    with pytest.raises(MaterialDuplicado, match="ya fue agregado"):
        crear_borrador_solicitud(
            tenant,
            date.today(),
            [
                {"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": "3"},
                {"tecnico_id": tecnico.pk, "material_id": material_no_seriado.pk, "cantidad": "4"},
            ],
            usuario_tenant,
        )
    assert not LineaAsignacion.objects.exists()

@pytest.mark.django_db
def test_editar_borrador_actualiza_todo_y_audita(
    usuario_tenant,
    tenant,
    tecnico,
    segundo_tecnico,
    material_no_seriado,
    almacen,
):
    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    solicitud = crear_borrador_solicitud(
        tenant,
        date(2026, 11, 10),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 2,
            }
        ],
        usuario_tenant,
    )
    actualizar_borrador_solicitud(
        solicitud,
        date(2026, 12, 1),
        [
            {
                "tecnico_id": segundo_tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 3,
            }
        ],
        usuario_tenant,
    )

    solicitud.refresh_from_db()
    linea = solicitud.lineas.get()
    assert solicitud.estado == EstadoSolicitud.BORRADOR
    assert solicitud.fecha == date(2026, 12, 1)
    assert linea.tecnico_id == segundo_tecnico.pk
    assert linea.cantidad == 3
    assert solicitud.excel_ruta == ""
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_no_seriado
        ).cantidad
        == 10
    )
    assert RegistroCambio.objects.filter(
        entidad="LineaAsignacion", campo="baja"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="LineaAsignacion", campo="alta"
    ).exists()
    assert RegistroCambio.objects.filter(
        entidad="SolicitudAsignacion",
        entidad_id=solicitud.pk,
        campo="actualizado",
    ).exists()


@pytest.mark.django_db
def test_datos_iniciales_precargan_series_agrupadas(
    usuario_tenant, tenant, tecnico, material_seriado, almacen
):
    series = [
        Serie.objects.create(
            numero=f"SER00000000{indice}",
            tenant=tenant,
            region=tenant.region,
            material=material_seriado,
            lote=material_seriado.lote,
            estado=EstadoSerie.DISPONIBLE,
            creado_por=usuario_tenant,
        )
        for indice in range(1, 3)
    ]
    solicitud = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_seriado.pk,
                "serie_ids": [serie.pk for serie in series],
            }
        ],
        usuario_tenant,
    )
    datos = datos_iniciales_solicitud(solicitud)
    assert len(datos) == 1
    assert len(datos[0]["filas"]) == 1
    assert datos[0]["filas"][0]["series"] == [serie.pk for serie in series]


@pytest.mark.django_db
def test_no_editar_solicitud_enviada(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
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
                "material_id": material_no_seriado.pk,
                "cantidad": 1,
            }
        ],
        usuario_tenant,
    )
    with pytest.raises(EstadoSolicitudInvalido):
        actualizar_borrador_solicitud(
            solicitud,
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


@pytest.mark.django_db
def test_editar_borrador_revalida_stock(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    stock = StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=2
    )
    solicitud = crear_borrador_solicitud(
        tenant,
        date.today(),
        [
            {
                "tecnico_id": tecnico.pk,
                "material_id": material_no_seriado.pk,
                "cantidad": 2,
            }
        ],
        usuario_tenant,
    )
    StockGeneral.objects.filter(pk=stock.pk).update(cantidad=1)

    with pytest.raises(CantidadExcedeDisponible, match="solo quedan 1"):
        actualizar_borrador_solicitud(
            solicitud,
            date.today(),
            [
                {
                    "tecnico_id": tecnico.pk,
                    "material_id": material_no_seriado.pk,
                    "cantidad": 2,
                }
            ],
            usuario_tenant,
        )
    assert solicitud.lineas.get().cantidad == 2
