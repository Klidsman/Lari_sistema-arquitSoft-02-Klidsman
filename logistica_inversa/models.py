"""Modelos de logística inversa."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class CausaBaja(models.TextChoices):
    AVERIA = "AVERIA", "Avería"
    MIGRACION = "MIGRACION", "Migración"
    OTRO = "OTRO", "Otro"


class Devolucion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="devoluciones",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="devoluciones",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="devoluciones",
    )
    fecha = models.DateField()
    observaciones = models.TextField(blank=True, default="")
    acta_ruta = models.CharField(max_length=255, blank=True, default="")
    acta_hash = models.CharField(max_length=64, blank=True, default="")
    acta_generada_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="devoluciones_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="devolucion_tenant_fecha"),
            models.Index(fields=["region", "fecha"], name="devolucion_region_fecha"),
            models.Index(fields=["tecnico", "fecha"], name="devolucion_tecnico_fecha"),
        ]
        ordering = ["-fecha", "-id"]

    def __str__(self) -> str:
        return f"Devolución {self.pk}"


class LineaDevolucion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="lineas_devolucion",
    )
    devolucion = models.ForeignKey(
        Devolucion,
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    serie = models.ForeignKey(
        "series.Serie",
        on_delete=models.PROTECT,
        related_name="lineas_devolucion",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_devolucion",
    )
    descripcion = models.CharField(max_length=255)
    lote = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["devolucion", "serie"],
                name="linea_devolucion_serie_unica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["devolucion", "serie"],
                name="linea_devolucion_conc_serie",
            ),
            models.Index(
                fields=["tenant", "material"],
                name="linea_devolucion_tenant_mat",
            ),
            models.Index(fields=["serie"], name="linea_devolucion_serie"),
        ]
        ordering = ["serie__numero"]

    def __str__(self) -> str:
        return f"Línea devolución {self.pk}"


class BajaEquipo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="bajas_equipos",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="bajas_equipos",
    )
    serie = models.OneToOneField(
        "series.Serie",
        on_delete=models.PROTECT,
        related_name="baja",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="bajas_equipos",
    )
    causa = models.CharField(max_length=20, choices=CausaBaja.choices)
    observaciones = models.TextField(blank=True, default="")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bajas_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(causa__in=["AVERIA", "MIGRACION", "OTRO"]),
                name="baja_causa_valida",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "causa"], name="baja_tenant_causa"),
            models.Index(fields=["region", "creado_en"], name="baja_region_fecha"),
            models.Index(fields=["serie"], name="baja_serie"),
        ]
        ordering = ["-creado_en", "-id"]

    def __str__(self) -> str:
        return f"Baja {self.pk}"
