"""Vistas de logística inversa."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from series.models import EstadoSerie, Serie

from . import services
from .forms import BajaEquipoForm, DevolucionForm
from .models import CausaBaja


def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje, status=status, content_type="text/html; charset=utf-8"
    )


def _tenant_o_error(request):
    try:
        return services.validar_cuenta_tenant(request.usuario), None
    except services.PermisoDenegado as exc:
        return None, _respuesta(str(exc), 403)


def _error(exc):
    if isinstance(
        exc,
        (
            services.NoEncontrado,
            services.BajaNoEncontrada,
            services.ArchivoNoDisponible,
        ),
    ):
        return _respuesta(str(exc), 404)
    if isinstance(
        exc,
        (
            services.SerieNoEnTecnico,
            services.SerieReservada,
            services.SerieYaInactiva,
            services.SerieInstalada,
            services.HashNoCoincide,
        ),
    ):
        return _respuesta(str(exc), 409)
    return _respuesta(str(exc), 400)


@login_required
@require_GET
def lista_devoluciones(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    pagina = Paginator(
        services.listar_devoluciones(
            tenant,
            request.GET.get("desde") or None,
            request.GET.get("hasta") or None,
        ),
        50,
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "logistica_inversa/devoluciones_listado.html",
        {
            "pagina": pagina,
            "devoluciones": pagina.object_list,
            "desde": request.GET.get("desde", ""),
            "hasta": request.GET.get("hasta", ""),
        },
    )


def _grupos_series(tenant, tecnico_id):
    if not tecnico_id:
        return []
    series = (
        Serie.objects.filter(
            tenant=tenant,
            estado=EstadoSerie.ASIGNADA,
            tecnico_id=tecnico_id,
        )
        .select_related("material")
        .order_by("material__codigo", "numero")
    )
    grupos = {}
    for serie in series:
        grupo = grupos.setdefault(
            serie.material_id,
            {"material": serie.material, "series": []},
        )
        grupo["series"].append(serie)
    return list(grupos.values())


@login_required
@require_GET
def series_tecnico_devolucion(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    tecnico_id = request.GET.get("tecnico")
    grupos = _grupos_series(tenant, tecnico_id)
    return render(
        request,
        "logistica_inversa/_series_tecnico.html",
        {"grupos": grupos, "seleccionadas": []},
    )


@login_required
@require_http_methods(["GET", "POST"])
def nueva_devolucion(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    if request.method == "POST":
        tecnico_id = request.POST.get("tecnico")
        formulario = DevolucionForm(
            request.POST, tenant=tenant, tecnico=tecnico_id
        )
        if not formulario.is_valid():
            return render(
                request,
                "logistica_inversa/devolucion_formulario.html",
                {
                    "formulario": formulario,
                    "grupos": _grupos_series(tenant, tecnico_id),
                    "seleccionadas": [
                        int(pk)
                        for pk in request.POST.getlist("series")
                        if str(pk).isdigit()
                    ],
                },
                status=400,
            )
        try:
            devolucion = services.registrar_devolucion(
                tenant,
                formulario.cleaned_data["tecnico"],
                formulario.cleaned_data["fecha"],
                list(formulario.cleaned_data["series"]),
                formulario.cleaned_data["observaciones"],
                request.usuario,
            )
        except services.ErrorLogistica as exc:
            return _error(exc)
        messages.success(request, "Devolución registrada y acta generada")
        return redirect(
            "detalle_devolucion", devolucion_id=devolucion.pk
        )
    tecnico_id = request.GET.get("tecnico")
    return render(
        request,
        "logistica_inversa/devolucion_formulario.html",
        {
            "formulario": DevolucionForm(
                tenant=tenant, tecnico=tecnico_id
            ),
            "grupos": _grupos_series(tenant, tecnico_id),
            "seleccionadas": [],
        },
    )


@login_required
@require_GET
def detalle_devolucion(request, devolucion_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        devolucion = services.obtener_devolucion(tenant, devolucion_id)
    except services.NoEncontrado as exc:
        return _error(exc)
    return render(
        request,
        "logistica_inversa/devolucion_detalle.html",
        {
            "devolucion": devolucion,
            "lineas": services.detalle_devolucion(devolucion),
        },
    )


@login_required
@require_GET
def acta_devolucion(request, devolucion_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        devolucion = services.obtener_devolucion(tenant, devolucion_id)
        ruta = services.verificar_hash_acta(devolucion)
    except services.ErrorLogistica as exc:
        return _error(exc)
    return FileResponse(
        open(ruta, "rb"),
        as_attachment=True,
        filename=f"acta-devolucion-{devolucion.pk}.xlsx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


@login_required
@require_GET
def series_tecnico_baja(request):
    return series_tecnico_devolucion(request)


@login_required
@require_GET
def lista_bajas(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    causa = request.GET.get("causa") or None
    pagina = Paginator(services.listar_bajas(tenant, causa), 50).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "logistica_inversa/bajas_listado.html",
        {
            "pagina": pagina,
            "bajas": pagina.object_list,
            "causa": causa or "",
            "causas": CausaBaja.choices,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def nueva_baja(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    if request.method == "POST":
        tecnico_id = request.POST.get("tecnico")
        formulario = BajaEquipoForm(
            request.POST, tenant=tenant, tecnico=tecnico_id
        )
        if not formulario.is_valid():
            return render(
                request,
                "logistica_inversa/baja_formulario.html",
                {
                    "formulario": formulario,
                    "grupos": _grupos_series(tenant, tecnico_id),
                    "seleccionadas": [
                        int(pk)
                        for pk in request.POST.getlist("series")
                        if str(pk).isdigit()
                    ],
                },
                status=400,
            )
        try:
            services.registrar_bajas_equipo(
                tenant,
                formulario.cleaned_data["tecnico"],
                list(formulario.cleaned_data["series"]),
                formulario.cleaned_data["causa"],
                formulario.cleaned_data["observaciones"],
                request.usuario,
            )
        except services.ErrorLogistica as exc:
            return _error(exc)
        messages.success(request, "Baja registrada")
        return redirect("lista_bajas")
    tecnico_id = request.GET.get("tecnico")
    return render(
        request,
        "logistica_inversa/baja_formulario.html",
        {
            "formulario": BajaEquipoForm(
                tenant=tenant, tecnico=tecnico_id
            ),
            "grupos": _grupos_series(tenant, tecnico_id),
            "seleccionadas": [],
        },
    )


@login_required
@require_GET
def detalle_baja(request, baja_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        baja = services.obtener_baja(tenant, baja_id)
    except services.BajaNoEncontrada as exc:
        return _error(exc)
    return render(
        request,
        "logistica_inversa/baja_detalle.html",
        {"baja": baja},
    )
