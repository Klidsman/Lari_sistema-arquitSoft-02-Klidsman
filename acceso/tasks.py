"""Tareas Celery de acceso."""

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_correo_invitacion(self, invitacion_id: int, token: str):
    """Envía el enlace de invitación y registra el resultado sin guardar el token."""
    from .models import Invitacion

    try:
        invitacion = Invitacion.objects.get(pk=invitacion_id)
    except Invitacion.DoesNotExist:
        return

    if invitacion.usada_en or invitacion.revocada_en:
        return

    enlace = f"{settings.BASE_URL.rstrip('/')}/invitacion/{token}/"

    try:
        send_mail(
            subject="Invitación a Lari",
            message=(
                "Has sido invitado a Lari. "
                f"Define tu contraseña en: {enlace}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitacion.correo],
            fail_silently=False,
        )
    except Exception as exc:
        Invitacion.objects.filter(pk=invitacion_id).update(
            ultimo_error=str(exc)[:500]
        )
        raise self.retry(exc=exc)

    Invitacion.objects.filter(pk=invitacion_id).update(
        enviada_en=timezone.now(),
        ultimo_error="",
    )
