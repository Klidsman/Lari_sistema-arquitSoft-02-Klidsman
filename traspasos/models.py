"""Modelos de traspasos entre técnicos."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class EstadoTraspaso(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    ENVIADA = "ENVIADA", "Enviada"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    RECHAZADA = "RECHAZADA", "Rechazada"
    CANCELADA = "CANCELADA", "Cancelada"


class SolicitudTraspaso(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="solicitudes_traspaso",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="solicitudes_traspaso",
    )
    fecha = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoTraspaso.choices,
        default=EstadoTraspaso.BORRADOR,
    )
    motivo_rechazo = models.TextField(blank=True, default="")
    excel_ruta = models.CharField(max_length=255, blank=True, default="")
    excel_hash = models.CharField(max_length=64, blank=True, default="")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="traspasos_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    confirmada_en = models.DateTimeField(null=True, blank=True)
    rechazada_en = models.DateTimeField(null=True, blank=True)
    cancelada_en = models.DateTimeField(null=True, blank=True)
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
                condition=Q(
                    estado__in=[
                        "BORRADOR",
                        "ENVIADA",
                        "CONFIRMADA",
                        "RECHAZADA",
                        "CANCELADA",
                    ]
                ),
                name="solicitud_traspaso_estado_valido",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "estado"],
                name="traspaso_tenant_estado",
            ),
            models.Index(
                fields=["region", "estado"],
                name="traspaso_region_estado",
            ),
            models.Index(
                fields=["tenant", "fecha"],
                name="traspaso_tenant_fecha",
            ),
        ]
        ordering = ["-fecha", "-id"]

    def __str__(self) -> str:
        return f"Traspaso {self.pk}"

    @property
    def origenes(self):
        return self._tecnicos("tecnico_origen")

    @property
    def destinos(self):
        return self._tecnicos("tecnico_destino")

    @property
    def tecnicos(self):
        vistos = {}
        for tecnico in list(self.origenes) + list(self.destinos):
            vistos[tecnico.pk] = tecnico
        return list(vistos.values())

    @property
    def forma(self) -> str:
        origenes = {linea.tecnico_origen_id for linea in self.lineas.all()}
        destinos = {linea.tecnico_destino_id for linea in self.lineas.all()}
        if len(origenes) == 1 and len(destinos) >= 1:
            return "1→N"
        if len(destinos) == 1 and len(origenes) >= 1:
            return "N→1"
        return "INVALIDA"

    def _tecnicos(self, campo):
        ids = (
            self.lineas.values_list(f"{campo}_id", flat=True)
            .distinct()
            .order_by()
        )
        from tecnicos.models import Tecnico

        return list(Tecnico.objects.filter(pk__in=ids).order_by("nif"))


class LineaTraspaso(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="lineas_traspaso",
    )
    solicitud = models.ForeignKey(
        SolicitudTraspaso,
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    tecnico_origen = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="lineas_traspaso_origen",
    )
    tecnico_destino = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="lineas_traspaso_destino",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_traspaso",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    serie = models.ForeignKey(
        "series.Serie",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="lineas_traspaso",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(tecnico_origen=F("tecnico_destino")),
                name="linea_traspaso_origen_destino_distintos",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_traspaso_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=True) | Q(cantidad=1),
                name="linea_traspaso_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="linea_traspaso_cantidad_no_negativa",
            ),
            models.UniqueConstraint(
                fields=["solicitud", "serie"],
                condition=Q(serie__isnull=False),
                name="linea_traspaso_serie_unica",
            ),
            models.UniqueConstraint(
                fields=[
                    "solicitud",
                    "tecnico_origen",
                    "tecnico_destino",
                    "material",
                ],
                condition=Q(serie__isnull=True),
                name="linea_traspaso_no_seriada_unica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["solicitud", "material"],
                name="linea_trasp_solicitud_material",
            ),
            models.Index(
                fields=["tenant", "material"],
                name="linea_traspaso_tenant_material",
            ),
            models.Index(
                fields=["tecnico_origen", "material"],
                name="linea_traspaso_origen_material",
            ),
            models.Index(
                fields=["tecnico_destino", "material"],
                name="linea_traspaso_destino_mat",
            ),
            models.Index(fields=["serie"], name="linea_traspaso_serie"),
        ]
        ordering = ["material__codigo", "serie__numero"]

    def __str__(self) -> str:
        return f"Línea traspaso {self.pk}"
