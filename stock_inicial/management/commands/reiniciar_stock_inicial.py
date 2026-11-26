"""Reinicia el stock inicial de un tenant (solo implementación)."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from acceso.models import Usuario
from stock_inicial import services
from tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Reinicia el stock inicial de un tenant. Requiere --confirmar y "
        "PERMITIR_REINICIO_STOCK_INICIAL=True."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            required=True,
            help="Código del tenant, por ejemplo TEN-004.",
        )
        parser.add_argument(
            "--usuario",
            required=True,
            help="Email del Administrador de plataforma.",
        )
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma el borrado y descuento de stock.",
        )

    def handle(self, *args, **options):
        if not settings.PERMITIR_REINICIO_STOCK_INICIAL:
            raise CommandError(
                "El reinicio del stock inicial está deshabilitado"
            )

        codigo = (options["tenant"] or "").strip()
        tenant = Tenant.objects.filter(codigo__iexact=codigo).first()
        if tenant is None:
            raise CommandError("El tenant no existe")

        email = (options["usuario"] or "").strip().lower()
        actor = Usuario.objects.filter(email__iexact=email).first()
        if actor is None:
            raise CommandError("El usuario no existe")

        if not options["confirmar"]:
            self.stdout.write(
                self.style.WARNING(
                    "Reinicio no ejecutado: falta --confirmar."
                )
            )
            return

        try:
            services.reiniciar_stock_inicial(tenant, actor)
        except services.ValidacionStockInicial as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Stock inicial reiniciado para {tenant.codigo}."
            )
        )
