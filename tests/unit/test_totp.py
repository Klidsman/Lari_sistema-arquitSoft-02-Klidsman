"""Pruebas unitarias de TOTP."""

import pyotp
import pytest

from acceso.totp import (
    cifrar_secreto,
    descifrar_secreto,
    generar_token,
    hash_token,
    verificar_codigo,
)


@pytest.mark.django_db
def test_cifrado_y_descifrado(usuario_admin):
    secreto = "JBSWY3DPEHPK3PXP"
    token = cifrar_secreto(secreto)

    assert token != secreto
    assert descifrar_secreto(token) == secreto


@pytest.mark.django_db
def test_secreto_corrupto(usuario_admin):
    with pytest.raises(ValueError):
        descifrar_secreto("token-invalido")


@pytest.mark.django_db
def test_codigo_totp_valido_e_invalido(usuario_admin):
    secreto = "JBSWY3DPEHPK3PXP"
    usuario_admin.secreto_totp = cifrar_secreto(secreto)
    usuario_admin.save(update_fields=["secreto_totp"])

    assert verificar_codigo(usuario_admin, pyotp.TOTP(secreto).now())
    assert not verificar_codigo(usuario_admin, "000000")


def test_token_hash():
    token = generar_token()
    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64
