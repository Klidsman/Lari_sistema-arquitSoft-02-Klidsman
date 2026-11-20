"""Servicios del catálogo de materiales."""

import re

from django.db import IntegrityError, transaction
from django.db.models import Q

from acceso.models import Rol
from auditoria.services import registrar_cambio

from .models import Material

PATRON_CODIGO = re.compile(r"^[0-9]{11}$")
TIPOS = {"SERIADO", "NO_SERIADO"}


class ValidacionMaterial(Exception):
    pass


class MaterialDuplicado(Exception):
    mensaje = "El material ya existe"


class PermisoDenegado(Exception):
    mensaje = "No tienes permiso para editar este material"


def normalizar_codigo(codigo) -> str:
    return (codigo or "").strip()


def normalizar_descripcion(descripcion) -> str:
    return " ".join((descripcion or "").split())


def normalizar_lote(lote) -> str:
    return " ".join((lote or "").split()).upper()


def _normalizar_tipo(valor):
    if isinstance(valor, bool):
        return valor
    if valor in TIPOS:
        return valor == "SERIADO"
    raise ValidacionMaterial("El tipo es obligatorio")


def validar_datos_material(datos) -> dict:
    codigo = normalizar_codigo(datos.get("codigo"))
    descripcion = normalizar_descripcion(datos.get("descripcion"))
    lote = normalizar_lote(datos.get("lote"))
    tipo = datos.get("tipo") if "tipo" in datos else datos.get("es_seriado")

    if not PATRON_CODIGO.match(codigo):
        raise ValidacionMaterial("El código debe tener 11 dígitos")
    if not descripcion:
        raise ValidacionMaterial("La descripción es obligatoria")
    if len(descripcion) > 100:
        raise ValidacionMaterial(
            "La descripción no puede superar los 100 caracteres"
        )
    if len(lote) > 50:
        raise ValidacionMaterial("El lote no puede superar los 50 caracteres")

    es_seriado = _normalizar_tipo(tipo)

    return {
        "codigo": codigo,
        "descripcion": descripcion,
        "lote": lote,
        "es_seriado": es_seriado,
        "tipo": "SERIADO" if es_seriado else "NO_SERIADO",
    }


def auditar_alta_material(material, usuario):
    valor = (
        f"codigo={material.codigo}; descripcion={material.descripcion}; "
        f"lote={material.lote}; tipo={material.tipo}"
    )
    return registrar_cambio(
        "Material",
        material.pk,
        "alta",
        "",
        valor,
        usuario,
    )


def auditar_cambios_material(material, cambios, usuario):
    registros = []
    for campo, anterior, nuevo in cambios:
        registros.append(
            registrar_cambio(
                "Material",
                material.pk,
                campo,
                anterior,
                nuevo,
                usuario,
            )
        )
    return registros


def _reactivar_material(material: Material, limpios, usuario) -> Material:
    """Reactiva un material dado de baja y actualiza sus datos."""
    with transaction.atomic():
        bloqueado = Material.objects.select_for_update().get(pk=material.pk)
        if bloqueado.activo:
            raise MaterialDuplicado

        cambios = []

        if limpios["descripcion"] != bloqueado.descripcion:
            cambios.append(
                ("descripcion", bloqueado.descripcion, limpios["descripcion"])
            )
            bloqueado.descripcion = limpios["descripcion"]

        if limpios["lote"] != bloqueado.lote:
            cambios.append(("lote", bloqueado.lote, limpios["lote"]))
            bloqueado.lote = limpios["lote"]

        if limpios["es_seriado"] != bloqueado.es_seriado:
            if not puede_cambiar_tipo(bloqueado):
                raise ValidacionMaterial(
                    "El tipo no se puede cambiar: el material tiene movimientos"
                )
            cambios.append(("tipo", bloqueado.tipo, limpios["tipo"]))
            bloqueado.es_seriado = limpios["es_seriado"]

        bloqueado.activo = True
        bloqueado.actualizado_por = usuario
        bloqueado.save(
            update_fields=[
                "descripcion",
                "lote",
                "es_seriado",
                "activo",
                "actualizado_por",
                "actualizado_en",
            ]
        )

        auditar_cambios_material(bloqueado, cambios, usuario)
        registrar_cambio(
            "Material",
            bloqueado.pk,
            "activo",
            False,
            True,
            usuario,
        )

    return bloqueado


def crear_material(datos, usuario) -> Material:
    if usuario is None or not getattr(usuario, "is_active", False):
        raise PermisoDenegado("La cuenta está desactivada")
    if usuario.rol != Rol.RESPONSABLE_ALMACEN:
        raise PermisoDenegado(
            "Solo el Responsable de almacén puede registrar materiales"
        )

    limpios = validar_datos_material(datos)

    existente = Material.objects.filter(codigo=limpios["codigo"]).first()
    if existente is not None:
        if existente.activo:
            raise MaterialDuplicado
        return _reactivar_material(existente, limpios, usuario)

    try:
        with transaction.atomic():
            material = Material.objects.create(
                codigo=limpios["codigo"],
                descripcion=limpios["descripcion"],
                lote=limpios["lote"],
                es_seriado=limpios["es_seriado"],
                activo=True,
                creado_por=usuario,
            )
            auditar_alta_material(material, usuario)
    except IntegrityError as exc:
        existente = Material.objects.filter(codigo=limpios["codigo"]).first()
        if existente is not None and not existente.activo:
            return _reactivar_material(existente, limpios, usuario)
        raise MaterialDuplicado from exc

    return material


def listar_materiales():
    return Material.objects.filter(activo=True).order_by("codigo")


def buscar_materiales(q: str = ""):
    materiales = Material.objects.filter(activo=True)
    q = (q or "").strip()
    if q:
        materiales = materiales.filter(
            Q(codigo__icontains=q) | Q(descripcion__icontains=q)
        )
    return materiales.order_by("codigo")


def obtener_datos_material(material) -> dict:
    return {
        "codigo": material.codigo,
        "descripcion": material.descripcion,
        "lote": material.lote,
        "tipo": material.tipo,
    }


def puede_editar_material(material, usuario) -> bool:
    """Cualquier almacén activo edita cualquier material; el admin también."""
    if usuario is None or not getattr(usuario, "is_active", False):
        return False
    if not material.activo:
        return False
    return usuario.rol in {
        Rol.RESPONSABLE_ALMACEN,
        Rol.ADMIN_PLATAFORMA,
    }


def dar_de_baja_material(material: Material, usuario) -> Material:
    """Baja lógica: oculta el material sin borrar la fila ni su auditoría."""
    if usuario is None or not getattr(usuario, "is_active", False):
        raise PermisoDenegado("La cuenta está desactivada")
    if usuario.rol != Rol.RESPONSABLE_ALMACEN:
        raise PermisoDenegado(
            "Solo el Responsable de almacén puede dar de baja materiales"
        )

    with transaction.atomic():
        bloqueado = Material.objects.select_for_update().get(pk=material.pk)
        if not bloqueado.activo:
            return bloqueado

        bloqueado.activo = False
        bloqueado.actualizado_por = usuario
        bloqueado.save(
            update_fields=["activo", "actualizado_por", "actualizado_en"]
        )
        registrar_cambio(
            "Material",
            bloqueado.pk,
            "activo",
            True,
            False,
            usuario,
        )

    return bloqueado


_VERIFICACIONES_MOVIMIENTOS = []


def registrar_verificacion_movimientos(func):
    """Registra una verificación de stock/movimientos y devuelve su baja."""
    _VERIFICACIONES_MOVIMIENTOS.append(func)

    def desregistrar():
        if func in _VERIFICACIONES_MOVIMIENTOS:
            _VERIFICACIONES_MOVIMIENTOS.remove(func)

    return desregistrar


def puede_cambiar_tipo(material) -> bool:
    for verificar in list(_VERIFICACIONES_MOVIMIENTOS):
        try:
            if verificar(material):
                return False
        except Exception:
            # Fallo seguro: ante una verificación rota, se asume que hay movimientos.
            return False
    return True


def actualizar_material(material: Material, cambios, usuario) -> Material:
    if not puede_editar_material(material, usuario):
        raise PermisoDenegado

    if "codigo" in cambios:
        raise ValidacionMaterial("El código no se puede cambiar")

    with transaction.atomic():
        bloqueado = Material.objects.select_for_update().get(pk=material.pk)

        if not puede_editar_material(bloqueado, usuario):
            raise PermisoDenegado

        cambios_auditoria = []
        campos_actualizados = []

        if "descripcion" in cambios:
            descripcion = normalizar_descripcion(cambios.get("descripcion"))
            if not descripcion:
                raise ValidacionMaterial("La descripción es obligatoria")
            if len(descripcion) > 100:
                raise ValidacionMaterial(
                    "La descripción no puede superar los 100 caracteres"
                )
            if descripcion != bloqueado.descripcion:
                cambios_auditoria.append(
                    ("descripcion", bloqueado.descripcion, descripcion)
                )
                bloqueado.descripcion = descripcion
                campos_actualizados.append("descripcion")

        if "lote" in cambios:
            lote = normalizar_lote(cambios.get("lote"))
            if len(lote) > 50:
                raise ValidacionMaterial(
                    "El lote no puede superar los 50 caracteres"
                )
            if lote != bloqueado.lote:
                cambios_auditoria.append(("lote", bloqueado.lote, lote))
                bloqueado.lote = lote
                campos_actualizados.append("lote")

        if "tipo" in cambios or "es_seriado" in cambios:
            valor = cambios["tipo"] if "tipo" in cambios else cambios["es_seriado"]
            nuevo_seriado = _normalizar_tipo(valor)
            if nuevo_seriado != bloqueado.es_seriado:
                if not puede_cambiar_tipo(bloqueado):
                    raise ValidacionMaterial(
                        "El tipo no se puede cambiar: el material tiene movimientos"
                    )
                cambios_auditoria.append(
                    ("tipo", bloqueado.tipo, "SERIADO" if nuevo_seriado else "NO_SERIADO")
                )
                bloqueado.es_seriado = nuevo_seriado
                campos_actualizados.append("es_seriado")

        if cambios_auditoria:
            bloqueado.actualizado_por = usuario
            bloqueado.save(
                update_fields=campos_actualizados
                + ["actualizado_por", "actualizado_en"]
            )
            auditar_cambios_material(bloqueado, cambios_auditoria, usuario)

    return bloqueado
