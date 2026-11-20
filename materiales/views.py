"""Vistas del catálogo de materiales."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_GET, require_POST

from acceso.decorators import requiere_rol
from acceso.models import Rol

from . import services
from .forms import MaterialEdicionForm, MaterialForm
from .models import Material


def _primer_error(formulario) -> str:
    for errores in formulario.errors.values():
        if errores:
            return errores[0]
    return "Revisa los datos ingresados"


def _error(request, plantilla, mensaje, status, contexto=None):
    return render(
        request,
        plantilla,
        {"error": mensaje, **(contexto or {})},
        status=status,
    )


def _contexto_lista(request):
    materiales = services.buscar_materiales(
        request.GET.get("q", "")
    ).select_related("creado_por")
    pagina = Paginator(materiales, 50).get_page(request.GET.get("page"))
    return {
        "pagina": pagina,
        "materiales": pagina.object_list,
        "q": request.GET.get("q", ""),
    }


@login_required
@require_GET
def listar_materiales(request):
    return render(
        request,
        "materiales/materiales_lista.html",
        _contexto_lista(request),
    )


@login_required
@require_GET
def buscar_materiales_htmx(request):
    try:
        limite = int(request.GET.get("limit", 20))
    except (TypeError, ValueError):
        limite = 20
    limite = max(1, min(50, limite))

    materiales = services.buscar_materiales(request.GET.get("q", ""))[:limite]

    return render(
        request,
        "materiales/_filas_busqueda.html",
        {"materiales": materiales},
    )


@login_required
@requiere_rol(Rol.RESPONSABLE_ALMACEN)
@require_http_methods(["GET", "POST"])
def crear_material(request):
    if request.method == "POST":
        formulario = MaterialForm(request.POST)
        contexto = {"form": formulario}

        if formulario.is_valid():
            try:
                services.crear_material(
                    formulario.cleaned_data,
                    request.usuario,
                )
            except services.MaterialDuplicado:
                return _error(
                    request,
                    "materiales/material_form.html",
                    services.MaterialDuplicado.mensaje,
                    409,
                    contexto,
                )
            except services.ValidacionMaterial as exc:
                return _error(
                    request,
                    "materiales/material_form.html",
                    str(exc),
                    400,
                    contexto,
                )
            except services.PermisoDenegado as exc:
                return _error(
                    request,
                    "materiales/material_form.html",
                    str(exc),
                    403,
                    contexto,
                )

            messages.success(request, "Material registrado")
            return redirect("listar_materiales")

        return _error(
            request,
            "materiales/material_form.html",
            _primer_error(formulario),
            400,
            contexto,
        )

    return render(
        request,
        "materiales/material_form.html",
        {"form": MaterialForm()},
    )


@login_required
@require_http_methods(["GET", "POST"])
def editar_material(request, material_id):
    material = get_object_or_404(Material.objects.filter(activo=True), pk=material_id)

    if request.method == "POST" and not services.puede_editar_material(
        material, request.usuario
    ):
        return _error(
            request,
            "materiales/material_form.html",
            services.PermisoDenegado.mensaje,
            403,
            {"material": material, "form": MaterialEdicionForm(instance=material)},
        )

    permitir_tipo = services.puede_cambiar_tipo(material)

    if request.method == "POST":
        if "codigo" in request.POST:
            return _error(
                request,
                "materiales/material_form.html",
                "El código no se puede cambiar",
                400,
                {"material": material, "permitir_tipo": permitir_tipo},
            )

        tipo_enviado = request.POST.get("tipo")
        if (
            not permitir_tipo
            and tipo_enviado
            and tipo_enviado != material.tipo
        ):
            return _error(
                request,
                "materiales/material_form.html",
                "El tipo no se puede cambiar: el material tiene movimientos",
                400,
                {
                    "material": material,
                    "permitir_tipo": permitir_tipo,
                    "form": MaterialEdicionForm(
                        request.POST,
                        instance=material,
                        permitir_tipo=permitir_tipo,
                    ),
                },
            )

        formulario = MaterialEdicionForm(
            request.POST,
            instance=material,
            permitir_tipo=permitir_tipo,
        )
        contexto = {
            "form": formulario,
            "material": material,
            "permitir_tipo": permitir_tipo,
        }

        if formulario.is_valid():
            try:
                services.actualizar_material(
                    material,
                    formulario.cleaned_data,
                    request.usuario,
                )
            except services.ValidacionMaterial as exc:
                return _error(
                    request,
                    "materiales/material_form.html",
                    str(exc),
                    400,
                    contexto,
                )
            except services.PermisoDenegado as exc:
                return _error(
                    request,
                    "materiales/material_form.html",
                    str(exc),
                    403,
                    contexto,
                )

            messages.success(request, "Material actualizado")
            return redirect("listar_materiales")

        return _error(
            request,
            "materiales/material_form.html",
            _primer_error(formulario),
            400,
            contexto,
        )

    return render(
        request,
        "materiales/material_form.html",
        {
            "form": MaterialEdicionForm(
                instance=material,
                permitir_tipo=permitir_tipo,
            ),
            "material": material,
            "permitir_tipo": permitir_tipo,
        },
    )


@login_required
@requiere_rol(Rol.RESPONSABLE_ALMACEN)
@require_POST
def dar_de_baja_material(request, material_id):
    material = get_object_or_404(Material, pk=material_id)

    if not material.activo:
        return render(
            request,
            "materiales/materiales_lista.html",
            _contexto_lista(request),
        )

    services.dar_de_baja_material(material, request.usuario)
    messages.success(request, "Material dado de baja")
    return redirect("listar_materiales")
