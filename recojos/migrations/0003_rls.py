"""Políticas RLS para recojos y líneas."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE recojos_recojo ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS recojo_por_tenant ON recojos_recojo",
    """
    CREATE POLICY recojo_por_tenant ON recojos_recojo
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE recojos_linearecojo ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS linea_recojo_por_tenant ON recojos_linearecojo",
    """
    CREATE POLICY linea_recojo_por_tenant ON recojos_linearecojo
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS linea_recojo_por_tenant ON recojos_linearecojo",
    "ALTER TABLE recojos_linearecojo DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS recojo_por_tenant ON recojos_recojo",
    "ALTER TABLE recojos_recojo DISABLE ROW LEVEL SECURITY",
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
        ("recojos", "0002_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
