"""Modelo de auditoría compartida."""

from django.conf import settings
from django.db import models


class RegistroCambio(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="registros_cambio",
    )
    entidad = models.CharField(max_length=50)
    entidad_id = models.BigIntegerField()
    campo = models.CharField(max_length=50)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["entidad", "entidad_id"],
                name="auditoria_entidad",
            ),
            models.Index(
                fields=["usuario", "fecha"],
                name="auditoria_usuario_fecha",
            ),
            models.Index(
                fields=["tenant", "fecha"],
                name="auditoria_tenant_fecha",
            ),
        ]
        ordering = ["-fecha", "-id"]

    def __str__(self) -> str:
        return f"{self.entidad}#{self.entidad_id} {self.campo}"
