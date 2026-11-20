"""Políticas RLS para asignaciones."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE asignaciones_solicitudasignacion ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS solicitud_asignacion_por_tenant ON asignaciones_solicitudasignacion",
    """
    CREATE POLICY solicitud_asignacion_por_tenant ON asignaciones_solicitudasignacion
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE asignaciones_lineaasignacion ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS linea_asignacion_por_tenant ON asignaciones_lineaasignacion",
    """
    CREATE POLICY linea_asignacion_por_tenant ON asignaciones_lineaasignacion
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS linea_asignacion_por_tenant ON asignaciones_lineaasignacion",
    "ALTER TABLE asignaciones_lineaasignacion DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS solicitud_asignacion_por_tenant ON asignaciones_solicitudasignacion",
    "ALTER TABLE asignaciones_solicitudasignacion DISABLE ROW LEVEL SECURITY",
]


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
        ("asignaciones", "0001_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
