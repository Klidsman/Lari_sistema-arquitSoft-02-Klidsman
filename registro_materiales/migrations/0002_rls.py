"""Políticas RLS para registro de materiales."""

from django.db import migrations

TABLAS = [
    ("registro_materiales_materialhabilitado", "material_habilitado_por_tenant"),
    ("registro_materiales_saldoinicialperiodo", "saldo_inicial_por_tenant"),
    ("registro_materiales_despachoalmacen", "despacho_almacen_por_tenant"),
    ("registro_materiales_cargaordenes", "carga_ordenes_por_tenant"),
    ("registro_materiales_ordenliquidacion", "orden_liquidacion_por_tenant"),
    ("registro_materiales_usomaterialorden", "uso_material_orden_por_tenant"),
    ("registro_materiales_advertenciauso", "advertencia_uso_por_tenant"),
    ("registro_materiales_cierremensual", "cierre_mensual_por_tenant"),
    ("registro_materiales_saldomensualmaterial", "saldo_mensual_por_tenant"),
    ("registro_materiales_justificacioncierre", "justificacion_cierre_por_tenant"),
]

APLICAR = []
REVERTIR = []
for tabla, politica in TABLAS:
    APLICAR.extend(
        [
            f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY",
            f"DROP POLICY IF EXISTS {politica} ON {tabla}",
            f"""
            CREATE POLICY {politica} ON {tabla}
            USING (
                current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
                OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
            )
            """,
        ]
    )
    REVERTIR.extend(
        [
            f"DROP POLICY IF EXISTS {politica} ON {tabla}",
            f"ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY",
        ]
    )
REVERTIR.reverse()


def aplicar(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for sentencia in APLICAR:
            cursor.execute(sentencia)


def revertir(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for sentencia in REVERTIR:
            cursor.execute(sentencia)


class Migration(migrations.Migration):
    dependencies = [
        ("registro_materiales", "0001_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
