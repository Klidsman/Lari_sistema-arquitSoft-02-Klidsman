"""Contrato de búsqueda en el listado de técnicos."""

import pytest
from django.urls import reverse

from tecnicos.models import Tecnico


@pytest.mark.django_db
def test_busqueda_por_nif_y_nombre(cliente_tenant, tecnico, tecnico_desactivado):
    por_nif = cliente_tenant.get(
        reverse("listar_tecnicos"), {"q": "LA1234"}
    ).content.decode()
    por_nombre = cliente_tenant.get(
        reverse("listar_tecnicos"), {"q": "Juan"}
    ).content.decode()

    assert tecnico.nif in por_nif
    assert tecnico.nombre in por_nombre
    assert tecnico_desactivado.nif not in por_nif


@pytest.mark.django_db
def test_busqueda_vacia_no_filtra(cliente_tenant, tecnico):
    respuesta = cliente_tenant.get(reverse("listar_tecnicos"), {"q": ""})

    assert tecnico.nif in respuesta.content.decode()


@pytest.mark.django_db
def test_filtro_estado(cliente_tenant, tecnico, tecnico_desactivado):
    activos = cliente_tenant.get(
        reverse("listar_tecnicos"), {"estado": "activos"}
    ).content.decode()
    desactivados = cliente_tenant.get(
        reverse("listar_tecnicos"), {"estado": "desactivados"}
    ).content.decode()

    assert tecnico.nif in activos
    assert tecnico_desactivado.nif not in activos
    assert tecnico_desactivado.nif in desactivados
    assert tecnico.nif not in desactivados


@pytest.mark.django_db
def test_orden_por_nombre_y_nif(cliente_tenant, tenant, usuario_tenant):
    Tecnico.objects.create(
        tenant=tenant, nif="LA0002", nombre="Zulema", creado_por=usuario_tenant
    )
    Tecnico.objects.create(
        tenant=tenant, nif="LA0001", nombre="Ana", creado_por=usuario_tenant
    )

    contenido = cliente_tenant.get(reverse("listar_tecnicos")).content.decode()

    assert contenido.index("Ana") < contenido.index("Zulema")


@pytest.mark.django_db
def test_paginacion_50(cliente_tenant, tenant, usuario_tenant):
    for indice in range(55):
        Tecnico.objects.create(
            tenant=tenant,
            nif=f"LA{indice:04d}",
            nombre=f"Tecnico {indice:02d}",
            creado_por=usuario_tenant,
        )

    respuesta = cliente_tenant.get(reverse("listar_tecnicos"))

    assert len(respuesta.context["pagina"]) == 50
    assert respuesta.context["pagina"].paginator.num_pages == 2


@pytest.mark.django_db
def test_aislamiento_entre_tenants(
    cliente_tenant, cliente_otro_tenant, tecnico, tecnico_otro_tenant
):
    contenido_propio = cliente_tenant.get(
        reverse("listar_tecnicos"), {"q": "LA"}
    ).content.decode()
    contenido_ajeno = cliente_otro_tenant.get(
        reverse("listar_tecnicos"), {"q": "LA"}
    ).content.decode()

    assert tecnico.nif in contenido_propio
    assert tecnico_otro_tenant.nif not in contenido_propio
    assert tecnico_otro_tenant.nif in contenido_ajeno
    assert tecnico.nif not in contenido_ajeno


@pytest.mark.django_db
def test_admin_y_almacen_403(cliente_autenticado, cliente_almacen):
    for cliente in (cliente_autenticado, cliente_almacen):
        assert cliente.get(reverse("listar_tecnicos")).status_code == 403
