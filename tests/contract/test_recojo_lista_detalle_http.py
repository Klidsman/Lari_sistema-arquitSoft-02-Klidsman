"""Contrato del listado y detalle de recojos."""

from datetime import date

import pytest
from django.urls import reverse

from recojos.models import Recojo


@pytest.mark.django_db
def test_listado(cliente_tenant, recojo):
    respuesta = cliente_tenant.get(reverse("lista_recojos"))

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert recojo.fecha.isoformat() in contenido
    assert str(recojo.pk) in contenido
    assert recojo.nombre in contenido


@pytest.mark.django_db
def test_busqueda_por_nombre(cliente_tenant, recojo, tenant, usuario_tenant):
    Recojo.objects.create(
        tenant=tenant,
        region=tenant.region,
        nombre="Recojo de cables",
        fecha=date.today(),
        creado_por=usuario_tenant,
    )

    respuesta = cliente_tenant.get(reverse("lista_recojos"), {"q": "cables"})
    contenido = respuesta.content.decode()

    assert "Recojo de cables" in contenido
    assert recojo.nombre not in contenido


@pytest.mark.django_db
def test_listado_paginado(cliente_tenant, tenant, usuario_tenant):
    for indice in range(55):
        Recojo.objects.create(
            tenant=tenant,
            region=tenant.region,
            fecha=date.today(),
            creado_por=usuario_tenant,
        )

    respuesta = cliente_tenant.get(reverse("lista_recojos"))

    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2


@pytest.mark.django_db
def test_detalle(cliente_tenant, recojo):
    respuesta = cliente_tenant.get(
        reverse("detalle_recojo", args=[recojo.pk])
    )

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert recojo.nombre in contenido
    assert recojo.tenant.codigo in contenido
    assert recojo.region.codigo in contenido


@pytest.mark.django_db
def test_recojo_de_otro_tenant_404(cliente_tenant, usuario_otro_tenant):
    ajeno = Recojo.objects.create(
        tenant=usuario_otro_tenant.tenant,
        region=usuario_otro_tenant.tenant.region,
        fecha=date.today(),
        creado_por=usuario_otro_tenant,
    )

    respuesta = cliente_tenant.get(
        reverse("detalle_recojo", args=[ajeno.pk])
    )

    assert respuesta.status_code == 404
    assert "El recojo no existe" in respuesta.content.decode()


@pytest.mark.django_db
def test_admin_y_almacen_no_acceden(cliente_autenticado, cliente_almacen):
    for cliente in (cliente_autenticado, cliente_almacen):
        assert cliente.get(reverse("lista_recojos")).status_code == 403


@pytest.mark.django_db
def test_metodos_no_permitidos(cliente_tenant, recojo):
    assert cliente_tenant.delete(reverse("lista_recojos")).status_code == 405
    assert (
        cliente_tenant.delete(reverse("detalle_recojo", args=[recojo.pk])).status_code
        == 405
    )
