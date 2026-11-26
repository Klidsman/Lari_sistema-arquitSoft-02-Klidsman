"""Vistas del registro de materiales."""

import re
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from materiales.models import Material
from tecnicos.models import Tecnico

from . import exportacion, services
from .models import CierreMensual, MaterialHabilitado


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
    if isinstance(
        exc,
        (
            services.SaldoInsuficiente,
            services.PeriodoCerrado,
            services.CargaNoDeshacible,
            services.CierreBloqueado,
        ),
    ):
        return _respuesta(str(exc), 409)
    return _respuesta(str(exc), 400)


def _periodo(request):
    return request.GET.get("periodo") or services.periodo_actual()


def _tecnicos(tenant):
    return Tecnico.objects.filter(tenant=tenant, activo=True).order_by("nif")


def _cantidades(request):
    datos = {}
    patron = re.compile(r"^cantidades\[(\d+)\]$")
    for clave, valor in request.POST.items():
        coincidencia = patron.match(clave)
        if coincidencia:
            datos[int(coincidencia.group(1))] = valor
    return datos


@login_required
@require_GET
def menu(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    return render(
        request,
        "registro_materiales/menu.html",
        {"periodo": services.periodo_actual()},
    )


@login_required
@require_http_methods(["GET", "POST"])
def cargar_ordenes(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    contexto = {
        "tecnicos": _tecnicos(tenant),
        "periodo": _periodo(request),
    }
    if request.method == "POST":
        try:
            tecnico = Tecnico.objects.filter(
                pk=request.POST.get("tecnico"), tenant=tenant
            ).first()
            carga = services.confirmar_carga(
                tenant,
                tecnico,
                request.POST.get("periodo") or services.periodo_actual(),
                request.POST.get("texto", ""),
                request.usuario,
            )
        except services.ErrorRegistro as exc:
            return _error(exc)
        messages.success(
            request,
            f"Carga creada: {carga.total_nuevas} órdenes nuevas",
        )
        return redirect("menu_registro_materiales")
    return render(
        request, "registro_materiales/cargar_ordenes.html", contexto
    )


@login_required
@require_POST
def preview_carga(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        tecnico = Tecnico.objects.filter(
            pk=request.POST.get("tecnico"), tenant=tenant
        ).first()
        resumen = services.previsualizar_carga(
            tenant,
            tecnico,
            request.POST.get("periodo") or services.periodo_actual(),
            request.POST.get("texto", ""),
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    return render(
        request,
        "registro_materiales/_resumen_carga.html",
        {"resumen": resumen},
    )


@login_required
@require_POST
def deshacer_carga(request, carga_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    from .models import CargaOrdenes

    carga = CargaOrdenes.objects.filter(pk=carga_id, tenant=tenant).first()
    if carga is None:
        return _respuesta("El registro no existe", 404)
    try:
        services.deshacer_carga(
            carga, request.usuario, request.POST.get("motivo", "")
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    messages.success(request, "Carga deshecha")
    return redirect("menu_registro_materiales")


@login_required
@require_GET
def pendientes(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        ordenes = services.ordenes_pendientes(
            tenant,
            request.GET.get("periodo") or None,
            request.GET.get("dias") or None,
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    return render(
        request,
        "registro_materiales/pendientes.html",
        {
            "ordenes": ordenes,
            "periodo": request.GET.get("periodo", ""),
            "dias": request.GET.get("dias", ""),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def catalogo(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    if request.method == "POST":
        try:
            material = Material.objects.filter(
                pk=request.POST.get("material")
            ).first()
            services.habilitar_material(
                tenant,
                material,
                request.POST.get("activo") == "1",
                request.usuario,
                int(request.POST.get("orden") or 0),
            )
        except services.ErrorRegistro as exc:
            return _error(exc)
        messages.success(request, "Catálogo actualizado")
        return redirect("catalogo_materiales")
    return render(
        request,
        "registro_materiales/catalogo.html",
        {
            "habilitados": MaterialHabilitado.objects.filter(
                tenant=tenant
            ).select_related("material"),
            "materiales": Material.objects.filter(activo=True).order_by(
                "codigo"
            ),
        },
    )


def _contexto_materiales(tenant, tecnico, periodo, numero):
    orden = None
    if tecnico is not None and numero:
        orden = services.buscar_orden(tenant, tecnico, periodo, numero)
    usos = {}
    if orden is not None:
        usos = {
            uso.material_id: uso.cantidad
            for uso in orden.usos.all()
        }
    filas = []
    for habilitado in services.materiales_habilitados(tenant):
        filas.append(
            {
                "material": habilitado.material,
                "cantidad": usos.get(habilitado.material_id, 0),
                "disponible": services.saldo_final(
                    tenant, habilitado.material, periodo
                ),
            }
        )
    return orden, filas


@login_required
@require_GET
def materiales(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    periodo = _periodo(request)
    tecnico = Tecnico.objects.filter(
        pk=request.GET.get("tecnico"), tenant=tenant
    ).first()
    numero = request.GET.get("numero_orden", "")
    orden, filas = _contexto_materiales(tenant, tecnico, periodo, numero)
    ordenes = []
    if tecnico is not None and orden is None:
        ordenes = services.ordenes_pendientes(
            tenant, periodo, tecnico=tecnico
        )
    return render(
        request,
        "registro_materiales/materiales.html",
        {
            "tecnicos": _tecnicos(tenant),
            "periodo": periodo,
            "tecnico": tecnico,
            "numero": numero,
            "orden": orden,
            "ordenes": ordenes,
            "filas": filas,
        },
    )


@login_required
@require_GET
def contexto_materiales(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        periodo = _periodo(request)
        tecnico = Tecnico.objects.filter(
            pk=request.GET.get("tecnico"), tenant=tenant
        ).first()
        orden, filas = _contexto_materiales(
            tenant,
            tecnico,
            periodo,
            request.GET.get("numero_orden", ""),
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    return render(
        request,
        "registro_materiales/_materiales_tabla.html",
        {"orden": orden, "filas": filas, "periodo": periodo},
    )


@login_required
@require_POST
def guardar_materiales(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        periodo = request.POST.get("periodo") or services.periodo_actual()
        tecnico = Tecnico.objects.filter(
            pk=request.POST.get("tecnico"), tenant=tenant
        ).first()
        orden = services.obtener_o_crear_orden(
            tenant,
            tecnico,
            periodo,
            request.POST.get("numero_orden", ""),
            request.usuario,
        )
        services.guardar_uso(
            orden,
            date.fromisoformat(
                request.POST.get("fecha_instalacion")
                or date.today().isoformat()
            ),
            _cantidades(request),
            request.usuario,
        )
    except (services.ErrorRegistro, ValueError) as exc:
        return _error(exc if isinstance(exc, services.ErrorRegistro) else services.PeriodoInvalido())
    messages.success(request, "Materiales registrados")
    return redirect("menu_registro_materiales")


@login_required
@require_GET
def historial(request, orden_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        registros = services.historial_orden(tenant, orden_id)
    except services.ErrorRegistro as exc:
        return _error(exc)
    return render(
        request,
        "registro_materiales/historial.html",
        {"registros": registros, "orden_id": orden_id},
    )


@login_required
@require_GET
def entradas(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    periodo = _periodo(request)
    despachos = services.despachos_del_periodo(tenant, periodo)
    filas = [
        {
            "material": habilitado.material,
            "saldo": services.saldo_inicial_efectivo(
                tenant, habilitado.material, periodo
            ),
            "despachos": despachos.get(habilitado.material_id, 0),
        }
        for habilitado in services.materiales_habilitados(tenant)
    ]
    return render(
        request,
        "registro_materiales/entradas.html",
        {"periodo": periodo, "filas": filas},
    )


@login_required
@require_POST
def guardar_saldo(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        material = Material.objects.filter(
            pk=request.POST.get("material")
        ).first()
        services.registrar_saldo_inicial(
            tenant,
            material,
            request.POST.get("periodo") or services.periodo_actual(),
            request.POST.get("cantidad", ""),
            request.usuario,
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    messages.success(request, "Saldo inicial registrado")
    return redirect(
        f"/registro-materiales/entradas/?periodo={request.POST.get('periodo', '')}"
    )


@login_required
@require_GET
def dashboard(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        datos = services.dashboard_mensual(
            tenant, _periodo(request)
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    return render(
        request, "registro_materiales/dashboard.html", {"datos": datos}
    )


@login_required
@require_GET
def cierre(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    periodo = _periodo(request)
    try:
        pendientes_cierre = services.lista_chequeo(tenant, periodo)
    except services.ErrorRegistro as exc:
        return _error(exc)
    estado = CierreMensual.objects.filter(
        tenant=tenant, periodo=periodo
    ).first()
    return render(
        request,
        "registro_materiales/cierre.html",
        {
            "periodo": periodo,
            "pendientes": pendientes_cierre,
            "estado": estado,
        },
    )


@login_required
@require_POST
def cerrar(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        services.cerrar_mes(
            tenant,
            request.POST.get("periodo") or services.periodo_actual(),
            request.POST.get("backup_ref", ""),
            request.usuario,
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    messages.success(request, "Mes cerrado")
    return redirect("cierre_mensual")


@login_required
@require_POST
def reabrir(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    cierre_obj = CierreMensual.objects.filter(
        pk=request.POST.get("cierre"), tenant=tenant
    ).first()
    if cierre_obj is None:
        return _respuesta("El registro no existe", 404)
    try:
        services.reabrir_mes(
            cierre_obj, request.POST.get("motivo", ""), request.usuario
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    messages.success(request, "Mes reabierto")
    return redirect("cierre_mensual")


@login_required
@require_POST
def justificar(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    periodo = request.POST.get("periodo") or services.periodo_actual()
    cierre_obj = CierreMensual.objects.filter(
        tenant=tenant, periodo=periodo
    ).first()
    if cierre_obj is None:
        cierre_obj = services._obtener_cierre(tenant, periodo)
    try:
        services.justificar_pendiente(
            cierre_obj,
            request.POST.get("tipo", ""),
            request.POST.get("referencia", ""),
            request.POST.get("motivo", ""),
            request.usuario,
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    messages.success(request, "Pendiente justificado")
    return redirect(f"/registro-materiales/cierre/?periodo={periodo}")


@login_required
@require_POST
def resolver_advertencia(request, advertencia_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    from .models import AdvertenciaUso

    advertencia = AdvertenciaUso.objects.filter(
        pk=advertencia_id, tenant=tenant
    ).first()
    if advertencia is None:
        return _respuesta("El registro no existe", 404)
    try:
        services.resolver_advertencia(
            advertencia, request.POST.get("justificacion", ""), request.usuario
        )
    except services.ErrorRegistro as exc:
        return _error(exc)
    messages.success(request, "Advertencia resuelta")
    return redirect("cierre_mensual")


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
def exportar_reporte(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        archivo = exportacion.exportar_reporte_mensual(
            tenant,
            request.GET.get("periodo") or services.periodo_actual(),
            request.GET.get("formato", "xlsx"),
        )
    except (services.ErrorRegistro, ValueError) as exc:
        return _error(
            exc if isinstance(exc, services.ErrorRegistro)
            else services.PeriodoInvalido()
        )
    return _descargar(archivo)


@login_required
@require_GET
def exportar_ordenes(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    try:
        archivo = exportacion.exportar_detalle_ordenes(
            tenant,
            request.GET.get("periodo") or services.periodo_actual(),
            request.GET.get("formato", "xlsx"),
        )
    except (services.ErrorRegistro, ValueError) as exc:
        return _error(
            exc if isinstance(exc, services.ErrorRegistro)
            else services.PeriodoInvalido()
        )
    return _descargar(archivo)
