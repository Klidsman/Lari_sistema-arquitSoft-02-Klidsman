"""Políticas de seguridad a nivel de fila para cuentas."""

from django.db import migrations

APLICAR = [
    "ALTER TABLE acceso_usuario ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS usuario_por_alcance ON acceso_usuario",
    """
    CREATE POLICY usuario_por_alcance ON acceso_usuario
    USING (
        current_setting('app.rol', true) = 'ADMIN_PLATAFORMA'
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::bigint
        OR region_id = NULLIF(current_setting('app.region_id', true), '')::bigint
    )
    """,
]

REVERTIR = [
    "DROP POLICY IF EXISTS usuario_por_alcance ON acceso_usuario",
    "ALTER TABLE acceso_usuario DISABLE ROW LEVEL SECURITY",
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
        ("acceso", "0002_initial"),
        ("tenants", "0002_rls"),
    ]

    # El número 0003 evita colisión con acceso.0002_initial.

    operations = [
        migrations.RunPython(aplicar, revertir),
    ]
