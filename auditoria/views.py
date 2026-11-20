"""Vistas de consulta de auditoría."""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

from acceso.services import registros_visibles_para

from .services import consultar_auditoria


@login_required
@require_GET
def auditoria_acceso(request):
    actor = getattr(request, "usuario", None)

    registro_id = request.GET.get("registro_id")
    if registro_id:
        if not str(registro_id).isdigit():
            raise Http404
        if not registros_visibles_para(actor).filter(pk=int(registro_id)).exists():
            raise Http404

    pagina = consultar_auditoria(actor, request.GET)
    contexto = {
        "pagina": pagina,
        "registros": pagina.object_list,
        "filtros": request.GET,
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "auditoria/_tabla_auditoria.html", contexto)

    return render(request, "auditoria/acceso_lista.html", contexto)
