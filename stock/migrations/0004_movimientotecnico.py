"""Movimientos de stock por técnico: fuente de verdad del saldo."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def crear_saldos_iniciales(apps, schema_editor):
    MovimientoTecnico = apps.get_model("stock", "MovimientoTecnico")
    StockTecnico = apps.get_model("stock", "StockTecnico")
    movimientos = []
    for fila in StockTecnico.objects.filter(cantidad__gt=0).iterator():
        movimientos.append(
            MovimientoTecnico(
                tenant_id=fila.tenant_id,
                tecnico_id=fila.tecnico_id,
                material_id=fila.material_id,
                cantidad=fila.cantidad,
                tipo="SALDO_INICIAL",
                referencia=f"INICIAL:{fila.pk}",
                creado_por_id=None,
            )
        )
    if movimientos:
        MovimientoTecnico.objects.bulk_create(movimientos, batch_size=500)


def eliminar_saldos_iniciales(apps, schema_editor):
    MovimientoTecnico = apps.get_model("stock", "MovimientoTecnico")
    MovimientoTecnico.objects.filter(tipo="SALDO_INICIAL").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("stock", "0003_rls"),
        ("materiales", "0002_material_activo"),
        ("tecnicos", "0002_rls"),
        ("tenants", "0003_tenant_fecha_stock_inicial_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MovimientoTecnico",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cantidad", models.IntegerField()),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("SALDO_INICIAL", "Saldo inicial"),
                            ("ASIGNACION", "Asignación"),
                            ("TRASPASO_SALIDA", "Traspaso: salida"),
                            ("TRASPASO_ENTRADA", "Traspaso: entrada"),
                            ("DEVOLUCION", "Devolución"),
                            ("BAJA", "Baja"),
                            ("CONCILIACION", "Conciliación"),
                            ("AJUSTE", "Ajuste"),
                        ],
                        default="AJUSTE",
                        max_length=30,
                    ),
                ),
                (
                    "referencia",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "creado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos_tecnico_creados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "material",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos_tecnico",
                        to="materiales.material",
                    ),
                ),
                (
                    "tecnico",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos_tecnico",
                        to="tecnicos.tecnico",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="movimientos_tecnico",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["-creado_en", "-id"],
                "indexes": [
                    models.Index(
                        fields=["tecnico", "material"],
                        name="movimiento_tecnico_tec_mat",
                    ),
                    models.Index(
                        fields=["tenant", "creado_en"],
                        name="mov_tecnico_tenant_fecha",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=~Q(cantidad=0),
                        name="movimiento_tecnico_cantidad_no_cero",
                    ),
                    models.UniqueConstraint(
                        fields=[
                            "tenant",
                            "tecnico",
                            "material",
                            "tipo",
                            "referencia",
                        ],
                        condition=~Q(referencia=""),
                        name="movimiento_tecnico_referencia_unica",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            crear_saldos_iniciales, eliminar_saldos_iniciales
        ),
    ]
