"""Vistas de recojos."""

from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from materiales.models import Material

from . import services
from .forms import LineaRecojoFormSet, RecojoForm


def _respuesta(mensaje, status):
    return HttpResponse(
        mensaje,
        status=status,
        content_type="text/html; charset=utf-8",
    )


def _tenant_o_error(request):
    try:
        return services.validar_cuenta_tenant(request.usuario), None
    except (services.PermisoDenegado, services.TenantSuspendido) as exc:
        return None, _respuesta(str(exc), 403)


def _contexto_formulario(form, formset):
    return {
        "form": form,
        "formset": formset,
        "materiales": Material.objects.filter(activo=True).order_by("codigo"),
    }


@login_required
@require_GET
def lista_recojos(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    q = request.GET.get("q", "")
    estado = request.GET.get("estado", "todos")
    if estado not in {"todos", "registrados", "anulados"}:
        estado = "todos"
    pagina = Paginator(
        services.listar_recojos(tenant, q, estado),
        50,
    ).get_page(request.GET.get("page"))
    return render(
        request,
        "recojos/recojos_lista.html",
        {
            "pagina": pagina,
            "recojos": pagina.object_list,
            "q": q,
            "estado": estado,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def crear_recojo(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    if request.method == "POST":
        form = RecojoForm(request.POST)
        formset = LineaRecojoFormSet(request.POST, prefix="lineas")
        contexto = _contexto_formulario(form, formset)

        if form.is_valid() and formset.is_valid():
            lineas = []
            for linea in formset.cleaned_data:
                if not (
                    linea.get("material_id")
                    or linea.get("material_codigo")
                    or linea.get("series")
                    or linea.get("cantidad")
                ):
                    continue

                material_id = linea.get("material_id")
                if not material_id and linea.get("material_codigo"):
                    material = Material.objects.filter(
                        codigo=linea["material_codigo"].strip()
                    ).first()
                    material_id = material.pk if material else None

                lineas.append(
                    {
                        "material_id": material_id,
                        "series": linea.get("series"),
                        "cantidad": linea.get("cantidad"),
                    }
                )

            datos = {
                "nombre": form.cleaned_data["nombre"],
                "fecha": form.cleaned_data["fecha"],
                "lineas": lineas,
            }
            try:
                recojo = services.crear_recojo(datos, request.usuario)
            except services.RecojoInvalido as exc:
                return render(
                    request,
                    "recojos/recojo_form.html",
                    {
                        "error": str(exc),
                        "resultado": exc.resultado,
                        **contexto,
                    },
                    status=400,
                )
            except services.SerieYaExiste:
                return render(
                    request,
                    "recojos/recojo_form.html",
                    {
                        "error": services.SerieYaExiste.mensaje,
                        **contexto,
                    },
                    status=409,
                )
            except services.RegionIncorrecta as exc:
                return render(
                    request,
                    "recojos/recojo_form.html",
                    {"error": str(exc), **contexto},
                    status=400,
                )

            return redirect("detalle_recojo", recojo_id=recojo.pk)

        primer_error = next(
            (
                errores[0]
                for errores in list(form.errors.values())
                + list(formset.errors)
                if errores
            ),
            "Revisa los datos ingresados",
        )
        return render(
            request,
            "recojos/recojo_form.html",
            {"error": primer_error, **contexto},
            status=400,
        )

    return render(
        request,
        "recojos/recojo_form.html",
        _contexto_formulario(
            RecojoForm(initial={"fecha": date.today()}),
            LineaRecojoFormSet(prefix="lineas"),
        ),
    )


def _contexto_detalle(recojo, error=None):
    puede_anular, mensaje_anulacion = services.puede_anular_recojo(recojo)
    return {
        "recojo": recojo,
        "totales": services.totales_recojo(recojo),
        "puede_anular": puede_anular,
        "mensaje_anulacion": mensaje_anulacion,
        "error": error,
    }


@login_required
@require_GET
def detalle_recojo(request, recojo_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    try:
        recojo = services.obtener_detalle_recojo(tenant, recojo_id)
    except services.NoEncontrado as exc:
        return _respuesta(str(exc), 404)

    return render(
        request,
        "recojos/recojo_detalle.html",
        _contexto_detalle(recojo),
    )


@login_required
@require_POST
def anular_recojo(request, recojo_id):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    try:
        recojo = services.obtener_detalle_recojo(tenant, recojo_id)
    except services.NoEncontrado as exc:
        return _respuesta(str(exc), 404)

    try:
        services.anular_recojo(
            recojo,
            request.POST.get("motivo", ""),
            request.usuario,
        )
    except services.MotivoAnulacionInvalido as exc:
        return render(
            request,
            "recojos/recojo_detalle.html",
            _contexto_detalle(recojo, error=str(exc)),
            status=400,
        )
    except services.AnulacionNoPermitida as exc:
        return render(
            request,
            "recojos/recojo_detalle.html",
            _contexto_detalle(recojo, error=str(exc)),
            status=409,
        )

    return redirect("detalle_recojo", recojo_id=recojo.pk)


@login_required
@require_POST
def validar_series(request):
    tenant, error = _tenant_o_error(request)
    if error is not None:
        return error

    material = None
    material_id = request.POST.get("material_id", "")
    material_codigo = (request.POST.get("material_codigo") or "").strip()

    if material_id:
        try:
            material = Material.objects.filter(
                pk=int(material_id), activo=True
            ).first()
        except (TypeError, ValueError):
            material = None
    elif material_codigo:
        material = Material.objects.filter(
            codigo=material_codigo, activo=True
        ).first()

    if material is None:
        return _respuesta("El material no existe en el catálogo", 404)

    try:
        estados = services.previsualizar_series(
            tenant,
            material,
            request.POST.get("series", ""),
        )
    except services.MaterialNoValido as exc:
        return _respuesta(str(exc), 400)

    return render(
        request,
        "recojos/_vista_previa_series.html",
        {"estados": estados},
    )
