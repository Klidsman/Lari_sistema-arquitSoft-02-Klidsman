"""Modelos de identidad y acceso."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

from .managers import UsuarioManager


class Rol(models.TextChoices):
    ADMIN_PLATAFORMA = "ADMIN_PLATAFORMA", "Administrador de plataforma"
    USUARIO_TENANT = "USUARIO_TENANT", "Cuenta del tenant"
    RESPONSABLE_ALMACEN = "RESPONSABLE_ALMACEN", "Responsable de almacén"


class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=30, choices=Rol.choices)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="usuarios",
    )
    region = models.ForeignKey(
        "tenants.Region",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="usuarios",
    )
    version_sesion = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        rol=Rol.ADMIN_PLATAFORMA,
                        tenant__isnull=True,
                        region__isnull=True,
                    )
                    | Q(
                        rol=Rol.USUARIO_TENANT,
                        tenant__isnull=False,
                        region__isnull=True,
                    )
                    | Q(
                        rol=Rol.RESPONSABLE_ALMACEN,
                        tenant__isnull=True,
                        region__isnull=False,
                    )
                ),
                name="usuario_alcance_coherente",
            ),
            models.UniqueConstraint(
                fields=["tenant"],
                condition=Q(rol=Rol.USUARIO_TENANT),
                name="un_usuario_tenant_por_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.email


class TipoInvitacion(models.TextChoices):
    ALTA = "ALTA", "Alta de cuenta"
    RESTABLECIMIENTO = "RESTABLECIMIENTO", "Restablecimiento de contraseña"


class Invitacion(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="invitaciones",
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoInvitacion.choices,
        default=TipoInvitacion.ALTA,
    )
    token_hash = models.CharField(max_length=64, unique=True)
    correo = models.EmailField()
    expira_en = models.DateTimeField()
    enviada_en = models.DateTimeField(null=True, blank=True)
    usada_en = models.DateTimeField(null=True, blank=True)
    revocada_en = models.DateTimeField(null=True, blank=True)
    ultimo_error = models.TextField(blank=True)
    creada_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="+",
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["usuario", "usada_en", "revocada_en"],
                name="invitacion_vigente",
            ),
        ]
        ordering = ["-creada_en"]

    def __str__(self) -> str:
        return f"Invitación {self.correo}"
