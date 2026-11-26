"""Modelos de registro de materiales."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class MaterialHabilitado(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="materiales_habilitados",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="habilitaciones",
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
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
            models.UniqueConstraint(
                fields=["tenant", "material"],
                name="material_habilitado_unico",
            ),
        ]
        ordering = ["orden", "material__codigo"]

    def __str__(self) -> str:
        return f"{self.material} ({'activo' if self.activo else 'inactivo'})"


class SaldoInicialPeriodo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="saldos_iniciales",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="saldos_iniciales",
    )
    periodo = models.CharField(max_length=7)
    cantidad = models.PositiveIntegerField(default=0)
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
            models.UniqueConstraint(
                fields=["tenant", "material", "periodo"],
                name="saldo_inicial_unico",
            ),
            models.CheckConstraint(
                condition=Q(periodo__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
                name="saldo_inicial_periodo_formato",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "periodo"], name="saldo_tenant_periodo"
            ),
        ]
        ordering = ["material__codigo"]

    def __str__(self) -> str:
        return f"{self.material} {self.periodo}: {self.cantidad}"


class DespachoAlmacen(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="despachos_almacen",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="despachos_almacen",
    )
    fecha = models.DateField()
    cantidad = models.PositiveIntegerField(default=0)
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
        indexes = [
            models.Index(
                fields=["tenant", "fecha"], name="despacho_tenant_fecha"
            ),
            models.Index(
                fields=["tenant", "material"], name="despacho_tenant_material"
            ),
        ]
        ordering = ["fecha", "id"]

    def __str__(self) -> str:
        return f"Despacho {self.pk}"


class CargaOrdenes(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="cargas_ordenes",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="cargas_ordenes",
    )
    periodo = models.CharField(max_length=7)
    hash_texto = models.CharField(max_length=64)
    total_leidas = models.PositiveIntegerField(default=0)
    total_nuevas = models.PositiveIntegerField(default=0)
    total_omitidas = models.PositiveIntegerField(default=0)
    total_otro_tecnico = models.PositiveIntegerField(default=0)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    deshecha_en = models.DateTimeField(null=True, blank=True)
    deshecha_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    motivo_deshacer = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(
                fields=["tenant", "periodo"], name="carga_tenant_periodo"
            ),
        ]
        ordering = ["-creado_en", "-id"]

    def __str__(self) -> str:
        return f"Carga {self.pk}"


class OrdenLiquidacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="ordenes_liquidacion",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="ordenes_liquidacion",
    )
    numero_original = models.CharField(max_length=30)
    numero_normalizado = models.CharField(max_length=30)
    periodo = models.CharField(max_length=7)
    fecha_instalacion = models.DateField(null=True, blank=True)
    carga = models.ForeignKey(
        CargaOrdenes,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ordenes",
    )
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
            models.UniqueConstraint(
                fields=["tenant", "tecnico", "periodo", "numero_normalizado"],
                name="orden_unica_por_tecnico_mes_numero",
            ),
            models.CheckConstraint(
                condition=Q(
                    numero_normalizado__regex=r"^[A-Z0-9]+([-_][A-Z0-9]+)*$"
                ),
                name="orden_numero_formato",
            ),
            models.CheckConstraint(
                condition=Q(periodo__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
                name="orden_periodo_formato",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "tecnico", "periodo"],
                name="orden_tenant_tec_periodo",
            ),
            models.Index(
                fields=["tenant", "periodo"], name="orden_tenant_periodo"
            ),
            models.Index(
                fields=["numero_normalizado"], name="orden_numero"
            ),
        ]
        ordering = ["-periodo", "numero_normalizado"]

    def __str__(self) -> str:
        return f"{self.numero_normalizado} ({self.periodo})"

    @property
    def tiene_materiales(self) -> bool:
        return self.usos.filter(cantidad__gt=0).exists()


class UsoMaterialOrden(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="usos_materiales",
    )
    orden = models.ForeignKey(
        OrdenLiquidacion,
        on_delete=models.CASCADE,
        related_name="usos",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="usos_materiales",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="usos_materiales",
    )
    cantidad = models.PositiveIntegerField(default=0)
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
            models.UniqueConstraint(
                fields=["orden", "material"], name="uso_orden_material_unico"
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0), name="uso_cantidad_no_negativa"
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "material"], name="uso_tenant_material"
            ),
            models.Index(fields=["orden"], name="uso_orden"),
        ]
        ordering = ["material__codigo"]

    def __str__(self) -> str:
        return f"{self.material} x {self.cantidad}"


class AdvertenciaUso(models.Model):
    TIPO = [("CANTIDAD_ATIPICA", "Cantidad atípica")]

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="advertencias_uso",
    )
    uso = models.ForeignKey(
        UsoMaterialOrden,
        on_delete=models.CASCADE,
        related_name="advertencias",
    )
    tipo = models.CharField(max_length=20, choices=TIPO, default="CANTIDAD_ATIPICA")
    mensaje = models.TextField()
    resuelta = models.BooleanField(default=False)
    justificacion = models.TextField(blank=True, default="")
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    resuelta_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(tipo="CANTIDAD_ATIPICA"),
                name="advertencia_tipo_valido",
            ),
        ]
        ordering = ["-creada_en", "-id"]

    def __str__(self) -> str:
        return self.mensaje


class CierreMensual(models.Model):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="cierres_mensuales",
    )
    periodo = models.CharField(max_length=7)
    estado = models.CharField(max_length=20, default=ABIERTO)
    version = models.PositiveIntegerField(default=1)
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    cerrado_en = models.DateTimeField(null=True, blank=True)
    reabierto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    reabierto_en = models.DateTimeField(null=True, blank=True)
    motivo_reapertura = models.TextField(blank=True, default="")
    backup_ref = models.CharField(max_length=255, blank=True, default="")
    backup_en = models.DateTimeField(null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "periodo"], name="cierre_unico_por_periodo"
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["ABIERTO", "CERRADO"]),
                name="cierre_estado_valido",
            ),
            models.CheckConstraint(
                condition=Q(periodo__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"),
                name="cierre_periodo_formato",
            ),
        ]
        ordering = ["-periodo"]

    def __str__(self) -> str:
        return f"Cierre {self.periodo}: {self.estado}"


class SaldoMensualMaterial(models.Model):
    cierre = models.ForeignKey(
        CierreMensual,
        on_delete=models.CASCADE,
        related_name="saldos",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="saldos_mensuales",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="saldos_mensuales",
    )
    saldo_inicial = models.IntegerField()
    despachos = models.IntegerField()
    usado = models.IntegerField()
    saldo_final = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cierre", "material"],
                name="saldo_mensual_unico_por_material",
            ),
        ]
        ordering = ["material__codigo"]

    def __str__(self) -> str:
        return f"{self.material} {self.cierre.periodo}: {self.saldo_final}"


class JustificacionCierre(models.Model):
    ORDEN_SIN_MATERIALES = "ORDEN_SIN_MATERIALES"
    SALDO_NEGATIVO = "SALDO_NEGATIVO"
    ADVERTENCIA = "ADVERTENCIA"
    TIPOS = [
        (ORDEN_SIN_MATERIALES, "Orden sin materiales"),
        (SALDO_NEGATIVO, "Saldo negativo"),
        (ADVERTENCIA, "Advertencia"),
    ]

    cierre = models.ForeignKey(
        CierreMensual,
        on_delete=models.CASCADE,
        related_name="justificaciones",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="justificaciones_cierre",
    )
    tipo = models.CharField(max_length=30, choices=TIPOS)
    referencia = models.CharField(max_length=100)
    motivo = models.TextField()
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cierre", "tipo", "referencia"],
                name="justificacion_unica_por_pendiente",
            ),
            models.CheckConstraint(
                condition=Q(
                    tipo__in=[
                        "ORDEN_SIN_MATERIALES",
                        "SALDO_NEGATIVO",
                        "ADVERTENCIA",
                    ]
                ),
                name="justificacion_tipo_valido",
            ),
        ]
        ordering = ["tipo", "referencia"]

    def __str__(self) -> str:
        return f"{self.tipo}: {self.referencia}"
