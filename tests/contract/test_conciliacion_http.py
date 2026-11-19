"""Contrato HTTP de conciliaciones."""

import pytest
from django.urls import reverse

from conciliaciones.models import EstadoConciliacion
from tests.reportes import archivo_xlsx, fila_no_seriada


@pytest.mark.django_db
def test_flujo_http_y_permisos(
    cliente_tenant,
    cliente_autenticado,
    cliente_otro_tenant,
    tenant,
    tecnico,
    material_no_seriado,
    almacen,
):
    archivo = archivo_xlsx(
        [fila_no_seriada(material_no_seriado, tecnico.nif, 1)]
    )
    assert cliente_tenant.get(reverse("lista_conciliaciones")).status_code == 200
    assert (
        cliente_tenant.get(reverse("cargar_conciliacion")).status_code == 200
    )
    assert (
        cliente_autenticado.get(reverse("lista_conciliaciones")).status_code
        == 403
    )

    respuesta = cliente_tenant.post(
        reverse("cargar_conciliacion"), {"archivo": archivo}
    )
    assert respuesta.status_code == 302
    conciliacion = tenant.conciliaciones.get()
    assert conciliacion.estado == EstadoConciliacion.EN_REVISION

    detalle = reverse("detalle_conciliacion", args=[conciliacion.pk])
    assert cliente_tenant.get(detalle).status_code == 200
    assert cliente_otro_tenant.get(detalle).status_code == 404
    assert cliente_autenticado.get(detalle).status_code == 403

    # Una segunda carga mientras hay una en revisión devuelve 409.
    respuesta = cliente_tenant.post(
        reverse("cargar_conciliacion"),
        {
            "archivo": archivo_xlsx(
                [fila_no_seriada(material_no_seriado, tecnico.nif, 2)]
            )
        },
    )
    assert respuesta.status_code == 409
    assert "Ya hay una conciliación en revisión" in respuesta.content.decode()

    # Las acciones no aceptan GET.
    for nombre in (
        "aprobar_conciliacion",
        "rechazar_conciliacion",
        "recalcular_conciliacion",
    ):
        assert (
            cliente_tenant.get(reverse(nombre, args=[conciliacion.pk])).status_code
            == 405
        )

    respuesta = cliente_tenant.post(
        reverse("aprobar_conciliacion", args=[conciliacion.pk])
    )
    assert respuesta.status_code == 302
    conciliacion.refresh_from_db()
    assert conciliacion.estado == EstadoConciliacion.APROBADA


@pytest.mark.django_db
def test_archivo_invalido_devuelve_400(
    cliente_tenant, material_no_seriado, almacen
):
    from django.core.files.uploadedfile import SimpleUploadedFile

    respuesta = cliente_tenant.post(
        reverse("cargar_conciliacion"),
        {"archivo": SimpleUploadedFile("reporte.csv", b"a,b\n1,2")},
    )
    assert respuesta.status_code == 400
    assert "El archivo debe ser un Excel .xlsx válido" in respuesta.content.decode()
