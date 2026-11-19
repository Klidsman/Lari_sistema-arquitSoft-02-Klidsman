"""Cada línea de asignación guarda su técnico; se copia el de la solicitud."""

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def copiar_tecnico_a_lineas(apps, schema_editor):
    LineaAsignacion = apps.get_model("asignaciones", "LineaAsignacion")
    for linea in LineaAsignacion.objects.select_related("solicitud"):
        linea.tecnico_id = linea.solicitud.tecnico_id
        linea.save(update_fields=["tecnico"])


class Migration(migrations.Migration):
    dependencies = [
        ("asignaciones", "0003_solicitudasignacion_motivo_rechazo_and_more"),
        ("tecnicos", "0002_rls"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineaasignacion",
            name="tecnico",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_asignacion",
                to="tecnicos.tecnico",
            ),
        ),
        migrations.RunPython(copiar_tecnico_a_lineas, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="lineaasignacion",
            name="tecnico",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_asignacion",
                to="tecnicos.tecnico",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="lineaasignacion",
            name="linea_asignacion_no_seriada_unica",
        ),
        migrations.AddConstraint(
            model_name="lineaasignacion",
            constraint=models.UniqueConstraint(
                condition=Q(serie__isnull=True),
                fields=("solicitud", "tecnico", "material"),
                name="linea_asignacion_no_seriada_unica",
            ),
        ),
        migrations.AddIndex(
            model_name="lineaasignacion",
            index=models.Index(
                fields=["solicitud", "tecnico"],
                name="linea_asign_solicitud_tecnico",
            ),
        ),
    ]
