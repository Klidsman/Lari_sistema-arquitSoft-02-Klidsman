"""Reenvío de invitaciones a nivel de servicio."""

import pytest

from acceso.models import Invitacion, Rol, Usuario
from acceso.services import InvitacionInvalida, aceptar_invitacion, enviar_invitacion
from acceso.tokens import hash_token


@pytest.mark.django_db
def test_reenvio_invalida_token_anterior(
    tenant, usuario_admin, monkeypatch, django_capture_on_commit_callbacks
):
    usuario = Usuario.objects.create_user(
        email="invitado@lari.local",
        password=None,
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=False,
    )
    tokens = iter(["token-viejo", "token-nuevo"])
    monkeypatch.setattr("acceso.services.generar_token", lambda: next(tokens))

    with django_capture_on_commit_callbacks(execute=True):
        enviar_invitacion(usuario, usuario_admin)
        segunda = enviar_invitacion(usuario, usuario_admin)

    vieja = Invitacion.objects.get(token_hash=hash_token("token-viejo"))
    assert vieja.revocada_en is not None
    assert segunda.revocada_en is None

    with pytest.raises(InvitacionInvalida):
        aceptar_invitacion("token-viejo", "ClaveSegura12345")

    aceptar_invitacion("token-nuevo", "ClaveSegura12345")

    usuario.refresh_from_db()
    assert usuario.check_password("ClaveSegura12345")
