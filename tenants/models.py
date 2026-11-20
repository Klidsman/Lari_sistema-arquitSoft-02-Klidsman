"""Modelos de regiones, almacenes y tenants."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class Region(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)
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
                condition=~Q(codigo=""),
                name="region_codigo_obligatorio",
            ),
        ]
        ordering = ["codigo"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class Almacen(models.Model):
    region = models.OneToOneField(
        Region,
        on_delete=models.PROTECT,
        related_name="almacen",
    )
    centro = models.CharField(max_length=20)
    codigo_almacen = models.CharField(max_length=20)
    buzon = models.EmailField()
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
                condition=~Q(centro="") & ~Q(codigo_almacen=""),
                name="almacen_parametros_obligatorios",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.region.codigo} - {self.codigo_almacen}"


class Tenant(models.Model):
    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_SUSPENDIDO = "SUSPENDIDO"
    ESTADOS = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_SUSPENDIDO, "Suspendido"),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="tenants",
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADOS,
        default=ESTADO_ACTIVO,
    )
    stock_inicial_cargado = models.BooleanField(default=False)
    fecha_stock_inicial = models.DateTimeField(null=True, blank=True)
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
                condition=~Q(codigo=""),
                name="tenant_codigo_obligatorio",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["ACTIVO", "SUSPENDIDO"]),
                name="tenant_estado_valido",
            ),
        ]
        indexes = [
            models.Index(
                fields=["region", "estado"],
                name="tenant_region_estado",
            ),
        ]
        ordering = ["codigo"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"

    def tiene_cuenta_activa(self) -> bool:
        return self.usuarios.filter(
            rol="USUARIO_TENANT",
            is_active=True,
        ).exists()
