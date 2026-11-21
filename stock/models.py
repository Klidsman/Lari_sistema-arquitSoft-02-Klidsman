"""Modelos de stock."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class TipoMovimientoTecnico(models.TextChoices):
    SALDO_INICIAL = "SALDO_INICIAL", "Saldo inicial"
    ASIGNACION = "ASIGNACION", "Asignación"
    TRASPASO_SALIDA = "TRASPASO_SALIDA", "Traspaso: salida"
    TRASPASO_ENTRADA = "TRASPASO_ENTRADA", "Traspaso: entrada"
    DEVOLUCION = "DEVOLUCION", "Devolución"
    BAJA = "BAJA", "Baja"
    CONCILIACION = "CONCILIACION", "Conciliación"
    AJUSTE = "AJUSTE", "Ajuste"


class MovimientoTecnico(models.Model):
    """Movimiento firmado que compone el saldo de un técnico."""

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="movimientos_tecnico",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="movimientos_tecnico",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="movimientos_tecnico",
    )
    cantidad = models.IntegerField()
    tipo = models.CharField(
        max_length=30,
        choices=TipoMovimientoTecnico.choices,
        default=TipoMovimientoTecnico.AJUSTE,
    )
    referencia = models.CharField(max_length=100, blank=True, default="")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="movimientos_tecnico_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
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
        ]
        indexes = [
            models.Index(
                fields=["tecnico", "material"],
                name="movimiento_tecnico_tec_mat",
            ),
            models.Index(
                fields=["tenant", "creado_en"],
                name="mov_tecnico_tenant_fecha",
            ),
        ]
        ordering = ["-creado_en", "-id"]

    def __str__(self) -> str:
        return (
            f"{self.tecnico.nif}/{self.material.codigo}: "
            f"{self.cantidad:+d}"
        )


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
