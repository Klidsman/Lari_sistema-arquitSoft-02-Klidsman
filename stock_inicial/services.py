"""Servicios de stock inicial de técnicos."""

import re
from dataclasses import dataclass, field
from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from acceso.models import Rol
from auditoria.services import registrar_cambio
from materiales.models import Material
from series.models import EstadoSerie, Serie
from series.services import (
    SerieInvalida,
    crear_serie,
    normalizar_numero,
    series_existentes,
    validar_numero,
)
from stock.services import (
    incrementar_stock_tecnico,
    decrementar_stock_tecnico,
)
from tecnicos.models import Tecnico
from tecnicos.services import normalizar_nif, validar_nif
from tenants.models import Tenant

from .excel import FormatoExcelInvalido, leer_excel_stock_inicial
from .models import CargaStockInicial, LineaStockInicial


class ValidacionStockInicial(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self):
        return self.mensaje


class StockInicialYaCargado(ValidacionStockInicial):
    pass


class StockInicialNoCargado(ValidacionStockInicial):
    pass


class StockInicialNoExiste(ValidacionStockInicial):
    pass


class PermisoDenegado(ValidacionStockInicial):
    pass


class TenantSuspendido(ValidacionStockInicial):
    pass


class TecnicoNoExiste(ValidacionStockInicial):
    pass


class MaterialNoExiste(ValidacionStockInicial):
    pass


class SerieDuplicada(ValidacionStockInicial):
    pass


class SerieYaExiste(ValidacionStockInicial):
    pass


class CantidadInvalida(ValidacionStockInicial):
    pass


class LineaNoEditable(ValidacionStockInicial):
    pass


class EdicionInvalida(ValidacionStockInicial):
    pass


class ReinicioDeshabilitado(ValidacionStockInicial):
    pass


@dataclass(frozen=True)
class ErrorValidacion:
    fila: int | None
    campo: str
    mensaje: str
    valor: str = ""


@dataclass(frozen=True)
class LineaValidada:
    tecnico: Tecnico
    material: Material
    serie: str | None
    cantidad: int
    lote: str
    descripcion: str


@dataclass
class ResultadoValidacionStockInicial:
    valido: bool
    lineas: list = field(default_factory=list)
    errores: list = field(default_factory=list)
    total_tecnicos: int = 0
    total_series: int = 0
    total_cantidad: int = 0

    @property
    def filas_error(self) -> int:
        """Filas con al menos un error, no errores totales."""
        return len({error.fila for error in self.errores})


def validar_cuenta_tenant(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado("No tienes permiso para cargar stock inicial")
    if actor.rol != Rol.USUARIO_TENANT or not actor.tenant_id:
        raise PermisoDenegado("No tienes permiso para cargar stock inicial")
    tenant = actor.tenant
    if tenant.estado != Tenant.ESTADO_ACTIVO:
        raise TenantSuspendido("El tenant está suspendido")
    return tenant


def validar_cuenta_admin(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado("No tienes permiso para reiniciar el stock inicial")
    if actor.rol != Rol.ADMIN_PLATAFORMA:
        raise PermisoDenegado("No tienes permiso para reiniciar el stock inicial")
    return actor


def validar_puede_cargar_stock_inicial(tenant):
    if tenant.stock_inicial_cargado or CargaStockInicial.objects.filter(
        tenant=tenant
    ).exists():
        raise StockInicialYaCargado(
            "El stock inicial ya fue cargado para este tenant"
        )


def validar_puede_editar_stock_inicial(tenant):
    if not tenant.stock_inicial_cargado:
        raise StockInicialNoCargado("El stock inicial aún no ha sido cargado")


def obtener_carga(tenant, carga_id):
    carga = CargaStockInicial.objects.filter(pk=carga_id, tenant=tenant).first()
    if carga is None:
        raise StockInicialNoExiste("El stock inicial no existe")
    return carga


def obtener_linea(carga, linea_id):
    linea = LineaStockInicial.objects.filter(pk=linea_id, carga=carga).first()
    if linea is None:
        raise StockInicialNoExiste("La línea no pertenece al stock inicial")
    return linea


def obtener_detalle_carga(tenant, carga_id):
    carga = obtener_carga(tenant, carga_id)
    return (
        CargaStockInicial.objects.filter(pk=carga.pk)
        .select_related("tenant", "region", "creado_por")
        .prefetch_related("lineas__tecnico", "lineas__material", "lineas__serie")
        .get()
    )


def totales_carga(carga):
    lineas = list(carga.lineas.select_related("tecnico", "material", "serie"))
    return {
        "total_tecnicos": len({linea.tecnico_id for linea in lineas}),
        "total_lineas": len(lineas),
        "total_series": sum(1 for linea in lineas if linea.serie_id),
        "total_cantidad": sum(
            linea.cantidad for linea in lineas if linea.serie_id is None
        ),
    }


def listar_lineas_agrupadas(carga):
    grupos = {}
    for linea in (
        carga.lineas.select_related("tecnico", "material", "serie")
        .order_by("tecnico__nombre", "material__codigo", "serie__numero")
    ):
        grupos.setdefault(linea.tecnico, []).append(linea)
    return grupos


def estado_stock_inicial(tenant):
    carga = CargaStockInicial.objects.filter(tenant=tenant).first()
    return {
        "cargado": tenant.stock_inicial_cargado,
        "carga": carga,
        "totales": totales_carga(carga) if carga else None,
    }


def _nif_normalizado(valor):
    return normalizar_nif(valor)


def _validar_nif(valor):
    try:
        return validar_nif(valor)
    except Exception as exc:
        raise ValidacionStockInicial("El NIF debe tener el formato LAXXXX") from exc


def _cantidad_excel(valor, fila):
    if valor in (None, ""):
        raise ValidacionStockInicial("La cantidad debe ser mayor a 0")
    if isinstance(valor, bool):
        raise ValidacionStockInicial(
            f"La cantidad de la fila {fila} no es un número válido"
        )
    try:
        if isinstance(valor, float) and not valor.is_integer():
            raise ValueError
        cantidad = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValidacionStockInicial(
            f"La cantidad de la fila {fila} no es un número válido"
        ) from exc
    if cantidad <= 0:
        raise ValidacionStockInicial("La cantidad debe ser mayor a 0")
    return cantidad


def _cantidad_formulario(valor):
    if valor in (None, ""):
        raise ValidacionStockInicial("La cantidad debe ser mayor a 0")
    try:
        if isinstance(valor, float) and not valor.is_integer():
            raise ValueError
        cantidad = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValidacionStockInicial(
            "La cantidad no es un número válido"
        ) from exc
    if cantidad <= 0:
        raise ValidacionStockInicial("La cantidad debe ser mayor a 0")
    return cantidad


def _texto(valor):
    return str(valor or "").strip()


def validar_filas_stock_inicial(tenant, filas, es_formulario=False):
    errores = []
    lineas = []
    todos_numeros = []
    vistos = set()

    # Precarga en bloque para evitar consultas por fila.
    nifs = {_texto(f.get("nif")) for f in filas if f.get("nif")}
    codigos = {_texto(f.get("material")) for f in filas if f.get("material")}
    tecnicos = {
        t.nif: t
        for t in Tecnico.objects.filter(tenant=tenant, nif__in=nifs)
    }
    materiales = {
        m.codigo: m
        for m in Material.objects.filter(codigo__in=codigos)
    }
    for fila in filas:
        if fila.get("serie") not in (None, ""):
            todos_numeros.append(normalizar_numero(fila.get("serie")))
    existentes = series_existentes(todos_numeros) if todos_numeros else set()

    no_seriadas = {}

    for fila in filas:
        numero_fila = fila.get("numero_fila")

        try:
            nif = _validar_nif(fila.get("nif"))
        except ValidacionStockInicial as exc:
            errores.append(ErrorValidacion(numero_fila, "tecnico", str(exc)))
            continue
        tecnico = tecnicos.get(nif)
        if tecnico is None:
            errores.append(
                ErrorValidacion(
                    numero_fila,
                    "tecnico",
                    "El técnico no existe en este tenant",
                )
            )
            continue

        codigo = _texto(fila.get("material"))
        material = materiales.get(codigo)
        if material is None:
            errores.append(
                ErrorValidacion(
                    numero_fila,
                    "material",
                    "El material no existe en el catálogo",
                )
            )
            continue

        serie = _texto(fila.get("serie"))
        if material.es_seriado:
            if not serie:
                errores.append(
                    ErrorValidacion(
                        numero_fila,
                        "tipo",
                        "El material es seriado y requiere número de serie",
                    )
                )
                continue
            numero = normalizar_numero(serie)
            try:
                validar_numero(numero)
            except SerieInvalida as exc:
                errores.append(
                    ErrorValidacion(numero_fila, "serie", str(exc))
                )
                continue
            if numero in vistos:
                errores.append(
                    ErrorValidacion(
                        numero_fila,
                        "serie",
                        "La serie está duplicada en la carga",
                    )
                )
                continue
            vistos.add(numero)
            if numero in existentes:
                errores.append(
                    ErrorValidacion(
                        numero_fila,
                        "serie",
                        "La serie ya está registrada en el sistema",
                    )
                )
                continue
            lineas.append(
                LineaValidada(
                    tecnico=tecnico,
                    material=material,
                    serie=numero,
                    cantidad=1,
                    lote=material.lote,
                    descripcion=material.descripcion,
                )
            )
        else:
            if serie:
                errores.append(
                    ErrorValidacion(
                        numero_fila,
                        "tipo",
                        "El material no es seriado y no admite número de serie",
                    )
                )
                continue
            try:
                cantidad = (
                    _cantidad_formulario(fila.get("libre"))
                    if es_formulario
                    else _cantidad_excel(fila.get("libre"), numero_fila)
                )
            except ValidacionStockInicial as exc:
                errores.append(
                    ErrorValidacion(numero_fila, "cantidad", str(exc))
                )
                continue
            clave = (tecnico.pk, material.pk)
            if clave in no_seriadas:
                no_seriadas[clave][1] += cantidad
            else:
                no_seriadas[clave] = [tecnico, material, cantidad]

    for tecnico, material, cantidad in no_seriadas.values():
        lineas.append(
            LineaValidada(
                tecnico=tecnico,
                material=material,
                serie=None,
                cantidad=cantidad,
                lote=material.lote,
                descripcion=material.descripcion,
            )
        )

    return ResultadoValidacionStockInicial(
        valido=not errores,
        lineas=lineas,
        errores=errores,
        total_tecnicos=len({linea.tecnico.pk for linea in lineas}),
        total_series=sum(1 for linea in lineas if linea.serie),
        total_cantidad=sum(
            linea.cantidad for linea in lineas if linea.serie is None
        ),
    )


def validar_excel_stock_inicial(tenant, archivo):
    filas, nombre, hash_archivo = leer_excel_stock_inicial(archivo)
    resultado = validar_filas_stock_inicial(tenant, filas)
    return resultado, nombre, hash_archivo


def validar_formulario_stock_inicial(tenant, datos):
    filas = []
    for indice, linea in enumerate(datos.get("lineas", []), start=2):
        tecnico = Tecnico.objects.filter(
            pk=linea.get("tecnico_id"),
            tenant=tenant,
        ).first()
        material = Material.objects.filter(pk=linea.get("material_id")).first()
        series = str(linea.get("series") or "")
        if material is not None and material.es_seriado:
            numeros = [
                numero
                for numero in re.split(r"[\s,]+", series)
                if numero.strip()
            ]
        else:
            numeros = [series]

        for numero in numeros or [""]:
            filas.append(
                {
                    "numero_fila": indice,
                    "nif": tecnico.nif if tecnico else "",
                    "material": material.codigo if material else "",
                    "serie": numero,
                    "libre": linea.get("cantidad"),
                }
            )
    return validar_filas_stock_inicial(tenant, filas, es_formulario=True)


def auditar_alta_carga(carga, actor):
    valor = (
        f"metodo={carga.metodo}; fecha={carga.fecha.isoformat()}; "
        f"region={carga.region.codigo}; archivo={carga.archivo_nombre}; "
        f"hash={carga.archivo_hash}"
    )
    return registrar_cambio(
        "CargaStockInicial",
        carga.pk,
        "alta",
        "",
        valor,
        actor,
        tenant=carga.tenant,
    )


def cargar_stock_inicial(
    tenant,
    resultado,
    metodo,
    actor,
    archivo_nombre="",
    archivo_hash="",
):
    if tenant.pk != getattr(getattr(actor, "tenant", None), "pk", None):
        raise PermisoDenegado("No tienes permiso para cargar stock inicial")
    validar_puede_cargar_stock_inicial(tenant)
    if not resultado.valido or not resultado.lineas:
        mensaje = (
            resultado.errores[0].mensaje
            if resultado.errores
            else "No hay líneas válidas para cargar"
        )
        raise ValidacionStockInicial(mensaje)

    try:
        with transaction.atomic():
            bloqueado = Tenant.objects.select_for_update().get(pk=tenant.pk)
            if bloqueado.stock_inicial_cargado or CargaStockInicial.objects.filter(
                tenant=bloqueado
            ).exists():
                raise StockInicialYaCargado(
                    "El stock inicial ya fue cargado para este tenant"
                )

            carga = CargaStockInicial.objects.create(
                tenant=bloqueado,
                region=bloqueado.region,
                metodo=metodo,
                archivo_nombre=archivo_nombre,
                archivo_hash=archivo_hash,
                creado_por=actor,
            )
            ahora = timezone.now()
            cantidades = {}
            tecnicos_por_id = {}
            materiales_por_id = {}

            for linea in resultado.lineas:
                serie = None
                if linea.serie:
                    serie = crear_serie(
                        bloqueado,
                        bloqueado.region,
                        linea.material,
                        linea.serie,
                        linea.material.lote,
                        actor,
                        estado=EstadoSerie.ASIGNADA,
                        tecnico=linea.tecnico,
                        asignada_en=ahora,
                    )
                    registrar_cambio(
                        "Serie",
                        serie.pk,
                        "alta",
                        "",
                        f"numero={serie.numero}; tecnico={linea.tecnico.nif}",
                        actor,
                        tenant=bloqueado,
                    )

                linea_obj = LineaStockInicial.objects.create(
                    tenant=bloqueado,
                    carga=carga,
                    tecnico=linea.tecnico,
                    material=linea.material,
                    lote=linea.material.lote,
                    serie=serie,
                    cantidad=linea.cantidad,
                )
                registrar_cambio(
                    "LineaStockInicial",
                    linea_obj.pk,
                    "alta",
                    "",
                    f"tecnico={linea.tecnico.nif}; material={linea.material.codigo}; "
                    f"serie={linea.serie or ''}; cantidad={linea.cantidad}",
                    actor,
                    tenant=bloqueado,
                )

                clave = (linea.tecnico.pk, linea.material.pk)
                cantidades[clave] = cantidades.get(clave, 0) + linea.cantidad
                tecnicos_por_id[linea.tecnico.pk] = linea.tecnico
                materiales_por_id[linea.material.pk] = linea.material

            for clave, cantidad in cantidades.items():
                incrementar_stock_tecnico(
                    tecnicos_por_id[clave[0]],
                    materiales_por_id[clave[1]],
                    cantidad,
                    actor,
                )

            bloqueado.stock_inicial_cargado = True
            bloqueado.fecha_stock_inicial = ahora
            bloqueado.actualizado_por = actor
            bloqueado.save(
                update_fields=[
                    "stock_inicial_cargado",
                    "fecha_stock_inicial",
                    "actualizado_por",
                    "actualizado_en",
                ]
            )
            registrar_cambio(
                "Tenant",
                bloqueado.pk,
                "stock_inicial_cargado",
                False,
                True,
                actor,
                tenant=bloqueado,
            )
            registrar_cambio(
                "Tenant",
                bloqueado.pk,
                "fecha_stock_inicial",
                "",
                ahora.isoformat(),
                actor,
                tenant=bloqueado,
            )
            auditar_alta_carga(carga, actor)
    except IntegrityError as exc:
        if CargaStockInicial.objects.filter(tenant=tenant).exists():
            raise StockInicialYaCargado(
                "El stock inicial ya fue cargado para este tenant"
            ) from exc
        raise SerieYaExiste("La serie ya está registrada en el sistema") from exc

    return carga


def cargar_desde_excel(tenant, archivo, actor):
    resultado, nombre, hash_archivo = validar_excel_stock_inicial(
        tenant, archivo
    )
    return cargar_stock_inicial(
        tenant,
        resultado,
        CargaStockInicial.METODO_EXCEL,
        actor,
        archivo_nombre=nombre,
        archivo_hash=hash_archivo,
    )


def cargar_desde_formulario(tenant, datos, actor):
    resultado = validar_formulario_stock_inicial(tenant, datos)
    return cargar_stock_inicial(
        tenant,
        resultado,
        CargaStockInicial.METODO_FORMULARIO,
        actor,
    )


def aplicar_edicion_stock_inicial(carga, operaciones, actor):
    tenant = carga.tenant
    if actor.tenant_id != tenant.pk:
        raise PermisoDenegado("No tienes permiso para editar el stock inicial")
    validar_puede_editar_stock_inicial(tenant)
    if not operaciones:
        raise EdicionInvalida("No se enviaron cambios")

    with transaction.atomic():
        Tenant.objects.select_for_update().get(pk=tenant.pk)
        carga = CargaStockInicial.objects.select_for_update().get(pk=carga.pk)

        for operacion in operaciones:
            tipo = operacion.get("tipo")
            if tipo == "ELIMINAR":
                linea = obtener_linea(carga, operacion.get("linea_id"))
                if linea.serie_id:
                    if linea.serie.tecnico_id != linea.tecnico_id:
                        raise EdicionInvalida(
                            "La serie ya no pertenece al stock inicial del técnico"
                        )
                    decrementar_stock_tecnico(
                        linea.tecnico, linea.material, 1, actor
                    )
                    serie = linea.serie
                    linea.serie = None
                    linea.save(update_fields=["serie"])
                    registrar_cambio(
                        "LineaStockInicial",
                        linea.pk,
                        "baja",
                        f"serie={serie.numero}",
                        "",
                        actor,
                        tenant=tenant,
                    )
                    linea.delete()
                    serie.delete()
                else:
                    decrementar_stock_tecnico(
                        linea.tecnico,
                        linea.material,
                        linea.cantidad,
                        actor,
                    )
                    registrar_cambio(
                        "LineaStockInicial",
                        linea.pk,
                        "baja",
                        f"cantidad={linea.cantidad}",
                        "",
                        actor,
                        tenant=tenant,
                    )
                    linea.delete()
            elif tipo == "MODIFICAR":
                linea = obtener_linea(carga, operacion.get("linea_id"))
                if linea.serie_id:
                    raise EdicionInvalida(
                        "La línea no es de un material no seriado"
                    )
                nueva = _cantidad_formulario(operacion.get("cantidad"))
                if nueva > linea.cantidad:
                    incrementar_stock_tecnico(
                        linea.tecnico,
                        linea.material,
                        nueva - linea.cantidad,
                        actor,
                    )
                elif nueva < linea.cantidad:
                    decrementar_stock_tecnico(
                        linea.tecnico,
                        linea.material,
                        linea.cantidad - nueva,
                        actor,
                    )
                registrar_cambio(
                    "LineaStockInicial",
                    linea.pk,
                    "cantidad",
                    linea.cantidad,
                    nueva,
                    actor,
                    tenant=tenant,
                )
                linea.cantidad = nueva
                linea.save(update_fields=["cantidad"])
            elif tipo == "AGREGAR":
                material = Material.objects.filter(
                    pk=operacion.get("material_id")
                ).first()
                tecnico = Tecnico.objects.filter(
                    pk=operacion.get("tecnico_id"), tenant=tenant
                ).first()
                if material is None:
                    raise EdicionInvalida("El material no existe en el catálogo")
                if tecnico is None:
                    raise EdicionInvalida("El técnico no existe en este tenant")
                if material.es_seriado:
                    numeros = [
                        normalizar_numero(n)
                        for n in str(operacion.get("series") or "").replace(
                            ",", "\n"
                        ).splitlines()
                        if n.strip()
                    ]
                    for numero in numeros:
                        try:
                            validar_numero(numero)
                        except SerieInvalida as exc:
                            raise EdicionInvalida(str(exc)) from exc
                        if Serie.objects.filter(numero=numero).exists():
                            raise SerieYaExiste(
                                "La serie ya está registrada en el sistema"
                            )
                        serie = crear_serie(
                            tenant,
                            tenant.region,
                            material,
                            numero,
                            material.lote,
                            actor,
                            estado=EstadoSerie.ASIGNADA,
                            tecnico=tecnico,
                            asignada_en=timezone.now(),
                        )
                        LineaStockInicial.objects.create(
                            tenant=tenant,
                            carga=carga,
                            tecnico=tecnico,
                            material=material,
                            lote=material.lote,
                            serie=serie,
                            cantidad=1,
                        )
                        incrementar_stock_tecnico(tecnico, material, 1, actor)
                else:
                    cantidad = _cantidad_formulario(operacion.get("cantidad"))
                    existente = LineaStockInicial.objects.filter(
                        carga=carga,
                        tecnico=tecnico,
                        material=material,
                        serie__isnull=True,
                    ).first()
                    if existente:
                        incrementar_stock_tecnico(
                            tecnico, material, cantidad, actor
                        )
                        registrar_cambio(
                            "LineaStockInicial",
                            existente.pk,
                            "cantidad",
                            existente.cantidad,
                            existente.cantidad + cantidad,
                            actor,
                            tenant=tenant,
                        )
                        existente.cantidad += cantidad
                        existente.save(update_fields=["cantidad"])
                    else:
                        linea = LineaStockInicial.objects.create(
                            tenant=tenant,
                            carga=carga,
                            tecnico=tecnico,
                            material=material,
                            lote=material.lote,
                            serie=None,
                            cantidad=cantidad,
                        )
                        incrementar_stock_tecnico(
                            tecnico, material, cantidad, actor
                        )
                        registrar_cambio(
                            "LineaStockInicial",
                            linea.pk,
                            "alta",
                            "",
                            f"cantidad={cantidad}",
                            actor,
                            tenant=tenant,
                        )
            else:
                raise EdicionInvalida("Operación de edición no válida")

    return carga


def reiniciar_stock_inicial(tenant, actor):
    from django.conf import settings

    if not settings.PERMITIR_REINICIO_STOCK_INICIAL:
        raise ReinicioDeshabilitado(
            "El reinicio del stock inicial está deshabilitado"
        )
    validar_cuenta_admin(actor)
    carga = CargaStockInicial.objects.filter(tenant=tenant).first()
    if carga is None:
        raise StockInicialNoCargado(
            "No hay stock inicial cargado para reiniciar"
        )
    with transaction.atomic():
        Tenant.objects.select_for_update().get(pk=tenant.pk)
        lineas = list(
            carga.lineas.select_related("tecnico", "material", "serie")
        )
        series = [linea.serie for linea in lineas if linea.serie_id]
        for linea in lineas:
            decrementar_stock_tecnico(
                linea.tecnico, linea.material, linea.cantidad, actor
            )
        carga.lineas.all().delete()
        for serie in series:
            serie.delete()
        carga.delete()
        tenant.stock_inicial_cargado = False
        tenant.fecha_stock_inicial = None
        tenant.actualizado_por = actor
        tenant.save(
            update_fields=[
                "stock_inicial_cargado",
                "fecha_stock_inicial",
                "actualizado_por",
                "actualizado_en",
            ]
        )
        registrar_cambio(
            "Tenant",
            tenant.pk,
            "stock_inicial_cargado",
            True,
            False,
            actor,
            tenant=tenant,
        )
