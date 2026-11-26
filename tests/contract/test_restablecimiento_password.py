"""Contrato de restablecimiento de contraseña y recuperación del 2FA."""

import re
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from acceso.models import Invitacion, Rol, TipoInvitacion, Usuario
from acceso.services import (
    CuentaInactivaRestablecimiento,
    InvitacionInvalida,
    aceptar_invitacion,
    solicitar_restablecimiento,
)
from acceso.tokens import hash_token
from auditoria.models import RegistroCambio


def _token_de(respuesta) -> str:
    coincidencia = re.search(r"/invitacion/([^/\"<\s]+)/", respuesta.content.decode())
    assert coincidencia, "La respuesta no contiene el enlace de invitación"
    return coincidencia.group(1)


@pytest.mark.django_db
def test_admin_genera_enlace_de_restablecimiento(
    cliente_autenticado, usuario_admin, usuario_tenant, django_capture_on_commit_callbacks
):
    version_anterior = usuario_tenant.version_sesion

    with django_capture_on_commit_callbacks(execute=True):
        respuesta = cliente_autenticado.post(
            reverse("restablecer_password", args=[usuario_tenant.pk]),
        )

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "Restablecer contraseña" in contenido
    assert usuario_tenant.email in contenido
    assert "no-store" in respuesta["Cache-Control"]

    invitacion = Invitacion.objects.get(usuario=usuario_tenant)
    assert invitacion.tipo == TipoInvitacion.RESTABLECIMIENTO
    assert invitacion.token_hash == hash_token(_token_de(respuesta))
    assert invitacion.usada_en is None
    assert invitacion.revocada_en is None

    usuario_tenant.refresh_from_db()
    assert usuario_tenant.version_sesion == version_anterior + 1
    assert RegistroCambio.objects.filter(
        entidad="Usuario",
        entidad_id=usuario_tenant.pk,
        campo="acceso_cuenta",
        valor_nuevo="restablecimiento_solicitado",
    ).exists()


@pytest.mark.django_db
def test_solo_admin_puede_restablecer(cliente_tenant, usuario_tenant):
    respuesta = cliente_tenant.post(
        reverse("restablecer_password", args=[usuario_tenant.pk]),
    )

    assert respuesta.status_code == 403
    assert not Invitacion.objects.filter(usuario=usuario_tenant).exists()


@pytest.mark.django_db
def test_restablecer_solo_acepta_post(cliente_autenticado, usuario_tenant):
    respuesta = cliente_autenticado.get(
        reverse("restablecer_password", args=[usuario_tenant.pk]),
    )

    assert respuesta.status_code == 405


@pytest.mark.django_db
def test_no_restablece_cuenta_inactiva(cliente_autenticado, usuario_tenant):
    usuario_tenant.is_active = False
    usuario_tenant.save(update_fields=["is_active"])

    respuesta = cliente_autenticado.post(
        reverse("restablecer_password", args=[usuario_tenant.pk]),
    )

    assert respuesta.status_code == 409
    assert "Reactiva la cuenta" in respuesta.content.decode()
    assert not Invitacion.objects.filter(usuario=usuario_tenant).exists()


@pytest.mark.django_db
def test_admin_no_se_restablece_a_si_mismo(
    cliente_autenticado, usuario_admin
):
    respuesta = cliente_autenticado.post(
        reverse("restablecer_password", args=[usuario_admin.pk]),
    )

    assert respuesta.status_code == 400
    assert "comando de consola" in respuesta.content.decode()
    assert not Invitacion.objects.filter(usuario=usuario_admin).exists()


@pytest.mark.django_db
def test_aceptar_restablecimiento_conserva_cuenta_y_2fa(
    usuario_admin, usuario_tenant, django_capture_on_commit_callbacks
):
    usuario_tenant.secreto_totp = "secreto-cifrado"
    usuario_tenant.segundo_factor_habilitado = True
    usuario_tenant.save(
        update_fields=["secreto_totp", "segundo_factor_habilitado"]
    )
    version_anterior = usuario_tenant.version_sesion

    with django_capture_on_commit_callbacks(execute=True):
        _, token = solicitar_restablecimiento(usuario_tenant, usuario_admin)

    aceptar_invitacion(token, "ClaveNueva12345")

    usuario_tenant.refresh_from_db()
    assert usuario_tenant.is_active is True
    assert usuario_tenant.check_password("ClaveNueva12345")
    assert usuario_tenant.rol == Rol.USUARIO_TENANT
    assert usuario_tenant.tenant_id is not None
    assert usuario_tenant.secreto_totp == "secreto-cifrado"
    assert usuario_tenant.segundo_factor_habilitado is True
    assert usuario_tenant.version_sesion == version_anterior + 2

    invitacion = Invitacion.objects.get(usuario=usuario_tenant)
    assert invitacion.usada_en is not None
    assert RegistroCambio.objects.filter(
        entidad="Usuario",
        entidad_id=usuario_tenant.pk,
        campo="acceso_cuenta",
        valor_nuevo="restablecimiento_completado",
    ).exists()


@pytest.mark.django_db
def test_restablecimiento_invalida_sesion_abierta(
    cliente_tenant, usuario_admin, usuario_tenant, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        _, token = solicitar_restablecimiento(usuario_tenant, usuario_admin)

    aceptar_invitacion(token, "ClaveNueva12345")

    respuesta = cliente_tenant.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/login/")


@pytest.mark.django_db
def test_token_de_restablecimiento_vencido(usuario_admin, usuario_tenant):
    invitacion = Invitacion.objects.create(
        usuario=usuario_tenant,
        tipo=TipoInvitacion.RESTABLECIMIENTO,
        token_hash=hash_token("token-vencido"),
        correo=usuario_tenant.email,
        expira_en=timezone.now() - timedelta(minutes=1),
        creada_por=usuario_admin,
    )

    with pytest.raises(InvitacionInvalida):
        aceptar_invitacion("token-vencido", "ClaveNueva12345")

    assert invitacion.usada_en is None


@pytest.mark.django_db
def test_invitacion_de_alta_no_restablece_cuenta_activa(
    usuario_admin, usuario_tenant
):
    Invitacion.objects.create(
        usuario=usuario_tenant,
        tipo=TipoInvitacion.ALTA,
        token_hash=hash_token("token-alta"),
        correo=usuario_tenant.email,
        expira_en=timezone.now() + timedelta(hours=2),
        creada_por=usuario_admin,
    )

    with pytest.raises(InvitacionInvalida):
        aceptar_invitacion("token-alta", "ClaveNueva12345")


@pytest.mark.django_db
def test_reenviar_invitacion_de_cuenta_inactiva(
    cliente_autenticado, tenant, usuario_admin, django_capture_on_commit_callbacks
):
    usuario = Usuario.objects.create_user(
        email="pendiente@lari.local",
        password=None,
        rol=Rol.USUARIO_TENANT,
        tenant=tenant,
        is_active=False,
    )
    anterior = Invitacion.objects.create(
        usuario=usuario,
        token_hash=hash_token("token-anterior"),
        correo=usuario.email,
        expira_en=timezone.now() + timedelta(hours=2),
        creada_por=usuario_admin,
    )

    with django_capture_on_commit_callbacks(execute=True):
        respuesta = cliente_autenticado.post(
            reverse("reenviar_invitacion_cuenta", args=[usuario.pk]),
        )

    assert respuesta.status_code == 200
    assert "Invitación reenviada" in respuesta.content.decode()

    anterior.refresh_from_db()
    assert anterior.revocada_en is not None
    nuevo = Invitacion.objects.get(
        usuario=usuario,
        token_hash=hash_token(_token_de(respuesta)),
    )
    assert nuevo.tipo == TipoInvitacion.ALTA


@pytest.mark.django_db
def test_reenviar_no_aplica_a_cuenta_activa(cliente_autenticado, usuario_tenant):
    respuesta = cliente_autenticado.post(
        reverse("reenviar_invitacion_cuenta", args=[usuario_tenant.pk]),
    )

    assert respuesta.status_code == 409
    assert "ya está activa" in respuesta.content.decode()


@pytest.mark.django_db
def test_comando_restablece_admin_e_invalida_sesiones(usuario_admin):
    version_anterior = usuario_admin.version_sesion
    salida = StringIO()

    call_command(
        "restablecer_admin_plataforma",
        email=usuario_admin.email,
        stdout=salida,
    )

    texto = salida.getvalue()
    assert "/invitacion/" in texto
    assert "72 horas" in texto

    usuario_admin.refresh_from_db()
    assert usuario_admin.version_sesion == version_anterior + 1
    assert Invitacion.objects.filter(
        usuario=usuario_admin,
        tipo=TipoInvitacion.RESTABLECIMIENTO,
    ).exists()


@pytest.mark.django_db
def test_comando_reinicia_2fa(usuario_admin):
    usuario_admin.secreto_totp = "secreto-cifrado"
    usuario_admin.segundo_factor_habilitado = True
    usuario_admin.save(
        update_fields=["secreto_totp", "segundo_factor_habilitado"]
    )

    call_command(
        "restablecer_admin_plataforma",
        email=usuario_admin.email,
        reiniciar_2fa=True,
        stdout=StringIO(),
    )

    usuario_admin.refresh_from_db()
    assert usuario_admin.secreto_totp == ""
    assert usuario_admin.segundo_factor_habilitado is False
    assert RegistroCambio.objects.filter(
        entidad="Usuario",
        entidad_id=usuario_admin.pk,
        campo="segundo_factor",
        valor_nuevo="reiniciado",
    ).exists()


@pytest.mark.django_db
def test_comando_rechaza_cuenta_que_no_es_admin(usuario_tenant):
    with pytest.raises(CommandError):
        call_command(
            "restablecer_admin_plataforma",
            email=usuario_tenant.email,
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_servicio_rechaza_cuenta_inactiva(usuario_admin, usuario_tenant):
    usuario_tenant.is_active = False
    usuario_tenant.save(update_fields=["is_active"])

    with pytest.raises(CuentaInactivaRestablecimiento):
        solicitar_restablecimiento(usuario_tenant, usuario_admin)
