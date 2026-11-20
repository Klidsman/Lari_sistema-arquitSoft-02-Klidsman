"""Reactivación y re-registro de series de un recojo anulado."""

from datetime import date

import pytest

from auditoria.models import RegistroCambio
from recojos.models import EstadoRecojo, LineaRecojo, Recojo
from recojos.services import RecojoInvalido, anular_recojo, crear_recojo
from series.models import EstadoSerie, Serie
from stock.models import StockGeneral

NUMERO = "ABC123456789"


def _recojo(usuario, material, nombre="Recojo"):
    return crear_recojo(
        {
            "nombre": nombre,
            "fecha": date.today(),
            "lineas": [
                {"material_id": material.pk, "series": NUMERO}
            ],
        },
        usuario,
    )


@pytest.mark.django_db
def test_anular_reactiva_la_serie(
    usuario_tenant, tenant, material_seriado, almacen
):
    recojo = _recojo(usuario_tenant, material_seriado)

    anular_recojo(recojo, "Error de carga", usuario_tenant)

    serie = Serie.objects.get(numero=NUMERO)
    assert serie.estado == EstadoSerie.DISPONIBLE
    assert serie.tecnico_id is None
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 0
    )
    assert RegistroCambio.objects.filter(
        entidad="Serie",
        entidad_id=serie.pk,
        campo="reactivada",
    ).exists()


@pytest.mark.django_db
def test_re_registrar_serie_anulada_conserva_historia(
    usuario_tenant, tenant, material_seriado, almacen
):
    recojo_anulado = _recojo(usuario_tenant, material_seriado, "Primero")
    serie = Serie.objects.get(numero=NUMERO)
    serie_pk = serie.pk
    anular_recojo(recojo_anulado, "Error de carga", usuario_tenant)

    recojo_nuevo = _recojo(usuario_tenant, material_seriado, "Segundo")

    assert Serie.objects.filter(numero=NUMERO).count() == 1
    assert Serie.objects.get(numero=NUMERO).pk == serie_pk
    lineas = LineaRecojo.objects.filter(serie_id=serie_pk).select_related(
        "recojo"
    ).order_by("recojo_id")
    assert lineas.count() == 2
    assert lineas[0].recojo_id == recojo_anulado.pk
    assert lineas[0].recojo.estado == EstadoRecojo.ANULADO
    assert lineas[1].recojo_id == recojo_nuevo.pk
    assert lineas[1].recojo.estado == EstadoRecojo.REGISTRADO
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 1
    )
    assert Serie.objects.get(pk=serie_pk).estado == EstadoSerie.DISPONIBLE


@pytest.mark.django_db
def test_serie_de_recojo_activo_no_se_reutiliza(
    usuario_tenant, tenant, material_seriado, almacen
):
    _recojo(usuario_tenant, material_seriado, "Activo")

    with pytest.raises(RecojoInvalido, match="ya está registrada"):
        _recojo(usuario_tenant, material_seriado, "Duplicado")

    assert Serie.objects.filter(numero=NUMERO).count() == 1
    assert LineaRecojo.objects.count() == 1
    assert Recojo.objects.count() == 1


@pytest.mark.django_db
def test_serie_inactiva_de_recojo_anulado_se_reactiva(
    usuario_tenant, tenant, material_seriado, almacen
):
    recojo = _recojo(usuario_tenant, material_seriado)
    anular_recojo(recojo, "Error", usuario_tenant)
    serie = Serie.objects.get(numero=NUMERO)
    Serie.objects.filter(pk=serie.pk).update(estado=EstadoSerie.INACTIVA)

    _recojo(usuario_tenant, material_seriado, "Segundo")

    serie.refresh_from_db()
    assert serie.estado == EstadoSerie.DISPONIBLE
    assert RegistroCambio.objects.filter(
        entidad="Serie",
        entidad_id=serie.pk,
        campo="estado",
        valor_anterior=str(EstadoSerie.INACTIVA),
        valor_nuevo=str(EstadoSerie.DISPONIBLE),
    ).exists()


@pytest.mark.django_db
def test_se_puede_anular_y_re_registrar_varias_veces(
    usuario_tenant, tenant, material_seriado, almacen
):
    primero = _recojo(usuario_tenant, material_seriado, "Primero")
    anular_recojo(primero, "Error", usuario_tenant)

    segundo = _recojo(usuario_tenant, material_seriado, "Segundo")
    anular_recojo(segundo, "Otro error", usuario_tenant)

    tercero = _recojo(usuario_tenant, material_seriado, "Tercero")

    serie = Serie.objects.get(numero=NUMERO)
    assert LineaRecojo.objects.filter(serie=serie).count() == 3
    assert LineaRecojo.objects.filter(
        serie=serie, recojo=tercero
    ).exists()
    assert (
        StockGeneral.objects.get(
            tenant=tenant, material=material_seriado
        ).cantidad
        == 1
    )
