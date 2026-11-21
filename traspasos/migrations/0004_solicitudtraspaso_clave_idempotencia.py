"""Clave de idempotencia para el alta de traspasos."""

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("traspasos", "0003_linea_tecnico_origen_destino"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudtraspaso",
            name="clave_idempotencia",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name="solicitudtraspaso",
            constraint=models.UniqueConstraint(
                condition=Q(clave_idempotencia__isnull=False)
                & ~Q(clave_idempotencia=""),
                fields=("tenant", "clave_idempotencia"),
                name="solicitud_traspaso_idempotencia_unica",
            ),
        ),
    ]
