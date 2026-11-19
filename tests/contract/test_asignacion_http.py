"""Contrato HTTP de asignaciones."""

from datetime import date

import pytest
from django.urls import reverse

from asignaciones.models import EstadoSolicitud, SolicitudAsignacion
from series.models import EstadoSerie


def _post(n, material, serie_ids=(), cantidad=""):
    datos = {
        "fecha": date.today().isoformat(),
        "lineas-TOTAL_FORMS": "1",
        "lineas-INITIAL_FORMS": "0",
        "lineas-MIN_NUM_FORMS": "0",
        "lineas-MAX_NUM_FORMS": "1000",
        "lineas-0-tecnico_id": n["tecnico_id"],
        "lineas-0-material_id": material.pk,
        "lineas-0-cantidad": cantidad,
        "accion": n.get("accion", "enviar"),
    }
    datos["lineas-0-serie_ids"] = list(serie_ids)
    return datos


@pytest.mark.django_db
def test_nueva_solicitud_seriada(
    cliente_tenant, tenant, tecnico, material_seriado, serie_existente, almacen, stock_general
):
    respuesta = cliente_tenant.post(
        reverse("nueva_asignacion"),
        _post(
            {"tecnico_id": tecnico.pk},
            material_seriado,
            [serie_existente.pk],
        ),
    )

    assert respuesta.status_code == 302
    solicitud = SolicitudAsignacion.objects.get()
    assert respuesta.url == reverse("detalle_asignacion", args=[solicitud.pk])
    assert solicitud.estado == EstadoSolicitud.ENVIADA
    serie_existente.refresh_from_db()
    assert serie_existente.estado == EstadoSerie.RESERVADA


@pytest.mark.django_db
def test_formulario_y_permisos(cliente_tenant, cliente_autenticado, cliente_almacen):
    assert cliente_tenant.get(reverse("nueva_asignacion")).status_code == 200
    for cliente in (cliente_autenticado, cliente_almacen):
        assert cliente.get(reverse("lista_asignaciones")).status_code == 403


@pytest.mark.django_db
def test_detalle_ajeno_404(cliente_tenant, usuario_otro_tenant):
    from tecnicos.models import Tecnico

    tecnico_ajeno = Tecnico.objects.create(
        tenant=usuario_otro_tenant.tenant,
        nif="LA8888",
        nombre="Ajeno",
        creado_por=usuario_otro_tenant,
    )
    ajena = SolicitudAsignacion.objects.create(
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        fecha=date.today(),
        creado_por=usuario_otro_tenant,
    )

    respuesta = cliente_tenant.get(
        reverse("detalle_asignacion", args=[ajena.pk])
    )
    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_cancelar_http(
    cliente_tenant, tenant, tecnico, material_seriado, serie_existente, almacen
):
    respuesta = cliente_tenant.post(
        reverse("nueva_asignacion"),
        _post(
            {"tecnico_id": tecnico.pk, "accion": "borrador"},
            material_seriado,
            [serie_existente.pk],
        ),
    )
    solicitud = SolicitudAsignacion.objects.get()
    respuesta = cliente_tenant.post(
        reverse("cancelar_asignacion", args=[solicitud.pk])
    )
    assert respuesta.status_code == 302
    solicitud.refresh_from_db()
    assert solicitud.estado == EstadoSolicitud.CANCELADA


@pytest.mark.django_db
def test_formulario_muestra_series_y_sobrante(
    cliente_tenant, tenant, tecnico, material_seriado, serie_existente, almacen
):
    respuesta = cliente_tenant.get(
        reverse("series_disponibles"),
        {"material_id": material_seriado.pk},
    )
    assert respuesta.status_code == 200
    assert b"serie-modal-check" in respuesta.content
    assert serie_existente.numero.encode() in respuesta.content
    assert b"checked" not in respuesta.content

    respuesta = cliente_tenant.get(
        reverse("series_disponibles"),
        {
            "material_id": material_seriado.pk,
            "seleccionados": str(serie_existente.pk),
        },
    )
    assert b"checked" in respuesta.content

    respuesta = cliente_tenant.get(
        reverse("series_disponibles"),
        {
            "material_id": material_seriado.pk,
            "excluir": str(serie_existente.pk),
        },
    )
    assert serie_existente.numero.encode() not in respuesta.content

    respuesta = cliente_tenant.post(
        reverse("sobrante_asignacion"),
        {
            "lineas-TOTAL_FORMS": "1",
            "lineas-0-tecnico_id": tecnico.pk,
            "lineas-0-material_id": material_seriado.pk,
            "lineas-0-serie_ids": [serie_existente.pk],
        },
    )
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "material-panel-check" in contenido
    assert material_seriado.codigo in contenido
    assert 'data-sin-sobrante="1"' in contenido


@pytest.mark.django_db
def test_varios_tecnicos_en_un_post_crean_una_solicitud(
    cliente_tenant, usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    from asignaciones.models import LineaAsignacion
    from stock.models import StockGeneral
    from tecnicos.models import Tecnico

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=20
    )
    segundo = Tecnico.objects.create(
        tenant=tenant, nif="LA4444", nombre="Otro", creado_por=usuario_tenant
    )
    respuesta = cliente_tenant.post(
        reverse("nueva_asignacion"),
        {
            "fecha": date.today().isoformat(),
            "lineas-TOTAL_FORMS": "2",
            "lineas-0-tecnico_id": tecnico.pk,
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": "5",
            "lineas-1-tecnico_id": segundo.pk,
            "lineas-1-material_id": material_no_seriado.pk,
            "lineas-1-cantidad": "7",
            "accion": "enviar",
        },
    )
    assert respuesta.status_code == 302
    solicitud = SolicitudAsignacion.objects.get()
    assert LineaAsignacion.objects.filter(solicitud=solicitud).count() == 2
    assert solicitud.nifs_tecnicos == f"{tecnico.nif}, {segundo.nif}"


@pytest.mark.django_db
def test_tenant_descarga_excel_y_detalle_muestra_boton(
    cliente_tenant, cliente_otro_tenant, tenant, tecnico, material_no_seriado, almacen
):
    from stock.models import StockGeneral

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=20
    )
    respuesta = cliente_tenant.post(
        reverse("nueva_asignacion"),
        _post({"tecnico_id": tecnico.pk}, material_no_seriado, cantidad="3"),
    )
    assert respuesta.status_code == 302
    solicitud = SolicitudAsignacion.objects.get()
    detalle = cliente_tenant.get(reverse("detalle_asignacion", args=[solicitud.pk]))
    assert reverse("excel_asignacion", args=[solicitud.pk]).encode() in detalle.content

    descarga = cliente_tenant.get(reverse("excel_asignacion", args=[solicitud.pk]))
    assert descarga.status_code == 200
    assert descarga["Content-Disposition"].endswith(f'asignacion-{solicitud.pk}.xlsx"')
    assert b"".join(descarga.streaming_content)[:2] == b"PK"

    assert cliente_otro_tenant.get(
        reverse("excel_asignacion", args=[solicitud.pk])
    ).status_code == 404


@pytest.mark.django_db
def test_sobrante_ignora_filas_incompletas(
    cliente_tenant, tenant, tecnico, material_no_seriado, almacen
):
    from stock.models import StockGeneral

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=20
    )
    respuesta = cliente_tenant.post(
        reverse("sobrante_asignacion"),
        {
            "lineas-TOTAL_FORMS": "3",
            "lineas-0-tecnico_id": tecnico.pk,
            "lineas-0-material_id": "",
            "lineas-0-cantidad": "",
            "lineas-1-tecnico_id": tecnico.pk,
            "lineas-1-material_id": material_no_seriado.pk,
            "lineas-1-cantidad": "5",
            "lineas-2-material_id": "",
        },
    )
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert material_no_seriado.codigo in contenido
    assert contenido.count("material-panel-check") == 1
    assert "Sobrante: 15" in contenido


@pytest.mark.django_db
def test_series_sin_material_responde_400(cliente_tenant, almacen):
    respuesta = cliente_tenant.get(
        reverse("series_disponibles"), {"material_id": ""}
    )
    assert respuesta.status_code == 400


@pytest.mark.django_db
def test_formulario_solo_muestra_materiales_con_existencias(
    cliente_tenant,
    tenant,
    material_seriado,
    material_no_seriado,
    almacen,
):
    from stock.models import StockGeneral

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=5
    )
    respuesta = cliente_tenant.get(reverse("nueva_asignacion"))
    contenido = respuesta.content.decode()
    assert material_no_seriado.codigo in contenido
    assert "(disponible: 5)" in contenido
    assert 'id="lista-materiales-panel"' in contenido
    assert "Sobrante: 5" in contenido
    assert material_seriado.codigo not in contenido
    assert "No hay materiales disponibles" not in contenido


@pytest.mark.django_db
def test_formulario_tiene_bloques_y_ventana_de_series(
    cliente_tenant, almacen
):
    respuesta = cliente_tenant.get(reverse("nueva_asignacion"))
    contenido = respuesta.content.decode()
    assert 'id="panel-materiales"' in contenido
    assert 'id="lista-materiales-panel"' in contenido
    assert 'id="agregar-seleccionados"' in contenido
    assert 'id="agregar-bloque"' in contenido
    assert 'id="dialogo-series"' in contenido
    assert 'id="plantilla-bloque"' in contenido
    assert 'id="plantilla-fila"' in contenido


@pytest.mark.django_db
def test_material_repetido_para_mismo_tecnico_devuelve_400(
    cliente_tenant, tenant, tecnico, material_no_seriado, almacen
):
    from stock.models import StockGeneral

    StockGeneral.objects.create(
        tenant=tenant, material=material_no_seriado, cantidad=10
    )
    respuesta = cliente_tenant.post(
        reverse("nueva_asignacion"),
        {
            "fecha": date.today().isoformat(),
            "lineas-TOTAL_FORMS": "2",
            "lineas-0-tecnico_id": tecnico.pk,
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": "3",
            "lineas-1-tecnico_id": tecnico.pk,
            "lineas-1-material_id": material_no_seriado.pk,
            "lineas-1-cantidad": "4",
            "accion": "enviar",
        },
    )
    assert respuesta.status_code == 400
    assert "ya fue agregado para este técnico" in respuesta.content.decode()
    assert not SolicitudAsignacion.objects.exists()
