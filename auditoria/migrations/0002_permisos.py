"""Auditoría inmutable: sin UPDATE ni DELETE para el rol de aplicación."""

from django.db import migrations

APLICAR = [
    "REVOKE UPDATE, DELETE ON TABLE auditoria_registrocambio FROM PUBLIC",
    "REVOKE UPDATE, DELETE ON TABLE auditoria_registrocambio FROM CURRENT_USER",
    """
    CREATE OR REPLACE FUNCTION auditoria_registro_inmutable()
    RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'La auditoría es inmutable'
            USING ERRCODE = 'insufficient_privilege';
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS auditoria_registro_inmutable ON auditoria_registrocambio",
    """
    CREATE TRIGGER auditoria_registro_inmutable
    BEFORE UPDATE OR DELETE ON auditoria_registrocambio
    FOR EACH ROW EXECUTE FUNCTION auditoria_registro_inmutable()
    """,
]

REVERTIR = [
    "DROP TRIGGER IF EXISTS auditoria_registro_inmutable ON auditoria_registrocambio",
    "DROP FUNCTION IF EXISTS auditoria_registro_inmutable()",
    "GRANT UPDATE, DELETE ON TABLE auditoria_registrocambio TO CURRENT_USER",
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
        ("auditoria", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(aplicar, revertir),
    ]
