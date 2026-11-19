"""La solicitud deja de tener un único técnico; el técnico vive en cada línea."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("asignaciones", "0004_linea_tecnico"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="solicitudasignacion",
            name="solicitud_asign_tecnico_fecha",
        ),
        migrations.RemoveField(
            model_name="solicitudasignacion",
            name="tecnico",
        ),
    ]
