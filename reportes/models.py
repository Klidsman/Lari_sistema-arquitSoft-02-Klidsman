"""Modelo de corte mensual."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class CorteMensual(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cortes_mensuales",
    )
    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField()
    solicitados = models.PositiveIntegerField(default=0)
    asignados = models.PositiveIntegerField(default=0)
    liquidados_instalados = models.PositiveIntegerField(default=0)
    devueltos = models.PositiveIntegerField(default=0)
    no_justificado = models.PositiveIntegerField(default=0)
    porcentaje_merma = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    version = models.PositiveIntegerField(default=1)
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cortes_generados",
    )
    generado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actualizado_en = models.DateTimeField(auto_now=True)
    regenerado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "anio", "mes"],
                condition=Q(tenant__isnull=False),
                name="corte_tenant_anio_mes_unico",
            ),
            models.UniqueConstraint(
                fields=["anio", "mes"],
                condition=Q(tenant__isnull=True),
                name="corte_global_anio_mes_unico",
            ),
            models.CheckConstraint(
                condition=Q(mes__gte=1, mes__lte=12),
                name="corte_mes_valido",
            ),
            models.CheckConstraint(
                condition=Q(anio__gte=2000, anio__lte=2100),
                name="corte_anio_valido",
            ),
            models.CheckConstraint(
                condition=Q(porcentaje_merma__gte=0, porcentaje_merma__lte=100),
                name="corte_merma_valida",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "anio", "mes"], name="corte_tenant_anio_mes"
            ),
            models.Index(fields=["anio", "mes"], name="corte_anio_mes"),
        ]
        ordering = ["-anio", "-mes", "tenant__codigo"]

    def __str__(self) -> str:
        alcance = self.tenant.codigo if self.tenant_id else "global"
        return f"Corte {alcance} {self.anio}-{self.mes:02d}"
