"""Modelo de técnicos del tenant."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class Tecnico(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="tecnicos",
    )
    nif = models.CharField(max_length=6, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
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
                condition=Q(nif__regex=r"^LA[0-9]{4}$"),
                name="tecnico_nif_formato",
            ),
            models.CheckConstraint(
                condition=~Q(nombre=""),
                name="tecnico_nombre_obligatorio",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "activo"],
                name="tecnico_tenant_activo",
            ),
            models.Index(
                fields=["tenant", "nombre"],
                name="tecnico_tenant_nombre",
            ),
        ]
        ordering = ["nombre", "nif"]

    def __str__(self) -> str:
        return f"{self.nif} - {self.nombre}"
