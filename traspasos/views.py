"""Vistas de traspasos del tenant."""

from datetime import date
import uuid

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
from .models import EstadoTraspaso, SolicitudTraspaso


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


def _datos_iniciales_edicion(traspaso):
    """Precarga el carrito de la interfaz para un borrador 1→N."""
    lineas = list(
        traspaso.lineas.select_related(
            "material", "serie", "tecnico_origen", "tecnico_destino"
        )
    )
    origenes = {linea.tecnico_origen_id for linea in lineas}
    destinos = sorted({linea.tecnico_destino_id for linea in lineas})
    datos = {
        "forma": traspaso.forma,
        "origen": min(origenes) if origenes else None,
        "destinos": destinos,
        "items": [],
        "bloqueado": False,
    }
    if not origenes or not destinos:
        return datos

    stock_por_origen = {}
    for origen_id in origenes:
        origen = Tecnico.objects.get(pk=origen_id)
        stock_por_origen[origen_id] = {
            fila.material.pk: fila.disponible
            for fila in services.stock_tecnico_para_traspaso(
                traspaso.tenant, origen, traspaso
            )
        }
    for linea in lineas:
        item = {
            "origenId": str(linea.tecnico_origen_id),
            "origenNif": linea.tecnico_origen.nif,
            "materialId": str(linea.material_id),
            "codigo": linea.material.codigo,
            "descripcion": linea.material.descripcion,
            "destinos": [str(linea.tecnico_destino_id)],
            "stock": stock_por_origen.get(
                linea.tecnico_origen_id, {}
            ).get(linea.material_id, 0),
        }
        if linea.serie_id:
            item.update(
                {
                    "tipo": "serie",
                    "serieId": str(linea.serie_id),
                    "numero": linea.serie.numero,
                }
            )
        else:
            item.update({"tipo": "cantidad", "cantidad": linea.cantidad})
        datos["items"].append(item)
    return datos


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


def _datos_iniciales_desde_lineas(tenant, lineas):
    """Reconstruye el carrito de la interfaz desde las líneas enviadas."""
    if not lineas:
        return None

    origenes = {}
    destinos = set()
    items = []
    for linea in lineas:
        origen_id = linea.get("tecnico_origen_id")
        destino_id = linea.get("tecnico_destino_id")
        material_id = linea.get("material_id")
        if not origen_id or not destino_id or not material_id:
            continue
        origen = Tecnico.objects.filter(pk=origen_id, tenant=tenant).first()
        material = Material.objects.filter(pk=material_id).first()
        if origen is None or material is None:
            continue
        origenes[origen.pk] = origen
        destinos.add(int(destino_id))
        items.append((origen, material, linea))

    if not items:
        return None

    stock_por_origen = {}
    for origen_id, origen in origenes.items():
        stock_por_origen[origen_id] = {
            fila.material.pk: fila.disponible
            for fila in services.stock_tecnico_para_traspaso(
                tenant, origen
            )
        }

    datos_items = []
    for origen, material, linea in items:
        base = {
            "origenId": str(origen.pk),
            "origenNif": origen.nif,
            "materialId": str(material.pk),
            "codigo": material.codigo,
            "descripcion": material.descripcion,
            "destinos": [str(destino_id)],
            "stock": stock_por_origen.get(origen.pk, {}).get(
                material.pk, 0
            ),
        }
        if material.es_seriado:
            for serie_id in linea.get("serie_ids") or []:
                serie = Serie.objects.filter(
                    pk=serie_id, tenant=tenant
                ).first()
                if serie is None:
                    continue
                item = dict(base)
                item.update(
                    {
                        "tipo": "serie",
                        "serieId": str(serie.pk),
                        "numero": serie.numero,
                    }
                )
                datos_items.append(item)
        else:
            try:
                cantidad = int(linea.get("cantidad"))
            except (TypeError, ValueError):
                continue
            if cantidad <= 0:
                continue
            item = dict(base)
            item.update({"tipo": "cantidad", "cantidad": cantidad})
            datos_items.append(item)

    if not datos_items:
        return None

    if len(origenes) == 1:
        forma = "1→N"
    elif len(destinos) == 1:
        forma = "N→1"
    else:
        forma = "MIXTA"
    return {
        "forma": forma,
        "origen": min(origenes),
        "destinos": sorted(destinos),
        "items": datos_items,
        "bloqueado": False,
    }


@login_required
@require_http_methods(["GET", "POST"])
def nuevo_traspaso(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error
    contexto = _contexto(tenant)
    if request.method == "POST":
        try:
            clave = request.POST.get("clave_idempotencia") or None
            if request.POST.get("accion") == "enviar":
                traspaso = services.crear_y_enviar_traspaso(
                    tenant,
                    request.POST.get("fecha") or date.today(),
                    _lineas(request, tenant),
                    request.usuario,
                    clave_idempotencia=clave,
                )
                messages.success(request, "Traspaso enviado")
            else:
                traspaso = services.crear_solicitud_traspaso(
                    tenant,
                    request.POST.get("fecha") or date.today(),
                    _lineas(request, tenant),
                    request.usuario,
                    clave_idempotencia=clave,
                )
                messages.success(request, "Borrador guardado")
        except services.ValidacionTraspaso as exc:
            contexto["error"] = str(exc)
            contexto["clave_idempotencia"] = (
                request.POST.get("clave_idempotencia") or uuid.uuid4().hex
            )
            datos = _datos_iniciales_desde_lineas(
                tenant, _lineas(request, tenant)
            )
            if datos is not None:
                contexto["datos_iniciales"] = datos
            return render(
                request, "traspasos/formulario.html", contexto, status=400
            )
        return redirect("detalle_traspaso", traspaso_id=traspaso.pk)
    contexto["clave_idempotencia"] = uuid.uuid4().hex
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
    contexto["datos_iniciales"] = _datos_iniciales_edicion(traspaso)
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
            datos = _datos_iniciales_desde_lineas(
                tenant, _lineas(request, tenant)
            )
            if datos is not None:
                contexto["datos_iniciales"] = datos
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


def _solicitud_exclusion(tenant, valor):
    if not valor or not str(valor).isdigit():
        return None
    return SolicitudTraspaso.objects.filter(
        pk=int(valor),
        tenant=tenant,
        estado=EstadoTraspaso.BORRADOR,
    ).first()


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
    solicitud = _solicitud_exclusion(
        tenant, request.GET.get("solicitud")
    )
    series = services.series_para_tecnico(
        tenant,
        tecnico,
        material,
        request.GET.get("q", ""),
        excluir_solicitud=solicitud,
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
    solicitud = _solicitud_exclusion(
        tenant, request.GET.get("solicitud")
    )
    for fila in services.stock_tecnico_para_traspaso(
        tenant, tecnico, solicitud
    ):
        item = {
            "material": fila.material,
            "cantidad": fila.disponible,
            "stock": fila.stock,
            "reservado": fila.reservado,
            "series": [],
        }
        if fila.material.es_seriado:
            item["series"] = list(
                services.series_para_tecnico(
                    tenant,
                    tecnico,
                    fila.material,
                    excluir_solicitud=solicitud,
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
    solicitud = _solicitud_exclusion(
        tenant, request.POST.get("solicitud")
    )
    return JsonResponse(
        services.validar_disponibilidad(
            tecnico,
            material,
            request.POST.get("cantidad") or None,
            series,
            excluir_solicitud=solicitud,
        )
    )
