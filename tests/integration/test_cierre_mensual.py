"""Cierre mensual: checklist, backup, congelamiento y reapertura."""

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from registro_materiales.models import (
    AdvertenciaUso,
    CierreMensual,
    JustificacionCierre,
    MaterialHabilitado,
    SaldoInicialPeriodo,
    SaldoMensualMaterial,
)
from registro_materiales.services import (
    BackupRequerido,
    CierreBloqueado,
    PeriodoCerrado,
    cerrar_mes,
    guardar_uso,
    justificar_pendiente,
    lista_chequeo,
    obtener_o_crear_orden,
    registrar_saldo_inicial,
    reabrir_mes,
)

PERIODO = "2026-11"


def _historial(tenant, material, usado=10):
    for periodo in ("2026-08", "2026-09", "2026-10"):
        cierre = CierreMensual.objects.create(
            tenant=tenant, periodo=periodo, estado=CierreMensual.CERRADO
        )
        SaldoMensualMaterial.objects.create(
            cierre=cierre,
            tenant=tenant,
            material=material,
            saldo_inicial=100,
            despachos=0,
            usado=usado,
            saldo_final=90,
        )


def _preparar(usuario_tenant, tenant, tecnico, material, saldo=100, uso=10):
    MaterialHabilitado.objects.create(
        tenant=tenant, material=material, creado_por=usuario_tenant
    )
    registrar_saldo_inicial(
        tenant, material, PERIODO, saldo, usuario_tenant
    )
    orden = obtener_o_crear_orden(
        tenant, tecnico, PERIODO, "A1", usuario_tenant
    )
    if uso:
        guardar_uso(
            orden, date(2026, 11, 10), {material.pk: uso}, usuario_tenant
        )
    return orden


@pytest.mark.django_db
def test_backup_obligatorio_y_con_formato(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _preparar(usuario_tenant, tenant, tecnico, material_no_seriado)
    for referencia in ("", "   ", "foo.sql", "backups/"):
        with pytest.raises(BackupRequerido):
            cerrar_mes(tenant, PERIODO, referencia, usuario_tenant)
    assert not CierreMensual.objects.filter(
        tenant=tenant, periodo=PERIODO, estado=CierreMensual.CERRADO
    ).exists()


@pytest.mark.django_db
def test_advertencia_sin_resolver_bloquea_y_justificar_libera(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _historial(tenant, material_no_seriado)
    _preparar(
        usuario_tenant,
        tenant,
        tecnico,
        material_no_seriado,
        saldo=100,
        uso=31,
    )
    advertencia = AdvertenciaUso.objects.get()
    pendientes = lista_chequeo(tenant, PERIODO)
    assert any(
        p["tipo"] == JustificacionCierre.ADVERTENCIA
        and p["referencia"] == str(advertencia.pk)
        for p in pendientes
    )
    with pytest.raises(CierreBloqueado):
        cerrar_mes(tenant, PERIODO, "backups/lari.sql", usuario_tenant)

    cierre = CierreMensual.objects.get(tenant=tenant, periodo=PERIODO)
    justificar_pendiente(
        cierre,
        JustificacionCierre.ADVERTENCIA,
        advertencia.pk,
        "Consumo autorizado",
        usuario_tenant,
    )
    advertencia.refresh_from_db()
    assert advertencia.resuelta is True

    cierre = cerrar_mes(tenant, PERIODO, "backups/lari.sql", usuario_tenant)
    assert cierre.estado == CierreMensual.CERRADO
    assert cierre.backup_ref == "backups/lari.sql"


@pytest.mark.django_db
def test_saldo_negativo_bloquea_y_justificar_libera(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _preparar(
        usuario_tenant,
        tenant,
        tecnico,
        material_no_seriado,
        saldo=10,
        uso=10,
    )
    SaldoInicialPeriodo.objects.filter(
        tenant=tenant, material=material_no_seriado, periodo=PERIODO
    ).update(cantidad=0)
    pendientes = lista_chequeo(tenant, PERIODO)
    assert any(
        p["tipo"] == JustificacionCierre.SALDO_NEGATIVO
        and p["referencia"] == material_no_seriado.codigo
        for p in pendientes
    )
    cierre = CierreMensual.objects.get(tenant=tenant, periodo=PERIODO)
    justificar_pendiente(
        cierre,
        JustificacionCierre.SALDO_NEGATIVO,
        material_no_seriado.codigo,
        "Ajuste pendiente",
        usuario_tenant,
    )
    cierre = cerrar_mes(tenant, PERIODO, "backups/lari.sql", usuario_tenant)
    assert cierre.estado == CierreMensual.CERRADO


@pytest.mark.django_db
def test_mes_cerrado_bloquea_usos_y_saldos(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    orden = _preparar(
        usuario_tenant, tenant, tecnico, material_no_seriado
    )
    cerrar_mes(tenant, PERIODO, "backups/lari.sql", usuario_tenant)

    with pytest.raises(PeriodoCerrado):
        guardar_uso(
            orden,
            date(2026, 11, 12),
            {material_no_seriado.pk: 1},
            usuario_tenant,
        )
    with pytest.raises(PeriodoCerrado):
        registrar_saldo_inicial(
            tenant, material_no_seriado, PERIODO, 5, usuario_tenant
        )


@pytest.mark.django_db
def test_reapertura_auditada_y_nuevo_cierre(
    usuario_tenant, tenant, tecnico, material_no_seriado, almacen
):
    _preparar(usuario_tenant, tenant, tecnico, material_no_seriado)
    cierre = cerrar_mes(tenant, PERIODO, "backups/lari.sql", usuario_tenant)
    reabierto = reabrir_mes(cierre, "Corrección de saldo", usuario_tenant)
    assert reabierto.estado == CierreMensual.ABIERTO
    assert reabierto.version == 2
    assert reabierto.motivo_reapertura == "Corrección de saldo"

    registrar_saldo_inicial(
        tenant, material_no_seriado, PERIODO, 120, usuario_tenant
    )
    assert saldo_inicial_efectivo(
        tenant, material_no_seriado, PERIODO
    ) == 120
    segundo = cerrar_mes(
        tenant, PERIODO, "backups/lari2.sql", usuario_tenant
    )
    assert segundo.estado == CierreMensual.CERRADO


def saldo_inicial_efectivo(tenant, material, periodo):
    from registro_materiales.services import (
        saldo_inicial_efectivo as _saldo,
    )

    return _saldo(tenant, material, periodo)


@pytest.mark.django_db
def test_comando_respaldar_bd_dry_run():
    salida = StringIO()
    call_command("respaldar_bd", "--dry-run", stdout=salida)
    referencia = salida.getvalue().strip()
    assert referencia.startswith("backups/")
    assert referencia.endswith(".sql")
