"""Pruebas del comando crear_admin_plataforma."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from acceso.models import Invitacion, Rol, Usuario


@pytest.mark.django_db
def test_crear_admin_plataforma():
    salida = StringIO()
    call_command("crear_admin_plataforma", "--email", "admin@lari.local", stdout=salida)

    usuario = Usuario.objects.get(email="admin@lari.local")
    assert usuario.rol == Rol.ADMIN_PLATAFORMA
    assert usuario.is_active is False
    assert usuario.is_staff is False
    assert usuario.is_superuser is False
    assert usuario.tenant is None
    assert usuario.region is None
    assert Invitacion.objects.filter(usuario=usuario).count() == 1
    assert "/invitacion/" in salida.getvalue()


@pytest.mark.django_db
def test_crear_admin_plataforma_email_duplicado():
    call_command("crear_admin_plataforma", "--email", "admin@lari.local", stdout=StringIO())

    with pytest.raises(CommandError):
        call_command("crear_admin_plataforma", "--email", "admin@lari.local", stdout=StringIO())
