"""Integración de invitaciones y aceptación."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from acceso.models import Invitacion, Rol, Usuario
from acceso.services import InvitacionInvalida, aceptar_invitacion, enviar_invitacion
from acceso.tokens import hash_token
from auditoria.models import RegistroCambio


@pytest.mark.django_db
def test_enviar_invitacion_guarda_hash_y_vigencia(
    usuario_tenant, usuario_admin, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        invitacion = enviar_invitacion(usuario_tenant, usuario_admin)

    assert len(invitacion.token_hash) == 64
    assert all(caracter in "0123456789abcdef" for caracter in invitacion.token_hash)
    assert invitacion.token_hash != "token"
    assert abs(
        invitacion.expira_en - (timezone.now() + timedelta(hours=72))
    ) < timedelta(minutes=1)
    invitacion.refresh_from_db()
    assert invitacion.enviada_en is not None
    assert invitacion.ultimo_error == ""


@pytest.mark.django_db
def test_enviar_invitacion_revoca_pendientes(
    usuario_tenant, usuario_admin, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        primera = enviar_invitacion(usuario_tenant, usuario_admin)
        segunda = enviar_invitacion(usuario_tenant, usuario_admin)

    primera.refresh_from_db()
    assert primera.revocada_en is not None
    assert segunda.revocada_en is None


@pytest.mark.django_db
def test_enviar_invitacion_registra_error_de_correo(
    usuario_tenant, usuario_admin, monkeypatch, django_capture_on_commit_callbacks
):
    def correo_que_falla(*args, **kwargs):
        raise RuntimeError("servidor de correo no disponible")

    monkeypatch.setattr("acceso.tasks.send_mail", correo_que_falla)

    with django_capture_on_commit_callbacks(execute=True):
        invitacion = enviar_invitacion(usuario_tenant, usuario_admin)

    invitacion.refresh_from_db()
    assert invitacion.enviada_en is None
    assert "servidor de correo" in invitacion.ultimo_error


@pytest.mark.django_db
def test_aceptar_invitacion_activa_cuenta_y_audita(tenant, usuario_admin):
    usuario = Usuario.objects.create_user(
        email="invitado@lari.local",
        password=None,
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=False,
    )
    invitacion = Invitacion.objects.create(
        usuario=usuario,
        token_hash=hash_token("token-valido"),
        correo=usuario.email,
        expira_en=timezone.now() + timedelta(hours=2),
        creada_por=usuario_admin,
    )

    aceptar_invitacion("token-valido", "ClaveSegura12345")

    usuario.refresh_from_db()
    invitacion.refresh_from_db()

    assert usuario.is_active is True
    assert usuario.check_password("ClaveSegura12345")
    assert invitacion.usada_en is not None
    assert RegistroCambio.objects.filter(
        entidad="Usuario", entidad_id=usuario.pk, campo="is_active"
    ).exists()


@pytest.mark.django_db
def test_aceptar_invitacion_password_debil(tenant, usuario_admin):
    usuario = Usuario.objects.create_user(
        email="invitado@lari.local",
        password=None,
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=False,
    )
    Invitacion.objects.create(
        usuario=usuario,
        token_hash=hash_token("token-valido"),
        correo=usuario.email,
        expira_en=timezone.now() + timedelta(hours=2),
        creada_por=usuario_admin,
    )

    with pytest.raises(ValidationError):
        aceptar_invitacion("token-valido", "123456789012")

    usuario.refresh_from_db()
    assert usuario.is_active is False


@pytest.mark.django_db
def test_aceptar_invitacion_dos_veces(tenant, usuario_admin):
    usuario = Usuario.objects.create_user(
        email="invitado@lari.local",
        password=None,
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=False,
    )
    Invitacion.objects.create(
        usuario=usuario,
        token_hash=hash_token("token-valido"),
        correo=usuario.email,
        expira_en=timezone.now() + timedelta(hours=2),
        creada_por=usuario_admin,
    )

    aceptar_invitacion("token-valido", "ClaveSegura12345")

    with pytest.raises(InvitacionInvalida):
        aceptar_invitacion("token-valido", "ClaveSegura12345")
