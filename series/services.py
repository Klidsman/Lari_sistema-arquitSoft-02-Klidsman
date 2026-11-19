"""Servicios de series."""

import re

from django.conf import settings

from .models import EstadoSerie, Serie


class SerieInvalida(Exception):
    pass


class SerieDuplicada(Exception):
    pass


class SerieYaExiste(Exception):
    mensaje = "La serie ya está registrada en el sistema"


GRUPO_SERIE = re.compile(r"[A-Za-z0-9]{12}")
CARACTER_ALFANUMERICO = re.compile(r"[A-Za-z0-9]")


def extraer_numeros(texto) -> list[str]:
    """Separa un bloque de series por líneas, guiones o espacios.

    Si una línea contiene varias series de 12 caracteres separadas por
    caracteres no alfanuméricos (por ejemplo `` - ``), se devuelven por
    separado. Si la línea no está compuesta solo por series válidas y
    separadores, se conserva completa para que la validación la marque como
    inválida en lugar de descartarla.
    """
    resultado = []
    for linea in (texto or "").splitlines():
        linea = linea.strip()
        if not linea:
            continue

        grupos = GRUPO_SERIE.findall(linea)
        resto = GRUPO_SERIE.sub("", linea)
        if grupos and not CARACTER_ALFANUMERICO.search(resto):
            resultado.extend(grupos)
        else:
            resultado.append(linea)
    return resultado


def normalizar_numero(numero) -> str:
    return re.sub(r"\s+", "", numero or "").upper()


def validar_numero(numero) -> str:
    numero = normalizar_numero(numero)
    if not re.match(settings.SERIE_PATRON, numero):
        raise SerieInvalida("La serie debe tener 12 caracteres alfanuméricos")
    return numero


def series_existentes(numeros):
    numeros = [normalizar_numero(numero) for numero in numeros]
    return set(
        Serie.objects.filter(numero__in=numeros).values_list("numero", flat=True)
    )


def crear_serie(
    tenant,
    region,
    material,
    numero,
    lote,
    actor,
    estado=EstadoSerie.DISPONIBLE,
    tecnico=None,
    asignada_en=None,
) -> Serie:
    numero = validar_numero(numero)

    if estado == EstadoSerie.ASIGNADA:
        if tecnico is None or asignada_en is None:
            raise SerieInvalida(
                "Una serie asignada requiere técnico y fecha de asignación"
            )
    elif tecnico is not None or asignada_en is not None:
        raise SerieInvalida(
            "Una serie no asignada no puede tener técnico ni fecha de asignación"
        )

    return Serie.objects.create(
        numero=numero,
        tenant=tenant,
        region=region,
        material=material,
        lote=lote or "",
        estado=estado,
        tecnico=tecnico,
        asignada_en=asignada_en,
        creado_por=actor,
    )
