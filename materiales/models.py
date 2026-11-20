"""Modelo del catálogo compartido de materiales."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class Material(models.Model):
    codigo = models.CharField(max_length=11, unique=True)
    descripcion = models.CharField(max_length=100)
    lote = models.CharField(max_length=50, blank=True, default="")
    es_seriado = models.BooleanField()
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
                condition=Q(codigo__regex=r"^[0-9]{11}$"),
                name="material_codigo_11_digitos",
            ),
            models.CheckConstraint(
                condition=~Q(descripcion=""),
                name="material_descripcion_obligatoria",
            ),
        ]
        ordering = ["codigo"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.descripcion}"

    @property
    def tipo(self) -> str:
        return "SERIADO" if self.es_seriado else "NO_SERIADO"
