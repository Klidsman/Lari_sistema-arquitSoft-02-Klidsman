"""Políticas de seguridad a nivel de fila para regiones, almacenes y tenants."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE tenants_region ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS region_por_alcance ON tenants_region",
    """
    CREATE POLICY region_por_alcance ON tenants_region
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR id = NULLIF(current_setting('app.region_id', true), '')::bigint
    )
    """,
    "ALTER TABLE tenants_almacen ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS almacen_por_region ON tenants_almacen",
    """
    CREATE POLICY almacen_por_region ON tenants_almacen
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR region_id = NULLIF(current_setting('app.region_id', true), '')::bigint
    )
    """,
    "ALTER TABLE tenants_tenant ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS tenant_por_alcance ON tenants_tenant",
    """
    CREATE POLICY tenant_por_alcance ON tenants_tenant
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
        OR region_id = NULLIF(current_setting('app.region_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS tenant_por_alcance ON tenants_tenant",
    "ALTER TABLE tenants_tenant DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS almacen_por_region ON tenants_almacen",
    "ALTER TABLE tenants_almacen DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS region_por_alcance ON tenants_region",
    "ALTER TABLE tenants_region DISABLE ROW LEVEL SECURITY",
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
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(aplicar, revertir),
    ]
