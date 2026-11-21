"""Vistas de asignaciones."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from materiales.models import Material
from tecnicos.models import Tecnico

from . import services
from .models import EstadoSolicitud

def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje,
        status=status,
        content_type="text/html; charset=utf-8",
    )


def _tenant_o_error(request, edicion=False):
    try:
        return services.validar_cuenta_tenant(request.usuario), None
    except (
        services.PermisoDenegado,
        services.TenantSuspendido,
    ) as exc:
        return None, _respuesta(str(exc), 403)


def _lineas_de_post(request):
    lineas = []
    total = int(request.POST.get("lineas-TOTAL_FORMS", "0") or 0)
    for indice in range(total):
        tecnico_id = request.POST.get(f"lineas-{indice}-tecnico_id", "")
        material_id = request.POST.get(f"lineas-{indice}-material_id")
        serie_ids = request.POST.getlist(f"lineas-{indice}-serie_ids")
        cantidad = request.POST.get(f"lineas-{indice}-cantidad", "")
        if not tecnico_id and not material_id and not serie_ids and not cantidad:
            continue
        lineas.append(
            {
                "tecnico_id": tecnico_id,
                "material_id": material_id,
                "serie_ids": [int(s) for s in serie_ids if str(s).isdigit()],
                "cantidad": cantidad,
            }
        )
    return lineas


def _contexto_formulario(tenant, solicitud=None):
    if solicitud is not None:
        lineas_sobrante = services.lineas_para_sobrante(solicitud)
        datos_iniciales = services.datos_iniciales_solicitud(solicitud)
    else:
        lineas_sobrante = []
        datos_iniciales = []
    return {
        "tecnicos": Tecnico.objects.filter(tenant=tenant, activo=True).order_by(
            "nombre", "nif"
        ),
        "materiales": services.materiales_para_formulario(tenant, solicitud),
        "panel_materiales": services.calcular_sobrante(
            tenant, lineas_sobrante
        ),
        "solicitud": solicitud,
        "datos_iniciales": datos_iniciales,
        "hoy": date.today(),
    }


@login_required
@require_GET
def lista_asignaciones(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    estado = request.GET.get("estado") or None
    if estado not in {
        EstadoSolicitud.BORRADOR,
        EstadoSolicitud.ENVIADA,
        EstadoSolicitud.CONFIRMADA,
        EstadoSolicitud.RECHAZADA,
        EstadoSolicitud.CANCELADA,
    }:
        estado = None
    pagina = Paginator(services.listar_solicitudes(tenant, estado), 50).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "asignaciones/lista.html",
        {"pagina": pagina, "solicitudes": pagina.object_list, "estado": estado or ""},
    )


@login_required
@require_http_methods(["GET", "POST"])
def nueva_asignacion(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    contexto = _contexto_formulario(tenant)

    if request.method == "POST":
        fecha = request.POST.get("fecha") or date.today()
        lineas = _lineas_de_post(request)
        accion = request.POST.get("accion", "enviar")

        try:
            if accion == "borrador":
                solicitud = services.crear_borrador_solicitud(
                    tenant, fecha, lineas, request.usuario
                )
                messages.success(request, "Borrador guardado")
            else:
                solicitud = services.crear_y_enviar_solicitud(
                    tenant, fecha, lineas, request.usuario
                )
                messages.success(request, "Solicitud enviada")
        except services.ValidacionAsignacion as exc:
            contexto["error"] = str(exc)
            return render(request, "asignaciones/formulario.html", contexto, status=400)
        except services.EstadoSolicitudInvalido as exc:
            contexto["error"] = str(exc)
            return render(request, "asignaciones/formulario.html", contexto, status=409)

        return redirect("detalle_asignacion", solicitud_id=solicitud.pk)

    return render(request, "asignaciones/formulario.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def editar_asignacion(request, solicitud_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_detalle_solicitud(tenant, solicitud_id)
    except services.SolicitudNoExiste as exc:
        return _respuesta(str(exc), 404)

    if solicitud.estado != EstadoSolicitud.BORRADOR:
        return _respuesta(
            "Solo se pueden editar solicitudes en borrador", 409
        )

    contexto = _contexto_formulario(tenant, solicitud)
    if request.method == "POST":
        fecha = request.POST.get("fecha") or date.today()
        lineas = _lineas_de_post(request)
        try:
            services.actualizar_borrador_solicitud(
                solicitud, fecha, lineas, request.usuario
            )
        except services.EstadoSolicitudInvalido as exc:
            contexto["error"] = str(exc)
            return render(
                request,
                "asignaciones/formulario.html",
                contexto,
                status=409,
            )
        except services.ValidacionAsignacion as exc:
            contexto["error"] = str(exc)
            return render(
                request,
                "asignaciones/formulario.html",
                contexto,
                status=400,
            )
        messages.success(request, "Borrador actualizado")
        return redirect("detalle_asignacion", solicitud_id=solicitud.pk)

    return render(request, "asignaciones/formulario.html", contexto)


@login_required
@require_GET
def detalle_asignacion(request, solicitud_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_detalle_solicitud(tenant, solicitud_id)
    except services.SolicitudNoExiste as exc:
        return _respuesta(str(exc), 404)

    return render(
        request,
        "asignaciones/detalle.html",
        {
            "solicitud": solicitud,
            "totales": services.totales_solicitud(solicitud),
            "alertas": services.alertas_cupo_solicitud(solicitud),
            "puede_enviar": solicitud.estado == EstadoSolicitud.BORRADOR,
            "envio_fallido": __import__(
                "asignaciones.correo",
                fromlist=["envio_definitivo_fallido"],
            ).envio_definitivo_fallido(solicitud),
        },
    )


@login_required
@require_GET
def descargar_excel_asignacion(request, solicitud_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_solicitud(tenant, solicitud_id)
        ruta = services.verificar_excel_solicitud(solicitud)
    except services.SolicitudNoExiste as exc:
        return _respuesta(str(exc), 404)
    except services.ArchivoNoDisponible as exc:
        return _respuesta(str(exc), 404)
    except services.ArchivoAlterado as exc:
        return _respuesta(str(exc), 409)
    return FileResponse(
        open(ruta, "rb"),
        as_attachment=True,
        filename=f"asignacion-{solicitud.pk}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required
@require_POST
def enviar_asignacion(request, solicitud_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_solicitud(tenant, solicitud_id)
        services.enviar_solicitud(solicitud, request.usuario)
    except services.SolicitudNoExiste as exc:
        return _respuesta(str(exc), 404)
    except services.ValidacionAsignacion as exc:
        return _respuesta(str(exc), 400)
    messages.success(request, "Solicitud enviada")
    return redirect("detalle_asignacion", solicitud_id=solicitud.pk)


@login_required
@require_POST
def cancelar_asignacion(request, solicitud_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        solicitud = services.obtener_solicitud(tenant, solicitud_id)
        services.cancelar_solicitud(solicitud, request.usuario)
    except services.SolicitudNoExiste as exc:
        return _respuesta(str(exc), 404)
    except services.ValidacionAsignacion as exc:
        return _respuesta(str(exc), 409)
    messages.success(request, "Solicitud cancelada")
    return redirect("detalle_asignacion", solicitud_id=solicitud.pk)


@login_required
@require_GET
def series_disponibles(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    material_id = request.GET.get("material_id")
    if not str(material_id or "").isdigit():
        return _respuesta("El material no existe en el catálogo", 400)
    material = Material.objects.filter(pk=material_id).first()
    if material is None:
        return _respuesta("El material no existe en el catálogo", 400)
    excluir = {
        int(valor)
        for valor in request.GET.get("excluir", "").split(",")
        if valor.isdigit()
    }
    series = services.series_disponibles_para_asignacion(
        tenant,
        material,
        request.GET.get("q", ""),
        excluir_ids=excluir,
    )[:50]
    seleccionados = {
        int(valor)
        for valor in request.GET.get("seleccionados", "").split(",")
        if valor.isdigit()
    }
    return render(
        request,
        "asignaciones/_series_disponibles.html",
        {
            "series": series,
            "material": material,
            "seleccionados": seleccionados,
        },
    )


@login_required
@require_POST
def sobrante_asignacion(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    resumen = services.calcular_sobrante(tenant, _lineas_de_post(request))
    return render(
        request,
        "asignaciones/_sobrante.html",
        {"resumen": resumen},
    )


@login_required
@require_POST
def validar_disponibilidad(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    material_id = request.POST.get("material_id")
    material = (
        Material.objects.filter(pk=material_id).first()
        if str(material_id or "").isdigit()
        else None
    )
    if material is None:
        return render(
            request,
            "asignaciones/_disponibilidad.html",
            {"error": "El material no existe en el catálogo"},
        )
    disponible = services.calcular_disponible(tenant, material)
    return render(
        request,
        "asignaciones/_disponibilidad.html",
        {"material": material, "disponible": disponible},
    )
