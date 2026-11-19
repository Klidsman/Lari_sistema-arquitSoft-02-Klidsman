"""Políticas RLS para stock inicial."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE stock_inicial_cargastockinicial ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS carga_stock_inicial_por_tenant ON stock_inicial_cargastockinicial",
    """
    CREATE POLICY carga_stock_inicial_por_tenant ON stock_inicial_cargastockinicial
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE stock_inicial_lineastockinicial ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS linea_stock_inicial_por_tenant ON stock_inicial_lineastockinicial",
    """
    CREATE POLICY linea_stock_inicial_por_tenant ON stock_inicial_lineastockinicial
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS linea_stock_inicial_por_tenant ON stock_inicial_lineastockinicial",
    "ALTER TABLE stock_inicial_lineastockinicial DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS carga_stock_inicial_por_tenant ON stock_inicial_cargastockinicial",
    "ALTER TABLE stock_inicial_cargastockinicial DISABLE ROW LEVEL SECURITY",
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
        ("stock_inicial", "0001_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
