"""Restablece el acceso de un Administrador de plataforma desde la consola."""

from django.core.management.base import BaseCommand, CommandError

from acceso import services
from acceso.models import Rol, Usuario


class Command(BaseCommand):
    help = (
        "Genera un enlace de restablecimiento de un solo uso para un "
        "Administrador de plataforma y, opcionalmente, reinicia su 2FA."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Correo del Administrador de plataforma.",
        )
        parser.add_argument(
            "--reiniciar-2fa",
            action="store_true",
            help="Borra el secreto TOTP para que se configure de nuevo.",
        )

    def handle(self, *args, **options):
        email = (options["email"] or "").strip().lower()
        if not email:
            raise CommandError("El correo es obligatorio.")

        usuario = Usuario.objects.filter(email__iexact=email).first()
        if usuario is None:
            raise CommandError("No existe una cuenta con ese correo.")
        if usuario.rol != Rol.ADMIN_PLATAFORMA:
            raise CommandError("La cuenta no es un Administrador de plataforma.")
        if not usuario.is_active:
            raise CommandError(
                "La cuenta está inactiva; reactívala antes de restablecerla."
            )

        try:
            _, token = services.solicitar_restablecimiento(
                usuario,
                usuario,
                enviar_correo=False,
            )
        except services.CuentaInactivaRestablecimiento as exc:
            raise CommandError(exc.mensaje) from exc

        if options["reiniciar_2fa"]:
            services.restablecer_segundo_factor(usuario, usuario)
            self.stdout.write(
                self.style.WARNING(
                    "Segundo factor reiniciado: se configurará de nuevo al "
                    "iniciar sesión."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Enlace de restablecimiento (72 horas, un solo uso):\n"
                f"/invitacion/{token}/"
            )
        )
