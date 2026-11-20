"""Modelos de stock inicial."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class CargaStockInicial(models.Model):
    METODO_EXCEL = "EXCEL"
    METODO_FORMULARIO = "FORMULARIO"
    METODOS = [
        (METODO_EXCEL, "Excel"),
        (METODO_FORMULARIO, "Formulario"),
    ]

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="cargas_stock_inicial",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="cargas_stock_inicial",
    )
    fecha = models.DateTimeField(auto_now_add=True)
    metodo = models.CharField(max_length=10, choices=METODOS)
    archivo_nombre = models.CharField(max_length=255, blank=True, default="")
    archivo_hash = models.CharField(max_length=64, blank=True, default="")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_stock_inicial_creadas",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="carga_stock_inicial_tenant_unico",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "fecha"],
                name="carga_stock_tenant_fecha",
            ),
        ]
        ordering = ["-fecha", "-id"]

    def __str__(self) -> str:
        return f"Carga stock inicial {self.pk}"


class LineaStockInicial(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="lineas_stock_inicial",
    )
    carga = models.ForeignKey(
        CargaStockInicial,
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="lineas_stock_inicial",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_stock_inicial",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    serie = models.OneToOneField(
        "series.Serie",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="linea_stock_inicial",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_stock_inicial_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=True) | Q(cantidad=1),
                name="linea_stock_inicial_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="linea_stock_inicial_cantidad_no_negativa",
            ),
            models.UniqueConstraint(
                fields=["carga", "tecnico", "material"],
                condition=Q(serie__isnull=True),
                name="linea_stock_inicial_no_seriada_unica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "tecnico"],
                name="linea_stock_tenant_tecnico",
            ),
            models.Index(
                fields=["carga", "tecnico"],
                name="linea_stock_carga_tecnico",
            ),
            models.Index(
                fields=["tenant", "material"],
                name="linea_stock_tenant_material",
            ),
        ]
        ordering = ["tecnico__nombre", "material__codigo", "serie__numero"]

    def __str__(self) -> str:
        return f"Línea stock inicial {self.pk}"
