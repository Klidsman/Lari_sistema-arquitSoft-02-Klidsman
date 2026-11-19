"""Política RLS para cortes mensuales."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE reportes_cortemensual ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS corte_mensual_por_tenant ON reportes_cortemensual",
    """
    CREATE POLICY corte_mensual_por_tenant ON reportes_cortemensual
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS corte_mensual_por_tenant ON reportes_cortemensual",
    "ALTER TABLE reportes_cortemensual DISABLE ROW LEVEL SECURITY",
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
        ("reportes", "0001_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
