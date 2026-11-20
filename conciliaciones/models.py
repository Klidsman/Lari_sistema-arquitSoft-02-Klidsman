"""Modelos de conciliación de stock."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class EstadoConciliacion(models.TextChoices):
    EN_REVISION = "EN_REVISION", "En revisión"
    APROBADA = "APROBADA", "Aprobada"
    RECHAZADA = "RECHAZADA", "Rechazada"


class TipoDiferenciaSerie(models.TextChoices):
    EN_REPORTE_NO_SISTEMA = "EN_REPORTE_NO_SISTEMA", "En reporte, no en sistema"
    EN_SISTEMA_NO_REPORTE = "EN_SISTEMA_NO_REPORTE", "En sistema, no en reporte"
    EN_OTRO_TECNICO = "EN_OTRO_TECNICO", "En otro técnico"


class Conciliacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="conciliaciones",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="conciliaciones",
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoConciliacion.choices,
        default=EstadoConciliacion.EN_REVISION,
    )
    archivo_nombre = models.CharField(max_length=255)
    archivo_ruta = models.CharField(max_length=255, blank=True, default="")
    hash_sha256 = models.CharField(max_length=64)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_rechazo = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True, default="")
    huella_stock = models.CharField(max_length=64)
    requiere_revision = models.BooleanField(default=False)
    ajustes_aplicados = models.PositiveIntegerField(default=0)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="conciliaciones_creadas",
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="conciliaciones_aprobadas",
    )
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
                fields=["tenant"],
                condition=Q(estado="EN_REVISION"),
                name="conciliacion_una_en_revision_por_tenant",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["EN_REVISION", "APROBADA", "RECHAZADA"]),
                name="conciliacion_estado_valido",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "estado"], name="conciliacion_tenant_estado"
            ),
            models.Index(
                fields=["region", "fecha_carga"],
                name="conciliacion_region_fecha",
            ),
        ]
        ordering = ["-fecha_carga", "-id"]

    def __str__(self) -> str:
        return f"Conciliación {self.pk}"


class DiferenciaSerie(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="diferencias_serie",
    )
    conciliacion = models.ForeignKey(
        Conciliacion,
        on_delete=models.CASCADE,
        related_name="diferencias_series",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="+",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="diferencias_serie",
    )
    numero = models.CharField(max_length=12)
    tipo = models.CharField(
        max_length=24,
        choices=TipoDiferenciaSerie.choices,
    )
    tecnico_sistema = models.ForeignKey(
        "tecnicos.Tecnico",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    lote = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conciliacion", "tipo", "numero"],
                name="diferencia_serie_unica_por_tipo",
            ),
            models.CheckConstraint(
                condition=Q(numero__regex=r"^[A-Z0-9]{12}$"),
                name="diferencia_serie_formato",
            ),
            models.CheckConstraint(
                condition=Q(
                    tipo__in=[
                        "EN_REPORTE_NO_SISTEMA",
                        "EN_SISTEMA_NO_REPORTE",
                        "EN_OTRO_TECNICO",
                    ]
                ),
                name="diferencia_serie_tipo_valido",
            ),
            models.CheckConstraint(
                condition=(
                    Q(tipo="EN_OTRO_TECNICO", tecnico_sistema__isnull=False)
                    | (~Q(tipo="EN_OTRO_TECNICO") & Q(tecnico_sistema__isnull=True))
                ),
                name="diferencia_serie_tecnico_sistema_coherente",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conciliacion", "tipo"],
                name="diferencia_serie_conc_tipo",
            ),
            models.Index(
                fields=["tenant", "numero"], name="diferencia_serie_tenant_num"
            ),
        ]
        ordering = ["tipo", "numero"]

    def __str__(self) -> str:
        return f"{self.tipo}: {self.numero}"


class DiferenciaCantidad(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="diferencias_cantidad",
    )
    conciliacion = models.ForeignKey(
        Conciliacion,
        on_delete=models.CASCADE,
        related_name="diferencias_cantidades",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="+",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="diferencias_cantidad",
    )
    cantidad_sistema = models.IntegerField()
    cantidad_reporte = models.IntegerField()
    diferencia = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conciliacion", "tecnico", "material"],
                name="diferencia_cantidad_unica",
            ),
            models.CheckConstraint(
                condition=Q(cantidad_sistema__gte=0, cantidad_reporte__gte=0),
                name="diferencia_cantidad_no_negativa",
            ),
            models.CheckConstraint(
                condition=Q(
                    diferencia=models.F("cantidad_reporte")
                    - models.F("cantidad_sistema")
                ),
                name="diferencia_cantidad_calculada",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conciliacion", "tecnico"],
                name="diferencia_cant_conc_tec",
            ),
            models.Index(
                fields=["tenant", "material"],
                name="diferencia_cant_tenant_mat",
            ),
        ]
        ordering = ["tecnico__nif", "material__codigo"]

    def __str__(self) -> str:
        return f"{self.tecnico_id}/{self.material_id}: {self.diferencia}"


class MaterialNoCatalogado(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="materiales_no_catalogados",
    )
    conciliacion = models.ForeignKey(
        Conciliacion,
        on_delete=models.CASCADE,
        related_name="materiales_no_catalogados",
    )
    codigo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, blank=True, default="")
    tecnico_nif = models.CharField(max_length=20, blank=True, default="")
    filas = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conciliacion", "codigo"],
                name="material_no_catalogado_unico",
            ),
        ]
        ordering = ["codigo"]

    def __str__(self) -> str:
        return self.codigo
