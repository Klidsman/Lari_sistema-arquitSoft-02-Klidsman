"""Segundo factor TOTP."""

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .tokens import generar_token, hash_token  # noqa: F401


def _fernet() -> Fernet:
    clave = settings.TOTP_ENCRYPTION_KEY
    if not clave:
        raise ImproperlyConfigured("Falta TOTP_ENCRYPTION_KEY.")
    try:
        return Fernet(clave.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured("TOTP_ENCRYPTION_KEY no es válida.") from exc


def cifrar_secreto(secreto: str) -> str:
    if not secreto:
        raise ValueError("El secreto TOTP es obligatorio.")
    return _fernet().encrypt(secreto.encode("utf-8")).decode("utf-8")


def descifrar_secreto(token: str) -> str:
    if not token:
        raise ValueError("El secreto TOTP es obligatorio.")
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("El secreto TOTP no se pudo descifrar.") from exc


def generar_uri_otpauth(usuario) -> str:
    secreto = descifrar_secreto(usuario.secreto_totp)
    return pyotp.TOTP(secreto).provisioning_uri(
        name=usuario.email,
        issuer_name="Lari",
    )


def secreto_agrupado(secreto: str) -> str:
    """Agrupa la clave en bloques de cuatro para dictarla o teclearla."""
    limpio = (secreto or "").replace(" ", "").upper()
    return " ".join(limpio[i : i + 4] for i in range(0, len(limpio), 4))


def contexto_configuracion(usuario) -> dict:
    """Datos que la pantalla de alta necesita para mostrar la clave."""
    if not usuario.secreto_totp:
        return {}

    secreto = descifrar_secreto(usuario.secreto_totp)
    return {
        "secreto": secreto,
        "secreto_agrupado": secreto_agrupado(secreto),
        "uri": generar_uri_otpauth(usuario),
        "cuenta_totp": usuario.email,
    }


def verificar_codigo(usuario, codigo: str) -> bool:
    if not codigo:
        return False
    secreto = descifrar_secreto(usuario.secreto_totp)
    return pyotp.TOTP(secreto).verify(codigo, valid_window=1)
