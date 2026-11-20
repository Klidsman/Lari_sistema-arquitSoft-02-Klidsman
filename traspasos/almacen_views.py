"""Vistas del almacén para traspasos."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from asignaciones.almacen_services import validar_cuenta_almacen

from . import services
from .models import EstadoTraspaso, SolicitudTraspaso


def _respuesta(mensaje, status):
    return HttpResponse(mensaje, status=status, content_type="text/html; charset=utf-8")


def _region_o_error(request):
    try:
        return validar_cuenta_almacen(request.usuario), None
    except Exception:
        return None, _respuesta(
            "No tienes permiso para gestionar traspasos", 403
        )


@login_required
@require_GET
def bandeja(request):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    solicitudes = SolicitudTraspaso.objects.filter(
        region=region,
        estado__in=[
            EstadoTraspaso.ENVIADA,
            EstadoTraspaso.CONFIRMADA,
            EstadoTraspaso.RECHAZADA,
        ],
    ).select_related("tenant", "tecnico_origen", "tecnico_destino")
    pagina = Paginator(solicitudes.order_by("-enviada_en", "-id"), 50).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "almacen/traspasos_lista.html",
        {"pagina": pagina, "traspasos": pagina.object_list},
    )


@login_required
@require_GET
def detalle(request, traspaso_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    traspaso = (
        SolicitudTraspaso.objects.filter(
            pk=traspaso_id,
            region=region,
            estado__in=[
                EstadoTraspaso.ENVIADA,
                EstadoTraspaso.CONFIRMADA,
                EstadoTraspaso.RECHAZADA,
            ],
        )
        .select_related("tenant", "tecnico_origen", "tecnico_destino")
        .prefetch_related("lineas__material", "lineas__serie")
        .first()
    )
    if traspaso is None:
        return _respuesta("El traspaso no existe", 404)
    return render(
        request,
        "almacen/traspaso_detalle.html",
        {"traspaso": traspaso},
    )


@login_required
@require_GET
def excel(request, traspaso_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    traspaso = SolicitudTraspaso.objects.filter(
        pk=traspaso_id, region=region
    ).first()
    if traspaso is None:
        return _respuesta("El traspaso no existe", 404)
    try:
        ruta = services.verificar_excel(traspaso)
    except services.TraspasoNoExiste:
        return _respuesta("El archivo no está disponible", 404)
    except services.ArchivoAlterado as exc:
        return _respuesta(str(exc), 409)
    return FileResponse(
        open(ruta, "rb"),
        as_attachment=True,
        filename=f"traspaso-{traspaso.pk}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required
@require_POST
def confirmar(request, traspaso_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    traspaso = SolicitudTraspaso.objects.filter(
        pk=traspaso_id, region=region
    ).first()
    if traspaso is None:
        return _respuesta("El traspaso no existe", 404)
    try:
        services.confirmar_traspaso(traspaso, request.usuario)
    except services.ValidacionTraspaso as exc:
        return _respuesta(str(exc), 409)
    messages.success(request, "Traspaso confirmado")
    return redirect("detalle_traspaso_almacen", traspaso_id=traspaso.pk)


@login_required
@require_POST
def rechazar(request, traspaso_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    traspaso = SolicitudTraspaso.objects.filter(
        pk=traspaso_id, region=region
    ).first()
    if traspaso is None:
        return _respuesta("El traspaso no existe", 404)
    try:
        services.rechazar_traspaso(
            traspaso,
            request.POST.get("motivo", ""),
            request.usuario,
        )
    except services.ValidacionTraspaso as exc:
        return _respuesta(str(exc), 400)
    messages.success(request, "Traspaso rechazado")
    return redirect("detalle_traspaso_almacen", traspaso_id=traspaso.pk)
