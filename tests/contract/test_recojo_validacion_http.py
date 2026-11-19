"""Contrato de validación de series en el alta."""

from datetime import date

import pytest
from django.urls import reverse

from recojos.models import Recojo
from series.models import Serie


def _datos(material, series):
    return {
        "nombre": "Recojo de prueba",
        "fecha": date.today().isoformat(),
        "lineas-TOTAL_FORMS": "1",
        "lineas-INITIAL_FORMS": "0",
        "lineas-MIN_NUM_FORMS": "0",
        "lineas-MAX_NUM_FORMS": "1000",
        "lineas-0-material_id": material.pk,
        "lineas-0-series": series,
        "lineas-0-cantidad": "",
    }


@pytest.mark.django_db
def test_serie_invalida(cliente_tenant, material_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _datos(material_seriado, "ABC123"),
    )

    assert respuesta.status_code == 400
    assert "La serie debe tener 12 caracteres alfanuméricos" in respuesta.content.decode()
    assert not Recojo.objects.exists()


@pytest.mark.django_db
def test_serie_duplicada(cliente_tenant, material_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _datos(material_seriado, "ABC123456789\nABC123456789"),
    )

    assert respuesta.status_code == 400
    assert "La serie está duplicada en el recojo" in respuesta.content.decode()
    assert not Serie.objects.exists()


@pytest.mark.django_db
def test_serie_existente_propia_y_ajena(
    cliente_tenant, material_seriado, serie_existente, almacen
):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _datos(material_seriado, serie_existente.numero),
    )
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 400
    assert "La serie ya está registrada en el sistema" in contenido
    assert 'data-estado="ya_existe"' in contenido
    assert serie_existente.tenant.codigo not in contenido


@pytest.mark.django_db
def test_series_en_una_fila_separadas_por_guiones(
    cliente_tenant, material_seriado, almacen
):
    texto = (
        "7493DA33A8E0 - 2C9682081050 - 7493DA526E40 -\n"
        "7493DA527310 - 2CEADC372510 - 2C96820D47A8-\n"
        "2C96820506D8 - CCEDDC71E958- 2C968256F088-\n"
        "CCD4A1378650 - CCEDDCC25C60"
    )

    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _datos(material_seriado, texto),
    )

    assert respuesta.status_code == 302
    assert Serie.objects.count() == 11


@pytest.mark.django_db
def test_serie_minusculas_se_normaliza(cliente_tenant, material_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _datos(material_seriado, "abc123456789"),
    )

    assert respuesta.status_code == 302
    assert Serie.objects.get().numero == "ABC123456789"


@pytest.mark.django_db
def test_no_se_escribe_nada_al_fallar(cliente_tenant, material_seriado, almacen):
    cliente_tenant.post(
        reverse("crear_recojo"),
        _datos(material_seriado, "ABC123456789\nABC123"),
    )

    assert not Recojo.objects.exists()
    assert not Serie.objects.exists()
