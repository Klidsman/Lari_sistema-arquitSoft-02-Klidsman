"""Permisos y aislamiento de las rutas de recojos."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_admin_y_almacen_403_en_todas_las_rutas(
    cliente_autenticado, cliente_almacen, recojo
):
    rutas_get = [
        reverse("lista_recojos"),
        reverse("crear_recojo"),
        reverse("detalle_recojo", args=[recojo.pk]),
    ]

    for cliente in (cliente_autenticado, cliente_almacen):
        for ruta in rutas_get:
            respuesta = cliente.get(ruta)
            assert respuesta.status_code == 403
            assert "No tienes permiso para registrar recojos" in respuesta.content.decode()
        assert cliente.post(reverse("validar_series")).status_code == 403


@pytest.mark.django_db
def test_recojo_ajeno_404(cliente_tenant, recojo, usuario_otro_tenant):
    from datetime import date

    from recojos.models import Recojo

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
