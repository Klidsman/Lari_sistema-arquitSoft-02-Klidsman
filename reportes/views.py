"""Vistas de reportes mensuales."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from acceso.models import Rol
from tenants.models import Tenant

from . import services


def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje, status=status, content_type="text/html; charset=utf-8"
    )


def _error(exc):
    if isinstance(exc, services.PermisoDenegado):
        return _respuesta(str(exc), 403)
    if isinstance(exc, services.CorteNoExiste):
        return _respuesta(str(exc), 404)
    if isinstance(exc, services.CorteExistente):
        return _respuesta(str(exc), 409)
    return _respuesta(str(exc), 400)


def _es_admin(usuario):
    return usuario.rol == Rol.ADMIN_PLATAFORMA


@login_required
@require_GET
def lista_cortes(request):
    anio = request.GET.get("anio") or None
    if _es_admin(request.usuario):
        from .models import CorteMensual

        cortes = CorteMensual.objects.select_related("tenant")
        if anio:
            cortes = cortes.filter(anio=anio)
        cortes = cortes.order_by("-anio", "-mes", "id")
    else:
        cortes = services.listar_cortes(request.usuario.tenant, anio)
    return render(
        request,
        "reportes/lista.html",
        {"cortes": cortes, "anio": anio or ""},
    )


@login_required
@require_http_methods(["GET", "POST"])
def generar_corte(request):
    if request.method == "POST":
        try:
            if _es_admin(request.usuario):
                tenant_id = request.POST.get("tenant") or None
                tenant = (
                    Tenant.objects.filter(pk=tenant_id).first()
                    if tenant_id
                    else None
                )
            else:
                tenant = request.usuario.tenant
            corte = services.generar_corte(
                tenant,
                request.POST.get("mes"),
                request.POST.get("anio"),
                request.usuario,
            )
        except services.ErrorReporte as exc:
            return _error(exc)
        messages.success(request, "Corte generado")
        return redirect("detalle_corte", corte_id=corte.pk)
    return render(
        request,
        "reportes/generar.html",
        {
            "es_admin": _es_admin(request.usuario),
            "tenants": (
                Tenant.objects.order_by("codigo")
                if _es_admin(request.usuario)
                else Tenant.objects.none()
            ),
        },
    )


@login_required
@require_GET
def detalle_corte(request, corte_id):
    try:
        corte = services.obtener_corte_visible(request.usuario, corte_id)
    except services.ErrorReporte as exc:
        return _error(exc)
    return render(
        request,
        "reportes/detalle.html",
        {"corte": corte, "detalle": services.detalle_corte(corte)},
    )


@login_required
@require_POST
def regenerar_corte(request, corte_id):
    try:
        corte = services.obtener_corte_visible(request.usuario, corte_id)
        services.regenerar_corte(corte, request.usuario)
    except services.ErrorReporte as exc:
        return _error(exc)
    messages.success(request, "Corte regenerado")
    return redirect("detalle_corte", corte_id=corte_id)


def _descargar(archivo):
    respuesta = HttpResponse(
        archivo.contenido, content_type=archivo.content_type
    )
    respuesta["Content-Disposition"] = (
        f'attachment; filename="{archivo.nombre}"'
    )
    return respuesta


@login_required
@require_GET
def exportar_auditoria(request, corte_id):
    try:
        corte = services.obtener_corte_visible(request.usuario, corte_id)
        archivo = services.exportar_auditoria(
            corte.tenant, corte.mes, corte.anio, request.usuario
        )
    except services.ErrorReporte as exc:
        return _error(exc)
    return _descargar(archivo)


@login_required
@require_GET
def exportar_conciliacion(request, corte_id):
    try:
        corte = services.obtener_corte_visible(request.usuario, corte_id)
        archivo = services.exportar_conciliacion(
            corte.tenant, corte.mes, corte.anio, request.usuario
        )
    except services.ErrorReporte as exc:
        return _error(exc)
    return _descargar(archivo)
