"""Modelos de recojos."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class EstadoRecojo(models.TextChoices):
    REGISTRADO = "REGISTRADO", "Registrado"
    ANULADO = "ANULADO", "Anulado"


class Recojo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="recojos",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="recojos",
    )
    nombre = models.CharField(max_length=100, default="")
    fecha = models.DateField()
    estado = models.CharField(
        max_length=10,
        choices=EstadoRecojo.choices,
        default=EstadoRecojo.REGISTRADO,
    )
    anulado_en = models.DateTimeField(null=True, blank=True)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="recojos_anulados",
    )
    motivo_anulacion = models.TextField(blank=True, default="")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recojos_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="recojo_tenant_fecha"),
            models.Index(fields=["region", "fecha"], name="recojo_region_fecha"),
            models.Index(fields=["tenant", "nombre"], name="recojo_tenant_nombre"),
            models.Index(
                fields=["tenant", "estado", "fecha"],
                name="recojo_tenant_estado_fecha",
            ),
        ]
        ordering = ["-fecha", "-id"]

    def __str__(self) -> str:
        return f"Recojo {self.pk} - {self.fecha}"


class LineaRecojo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="lineas_recojo",
    )
    recojo = models.ForeignKey(
        Recojo,
        on_delete=models.PROTECT,
        related_name="lineas",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_recojo",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    serie = models.OneToOneField(
        "series.Serie",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="linea_recojo",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_recojo_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=True) | Q(cantidad=1),
                name="linea_recojo_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="linea_recojo_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(
                fields=["recojo", "material"],
                name="linea_recojo_recojo_material",
            ),
            models.Index(
                fields=["tenant", "material"],
                name="linea_recojo_tenant_material",
            ),
        ]
        ordering = ["material__codigo", "serie__numero"]

    def __str__(self) -> str:
        return f"Línea {self.pk} del recojo {self.recojo_id}"
