"""Contrato de la vista previa de series."""

import pytest
from django.urls import reverse

from recojos.models import Recojo
from series.models import Serie


@pytest.mark.django_db
def test_estados_de_la_vista_previa(
    cliente_tenant, material_seriado, serie_existente
):
    respuesta = cliente_tenant.post(
        reverse("validar_series"),
        {
            "material_id": material_seriado.pk,
            "series": "abc123456789\nABC123\nNUEVA1234567\nNUEVA1234567",
        },
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert 'data-serie="ABC123456789" data-estado="ya_existe"' in contenido
    assert 'data-serie="ABC123" data-estado="invalida"' in contenido
    assert 'data-serie="NUEVA1234567" data-estado="duplicada"' in contenido


@pytest.mark.django_db
def test_series_en_una_fila_separadas_por_guiones(
    cliente_tenant, material_seriado
):
    texto = (
        "7493DA33A8E0 - 2C9682081050 - 7493DA526E40 -\n"
        "7493DA527310 - 2CEADC372510 - 2C96820D47A8-\n"
        "2C96820506D8 - CCEDDC71E958- 2C968256F088-\n"
        "CCD4A1378650 - CCEDDCC25C60"
    )

    respuesta = cliente_tenant.post(
        reverse("validar_series"),
        {"material_id": material_seriado.pk, "series": texto},
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert contenido.count('data-estado="valida"') == 11
    assert 'data-serie="7493DA33A8E0"' in contenido
    assert 'data-serie="CCEDDCC25C60"' in contenido


@pytest.mark.django_db
def test_serie_valida(cliente_tenant, material_seriado):
    respuesta = cliente_tenant.post(
        reverse("validar_series"),
        {"material_id": material_seriado.pk, "series": " nueva1234567 "},
    )

    assert (
        'data-serie="NUEVA1234567" data-estado="valida"'
        in respuesta.content.decode()
    )


@pytest.mark.django_db
def test_vista_previa_con_codigo_de_material(cliente_tenant, material_seriado):
    respuesta = cliente_tenant.post(
        reverse("validar_series"),
        {
            "material_codigo": material_seriado.codigo,
            "series": "ABC123456789",
        },
    )

    assert respuesta.status_code == 200
    assert 'data-estado="valida"' in respuesta.content.decode()


@pytest.mark.django_db
def test_sin_series(cliente_tenant, material_seriado):
    respuesta = cliente_tenant.post(
        reverse("validar_series"),
        {"material_id": material_seriado.pk, "series": "\n  \n"},
    )

    assert "No se ingresaron series" in respuesta.content.decode()


@pytest.mark.django_db
def test_material_inexistente(cliente_tenant):
    respuesta = cliente_tenant.post(
        reverse("validar_series"),
        {"material_id": 9999, "series": "ABC123456789"},
    )

    assert respuesta.status_code == 404
    assert "El material no existe en el catálogo" in respuesta.content.decode()


@pytest.mark.django_db
def test_material_no_seriado(cliente_tenant, material_no_seriado):
    respuesta = cliente_tenant.post(
        reverse("validar_series"),
        {"material_id": material_no_seriado.pk, "series": "ABC123456789"},
    )

    assert respuesta.status_code == 400
    assert "El material no es seriado" in respuesta.content.decode()


@pytest.mark.django_db
def test_no_escribe_y_roles(cliente_tenant, cliente_autenticado, material_seriado):
    antes = (Recojo.objects.count(), Serie.objects.count())

    cliente_tenant.post(
        reverse("validar_series"),
        {"material_id": material_seriado.pk, "series": "NUEVA1234567"},
    )
    assert (Recojo.objects.count(), Serie.objects.count()) == antes

    assert cliente_autenticado.post(reverse("validar_series")).status_code == 403
    assert cliente_tenant.get(reverse("validar_series")).status_code == 405
    assert cliente_tenant.delete(reverse("validar_series")).status_code == 405


@pytest.mark.django_db
def test_sin_datos_sensibles(cliente_tenant, material_seriado, serie_existente):
    contenido = cliente_tenant.post(
        reverse("validar_series"),
        {"material_id": material_seriado.pk, "series": serie_existente.numero},
    ).content.decode()

    assert "tenant_id" not in contenido
    assert "region_id" not in contenido
    assert "stock" not in contenido
    assert serie_existente.tenant.codigo not in contenido
