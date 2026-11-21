"""Enlaces de navegación con estado activo según la ruta actual."""

from django import template
from django.urls import reverse
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def enlace_nav(context, nombre_url, texto, prefijo=None, excluir=None):
    """Renderiza un enlace de la barra lateral y lo marca si está activo."""
    request = context.get("request")
    ruta = getattr(request, "path", "")
    url = reverse(nombre_url)

    if prefijo:
        activo = ruta.startswith(prefijo) and not (
            excluir and ruta.startswith(excluir)
        )
    else:
        activo = ruta == url

    if activo:
        return format_html(
            '<a class="shell-enlace shell-enlace--activo" '
            'href="{}" aria-current="page">{}</a>',
            url,
            texto,
        )

    return format_html(
        '<a class="shell-enlace" href="{}">{}</a>',
        url,
        texto,
    )
