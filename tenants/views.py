"""Vistas de regiones, almacenes y tenants."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from acceso.decorators import requiere_rol
from acceso.models import Rol

from . import services
from .forms import AlmacenForm, RegionForm, TenantForm
from .models import Region, Tenant


def _peticion_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _primer_error(*formularios) -> str:
    for formulario in formularios:
        for errores in formulario.errors.values():
            if errores:
                return errores[0]
    return "Revisa los datos ingresados"


def _error(request, mensaje, status, plantilla, contexto):
    if _peticion_htmx(request):
        return JsonResponse({"mensaje": mensaje}, status=status)
    return render(
        request,
        plantilla,
        {**contexto, "error": mensaje},
        status=status,
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET"])
def listar_regiones(request):
    regiones = (
        Region.objects.select_related("almacen")
        .annotate(num_tenants=Count("tenants"))
        .order_by("codigo")
    )
    pagina = Paginator(regiones, 50).get_page(request.GET.get("page"))
    contexto = {"pagina": pagina, "regiones": pagina.object_list}

    if _peticion_htmx(request):
        return render(request, "tenants/_tabla_regiones.html", contexto)

    return render(request, "tenants/regiones_lista.html", contexto)


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET", "POST"])
def crear_region(request):
    if request.method == "POST":
        form_region = RegionForm(request.POST)
        form_almacen = AlmacenForm(request.POST)
        contexto = {"form_region": form_region, "form_almacen": form_almacen}

        if form_region.is_valid() and form_almacen.is_valid():
            datos = {**form_region.cleaned_data, **form_almacen.cleaned_data}
            try:
                services.crear_region(datos, request.usuario)
            except services.RegionDuplicada:
                return _error(
                    request,
                    services.RegionDuplicada.mensaje,
                    409,
                    "tenants/region_form.html",
                    contexto,
                )
            except services.RegionInvalida as exc:
                return _error(
                    request,
                    str(exc),
                    400,
                    "tenants/region_form.html",
                    contexto,
                )

            messages.success(request, "Región creada")
            return redirect("listar_regiones")

        return _error(
            request,
            _primer_error(form_region, form_almacen),
            400,
            "tenants/region_form.html",
            contexto,
        )

    return render(
        request,
        "tenants/region_form.html",
        {"form_region": RegionForm(), "form_almacen": AlmacenForm()},
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET", "POST"])
def editar_region(request, region_id):
    region = get_object_or_404(Region, pk=region_id)
    almacen = getattr(region, "almacen", None)

    if request.method == "POST":
        form_region = RegionForm(request.POST, instance=region)
        form_almacen = AlmacenForm(request.POST, con_activa=True)
        contexto = {
            "form_region": form_region,
            "form_almacen": form_almacen,
            "region": region,
        }

        if form_region.is_valid() and form_almacen.is_valid():
            datos = {**form_region.cleaned_data, **form_almacen.cleaned_data}
            try:
                services.actualizar_region(region, datos, request.usuario)
            except services.RegionInvalida as exc:
                return _error(
                    request,
                    str(exc),
                    400,
                    "tenants/region_form.html",
                    contexto,
                )

            messages.success(request, "Región actualizada")
            return redirect("listar_regiones")

        return _error(
            request,
            _primer_error(form_region, form_almacen),
            400,
            "tenants/region_form.html",
            contexto,
        )

    return render(
        request,
        "tenants/region_form.html",
        {
            "form_region": RegionForm(instance=region),
            "form_almacen": AlmacenForm(
                con_activa=True,
                initial={
                    "centro": almacen.centro if almacen else "",
                    "almacen": almacen.codigo_almacen if almacen else "",
                    "buzon": almacen.buzon if almacen else "",
                    "activa": region.activa,
                },
            ),
            "region": region,
        },
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET"])
def listar_tenants(request):
    tenants = (
        Tenant.objects.select_related("region")
        .order_by("codigo")
    )
    pagina = Paginator(tenants, 50).get_page(request.GET.get("page"))
    contexto = {"pagina": pagina, "tenants": pagina.object_list}

    if _peticion_htmx(request):
        return render(request, "tenants/_tabla_tenants.html", contexto)

    return render(request, "tenants/tenants_lista.html", contexto)


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET", "POST"])
def crear_tenant(request):
    if request.method == "POST":
        formulario = TenantForm(request.POST)
        contexto = {"formulario": formulario}

        if formulario.is_valid():
            try:
                tenant = services.crear_tenant(
                    formulario.cleaned_data,
                    request.usuario,
                )
            except services.TenantDuplicado:
                return _error(
                    request,
                    services.TenantDuplicado.mensaje,
                    409,
                    "tenants/tenant_form.html",
                    contexto,
                )
            except services.TenantInvalido as exc:
                return _error(
                    request,
                    str(exc),
                    400,
                    "tenants/tenant_form.html",
                    contexto,
                )

            messages.success(request, "Tenant creado")
            return redirect("detalle_tenant", tenant_id=tenant.pk)

        return _error(
            request,
            _primer_error(formulario),
            400,
            "tenants/tenant_form.html",
            contexto,
        )

    return render(
        request,
        "tenants/tenant_form.html",
        {"formulario": TenantForm()},
    )


def _contexto_detalle(tenant):
    cuenta = tenant.usuarios.filter(rol=Rol.USUARIO_TENANT).first()
    return {"tenant": tenant, "cuenta": cuenta}


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_http_methods(["GET"])
def detalle_tenant(request, tenant_id):
    tenant = get_object_or_404(
        Tenant.objects.select_related("region"),
        pk=tenant_id,
    )
    return render(
        request,
        "tenants/tenant_detalle.html",
        _contexto_detalle(tenant),
    )


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_POST
def suspender_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)

    if tenant.estado == Tenant.ESTADO_SUSPENDIDO:
        return render(
            request,
            "tenants/tenant_detalle.html",
            _contexto_detalle(tenant),
        )

    services.suspender_tenant(tenant, request.usuario)
    messages.success(request, "Tenant suspendido")
    return redirect("detalle_tenant", tenant_id=tenant.pk)


@requiere_rol(Rol.ADMIN_PLATAFORMA)
@require_POST
def activar_tenant(request, tenant_id):
    tenant = get_object_or_404(Tenant, pk=tenant_id)

    if tenant.estado == Tenant.ESTADO_ACTIVO:
        return render(
            request,
            "tenants/tenant_detalle.html",
            _contexto_detalle(tenant),
        )

    services.activar_tenant(tenant, request.usuario)
    messages.success(request, "Tenant activado")
    return redirect("detalle_tenant", tenant_id=tenant.pk)
