"""Contrato del alta de recojos."""

from datetime import date

import pytest
from django.urls import reverse

from recojos.models import LineaRecojo, Recojo
from series.models import Serie


def _post_data(**cambios):
    datos = {
        "nombre": "Recojo de prueba",
        "fecha": date.today().isoformat(),
        "lineas-TOTAL_FORMS": "1",
        "lineas-INITIAL_FORMS": "0",
        "lineas-MIN_NUM_FORMS": "0",
        "lineas-MAX_NUM_FORMS": "1000",
        "lineas-0-material_id": "",
        "lineas-0-series": "",
        "lineas-0-cantidad": "",
    }
    datos.update(cambios)
    return datos


@pytest.mark.django_db
def test_alta_seriada(cliente_tenant, material_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(
            **{
                "lineas-0-material_id": material_seriado.pk,
                "lineas-0-series": "abc123456789\nDEF123456789",
            }
        ),
    )

    assert respuesta.status_code == 302
    recojo = Recojo.objects.get()
    assert respuesta.url == reverse("detalle_recojo", args=[recojo.pk])
    assert recojo.lineas.count() == 2
    assert Serie.objects.count() == 2


@pytest.mark.django_db
def test_formulario_tiene_busqueda_y_edicion_de_lineas(cliente_tenant, almacen):
    respuesta = cliente_tenant.get(reverse("crear_recojo"))
    contenido = respuesta.content.decode()

    assert respuesta.status_code == 200
    assert 'name="lineas-0-material_id"' in contenido
    assert 'id="series-lateral"' in contenido
    assert "Quitar línea" in contenido


@pytest.mark.django_db
def test_alta_con_material_codigo(cliente_tenant, material_seriado, almacen):
    datos = _post_data(
        **{
            "lineas-0-material_codigo": material_seriado.codigo,
            "lineas-0-series": "ABC123456789",
        }
    )
    datos.pop("lineas-0-material_id")

    respuesta = cliente_tenant.post(reverse("crear_recojo"), datos)

    assert respuesta.status_code == 302
    assert Recojo.objects.get().lineas.count() == 1


@pytest.mark.django_db
def test_alta_no_seriada(cliente_tenant, material_no_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(
            **{
                "lineas-0-material_id": material_no_seriado.pk,
                "lineas-0-cantidad": "25",
            }
        ),
    )

    assert respuesta.status_code == 302
    linea = LineaRecojo.objects.get()
    assert linea.serie is None
    assert linea.cantidad == 25


@pytest.mark.django_db
def test_nombre_obligatorio(cliente_tenant, material_no_seriado, almacen):
    datos = _post_data(
        **{
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": "1",
        }
    )
    datos["nombre"] = ""

    respuesta = cliente_tenant.post(reverse("crear_recojo"), datos)

    assert respuesta.status_code == 400
    assert "El nombre es obligatorio" in respuesta.content.decode()


@pytest.mark.django_db
def test_nombre_se_guarda(cliente_tenant, material_no_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(
            nombre="Recojo de laptops",
            **{
                "lineas-0-material_id": material_no_seriado.pk,
                "lineas-0-cantidad": "2",
            },
        ),
    )

    assert respuesta.status_code == 302
    assert Recojo.objects.get().nombre == "Recojo de laptops"


@pytest.mark.django_db
def test_fecha_obligatoria(cliente_tenant, material_no_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(fecha="", **{"lineas-0-material_id": material_no_seriado.pk}),
    )

    assert respuesta.status_code == 400
    assert "La fecha es obligatoria" in respuesta.content.decode()


@pytest.mark.django_db
def test_sin_lineas(cliente_tenant, almacen):
    respuesta = cliente_tenant.post(reverse("crear_recojo"), _post_data())

    assert respuesta.status_code == 400
    assert "El recojo debe tener al menos una línea" in respuesta.content.decode()


@pytest.mark.django_db
def test_material_inexistente(cliente_tenant, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(**{"lineas-0-material_id": 9999, "lineas-0-cantidad": "1"}),
    )

    assert respuesta.status_code == 400
    assert "El material no existe en el catálogo" in respuesta.content.decode()


@pytest.mark.django_db
def test_seriado_sin_series(cliente_tenant, material_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(**{"lineas-0-material_id": material_seriado.pk}),
    )

    assert respuesta.status_code == 400
    assert "Debe indicar al menos una serie" in respuesta.content.decode()


@pytest.mark.django_db
def test_no_seriado_cantidad_cero(cliente_tenant, material_no_seriado, almacen):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(
            **{
                "lineas-0-material_id": material_no_seriado.pk,
                "lineas-0-cantidad": "0",
            }
        ),
    )

    assert respuesta.status_code == 400
    assert "La cantidad debe ser mayor a 0" in respuesta.content.decode()


@pytest.mark.django_db
def test_tenant_y_region_forzados_se_ignoran(
    cliente_tenant, tenant, material_no_seriado, almacen, usuario_otro_tenant
):
    respuesta = cliente_tenant.post(
        reverse("crear_recojo"),
        _post_data(
            tenant_id=usuario_otro_tenant.tenant_id,
            region_id=usuario_otro_tenant.tenant.region_id,
            **{
                "lineas-0-material_id": material_no_seriado.pk,
                "lineas-0-cantidad": "3",
            },
        ),
    )

    assert respuesta.status_code == 302
    recojo = Recojo.objects.get()
    assert recojo.tenant_id == tenant.pk
    assert recojo.region_id == tenant.region_id


@pytest.mark.django_db
def test_admin_y_almacen_no_crean(cliente_autenticado, cliente_almacen, material_no_seriado, almacen):
    datos = _post_data(
        **{
            "lineas-0-material_id": material_no_seriado.pk,
            "lineas-0-cantidad": "1",
        }
    )
    for cliente in (cliente_autenticado, cliente_almacen):
        respuesta = cliente.post(reverse("crear_recojo"), datos)
        assert respuesta.status_code == 403
        assert "No tienes permiso para registrar recojos" in respuesta.content.decode()


@pytest.mark.django_db
def test_metodos_no_permitidos(cliente_tenant, almacen):
    for metodo in ("put", "patch", "delete"):
        respuesta = getattr(cliente_tenant, metodo)(reverse("crear_recojo"))
        assert respuesta.status_code == 405
