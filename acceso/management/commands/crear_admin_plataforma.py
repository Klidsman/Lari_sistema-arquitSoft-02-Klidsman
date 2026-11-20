"""Crea la primera cuenta de Administrador de plataforma."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from acceso.models import Invitacion, Rol, Usuario
from acceso.totp import generar_token, hash_token


class Command(BaseCommand):
    help = "Crea un Administrador de plataforma inactivo con invitación de un solo uso."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Correo de la cuenta administradora.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        if not email:
            raise CommandError("El correo es obligatorio.")

        if Usuario.objects.filter(email__iexact=email).exists():
            raise CommandError("El correo ya está registrado.")

        usuario = Usuario.objects.create_user(
            email=email,
            password=None,
            rol=Rol.ADMIN_PLATAFORMA,
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )

        token = generar_token()
        Invitacion.objects.create(
            usuario=usuario,
            token_hash=hash_token(token),
            correo=email,
            expira_en=timezone.now() + timedelta(hours=72),
            creada_por=usuario,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Administrador creado inactivo. Invitación: "
                f"/invitacion/{token}/"
            )
        )
