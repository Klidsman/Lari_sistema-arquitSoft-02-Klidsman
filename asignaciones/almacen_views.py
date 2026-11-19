"""Vistas del almacén (007)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from acceso.models import Rol

from . import almacen_services as services
from .models import EstadoSolicitud, SolicitudAsignacion


def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje,
        status=status,
        content_type="text/html; charset=utf-8",
    )


def _region_o_error(request, permitir_admin=False):
    usuario = getattr(request, "usuario", None)
    if permitir_admin and usuario and usuario.rol == Rol.ADMIN_PLATAFORMA:
        return None, None
    try:
        return services.validar_cuenta_almacen(usuario), None
    except services.PermisoDenegado:
        return None, _respuesta(
            "No tienes permiso para gestionar despachos", 403
        )


def _totales(solicitud):
    lineas = list(solicitud.lineas.all())
    return {
        "total_lineas": len(lineas),
        "total_series": sum(1 for linea in lineas if linea.serie_id),
        "total_cantidad": sum(
            linea.cantidad for linea in lineas if linea.serie_id is None
        ),
    }


@login_required
@require_GET
def bandeja(request):
    region, error = _region_o_error(request)
    if error is not None:
        return error

    estado = request.GET.get("estado") or None
    solicitudes = services.bandeja(region, estado)
    pagina = Paginator(solicitudes, 50).get_page(request.GET.get("page"))
    pendientes = services.bandeja(region, EstadoSolicitud.ENVIADA).count()
    return render(
        request,
        "almacen/bandeja.html",
        {
            "pagina": pagina,
            "solicitudes": pagina.object_list,
            "estado": estado or "",
            "pendientes": pendientes,
        },
    )


@login_required
@require_GET
def detalle_solicitud(request, solicitud_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.detalle_solicitud_region(region, solicitud_id)
    except services.SolicitudNoExiste:
        return _respuesta("La solicitud no existe", 404)
    return render(
        request,
        "almacen/detalle.html",
        {
            "solicitud": solicitud,
            "totales": _totales(solicitud),
            "ultimo_envio": services.ultimo_envio(solicitud),
            "envio_fallido": services.envio_definitivo_fallido(solicitud),
        },
    )


@login_required
@require_GET
def previsualizar_solicitud(request, solicitud_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.detalle_solicitud_region(region, solicitud_id)
    except services.SolicitudNoExiste:
        return _respuesta("La solicitud no existe", 404)
    return render(
        request,
        "almacen/_previsualizar.html",
        {"solicitud": solicitud, "totales": _totales(solicitud)},
    )


@login_required
@require_POST
def confirmar_solicitud(request, solicitud_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_solicitud_region(region, solicitud_id)
        services.confirmar_solicitud(solicitud, request.usuario)
    except services.SolicitudNoExiste:
        return _respuesta("La solicitud no existe", 404)
    except services.EstadoSolicitudInvalido as exc:
        return _respuesta(str(exc), 409)
    messages.success(request, "Solicitud confirmada")
    return redirect("detalle_almacen", solicitud_id=solicitud_id)


@login_required
@require_POST
def rechazar_solicitud(request, solicitud_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_solicitud_region(region, solicitud_id)
        services.rechazar_solicitud(
            solicitud,
            request.POST.get("motivo", ""),
            request.usuario,
        )
    except services.SolicitudNoExiste:
        return _respuesta("La solicitud no existe", 404)
    except services.MotivoRechazoInvalido as exc:
        return _respuesta(str(exc), 400)
    except services.EstadoSolicitudInvalido as exc:
        return _respuesta(str(exc), 409)
    messages.success(request, "Solicitud rechazada")
    return redirect("detalle_almacen", solicitud_id=solicitud_id)


@login_required
@require_GET
def descargar_excel(request, solicitud_id):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_solicitud_region(region, solicitud_id)
        ruta = services.verificar_archivo(solicitud)
    except services.SolicitudNoExiste:
        return _respuesta("La solicitud no existe", 404)
    except services.ArchivoAlterado as exc:
        return _respuesta(str(exc), 409)
    return FileResponse(
        open(ruta, "rb"),
        as_attachment=True,
        filename=f"asignacion-{solicitud.pk}.xlsx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


@login_required
@require_GET
def historicos(request):
    usuario = getattr(request, "usuario", None)
    if usuario is None or usuario.rol not in {
        Rol.RESPONSABLE_ALMACEN,
        Rol.ADMIN_PLATAFORMA,
    }:
        return _respuesta("No tienes permiso para gestionar despachos", 403)
    try:
        solicitudes = services.historicos(usuario, request.GET)
    except services.PermisoDenegado:
        return _respuesta("No tienes permiso para gestionar despachos", 403)
    pagina = Paginator(solicitudes, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "almacen/historicos.html",
        {"pagina": pagina, "solicitudes": pagina.object_list},
    )


@login_required
@require_GET
def descargar_historico(request, solicitud_id):
    usuario = getattr(request, "usuario", None)
    if usuario is None or usuario.rol not in {
        Rol.RESPONSABLE_ALMACEN,
        Rol.ADMIN_PLATAFORMA,
    }:
        return _respuesta("No tienes permiso para gestionar despachos", 403)
    solicitud = SolicitudAsignacion.objects.filter(pk=solicitud_id).first()
    if solicitud is None:
        return _respuesta("La solicitud no existe", 404)
    if usuario.rol == Rol.RESPONSABLE_ALMACEN and solicitud.region_id != usuario.region_id:
        return _respuesta("La solicitud no existe", 404)
    try:
        ruta = services.verificar_archivo(solicitud)
    except services.SolicitudNoExiste:
        return _respuesta("La solicitud no existe", 404)
    except services.ArchivoAlterado as exc:
        return _respuesta(str(exc), 409)
    return FileResponse(
        open(ruta, "rb"),
        as_attachment=True,
        filename=f"asignacion-{solicitud.pk}.xlsx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


@login_required
@require_GET
def pendientes(request):
    region, error = _region_o_error(request)
    if error is not None:
        return error
    solicitudes = services.bandeja(region, EstadoSolicitud.ENVIADA)
    ultima = solicitudes.first()
    return render(
        request,
        "almacen/_pendientes.html",
        {"pendientes": solicitudes.count(), "ultima": ultima},
    )


@login_required
@require_GET
def sse(request):
    region, error = _region_o_error(request)
    if error is not None:
        return error

    def eventos():
        pendientes = services.bandeja(region, EstadoSolicitud.ENVIADA).count()
        yield f"data: {pendientes}\n\n"

    respuesta = StreamingHttpResponse(
        eventos(), content_type="text/event-stream"
    )
    respuesta["Cache-Control"] = "no-cache"
    return respuesta
