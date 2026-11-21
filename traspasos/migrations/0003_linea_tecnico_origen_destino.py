"""Traspaso multi-técnico: origen y destino por línea."""

import django.db.models.deletion
from django.db import migrations, models


def rellenar_tecnicos(apps, schema_editor):
    LineaTraspaso = apps.get_model("traspasos", "LineaTraspaso")
    for linea in LineaTraspaso.objects.select_related("solicitud").iterator():
        linea.tecnico_origen_id = linea.solicitud.tecnico_origen_id
        linea.tecnico_destino_id = linea.solicitud.tecnico_destino_id
        linea.save(
            update_fields=["tecnico_origen", "tecnico_destino"]
        )


def revertir_tecnicos(apps, schema_editor):
    LineaTraspaso = apps.get_model("traspasos", "LineaTraspaso")
    for linea in LineaTraspaso.objects.select_related("solicitud").iterator():
        linea.solicitud.tecnico_origen_id = linea.tecnico_origen_id
        linea.solicitud.tecnico_destino_id = linea.tecnico_destino_id
        linea.solicitud.save(
            update_fields=["tecnico_origen", "tecnico_destino"]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("traspasos", "0002_rls"),
        ("tecnicos", "0002_rls"),
    ]

    operations = [
        migrations.AddField(
            model_name="lineatraspaso",
            name="tecnico_origen",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_traspaso_origen",
                to="tecnicos.tecnico",
            ),
        ),
        migrations.AddField(
            model_name="lineatraspaso",
            name="tecnico_destino",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_traspaso_destino",
                to="tecnicos.tecnico",
            ),
        ),
        migrations.RunPython(rellenar_tecnicos, revertir_tecnicos),
        migrations.AlterField(
            model_name="lineatraspaso",
            name="tecnico_origen",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_traspaso_origen",
                to="tecnicos.tecnico",
            ),
        ),
        migrations.AlterField(
            model_name="lineatraspaso",
            name="tecnico_destino",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="lineas_traspaso_destino",
                to="tecnicos.tecnico",
            ),
        ),
        migrations.AddConstraint(
            model_name="lineatraspaso",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("tecnico_origen", models.F("tecnico_destino")),
                    _negated=True,
                ),
                name="linea_traspaso_origen_destino_distintos",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="lineatraspaso",
            name="linea_traspaso_no_seriada_unica",
        ),
        migrations.AddConstraint(
            model_name="lineatraspaso",
            constraint=models.UniqueConstraint(
                condition=models.Q(("serie__isnull", True)),
                fields=(
                    "solicitud",
                    "tecnico_origen",
                    "tecnico_destino",
                    "material",
                ),
                name="linea_traspaso_no_seriada_unica",
            ),
        ),
        migrations.AddIndex(
            model_name="lineatraspaso",
            index=models.Index(
                fields=["tecnico_origen", "material"],
                name="linea_traspaso_origen_material",
            ),
        ),
        migrations.AddIndex(
            model_name="lineatraspaso",
            index=models.Index(
                fields=["tecnico_destino", "material"],
                name="linea_traspaso_destino_mat",
            ),
        ),
        migrations.RemoveIndex(
            model_name="solicitudtraspaso",
            name="traspaso_origen_fecha",
        ),
        migrations.RemoveIndex(
            model_name="solicitudtraspaso",
            name="traspaso_destino_fecha",
        ),
        migrations.RemoveConstraint(
            model_name="solicitudtraspaso",
            name="solicitud_traspaso_origen_destino_distintos",
        ),
        migrations.RemoveField(
            model_name="solicitudtraspaso",
            name="tecnico_origen",
        ),
        migrations.RemoveField(
            model_name="solicitudtraspaso",
            name="tecnico_destino",
        ),
    ]
