"""Tokens de invitación: generación y almacenamiento seguro."""

import hashlib
import secrets


def generar_token() -> str:
    """Token aleatorio de alta entropía para invitaciones."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash SHA-256 en hexadecimal (64 caracteres) del token original."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
