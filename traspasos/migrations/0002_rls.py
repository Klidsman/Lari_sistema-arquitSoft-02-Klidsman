"""Políticas RLS para traspasos."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE traspasos_solicitudtraspaso ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS solicitud_traspaso_por_tenant ON traspasos_solicitudtraspaso",
    """
    CREATE POLICY solicitud_traspaso_por_tenant ON traspasos_solicitudtraspaso
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
    "ALTER TABLE traspasos_lineatraspaso ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS linea_traspaso_por_tenant ON traspasos_lineatraspaso",
    """
    CREATE POLICY linea_traspaso_por_tenant ON traspasos_lineatraspaso
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS linea_traspaso_por_tenant ON traspasos_lineatraspaso",
    "ALTER TABLE traspasos_lineatraspaso DISABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS solicitud_traspaso_por_tenant ON traspasos_solicitudtraspaso",
    "ALTER TABLE traspasos_solicitudtraspaso DISABLE ROW LEVEL SECURITY",
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
        ("traspasos", "0001_initial"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
