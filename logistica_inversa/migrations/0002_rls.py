"""Políticas RLS para logística inversa."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE logistica_inversa_devolucion ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS devolucion_por_tenant ON logistica_inversa_devolucion",
    """
    CREATE POLICY devolucion_por_tenant ON logistica_inversa_devolucion
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE logistica_inversa_lineadevolucion ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS linea_devolucion_por_tenant ON logistica_inversa_lineadevolucion",
    """
    CREATE POLICY linea_devolucion_por_tenant ON logistica_inversa_lineadevolucion
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE logistica_inversa_bajaequipo ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS baja_equipo_por_tenant ON logistica_inversa_bajaequipo",
    """
    CREATE POLICY baja_equipo_por_tenant ON logistica_inversa_bajaequipo
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS baja_equipo_por_tenant ON logistica_inversa_bajaequipo",
    "ALTER TABLE logistica_inversa_bajaequipo DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS linea_devolucion_por_tenant ON logistica_inversa_lineadevolucion",
    "ALTER TABLE logistica_inversa_lineadevolucion DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS devolucion_por_tenant ON logistica_inversa_devolucion",
    "ALTER TABLE logistica_inversa_devolucion DISABLE ROW LEVEL SECURITY",
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
        ("logistica_inversa", "0001_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
