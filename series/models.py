"""Modelo de series."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class EstadoSerie(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    RESERVADA = "RESERVADA", "Reservada"
    ASIGNADA = "ASIGNADA", "Asignada"
    INSTALADA = "INSTALADA", "Instalada"
    INACTIVA = "INACTIVA", "Inactiva"


class Serie(models.Model):
    numero = models.CharField(max_length=12, unique=True)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="series",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="series",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="series",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    estado = models.CharField(
        max_length=10,
        choices=EstadoSerie.choices,
        default=EstadoSerie.DISPONIBLE,
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="series",
    )
    asignada_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(numero__regex=r"^[A-Z0-9]{12}$"),
                name="serie_formato",
            ),
            models.CheckConstraint(
                condition=Q(
                    estado__in=[
                        "DISPONIBLE",
                        "RESERVADA",
                        "ASIGNADA",
                        "INSTALADA",
                        "INACTIVA",
                    ]
                ),
                name="serie_estado_valido",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        estado="ASIGNADA",
                        tecnico__isnull=False,
                        asignada_en__isnull=False,
                    )
                    | Q(
                        estado__in=[
                            "DISPONIBLE",
                            "RESERVADA",
                            "INSTALADA",
                            "INACTIVA",
                        ],
                        tecnico__isnull=True,
                        asignada_en__isnull=True,
                    )
                ),
                name="serie_tecnico_coherente_estado",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "estado"], name="serie_tenant_estado"),
            models.Index(fields=["tenant", "material"], name="serie_tenant_material"),
            models.Index(fields=["tecnico", "estado"], name="serie_tecnico_estado"),
            models.Index(fields=["tecnico", "material"], name="serie_tecnico_material"),
        ]
        ordering = ["numero"]

    def __str__(self) -> str:
        return self.numero
