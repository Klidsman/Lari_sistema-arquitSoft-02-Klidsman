"""Vistas de conciliación de stock."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import services
from .excel import (
    CantidadInvalida,
    ColumnasFaltantes,
    FormatoInvalido,
    HojaGeneralAusente,
)
from .forms import ReporteConciliacionForm
from .models import EstadoConciliacion


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
    if isinstance(exc, services.NoEncontrado):
        return _respuesta(str(exc), 404)
    if isinstance(exc, services.ArchivoNoDisponible):
        return _respuesta(str(exc), 404)
    if isinstance(exc, services.ConciliacionEnRevision):
        return _respuesta(str(exc), 409)
    if isinstance(
        exc,
        (
            services.EstadoConciliacionInvalido,
            services.AprobacionBloqueada,
            services.HuboCambios,
        ),
    ):
        return _respuesta(str(exc), 409)
    return _respuesta(str(exc), 400)


@login_required
@require_GET
def lista_conciliaciones(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    estado = request.GET.get("estado") or None
    pagina = Paginator(
        services.listar_conciliaciones(tenant, estado), 50
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "conciliaciones/listado.html",
        {
            "pagina": pagina,
            "conciliaciones": pagina.object_list,
            "estado": estado or "",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def cargar_conciliacion(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    if request.method == "POST":
        formulario = ReporteConciliacionForm(request.POST, request.FILES)
        if not formulario.is_valid():
            return render(
                request,
                "conciliaciones/cargar.html",
                {"formulario": formulario},
                status=400,
            )
        try:
            conciliacion = services.crear_conciliacion(
                request.usuario, formulario.cleaned_data["archivo"]
            )
        except (
            FormatoInvalido,
            HojaGeneralAusente,
            ColumnasFaltantes,
            CantidadInvalida,
            services.TecnicosFueraRegion,
            services.TecnicoFormatoInvalido,
            services.MaterialNoExiste,
            services.SerieFormatoInvalido,
            services.SerieDuplicada,
            services.SerieInstalada,
            services.SerieFueraTenant,
            services.MaterialSerieIncoherente,
            services.ConciliacionEnRevision,
        ) as exc:
            return _error(exc)
        messages.success(request, "Conciliación creada en revisión")
        return redirect(
            "detalle_conciliacion", conciliacion_id=conciliacion.pk
        )
    return render(
        request,
        "conciliaciones/cargar.html",
        {"formulario": ReporteConciliacionForm()},
    )


@login_required
@require_GET
def detalle_conciliacion(request, conciliacion_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        conciliacion = services.obtener_conciliacion(tenant, conciliacion_id)
    except services.NoEncontrado as exc:
        return _error(exc)
    return render(
        request,
        "conciliaciones/detalle.html",
        {
            "conciliacion": conciliacion,
            "detalle": services.detalle_conciliacion(conciliacion),
            "en_revision": conciliacion.estado
            == EstadoConciliacion.EN_REVISION,
        },
    )


@login_required
@require_POST
def recalcular_conciliacion(request, conciliacion_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        conciliacion = services.obtener_conciliacion(tenant, conciliacion_id)
        services.recalcular_diferencias(conciliacion, request.usuario)
    except services.ErrorConciliacion as exc:
        return _error(exc)
    messages.success(request, "Diferencias recalculadas")
    return redirect("detalle_conciliacion", conciliacion_id=conciliacion_id)


@login_required
@require_POST
def aprobar_conciliacion(request, conciliacion_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        conciliacion = services.obtener_conciliacion(tenant, conciliacion_id)
        services.aprobar_conciliacion(conciliacion, request.usuario)
    except services.ErrorConciliacion as exc:
        return _error(exc)
    messages.success(request, "Conciliación aprobada")
    return redirect("detalle_conciliacion", conciliacion_id=conciliacion_id)


@login_required
@require_POST
def rechazar_conciliacion(request, conciliacion_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        conciliacion = services.obtener_conciliacion(tenant, conciliacion_id)
        services.rechazar_conciliacion(
            conciliacion,
            request.usuario,
            request.POST.get("motivo", ""),
        )
    except services.ErrorConciliacion as exc:
        return _error(exc)
    messages.success(request, "Conciliación rechazada")
    return redirect("detalle_conciliacion", conciliacion_id=conciliacion_id)
