"""Genera el respaldo de PostgreSQL exigido antes del cierre mensual."""

import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = (
        "Genera un respaldo de PostgreSQL bajo backups/ y devuelve la "
        "referencia relativa que usa el cierre mensual."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            default="",
            help=(
                "Nombre relativo bajo backups/. Por defecto se genera con "
                "la fecha y hora actual."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo calcula y muestra la referencia, sin ejecutar pg_dump.",
        )

    def handle(self, *args, **options):
        datos = connection.settings_dict
        nombre = (options["salida"] or "").strip()
        if not nombre:
            marca = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre = f"{datos['NAME']}_{marca}.sql"
        if not nombre.startswith("backups/"):
            nombre = f"backups/{nombre}"

        ruta = Path(settings.BASE_DIR) / nombre
        if options["dry_run"]:
            self.stdout.write(nombre)
            return

        ruta.parent.mkdir(parents=True, exist_ok=True)
        comando = [
            "pg_dump",
            "-h",
            str(datos.get("HOST") or "localhost"),
            "-p",
            str(datos.get("PORT") or "5432"),
            "-U",
            str(datos.get("USER") or ""),
            "-d",
            str(datos.get("NAME") or ""),
            "-f",
            str(ruta),
        ]
        entorno = os.environ.copy()
        if datos.get("PASSWORD"):
            entorno["PGPASSWORD"] = str(datos["PASSWORD"])
        try:
            subprocess.run(comando, check=True, env=entorno)
        except FileNotFoundError as exc:
            raise CommandError(
                "pg_dump no está disponible en el PATH"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(
                "pg_dump falló al generar el respaldo"
            ) from exc

        self.stdout.write(self.style.SUCCESS(nombre))
