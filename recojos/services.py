"""Servicios de recojos de materiales."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from acceso.models import Rol
from auditoria.services import registrar_cambio
from materiales.models import Material
from series.models import EstadoSerie, Serie
from series.services import (
    SerieInvalida,
    extraer_numeros,
    normalizar_numero,
    series_existentes,
    validar_numero,
)
from stock.models import StockGeneral
from stock.services import (
    StockInsuficiente,
    decrementar_stock_general,
    incrementar_stock_general,
)
from tenants.models import Tenant

from .models import EstadoRecojo, LineaRecojo, Recojo

PLAZO_ANULACION_HORAS = 24


class ValidacionRecojo(Exception):
    pass


class RecojoInvalido(Exception):
    def __init__(self, mensaje, resultado=None):
        super().__init__(mensaje)
        self.resultado = resultado


class MaterialNoValido(Exception):
    pass


class PermisoDenegado(Exception):
    mensaje = "No tienes permiso para registrar recojos"

    def __str__(self):
        return self.mensaje


class NoEncontrado(Exception):
    mensaje = "El recojo no existe"

    def __str__(self):
        return self.mensaje


class TenantSuspendido(Exception):
    mensaje = "El tenant está suspendido"

    def __str__(self):
        return self.mensaje


class RegionIncorrecta(Exception):
    mensaje = "La región del tenant no tiene almacén configurado"

    def __str__(self):
        return self.mensaje


class RecojoNoEncontrado(NoEncontrado):
    pass


class MotivoAnulacionInvalido(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self):
        return self.mensaje


class AnulacionNoPermitida(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje

    def __str__(self):
        return self.mensaje


class PlazoAnulacionVencido(AnulacionNoPermitida):
    pass


@dataclass
class ResultadoValidacion:
    valido: bool
    fecha: date | None
    nombre: str | None = None
    lineas: list = field(default_factory=list)
    series_estados: list = field(default_factory=list)
    series_reutilizables: dict = field(default_factory=dict)
    errores: list = field(default_factory=list)


def normalizar_nombre_recojo(nombre) -> str:
    return " ".join((nombre or "").split())


def validar_cuenta_tenant(actor):
    if actor is None or not getattr(actor, "is_active", False):
        raise PermisoDenegado
    if actor.rol != Rol.USUARIO_TENANT or not actor.tenant_id:
        raise PermisoDenegado

    tenant = actor.tenant
    if tenant.estado != Tenant.ESTADO_ACTIVO:
        raise TenantSuspendido
    return tenant


def validar_region_tenant(tenant):
    region = tenant.region
    if region is None or not hasattr(region, "almacen"):
        raise RegionIncorrecta
    return region


def obtener_recojo(tenant, recojo_id) -> Recojo:
    recojo = Recojo.objects.filter(tenant=tenant, pk=recojo_id).first()
    if recojo is None:
        raise NoEncontrado
    return recojo


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _texto_series(valor):
    return extraer_numeros(str(valor) if valor else "")


def clasificar_series(numeros, existentes):
    vistos = set()
    resultado = []
    for numero in numeros:
        normalizado = normalizar_numero(numero)
        if normalizado in vistos:
            estado = "duplicada"
        elif not normalizado or not _formato_valido(normalizado):
            estado = "invalida"
        elif normalizado in existentes:
            estado = "ya_existe"
        else:
            estado = "valida"
        vistos.add(normalizado)
        resultado.append({"numero": normalizado, "estado": estado})
    return resultado


def _formato_valido(numero):
    try:
        validar_numero(numero)
        return True
    except SerieInvalida:
        return False


def series_reutilizables(numeros) -> dict:
    """Series existentes cuyo recojo anterior está ANULADO y pueden re-registrarse."""
    numeros = [normalizar_numero(numero) for numero in numeros]
    if not numeros:
        return {}
    series = Serie.objects.filter(numero__in=numeros).prefetch_related(
        "lineas_recojo__recojo"
    )
    reutilizables = {}
    for serie in series:
        lineas = list(serie.lineas_recojo.all())
        if not lineas:
            continue
        if serie.estado not in (EstadoSerie.DISPONIBLE, EstadoSerie.INACTIVA):
            continue
        if serie.tecnico_id:
            continue
        if all(linea.recojo.estado == EstadoRecojo.ANULADO for linea in lineas):
            reutilizables[serie.numero] = serie
    return reutilizables


def normalizar_lineas(datos):
    lineas = []
    for linea in datos.get("lineas", []):
        material_id = linea.get("material_id")
        series = linea.get("series")
        cantidad = linea.get("cantidad")
        if not material_id and not series and cantidad in (None, ""):
            continue
        lineas.append(
            {
                "material_id": material_id,
                "series": series,
                "cantidad": cantidad,
            }
        )
    return lineas


def validar_recojo_previo(tenant, datos) -> ResultadoValidacion:
    errores = []

    nombre = normalizar_nombre_recojo(datos.get("nombre"))
    if not nombre:
        errores.append("El nombre es obligatorio")
    elif len(nombre) > 100:
        errores.append("El nombre no puede superar los 100 caracteres")

    fecha = datos.get("fecha")
    if isinstance(fecha, date):
        fecha_normalizada = fecha
    elif fecha in (None, ""):
        fecha_normalizada = None
        errores.append("La fecha es obligatoria")
    else:
        fecha_normalizada = parse_date(str(fecha))
        if fecha_normalizada is None:
            errores.append("La fecha no es válida")

    lineas_entrada = normalizar_lineas(datos)
    if not lineas_entrada:
        errores.append("El recojo debe tener al menos una línea")

    registros = []
    numeros_globales = []

    for linea in lineas_entrada:
        material_id = _entero(linea.get("material_id"))
        material = (
            Material.objects.filter(pk=material_id).first()
            if material_id is not None
            else None
        )
        if material is None:
            errores.append("El material no existe en el catálogo")
            continue

        if material.es_seriado:
            numeros = _texto_series(linea.get("series"))
            if not numeros:
                errores.append("Debe indicar al menos una serie")
                continue
            cantidad = linea.get("cantidad")
            if cantidad not in (None, "") and _entero(cantidad) != 1:
                errores.append("Para un material seriado la cantidad debe ser 1")
            for numero in numeros:
                normalizado = normalizar_numero(numero)
                numeros_globales.append(normalizado)
                registros.append(
                    {
                        "material": material,
                        "lote": material.lote,
                        "serie_numero": normalizado,
                        "cantidad": 1,
                    }
                )
        else:
            if _texto_series(linea.get("series")):
                errores.append("Un material no seriado no admite series")
                continue
            cantidad = _entero(linea.get("cantidad"))
            if cantidad is None or cantidad <= 0:
                errores.append("La cantidad debe ser mayor a 0")
                continue
            registros.append(
                {
                    "material": material,
                    "lote": material.lote,
                    "serie_numero": None,
                    "cantidad": cantidad,
                }
            )

    existentes = series_existentes(numeros_globales) if numeros_globales else set()
    reutilizables = series_reutilizables(numeros_globales)
    no_reutilizables = existentes - set(reutilizables)
    estados = clasificar_series(numeros_globales, no_reutilizables)

    if any(estado["estado"] == "invalida" for estado in estados):
        errores.append("La serie debe tener 12 caracteres alfanuméricos")
    if any(estado["estado"] == "duplicada" for estado in estados):
        errores.append("La serie está duplicada en el recojo")
    if any(estado["estado"] == "ya_existe" for estado in estados):
        errores.append("La serie ya está registrada en el sistema")

    estados_por_numero = {
        estado["numero"]: estado["estado"] for estado in estados
    }
    lineas = [
        registro
        for registro in registros
        if registro["serie_numero"] is None
        or estados_por_numero.get(registro["serie_numero"]) == "valida"
    ]

    return ResultadoValidacion(
        valido=not errores,
        fecha=fecha_normalizada,
        nombre=nombre or None,
        lineas=lineas,
        series_estados=estados,
        series_reutilizables=reutilizables,
        errores=errores,
    )


def auditar_alta_recojo(recojo, actor):
    total_series = recojo.lineas.filter(serie__isnull=False).count()
    total_cantidad = sum(
        recojo.lineas.filter(serie__isnull=True).values_list(
            "cantidad", flat=True
        )
    )
    valor = (
        f"nombre={recojo.nombre}; fecha={recojo.fecha.isoformat()}; "
        f"region={recojo.region.codigo}; lineas={recojo.lineas.count()}; "
        f"series={total_series}; cantidad={total_cantidad}"
    )
    return registrar_cambio(
        "Recojo",
        recojo.pk,
        "alta",
        "",
        valor,
        actor,
        tenant=recojo.tenant,
    )


def materiales_tiene_movimientos(material) -> bool:
    if LineaRecojo.objects.filter(material=material).exists():
        return True
    if Serie.objects.filter(material=material).exists():
        return True
    return StockGeneral.objects.filter(
        material=material,
        cantidad__gt=0,
    ).exists()


def _reactivar_serie_recojo(serie, tenant, recojo, actor):
    """Reutiliza una serie de un recojo anulado sin duplicar la fila."""
    bloqueada = Serie.objects.select_for_update().get(pk=serie.pk)
    if bloqueada.tenant_id != tenant.pk or bloqueada.tecnico_id:
        raise SerieYaExiste("La serie ya está registrada en el sistema")
    if LineaRecojo.objects.filter(
        serie=bloqueada,
        recojo__estado=EstadoRecojo.REGISTRADO,
    ).exists():
        raise SerieYaExiste("La serie ya está registrada en el sistema")
    if bloqueada.estado == EstadoSerie.INACTIVA:
        bloqueada.estado = EstadoSerie.DISPONIBLE
        bloqueada.actualizado_por = actor
        bloqueada.save(
            update_fields=["estado", "actualizado_por", "actualizado_en"]
        )
        registrar_cambio(
            "Serie",
            bloqueada.pk,
            "estado",
            EstadoSerie.INACTIVA,
            EstadoSerie.DISPONIBLE,
            actor,
            tenant=tenant,
        )
    return bloqueada


def crear_recojo(datos, actor) -> Recojo:
    # 004 nunca escribe StockGeneral directamente: delega en el servicio de 008,
    # que es el responsable de bloquear/sumar con select_for_update o F().
    tenant = validar_cuenta_tenant(actor)
    region = validar_region_tenant(tenant)

    try:
        with transaction.atomic():
            resultado = validar_recojo_previo(tenant, datos)
            if not resultado.valido:
                raise RecojoInvalido(
                    resultado.errores[0] if resultado.errores else "Recojo inválido",
                    resultado=resultado,
                )

            recojo = Recojo.objects.create(
                tenant=tenant,
                region=region,
                nombre=resultado.nombre or "",
                fecha=resultado.fecha,
                creado_por=actor,
            )

            cantidades = {}
            materiales = {}

            for linea in resultado.lineas:
                material = linea["material"]
                if linea["serie_numero"] is not None:
                    serie = resultado.series_reutilizables.get(
                        linea["serie_numero"]
                    )
                    if serie is not None:
                        serie = _reactivar_serie_recojo(
                            serie, tenant, recojo, actor
                        )
                    else:
                        serie = Serie.objects.create(
                            numero=linea["serie_numero"],
                            tenant=tenant,
                            region=region,
                            material=material,
                            lote=material.lote,
                            estado=EstadoSerie.DISPONIBLE,
                            creado_por=actor,
                        )
                    LineaRecojo.objects.create(
                        tenant=tenant,
                        recojo=recojo,
                        material=material,
                        lote=material.lote,
                        serie=serie,
                        cantidad=1,
                    )
                    cantidad = 1
                else:
                    LineaRecojo.objects.create(
                        tenant=tenant,
                        recojo=recojo,
                        material=material,
                        lote=material.lote,
                        serie=None,
                        cantidad=linea["cantidad"],
                    )
                    cantidad = linea["cantidad"]

                cantidades[material.pk] = cantidades.get(material.pk, 0) + cantidad
                materiales[material.pk] = material

            for material_pk, cantidad in cantidades.items():
                incrementar_stock_general(
                    tenant,
                    materiales[material_pk],
                    cantidad,
                    actor,
                )

            auditar_alta_recojo(recojo, actor)
    except IntegrityError as exc:
        raise SerieYaExiste from exc

    return recojo


def _cantidades_por_material(lineas):
    cantidades = {}
    for linea in lineas:
        cantidad = linea["cantidad"]
        cantidades[linea["material_id"]] = (
            cantidades.get(linea["material_id"], 0) + cantidad
        )
    return cantidades


def puede_anular_recojo(recojo, ahora=None):
    """Devuelve (puede, mensaje) para la interfaz y la validación previa."""
    if recojo.estado == EstadoRecojo.ANULADO:
        return False, "Este recojo ya fue anulado."

    ahora = ahora or timezone.now()
    limite = recojo.creado_en + timedelta(hours=PLAZO_ANULACION_HORAS)
    if ahora > limite:
        return (
            False,
            "El plazo de 24 horas para anular este recojo venció.",
        )

    lineas = list(
        LineaRecojo.objects.filter(recojo=recojo).values(
            "material_id", "serie_id", "cantidad"
        )
    )
    series = {
        serie.pk: serie
        for serie in Serie.objects.filter(
            pk__in=[l["serie_id"] for l in lineas if l["serie_id"]]
        )
    }
    if any(
        serie.estado != EstadoSerie.DISPONIBLE or serie.tecnico_id
        for serie in series.values()
    ):
        return False, "No se puede anular: una serie ya fue utilizada."

    for material_id, cantidad in _cantidades_por_material(lineas).items():
        stock = StockGeneral.objects.filter(
            tenant=recojo.tenant,
            material_id=material_id,
        ).first()
        if stock is None or stock.cantidad < cantidad:
            return (
                False,
                "No se puede anular: el stock del material ya fue utilizado.",
            )

    return (
        True,
        "Puedes anular este recojo dentro de las próximas 24 horas.",
    )


def anular_recojo(recojo, motivo, actor) -> Recojo:
    tenant = validar_cuenta_tenant(actor)

    if recojo.tenant_id != tenant.pk:
        raise NoEncontrado

    motivo = " ".join((motivo or "").split())
    if not motivo:
        raise MotivoAnulacionInvalido("El motivo de anulación es obligatorio")
    if len(motivo) > 500:
        raise MotivoAnulacionInvalido(
            "El motivo no puede superar los 500 caracteres"
        )

    with transaction.atomic():
        bloqueado = Recojo.objects.select_for_update().get(
            pk=recojo.pk,
            tenant=tenant,
        )
        if bloqueado.estado == EstadoRecojo.ANULADO:
            return bloqueado

        ahora = timezone.now()
        limite = bloqueado.creado_en + timedelta(hours=PLAZO_ANULACION_HORAS)
        if ahora > limite:
            raise PlazoAnulacionVencido(
                "El plazo de 24 horas para anular este recojo venció."
            )

        lineas = list(
            LineaRecojo.objects.select_for_update()
            .filter(recojo=bloqueado)
            .order_by()
            .values("material_id", "serie_id", "cantidad")
        )
        ids_series = [linea["serie_id"] for linea in lineas if linea["serie_id"]]
        series = list(
            Serie.objects.select_for_update().filter(pk__in=ids_series)
        )

        if any(
            serie.estado != EstadoSerie.DISPONIBLE or serie.tecnico_id
            for serie in series
        ):
            raise AnulacionNoPermitida(
                "No se puede anular: una serie ya fue utilizada"
            )

        try:
            for material_id, cantidad in _cantidades_por_material(lineas).items():
                decrementar_stock_general(
                    tenant,
                    material_id,
                    cantidad,
                    actor,
                )
        except StockInsuficiente as exc:
            raise AnulacionNoPermitida(
                "No se puede anular: el stock del material ya fue utilizado"
            ) from exc

        for serie in series:
            if serie.estado != EstadoSerie.DISPONIBLE:
                serie.estado = EstadoSerie.DISPONIBLE
                serie.actualizado_por = actor
                serie.save(
                    update_fields=[
                        "estado",
                        "actualizado_por",
                        "actualizado_en",
                    ]
                )
            registrar_cambio(
                "Serie",
                serie.pk,
                "reactivada",
                "",
                f"recojo={bloqueado.pk}; estado={EstadoSerie.DISPONIBLE}",
                actor,
                tenant=tenant,
            )

        bloqueado.estado = EstadoRecojo.ANULADO
        bloqueado.anulado_en = ahora
        bloqueado.anulado_por = actor
        bloqueado.motivo_anulacion = motivo
        bloqueado.save(
            update_fields=[
                "estado",
                "anulado_en",
                "anulado_por",
                "motivo_anulacion",
            ]
        )

        registrar_cambio(
            "Recojo",
            bloqueado.pk,
            "estado",
            EstadoRecojo.REGISTRADO,
            EstadoRecojo.ANULADO,
            actor,
            tenant=tenant,
        )
        registrar_cambio(
            "Recojo",
            bloqueado.pk,
            "motivo_anulacion",
            "",
            motivo,
            actor,
            tenant=tenant,
        )

    return bloqueado


def listar_recojos(tenant, q="", estado="todos"):
    from django.db.models import Count, Q, Sum

    recojos = Recojo.objects.filter(tenant=tenant)
    q = (q or "").strip()
    if q:
        recojos = recojos.filter(nombre__icontains=q)
    if estado == "registrados":
        recojos = recojos.filter(estado=EstadoRecojo.REGISTRADO)
    elif estado == "anulados":
        recojos = recojos.filter(estado=EstadoRecojo.ANULADO)

    return (
        recojos
        .annotate(
            total_lineas=Count("lineas", distinct=True),
            total_series=Count(
                "lineas",
                filter=Q(lineas__serie__isnull=False),
                distinct=True,
            ),
            total_cantidad=Sum(
                "lineas__cantidad",
                filter=Q(lineas__serie__isnull=True),
            ),
        )
        .order_by("-fecha", "-id")
    )


def obtener_detalle_recojo(tenant, recojo_id):
    recojo = obtener_recojo(tenant, recojo_id)
    return (
        Recojo.objects.filter(pk=recojo.pk)
        .select_related("tenant", "region", "creado_por")
        .prefetch_related("lineas__material", "lineas__serie")
        .get()
    )


def totales_recojo(recojo):
    lineas = list(recojo.lineas.all())
    return {
        "total_lineas": len(lineas),
        "total_series": sum(1 for linea in lineas if linea.serie_id),
        "total_cantidad": sum(
            linea.cantidad for linea in lineas if linea.serie_id is None
        ),
    }


def previsualizar_series(tenant, material, texto_series):
    if not material.es_seriado:
        raise MaterialNoValido("El material no es seriado; indique la cantidad")

    numeros = [normalizar_numero(n) for n in _texto_series(texto_series)]
    if not numeros:
        return []

    existentes = series_existentes(numeros)
    return clasificar_series(numeros, existentes)


# Importación diferida para evitar ciclos con series.services.
from series.services import SerieYaExiste  # noqa: E402,F401
