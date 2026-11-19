"""Modelos de solicitudes de asignación."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class EstadoSolicitud(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    ENVIADA = "ENVIADA", "Enviada"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    RECHAZADA = "RECHAZADA", "Rechazada"
    CANCELADA = "CANCELADA", "Cancelada"


class SolicitudAsignacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion",
    )
    fecha = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.BORRADOR,
    )
    excel_ruta = models.CharField(max_length=255, blank=True, default="")
    excel_hash = models.CharField(max_length=64, blank=True, default="")
    excel_generado_en = models.DateTimeField(null=True, blank=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    confirmada_en = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True, default="")
    rechazada_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion_actualizadas",
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
                name="solicitud_asignacion_estado_valido",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant", "estado"],
                name="solicitud_asign_tenant_estado",
            ),
            models.Index(
                fields=["region", "fecha"],
                name="solicitud_asign_region_fecha",
            ),
        ]
        ordering = ["-fecha", "-id"]

    def __str__(self) -> str:
        return f"Solicitud {self.pk}"

    @property
    def tecnicos(self):
        """Técnicos de la solicitud, sin repetir."""
        vistos = {}
        for linea in sorted(self.lineas.all(), key=lambda item: item.pk):
            vistos.setdefault(linea.tecnico_id, linea.tecnico)
        return list(vistos.values())

    @property
    def nifs_tecnicos(self) -> str:
        return ", ".join(tecnico.nif for tecnico in self.tecnicos)


class LineaAsignacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    solicitud = models.ForeignKey(
        SolicitudAsignacion,
        on_delete=models.PROTECT,
        related_name="lineas",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    serie = models.ForeignKey(
        "series.Serie",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_asignacion_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=True) | Q(cantidad=1),
                name="linea_asignacion_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="linea_asignacion_cantidad_no_negativa",
            ),
            models.UniqueConstraint(
                fields=["solicitud", "serie"],
                condition=Q(serie__isnull=False),
                name="linea_asignacion_serie_unica_en_solicitud",
            ),
            models.UniqueConstraint(
                fields=["solicitud", "tecnico", "material"],
                condition=Q(serie__isnull=True),
                name="linea_asignacion_no_seriada_unica",
            ),
        ]
        indexes = [
            models.Index(
                fields=["solicitud", "material"],
                name="linea_asign_solicitud_material",
            ),
            models.Index(
                fields=["solicitud", "tecnico"],
                name="linea_asign_solicitud_tecnico",
            ),
            models.Index(
                fields=["tenant", "material"],
                name="linea_asign_tenant_material",
            ),
            models.Index(fields=["serie"], name="linea_asign_serie"),
        ]
        ordering = ["material__codigo", "serie__numero"]

    def __str__(self) -> str:
        return f"Línea asignación {self.pk}"


class EnvioCorreo(models.Model):
    ESTADO_REINTENTANDO = "REINTENTANDO"
    ESTADO_EXITOSO = "EXITOSO"
    ESTADO_FALLIDO = "FALLIDO"
    ESTADOS = [
        (ESTADO_REINTENTANDO, "Reintentando"),
        (ESTADO_EXITOSO, "Exitoso"),
        (ESTADO_FALLIDO, "Fallido"),
    ]

    solicitud = models.ForeignKey(
        SolicitudAsignacion,
        on_delete=models.PROTECT,
        related_name="envios_correo",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="envios_correo",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="envios_correo",
    )
    numero_intento = models.PositiveIntegerField()
    destinatario = models.EmailField()
    archivo = models.CharField(max_length=255)
    hash_sha256 = models.CharField(max_length=64)
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_REINTENTANDO,
    )
    error_mensaje = models.TextField(blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    enviado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "numero_intento"],
                name="envio_correo_intento_unico",
            ),
            models.CheckConstraint(
                condition=Q(numero_intento__gte=1),
                name="envio_correo_numero_intento_positivo",
            ),
            models.CheckConstraint(
                condition=Q(
                    estado__in=["REINTENTANDO", "EXITOSO", "FALLIDO"]
                ),
                name="envio_correo_estado_valido",
            ),
        ]
        indexes = [
            models.Index(
                fields=["region", "estado"],
                name="envio_correo_region_estado",
            ),
            models.Index(
                fields=["tenant", "creado_en"],
                name="envio_correo_tenant_creado",
            ),
            models.Index(
                fields=["solicitud", "numero_intento"],
                name="envio_correo_solicitud_intento",
            ),
        ]
        ordering = ["solicitud", "numero_intento"]

    def __str__(self) -> str:
        return f"Envío {self.pk} de solicitud {self.solicitud_id}"
