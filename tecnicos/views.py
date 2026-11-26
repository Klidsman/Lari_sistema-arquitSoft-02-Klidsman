"""Vistas de técnicos del tenant."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import services
from .forms import TecnicoEdicionForm, TecnicoForm


def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje,
        status=status,
        content_type="text/html; charset=utf-8",
    )


def _primer_error(formulario) -> str:
    for errores in formulario.errors.values():
        if errores:
            return errores[0]
    return "Revisa los datos ingresados"


def _tenant_o_error(request):
    try:
        return services.validar_cuenta_tenant(request.usuario), None
    except (services.PermisoDenegado, services.TenantSuspendido) as exc:
        return None, _respuesta(str(exc), 403)


def _tecnico_o_error(tenant, tecnico_id):
    try:
        return services.obtener_tecnico(tenant, tecnico_id), None
    except services.NoEncontrado as exc:
        return None, _respuesta(str(exc), 404)


@login_required
@require_GET
def listar_tecnicos(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    estado = request.GET.get("estado", "todos")
    if estado not in {"todos", "activos", "desactivados"}:
        estado = "todos"

    tecnicos = services.buscar_tecnicos(
        tenant,
        request.GET.get("q", ""),
        estado=estado,
    )
    pagina = Paginator(tecnicos, 50).get_page(request.GET.get("page"))

    return render(
        request,
        "tecnicos/tecnicos_lista.html",
        {
            "pagina": pagina,
            "tecnicos": pagina.object_list,
            "q": request.GET.get("q", ""),
            "estado": estado,
        },
    )


@login_required
@require_GET
def stock_actual_tecnicos(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    q = request.GET.get("q", "")
    tecnicos = services.listar_tecnicos_con_stock(tenant, q=q)
    resumen = services.resumen_stock_actual(tenant, q=q)
    pagina = Paginator(tecnicos, 50).get_page(request.GET.get("page"))

    return render(
        request,
        "tecnicos/stock_actual.html",
        {
            "pagina": pagina,
            "tecnicos": pagina.object_list,
            "q": q,
            "resumen": resumen,
        },
    )


@login_required
@require_GET
def detalle_stock_tecnico(request, tecnico_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    tecnico, error = _tecnico_o_error(tenant, tecnico_id)
    if error is not None:
        return error

    filas = services.stock_actual_tecnico(tecnico, solo_con_stock=True)
    resumen = filas.aggregate(
        materiales=Count("material", distinct=True),
        unidades=Sum("cantidad", default=0),
    )
    series = services.series_en_custodia(tecnico)
    return render(
        request,
        "tecnicos/stock_tecnico.html",
        {
            "tecnico": tecnico,
            "filas": filas,
            "resumen": resumen,
            "series": series,
        },
    )


@login_required
@require_GET
def buscar_tecnicos_htmx(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    try:
        limite = int(request.GET.get("limit", 20))
    except (TypeError, ValueError):
        limite = 20
    limite = max(1, min(50, limite))

    tecnicos = services.buscar_tecnicos(
        tenant,
        request.GET.get("q", ""),
        solo_activos=True,
    )[:limite]

    return render(
        request,
        "tecnicos/_filas_busqueda.html",
        {"tecnicos": tecnicos},
    )


@login_required
@require_http_methods(["GET", "POST"])
def crear_tecnico(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    if request.method == "POST":
        formulario = TecnicoForm(request.POST)
        contexto = {"form": formulario}

        if formulario.is_valid():
            try:
                tecnico = services.crear_tecnico(
                    formulario.cleaned_data,
                    request.usuario,
                )
            except services.NifDuplicado as exc:
                return render(
                    request,
                    "tecnicos/tecnico_form.html",
                    {"error": str(exc), **contexto},
                    status=409,
                )
            except services.ValidacionTecnico as exc:
                return render(
                    request,
                    "tecnicos/tecnico_form.html",
                    {"error": str(exc), **contexto},
                    status=400,
                )
            except (services.PermisoDenegado, services.TenantSuspendido) as exc:
                return _respuesta(str(exc), 403)

            messages.success(request, "Técnico registrado")
            return redirect("detalle_tecnico", tecnico_id=tecnico.pk)

        return render(
            request,
            "tecnicos/tecnico_form.html",
            {"error": _primer_error(formulario), **contexto},
            status=400,
        )

    return render(
        request,
        "tecnicos/tecnico_form.html",
        {"form": TecnicoForm()},
    )


@login_required
@require_GET
def detalle_tecnico(request, tecnico_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    tecnico, error = _tecnico_o_error(tenant, tecnico_id)
    if error is not None:
        return error

    return render(
        request,
        "tecnicos/tecnico_detalle.html",
        {
            "tecnico": tecnico,
            "stock": services.stock_actual_tecnico(tecnico),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def editar_tecnico(request, tecnico_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    tecnico, error = _tecnico_o_error(tenant, tecnico_id)
    if error is not None:
        return error

    if request.method == "POST":
        if "nif" in request.POST:
            return render(
                request,
                "tecnicos/tecnico_form.html",
                {
                    "error": "El NIF no se puede cambiar",
                    "form": TecnicoEdicionForm(instance=tecnico),
                    "tecnico": tecnico,
                },
                status=400,
            )
        if "tenant" in request.POST or "tenant_id" in request.POST:
            return render(
                request,
                "tecnicos/tecnico_form.html",
                {
                    "error": "El tenant del técnico no se puede cambiar",
                    "form": TecnicoEdicionForm(instance=tecnico),
                    "tecnico": tecnico,
                },
                status=400,
            )

        formulario = TecnicoEdicionForm(request.POST, instance=tecnico)
        contexto = {"form": formulario, "tecnico": tecnico}

        if formulario.is_valid():
            try:
                services.actualizar_tecnico(
                    tecnico,
                    formulario.cleaned_data,
                    request.usuario,
                )
            except services.ValidacionTecnico as exc:
                return render(
                    request,
                    "tecnicos/tecnico_form.html",
                    {"error": str(exc), **contexto},
                    status=400,
                )
            except (services.PermisoDenegado, services.TenantSuspendido) as exc:
                return _respuesta(str(exc), 403)
            except services.NoEncontrado as exc:
                return _respuesta(str(exc), 404)

            messages.success(request, "Técnico actualizado")
            return redirect("detalle_tecnico", tecnico_id=tecnico.pk)

        return render(
            request,
            "tecnicos/tecnico_form.html",
            {"error": _primer_error(formulario), **contexto},
            status=400,
        )

    return render(
        request,
        "tecnicos/tecnico_form.html",
        {"form": TecnicoEdicionForm(instance=tecnico), "tecnico": tecnico},
    )


@login_required
@require_POST
def desactivar_tecnico(request, tecnico_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    tecnico, error = _tecnico_o_error(tenant, tecnico_id)
    if error is not None:
        return error

    services.desactivar_tecnico(tecnico, request.usuario)
    messages.success(request, "Técnico desactivado")
    return redirect("detalle_tecnico", tecnico_id=tecnico.pk)


@login_required
@require_POST
def reactivar_tecnico(request, tecnico_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    tecnico, error = _tecnico_o_error(tenant, tecnico_id)
    if error is not None:
        return error

    services.reactivar_tecnico(tecnico, request.usuario)
    messages.success(request, "Técnico reactivado")
    return redirect("detalle_tecnico", tecnico_id=tecnico.pk)
