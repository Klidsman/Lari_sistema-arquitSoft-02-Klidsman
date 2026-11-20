"""Políticas RLS para conciliaciones."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE conciliaciones_conciliacion ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS conciliacion_por_tenant ON conciliaciones_conciliacion",
    """
    CREATE POLICY conciliacion_por_tenant ON conciliaciones_conciliacion
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE conciliaciones_diferenciaserie ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS diferencia_serie_por_tenant ON conciliaciones_diferenciaserie",
    """
    CREATE POLICY diferencia_serie_por_tenant ON conciliaciones_diferenciaserie
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE conciliaciones_diferenciacantidad ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS diferencia_cantidad_por_tenant ON conciliaciones_diferenciacantidad",
    """
    CREATE POLICY diferencia_cantidad_por_tenant ON conciliaciones_diferenciacantidad
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE conciliaciones_materialnocatalogado ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS material_no_catalogado_por_tenant ON conciliaciones_materialnocatalogado",
    """
    CREATE POLICY material_no_catalogado_por_tenant ON conciliaciones_materialnocatalogado
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS material_no_catalogado_por_tenant ON conciliaciones_materialnocatalogado",
    "ALTER TABLE conciliaciones_materialnocatalogado DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS diferencia_cantidad_por_tenant ON conciliaciones_diferenciacantidad",
    "ALTER TABLE conciliaciones_diferenciacantidad DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS diferencia_serie_por_tenant ON conciliaciones_diferenciaserie",
    "ALTER TABLE conciliaciones_diferenciaserie DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS conciliacion_por_tenant ON conciliaciones_conciliacion",
    "ALTER TABLE conciliaciones_conciliacion DISABLE ROW LEVEL SECURITY",
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
        ("conciliaciones", "0001_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
