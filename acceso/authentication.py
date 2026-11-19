"""Backend de autenticación por correo electrónico."""

from django.contrib.auth.backends import ModelBackend

from .models import Usuario


class EmailBackend(ModelBackend):
    """Autentica con email en lugar de username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or password is None:
            return None

        try:
            usuario = Usuario.objects.get(email__iexact=email.strip())
        except Usuario.DoesNotExist:
            return None

        if usuario.check_password(password):
            return usuario
        return None

    def user_can_authenticate(self, user):
        # La vista de login distingue cuenta inactiva de credenciales incorrectas.
        return True
