"""Políticas RLS para stock general y por técnico."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE stock_stockgeneral ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS stock_general_por_tenant ON stock_stockgeneral",
    """
    CREATE POLICY stock_general_por_tenant ON stock_stockgeneral
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE stock_stocktecnico ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS stock_tecnico_por_tenant ON stock_stocktecnico",
    """
    CREATE POLICY stock_tecnico_por_tenant ON stock_stocktecnico
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS stock_tecnico_por_tenant ON stock_stocktecnico",
    "ALTER TABLE stock_stocktecnico DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS stock_general_por_tenant ON stock_stockgeneral",
    "ALTER TABLE stock_stockgeneral DISABLE ROW LEVEL SECURITY",
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
        ("stock", "0002_stocktecnico"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
