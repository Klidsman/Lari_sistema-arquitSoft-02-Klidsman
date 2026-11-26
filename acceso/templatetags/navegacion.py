"""Enlaces de navegación con estado activo según la ruta actual."""

from django import template
from django.urls import reverse
from django.utils.html import format_html

register = template.Library()

# Iconos permitidos en la navegación. Se mantiene una lista explícita para no
# inyectar nombres arbitrarios en el sprite SVG.
ICONOS = {
    "inicio",
    "material",
    "tecnicos",
    "recojo",
    "stock",
    "inventario",
    "asignacion",
    "traspaso",
    "conciliacion",
    "devolucion",
    "baja",
    "registro",
    "reportes",
    "bandeja",
    "regiones",
    "tenants",
    "cuentas",
    "auditoria",
    "perfil",
}


def _icono(nombre):
    if nombre not in ICONOS:
        return ""
    return format_html(
        '<svg class="icono" aria-hidden="true" focusable="false">'
        '<use href="#i-{}"></use></svg>',
        nombre,
    )


@register.simple_tag(takes_context=True)
def enlace_nav(
    context,
    nombre_url,
    texto,
    prefijo=None,
    excluir=None,
    icono=None,
):
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
            'href="{}" aria-current="page">{}'
            '<span class="shell-enlace__texto">{}</span></a>',
            url,
            _icono(icono),
            texto,
        )

    return format_html(
        '<a class="shell-enlace" href="{}">{}'
        '<span class="shell-enlace__texto">{}</span></a>',
        url,
        _icono(icono),
        texto,
    )
