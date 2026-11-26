"""RLS para las series consumidas por una orden."""

from django.db import migrations

TABLA = "registro_materiales_usomaterialserie"
POLITICA = "uso_material_serie_por_tenant"

APLICAR = [
    f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY",
    f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}",
    f"""
    CREATE POLICY {POLITICA} ON {TABLA}
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}",
    f"ALTER TABLE {TABLA} DISABLE ROW LEVEL SECURITY",
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
        ("registro_materiales", "0005_usomaterialserie"),
        ("tenants", "0002_rls"),
    ]

    operations = [migrations.RunPython(aplicar, revertir)]
