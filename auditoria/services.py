"""Servicios de auditoría compartida."""

import json
from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.dateparse import parse_date

from .models import RegistroCambio

CAMPOS_PROHIBIDOS = {
    "password",
    "contraseña",
    "contrasena",
    "token",
    "token_hash",
    "secreto_totp",
    "secret",
    "totp",
    "secret_totp",
}


def serializar_valor(valor) -> str:
    """Convierte un valor de dominio a texto legible para la auditoría."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "True" if valor else "False"
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (dict, list, tuple)):
        return json.dumps(valor, ensure_ascii=False, sort_keys=True, default=str)
    return str(valor)


def _resolver_tenant(entidad: str, entidad_id: int, usuario):
    """Obtiene el tenant de la entidad o del actor, sin confiar en el cliente."""
    if getattr(usuario, "tenant_id", None):
        return usuario.tenant

    if entidad == "Tenant":
        from tenants.models import Tenant

        return Tenant.objects.filter(pk=entidad_id).first()

    return None


def _validar_campo(campo: str) -> None:
    nombre = campo.strip().lower()
    if any(prohibido in nombre for prohibido in CAMPOS_PROHIBIDOS):
        raise ValidationError("No se auditan contraseñas, tokens ni secretos.")


@transaction.atomic
def registrar_cambio(
    entidad: str,
    entidad_id: int,
    campo: str,
    valor_anterior,
    valor_nuevo,
    usuario,
    tenant=None,
):
    """Inserta un registro de auditoría inmutable."""
    if not entidad:
        raise ValidationError("La entidad es obligatoria.")
    if entidad_id is None:
        raise ValidationError("El identificador de la entidad es obligatorio.")
    if usuario is None:
        raise ValidationError("El usuario de la auditoría es obligatorio.")

    _validar_campo(campo)

    return RegistroCambio.objects.create(
        tenant=tenant or _resolver_tenant(entidad, entidad_id, usuario),
        entidad=entidad,
        entidad_id=entidad_id,
        campo=campo,
        valor_anterior=serializar_valor(valor_anterior),
        valor_nuevo=serializar_valor(valor_nuevo),
        usuario=usuario,
    )


def consultar_auditoria(actor, filtros):
    """Devuelve una página de auditoría limitada al alcance del actor."""
    from acceso.services import registros_visibles_para

    registros = (
        registros_visibles_para(actor)
        .select_related("usuario")
        .order_by("-fecha", "-id")
    )

    entidad = filtros.get("entidad")
    if entidad:
        registros = registros.filter(entidad=entidad)

    entidad_id = filtros.get("entidad_id")
    if entidad_id and str(entidad_id).isdigit():
        registros = registros.filter(entidad_id=int(entidad_id))

    usuario = filtros.get("usuario")
    if usuario:
        if "@" in usuario:
            registros = registros.filter(usuario__email__iexact=usuario)
        elif str(usuario).isdigit():
            registros = registros.filter(usuario_id=int(usuario))

    desde = parse_date(filtros.get("desde") or "")
    if desde:
        registros = registros.filter(fecha__date__gte=desde)

    hasta = parse_date(filtros.get("hasta") or "")
    if hasta:
        registros = registros.filter(fecha__date__lte=hasta)

    registro_id = filtros.get("registro_id")
    if registro_id and str(registro_id).isdigit():
        registros = registros.filter(pk=int(registro_id))

    return Paginator(registros, 50).get_page(filtros.get("page"))
