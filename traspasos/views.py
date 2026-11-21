"""Vistas de traspasos del tenant."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from materiales.models import Material
from series.models import Serie
from tecnicos.models import Tecnico

from . import services
from .models import EstadoTraspaso


def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje, status=status, content_type="text/html; charset=utf-8"
    )


def _tenant_o_error(request):
    try:
        return services.validar_cuenta_tenant(request.usuario), None
    except (services.PermisoDenegado,) as exc:
        return None, _respuesta(str(exc), 403)


def _lineas(request, tenant):
    lineas = []
    total = int(request.POST.get("lineas-TOTAL_FORMS", "0") or 0)
    for indice in range(total):
        material_id = request.POST.get(f"lineas-{indice}-material_id")
        origen_id = request.POST.get(f"lineas-{indice}-tecnico_origen_id")
        destino_id = request.POST.get(f"lineas-{indice}-tecnico_destino_id")
        serie_ids = request.POST.getlist(f"lineas-{indice}-serie_ids")
        texto_series = request.POST.get(f"lineas-{indice}-series", "")
        cantidad = request.POST.get(f"lineas-{indice}-cantidad", "")
        if (
            not material_id
            and not serie_ids
            and not cantidad
            and not texto_series
        ):
            continue
        if not serie_ids and texto_series:
            numeros = [
                numero
                for numero in texto_series.replace(",", " ").split()
                if numero.strip()
            ]
            serie_ids = list(
                Serie.objects.filter(
                    tenant=tenant,
                    material_id=material_id,
                    numero__in=[n.upper() for n in numeros],
                ).values_list("pk", flat=True)
            )
        lineas.append(
            {
                "tecnico_origen_id": origen_id,
                "tecnico_destino_id": destino_id,
                "material_id": material_id,
                "serie_ids": [
                    int(s) for s in serie_ids if str(s).isdigit()
                ],
                "cantidad": cantidad,
            }
        )
    return lineas


def _contexto(tenant):
    return {
        "tecnicos": Tecnico.objects.filter(tenant=tenant).order_by(
            "nombre", "nif"
        ),
        "materiales": Material.objects.filter(activo=True).order_by("codigo"),
        "hoy": date.today(),
        "lineas": range(5),
    }


@login_required
@require_GET
def lista_traspasos(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    estado = request.GET.get("estado") or None
    pagina = Paginator(services.listar_traspasos(tenant, estado), 50).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "traspasos/lista.html",
        {
            "pagina": pagina,
            "traspasos": pagina.object_list,
            "estado": estado or "",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def nuevo_traspaso(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    contexto = _contexto(tenant)
    if request.method == "POST":
        try:
            traspaso = services.crear_solicitud_traspaso(
                tenant,
                request.POST.get("fecha") or date.today(),
                _lineas(request, tenant),
                request.usuario,
            )
            if request.POST.get("accion") == "enviar":
                traspaso = services.enviar_solicitud_traspaso(
                    traspaso, request.usuario
                )
                messages.success(request, "Traspaso enviado")
            else:
                messages.success(request, "Borrador guardado")
        except services.ValidacionTraspaso as exc:
            contexto["error"] = str(exc)
            return render(
                request, "traspasos/formulario.html", contexto, status=400
            )
        return redirect("detalle_traspaso", traspaso_id=traspaso.pk)
    return render(request, "traspasos/formulario.html", contexto)


@login_required
@require_GET
def detalle_traspaso(request, traspaso_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        traspaso = services.obtener_detalle_traspaso(tenant, traspaso_id)
    except services.TraspasoNoExiste:
        return _respuesta("El traspaso no existe", 404)
    return render(
        request,
        "traspasos/detalle.html",
        {
            "traspaso": traspaso,
            "puede_enviar": traspaso.estado == EstadoTraspaso.BORRADOR,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def editar_traspaso(request, traspaso_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        traspaso = services.obtener_detalle_traspaso(tenant, traspaso_id)
    except services.TraspasoNoExiste:
        return _respuesta("El traspaso no existe", 404)
    if traspaso.estado != EstadoTraspaso.BORRADOR:
        return _respuesta("Solo se pueden editar traspasos en borrador", 409)
    contexto = _contexto(tenant)
    contexto["traspaso"] = traspaso
    if request.method == "POST":
        try:
            services.actualizar_lineas_borrador(
                traspaso,
                request.POST.get("fecha") or date.today(),
                _lineas(request, tenant),
                request.usuario,
            )
        except services.ValidacionTraspaso as exc:
            contexto["error"] = str(exc)
            return render(
                request, "traspasos/formulario.html", contexto, status=409
            )
        return redirect("detalle_traspaso", traspaso_id=traspaso.pk)
    return render(request, "traspasos/formulario.html", contexto)


@login_required
@require_POST
def enviar_traspaso(request, traspaso_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        traspaso = services.obtener_traspaso(tenant, traspaso_id)
        services.enviar_solicitud_traspaso(traspaso, request.usuario)
    except services.TraspasoNoExiste:
        return _respuesta("El traspaso no existe", 404)
    except services.ValidacionTraspaso as exc:
        return _respuesta(str(exc), 409)
    return redirect("detalle_traspaso", traspaso_id=traspaso.pk)


@login_required
@require_POST
def cancelar_traspaso(request, traspaso_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        traspaso = services.obtener_traspaso(tenant, traspaso_id)
        services.cancelar_traspaso(traspaso, request.usuario)
    except services.TraspasoNoExiste:
        return _respuesta("El traspaso no existe", 404)
    except services.ValidacionTraspaso as exc:
        return _respuesta(str(exc), 409)
    return redirect("detalle_traspaso", traspaso_id=traspaso.pk)


@login_required
@require_GET
def excel_traspaso(request, traspaso_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        traspaso = services.obtener_traspaso(tenant, traspaso_id)
        ruta = services.verificar_excel(traspaso)
    except services.TraspasoNoExiste:
        return _respuesta("El archivo no está disponible", 404)
    except services.ArchivoAlterado as exc:
        return _respuesta(str(exc), 409)
    return FileResponse(
        open(ruta, "rb"),
        as_attachment=True,
        filename=f"traspaso-{traspaso.pk}.xlsx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )


@login_required
@require_GET
def series_tecnico(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    tecnico = Tecnico.objects.filter(
        pk=request.GET.get("tecnico"), tenant=tenant
    ).first()
    material = Material.objects.filter(pk=request.GET.get("material")).first()
    if tecnico is None or material is None:
        return _respuesta("No se encontraron series", 400)
    series = services.series_para_tecnico(
        tenant, tecnico, material, request.GET.get("q", "")
    )[:50]
    return render(
        request,
        "traspasos/_series.html",
        {"series": series, "indice": request.GET.get("indice", "0")},
    )


@login_required
@require_GET
def stock_tecnico(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    tecnico = Tecnico.objects.filter(
        pk=request.GET.get("tecnico"), tenant=tenant
    ).first()
    if tecnico is None:
        return _respuesta("El técnico no existe", 404)
    return render(
        request,
        "traspasos/_stock_tecnico.html",
        {
            "tecnico": tecnico,
            "stock": services.stock_tecnico_para_traspaso(tenant, tecnico),
        },
    )


@login_required
@require_GET
def materiales_tecnico(request):
    """Materiales en mano del técnico, con cantidades o series elegibles."""
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    tecnico = Tecnico.objects.filter(
        pk=request.GET.get("tecnico"), tenant=tenant
    ).first()
    if tecnico is None:
        return _respuesta("El técnico no existe", 404)

    materiales = []
    for fila in services.stock_tecnico_para_traspaso(tenant, tecnico):
        item = {
            "material": fila.material,
            "cantidad": fila.cantidad,
            "series": [],
        }
        if fila.material.es_seriado:
            item["series"] = list(
                services.series_para_tecnico(
                    tenant, tecnico, fila.material
                )
            )
        materiales.append(item)

    return render(
        request,
        "traspasos/_materiales_tecnico.html",
        {"tecnico": tecnico, "materiales": materiales},
    )


@login_required
@require_POST
def validar_disponibilidad(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    tecnico = Tecnico.objects.filter(
        pk=request.POST.get("tecnico"), tenant=tenant
    ).first()
    material = Material.objects.filter(pk=request.POST.get("material")).first()
    if tecnico is None or material is None:
        return JsonResponse({"valido": False, "errores": ["Datos inválidos"]})
    series_ids = [
        int(s) for s in request.POST.getlist("series") if str(s).isdigit()
    ]
    series = list(Serie.objects.filter(pk__in=series_ids, tenant=tenant))
    return JsonResponse(
        services.validar_disponibilidad(
            tecnico,
            material,
            request.POST.get("cantidad") or None,
            series,
        )
    )
