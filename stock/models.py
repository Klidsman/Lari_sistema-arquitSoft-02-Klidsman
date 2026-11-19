"""Modelos de stock."""

from django.db import models
from django.db.models import Q


class StockTecnico(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tecnico", "material"],
                name="stock_tecnico_tecnico_material_unico",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="stock_tecnico_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "material"],
                name="stock_tecnico_tenant_material",
            ),
            models.Index(
                fields=["tecnico", "material"],
                name="stock_tecnico_tecnico_material",
            ),
        ]
        ordering = ["tenant", "tecnico", "material"]

    def __str__(self) -> str:
        return f"{self.tecnico.nif}/{self.material.codigo}: {self.cantidad}"


class StockGeneral(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="stock_general",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="stock_general",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "material"],
                name="stock_general_tenant_material_unico",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="stock_general_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "material"],
                name="stock_general_tenant_material",
            ),
        ]
        ordering = ["tenant", "material"]

    def __str__(self) -> str:
        return f"{self.tenant.codigo}/{self.material.codigo}: {self.cantidad}"
