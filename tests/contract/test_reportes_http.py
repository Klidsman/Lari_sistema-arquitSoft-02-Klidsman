"""Contrato HTTP de reportes mensuales."""

import pytest
from django.urls import reverse

from reportes.models import CorteMensual

MES = 11
ANIO = 2026


@pytest.mark.django_db
def test_flujo_http_tenant(
    cliente_tenant,
    cliente_otro_tenant,
    usuario_tenant,
    tenant,
    almacen,
):
    assert cliente_tenant.get(reverse("lista_cortes")).status_code == 200
    assert cliente_tenant.get(reverse("generar_corte")).status_code == 200

    respuesta = cliente_tenant.post(
        reverse("generar_corte"), {"mes": MES, "anio": ANIO}
    )
    assert respuesta.status_code == 302
    corte = CorteMensual.objects.get(tenant=tenant)
    detalle = reverse("detalle_corte", args=[corte.pk])
    assert cliente_tenant.get(detalle).status_code == 200
    assert cliente_otro_tenant.get(detalle).status_code == 404

    # Duplicado
    respuesta = cliente_tenant.post(
        reverse("generar_corte"), {"mes": MES, "anio": ANIO}
    )
    assert respuesta.status_code == 409
    assert "Ya existe un corte" in respuesta.content.decode()

    # Mes inválido
    respuesta = cliente_tenant.post(
        reverse("generar_corte"), {"mes": 13, "anio": ANIO}
    )
    assert respuesta.status_code == 400
    assert "El mes debe estar entre 1 y 12" in respuesta.content.decode()

    # Regenerar no acepta GET
    assert (
        cliente_tenant.get(
            reverse("regenerar_corte", args=[corte.pk])
        ).status_code
        == 405
    )
    respuesta = cliente_tenant.post(
        reverse("regenerar_corte", args=[corte.pk])
    )
    assert respuesta.status_code == 302
    corte.refresh_from_db()
    assert corte.version == 2

    for nombre in ("exportar_auditoria", "exportar_conciliacion"):
        respuesta = cliente_tenant.get(reverse(nombre, args=[corte.pk]))
        assert respuesta.status_code == 200
        assert respuesta["Content-Type"].startswith(
            "application/vnd.openxmlformats"
        )
        assert respuesta.content[:2] == b"PK"

    # Un tenant no puede generar el corte global.
    respuesta = cliente_tenant.post(
        reverse("generar_corte"),
        {"mes": 12, "anio": ANIO, "tenant": ""},
    )
    assert respuesta.status_code == 302
    assert not CorteMensual.objects.filter(
        tenant__isnull=True, mes=12
    ).exists()


@pytest.mark.django_db
def test_admin_genera_global_y_ve_todo(
    cliente_autenticado, usuario_admin, usuario_tenant, tenant, almacen
):
    assert cliente_autenticado.get(reverse("lista_cortes")).status_code == 200
    respuesta = cliente_autenticado.post(
        reverse("generar_corte"), {"mes": MES, "anio": ANIO, "tenant": ""}
    )
    assert respuesta.status_code == 302
    global_corte = CorteMensual.objects.get(tenant__isnull=True)
    assert (
        cliente_autenticado.get(
            reverse("detalle_corte", args=[global_corte.pk])
        ).status_code
        == 200
    )

    from reportes.services import generar_corte

    tenant_corte = generar_corte(tenant, MES, ANIO, usuario_tenant)
    assert (
        cliente_autenticado.get(
            reverse("detalle_corte", args=[tenant_corte.pk])
        ).status_code
        == 200
    )
