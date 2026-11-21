"""Vistas de stock inicial."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from materiales.models import Material
from tecnicos.models import Tecnico

from . import services
from .excel import FormatoExcelInvalido
from .forms import CargaExcelForm
from .models import CargaStockInicial, LineaStockInicial


def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje,
        status=status,
        content_type="text/html; charset=utf-8",
    )


def _tenant_o_error(request, edicion=False):
    try:
        return services.validar_cuenta_tenant(request.usuario), None
    except (services.PermisoDenegado, services.TenantSuspendido) as exc:
        return None, _respuesta(str(exc), 403)


def _contexto_formulario():
    return {
        "tecnicos": Tecnico.objects.filter(activo=True).order_by("nombre", "nif"),
        "materiales": Material.objects.filter(activo=True).order_by("codigo"),
    }


@login_required
@require_GET
def estado_stock_inicial(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    estado = services.estado_stock_inicial(tenant)
    return render(
        request,
        "stock_inicial/estado.html",
        {
            "estado": estado,
            "form": CargaExcelForm(),
        },
    )


@login_required
@require_POST
def validar_excel(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    formulario = CargaExcelForm(request.POST, request.FILES)
    if not formulario.is_valid():
        mensaje = formulario.errors["archivo"][0]
        return render(
            request,
            "stock_inicial/_resultado_validacion.html",
            {"error": mensaje},
            status=400,
        )

    try:
        resultado, nombre, hash_archivo = services.validar_excel_stock_inicial(
            tenant,
            formulario.cleaned_data["archivo"],
        )
    except FormatoExcelInvalido as exc:
        return render(
            request,
            "stock_inicial/_resultado_validacion.html",
            {"error": str(exc)},
            status=400,
        )

    return render(
        request,
        "stock_inicial/_resultado_validacion.html",
        {
            "resultado": resultado,
            "archivo_nombre": nombre,
            "archivo_hash": hash_archivo,
        },
    )


@login_required
@require_POST
def cargar_excel(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    formulario = CargaExcelForm(request.POST, request.FILES)
    if not formulario.is_valid():
        return render(
            request,
            "stock_inicial/estado.html",
            {
                "estado": services.estado_stock_inicial(tenant),
                "form": formulario,
                "error": formulario.errors["archivo"][0],
            },
            status=400,
        )

    archivo = formulario.cleaned_data["archivo"]
    try:
        resultado, nombre, hash_archivo = services.validar_excel_stock_inicial(
            tenant,
            archivo,
        )
    except FormatoExcelInvalido as exc:
        return render(
            request,
            "stock_inicial/estado.html",
            {
                "estado": services.estado_stock_inicial(tenant),
                "form": CargaExcelForm(),
                "error": str(exc),
            },
            status=400,
        )

    if not resultado.valido:
        return render(
            request,
            "stock_inicial/estado.html",
            {
                "estado": services.estado_stock_inicial(tenant),
                "form": CargaExcelForm(),
                "resultado": resultado,
                "archivo_nombre": nombre,
                "archivo_hash": hash_archivo,
            },
            status=400,
        )

    # La carga revalida el archivo; hay que devolver el puntero al inicio.
    archivo.seek(0)

    try:
        carga = services.cargar_desde_excel(
            tenant,
            archivo,
            request.usuario,
        )
    except (services.StockInicialYaCargado, services.SerieYaExiste) as exc:
        return render(
            request,
            "stock_inicial/estado.html",
            {
                "estado": services.estado_stock_inicial(tenant),
                "form": CargaExcelForm(),
                "error": str(exc),
            },
            status=409,
        )
    except (FormatoExcelInvalido, services.ValidacionStockInicial) as exc:
        return render(
            request,
            "stock_inicial/estado.html",
            {
                "estado": services.estado_stock_inicial(tenant),
                "form": CargaExcelForm(),
                "error": str(exc),
            },
            status=400,
        )

    messages.success(request, "Stock inicial cargado")
    return redirect("detalle_stock_inicial", carga_id=carga.pk)


@login_required
@require_http_methods(["GET", "POST"])
def formulario_stock_inicial(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    contexto = _contexto_formulario()
    contexto["estado"] = services.estado_stock_inicial(tenant)

    if request.method == "POST":
        lineas = []
        total = int(request.POST.get("lineas-TOTAL_FORMS", "0") or 0)
        for indice in range(total):
            tecnico_id = request.POST.get(f"lineas-{indice}-tecnico_id")
            material_id = request.POST.get(f"lineas-{indice}-material_id")
            series = request.POST.get(f"lineas-{indice}-series", "")
            cantidad = request.POST.get(f"lineas-{indice}-cantidad", "")
            if not tecnico_id and not material_id and not series and not cantidad:
                continue
            lineas.append(
                {
                    "tecnico_id": tecnico_id,
                    "material_id": material_id,
                    "series": series,
                    "cantidad": cantidad,
                }
            )

        try:
            carga = services.cargar_desde_formulario(
                tenant,
                {"lineas": lineas},
                request.usuario,
            )
        except services.StockInicialYaCargado as exc:
            contexto["error"] = str(exc)
            return render(
                request, "stock_inicial/formulario.html", contexto, status=409
            )
        except services.ValidacionStockInicial as exc:
            contexto["error"] = str(exc)
            return render(
                request, "stock_inicial/formulario.html", contexto, status=400
            )

        messages.success(request, "Stock inicial cargado")
        return redirect("detalle_stock_inicial", carga_id=carga.pk)

    contexto["lineas"] = range(3)
    return render(request, "stock_inicial/formulario.html", contexto)


@login_required
@require_GET
def detalle_stock_inicial(request, carga_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    try:
        carga = services.obtener_detalle_carga(tenant, carga_id)
    except services.StockInicialNoExiste as exc:
        return _respuesta(str(exc), 404)

    return render(
        request,
        "stock_inicial/detalle.html",
        {
            "carga": carga,
            "totales": services.totales_carga(carga),
            "grupos": services.listar_lineas_agrupadas(carga),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def editar_stock_inicial(request, carga_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    try:
        carga = services.obtener_detalle_carga(tenant, carga_id)
    except services.StockInicialNoExiste as exc:
        return _respuesta(str(exc), 404)

    if request.method == "POST":
        operaciones = []
        for linea in carga.lineas.all():
            if request.POST.get(f"linea-{linea.pk}-eliminar"):
                operaciones.append({"tipo": "ELIMINAR", "linea_id": linea.pk})
            elif request.POST.get(f"linea-{linea.pk}-cantidad") not in (None, ""):
                operaciones.append(
                    {
                        "tipo": "MODIFICAR",
                        "linea_id": linea.pk,
                        "cantidad": request.POST.get(
                            f"linea-{linea.pk}-cantidad"
                        ),
                    }
                )

        total = int(request.POST.get("nuevas-TOTAL_FORMS", "0") or 0)
        for indice in range(total):
            tecnico_id = request.POST.get(f"nuevas-{indice}-tecnico_id")
            material_id = request.POST.get(f"nuevas-{indice}-material_id")
            series = request.POST.get(f"nuevas-{indice}-series", "")
            cantidad = request.POST.get(f"nuevas-{indice}-cantidad", "")
            if not tecnico_id and not material_id and not series and not cantidad:
                continue
            operaciones.append(
                {
                    "tipo": "AGREGAR",
                    "tecnico_id": tecnico_id,
                    "material_id": material_id,
                    "series": series,
                    "cantidad": cantidad,
                }
            )

        try:
            services.aplicar_edicion_stock_inicial(
                carga, operaciones, request.usuario
            )
        except services.SerieYaExiste as exc:
            return render(
                request,
                "stock_inicial/editar.html",
                {
                    "carga": carga,
                    "totales": services.totales_carga(carga),
                    "grupos": services.listar_lineas_agrupadas(carga),
                    "nuevas_lineas": range(2),
                    "error": str(exc),
                    **_contexto_formulario(),
                },
                status=409,
            )
        except services.ValidacionStockInicial as exc:
            return render(
                request,
                "stock_inicial/editar.html",
                {
                    "carga": carga,
                    "totales": services.totales_carga(carga),
                    "grupos": services.listar_lineas_agrupadas(carga),
                    "nuevas_lineas": range(2),
                    "error": str(exc),
                    **_contexto_formulario(),
                },
                status=400,
            )

        messages.success(request, "Stock inicial actualizado")
        return redirect("detalle_stock_inicial", carga_id=carga.pk)

    return render(
        request,
        "stock_inicial/editar.html",
        {
            "carga": carga,
            "totales": services.totales_carga(carga),
            "grupos": services.listar_lineas_agrupadas(carga),
            "nuevas_lineas": range(2),
            **_contexto_formulario(),
        },
    )
