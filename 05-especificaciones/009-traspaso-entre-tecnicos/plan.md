# Plan técnico: 009 Traspaso entre Técnicos

**Branch**: `009-traspaso-entre-tecnicos` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/009-traspaso-entre-tecnicos/spec.md`

**Input**: Spec en `05-especificaciones/009-traspaso-entre-tecnicos/spec.md`

## Summary

Implementar el traspaso de materiales entre técnicos del mismo tenant: el tenant crea una solicitud,
selecciona series o cantidades que el técnico origen tiene realmente en custodia, el sistema valida
disponibilidad y cuadre, genera un Excel de dos hojas (Z32 Desasignación y Z31 Asignación) al enviar,
y el Responsable de almacén confirma o rechaza. Al confirmar, las series cambian de técnico, el stock
del origen baja y el del destino sube, los días en mano se reinician para las series y el stock
general del tenant **no cambia**. Al rechazar, no cambia nada.

La spec 009 revela una decisión transversal pendiente: `series.Serie` no tiene técnico ni fecha de
custodia. Sin ellos no se puede cumplir CA-06 (cambiar de técnico) ni CA-09 (reiniciar días en mano).
Este plan resuelve el vacío añadiendo a `Serie` los campos `tecnico` y `asignada_en`, con coherencia
entre estado y custodia, y coordina las correcciones en 004, 005, 006, 008 y 011.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX; rutas de tenant y rutas de almacén; descarga de Excel |
| App nueva | `traspasos` |
| Excel | `openpyxl`; dos hojas; generado al enviar; hash SHA-256 |
| Stock | Se usan los servicios de 008; **nunca** se escribe `StockGeneral` |
| Series | `series.Serie` con `tecnico` y `asignada_en`; 009 cambia la custodia |
| Reservas | Derivadas de solicitudes `ENVIADA`; no hay tabla de reservas |
| Transacciones | Crear, enviar, confirmar, rechazar y cancelar son atómicas |
| Bloqueos | `select_for_update` en orden estable; sin `F()` ciego |
| Auditoría | `auditoria.RegistroCambio` en la misma transacción |
| Días en mano | Se reinician con `Serie.asignada_en` al confirmar |
| Correo/Celery | **Fuera de alcance de 009**; no se añaden tareas ni dependencias |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL`, `ContextoUsuarioMiddleware`, `Tenant`, `Region`, roles y auditoría.
- **002**: `Material` con `codigo`, `descripcion`, `lote` y `es_seriado`.
- **003**: `Tecnico` con `tenant`, `nif`, `nombre` y `activo`.
- **004**: `series.Serie` con `numero`, `tenant`, `region`, `material`, `lote` y `estado`; además, los
  campos `tecnico` y `asignada_en` que añade este plan.
- **005**: stock inicial con series `ASIGNADA` y `serie.tecnico`/`serie.asignada_en` fijados.
- **006/007**: solicitudes de asignación, confirmación y `confirmada_en`; 007 aporta
  `validar_cuenta_almacen` y el patrón de descarga segura.
- **008**: `StockTecnico`, `incrementar_stock_tecnico`, `decrementar_stock_tecnico`,
  `actualizar_stock_confirmacion_asignacion` y la auditoría `StockTecnico/cantidad`; al confirmar una
  asignación, 008 fija `serie.tecnico` y `serie.asignada_en`.
- **Infraestructura**: PostgreSQL con rol sin `SUPERUSER` ni `BYPASSRLS`.

Si falta cualquiera, la implementación se detiene y se reporta.

### Orden de implementación

1. Correcciones documentales de 004/005/006/008/011 y migración de `series` con
   `tecnico`/`asignada_en`.
2. 001–008 implementadas hasta la confirmación de asignaciones.
3. App `traspasos`: modelos, migraciones, servicios de creación y envío.
4. Confirmación/rechazo/cancelación y rutas del almacén.
5. 010, 011 y 012 consumen `Serie.asignada_en`/`tecnico` sin duplicar la custodia.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | `SolicitudTraspaso` y `LineaTraspaso` llevan `tenant`; la solicitud lleva `region`. Tenant y región salen de la sesión y de `tenant.region`, nunca del cliente. Técnicos, series y stock de otro tenant se rechazan. RLS como respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | Origen y destino pertenecen al tenant; el almacén confirma solo traspasos de su región. El Administrador de plataforma no opera traspasos. |
| III. Invariantes de stock | PASA | El stock general no se lee ni se escribe. El stock técnico baja en el origen y sube en el destino por el mismo total. No se traspasa más de lo disponible, descontando reservas `ENVIADA`. |
| IV. Identidad y unicidad de series | PASA | Se usa `series.Serie`; una serie solo se traspasa si está `ASIGNADA` al origen. No se crea otra tabla de series ni otro número. La serie no cambia de tenant, región ni material. |
| V. Integridad transaccional | PASA | Crear, enviar, confirmar, rechazar y cancelar son transacciones únicas. Cualquier fallo revierte líneas, estado, reservas, stock, Excel y auditoría. |
| VI. Auditoría inmutable y trazabilidad | PASA | Se auditan `SolicitudTraspaso/estado`, `LineaTraspaso/alta`, `Serie/tecnico`, `Serie/asignada_en` y los `StockTecnico/cantidad` que escribe 008. Sin secretos ni binarios. |
| VII. Autoridad del reporte de Lari y aprobación humana | PASA | El traspaso no procesa reportes de Lari y requiere confirmación humana del almacén. No hay automatismo. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA-01…CA-09 tiene prueba. No se agregan dependencias; no se implementa correo/Celery porque la spec 009 no lo pide. La lógica vive en `traspasos/services.py` y es testeable sin interfaz. |

**Post-design re-check**: PASA. El diseño usa una única fuente de líneas para las dos hojas del Excel,
deriva las reservas de `ENVIADA`, no toca el stock general, no duplica la custodia y corrige la
contradicción de la FK de técnico en `Serie`.

## Project Structure

```text
traspasos/
├── __init__.py
├── apps.py
├── models.py
├── services.py
├── excel.py
├── forms.py
├── views.py
├── urls.py
├── migrations/
│   ├── 0001_initial.py
│   └── 0002_rls.py

series/
└── migrations/
    └── 0003_serie_tecnico_asignada_en.py

templates/
├── traspasos/
│   ├── listado.html
│   ├── formulario.html
│   ├── detalle.html
│   └── _series_tecnico.html
└── almacen/
    └── traspasos/
        ├── listado.html
        └── detalle.html

tests/
├── unit/
│   ├── test_traspaso_servicios.py
│   ├── test_traspaso_cuadre.py
│   └── test_traspaso_excel.py
├── integration/
│   ├── test_traspaso_creacion.py
│   ├── test_traspaso_envio.py
│   ├── test_traspaso_confirmacion.py
│   ├── test_traspaso_rechazo.py
│   ├── test_traspaso_concurrencia.py
│   └── test_traspaso_auditoria.py
└── contract/
    └── test_traspaso_http.py
```

También se modifican:

- `config/settings/base.py`: registrar `traspasos` y `TRASPASOS_EXCEL_DIR` si se parametriza la ruta.
- `config/urls.py`: incluir `traspasos.urls`.
- `templates/base.html`: enlaces a traspasos para `USUARIO_TENANT` y al almacén para
  `RESPONSABLE_ALMACEN`.
- `series/models.py` y `series/migrations/`: campos de custodia.
- `05-especificaciones/009-traspaso-entre-tecnicos/plan.md`: este documento.
- No se crean tareas Celery ni se modifica `StockGeneral`.

## Modelo de datos

### `traspasos.SolicitudTraspaso`

```python
class SolicitudTraspaso(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT,
                               related_name="solicitudes_traspaso")
    region = models.ForeignKey("tenants.Region", on_delete=models.PROTECT,
                               related_name="solicitudes_traspaso")
    tecnico_origen = models.ForeignKey("tecnicos.Tecnico", on_delete=models.PROTECT,
                                       related_name="traspasos_origen")
    tecnico_destino = models.ForeignKey("tecnicos.Tecnico", on_delete=models.PROTECT,
                                        related_name="traspasos_destino")
    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=EstadoTraspaso.choices,
                              default=EstadoTraspaso.BORRADOR)
    motivo_rechazo = models.TextField(blank=True, default="")
    excel_ruta = models.CharField(max_length=255, blank=True, default="")
    excel_hash = models.CharField(max_length=64, blank=True, default="")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="traspasos_creados")
    creado_en = models.DateTimeField(auto_now_add=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    confirmada_en = models.DateTimeField(null=True, blank=True)
    rechazada_en = models.DateTimeField(null=True, blank=True)
    cancelada_en = models.DateTimeField(null=True, blank=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                        null=True, blank=True, related_name="+")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(tecnico_origen=models.F("tecnico_destino")),
                name="solicitud_traspaso_origen_destino_distintos",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["BORRADOR", "ENVIADA", "CONFIRMADA",
                                        "RECHAZADA", "CANCELADA"]),
                name="solicitud_traspaso_estado_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "estado"], name="traspaso_tenant_estado"),
            models.Index(fields=["region", "estado"], name="traspaso_region_estado"),
            models.Index(fields=["tenant", "fecha"], name="traspaso_tenant_fecha"),
            models.Index(fields=["tecnico_origen", "fecha"], name="traspaso_origen_fecha"),
            models.Index(fields=["tecnico_destino", "fecha"], name="traspaso_destino_fecha"),
        ]
```

- `region` se copia de `tenant.region` y es inmutable; sirve para la bandeja del almacén y RLS.
- `tenant`, `region`, `tecnico_origen` y `tecnico_destino` no cambian tras crear la solicitud.
- `estado` solo avanza por las transiciones definidas en `services.py`.
- `motivo_rechazo` solo se llena al rechazar; no se borra.
- `excel_ruta` es relativa a `MEDIA_ROOT`/`TRASPASOS_EXCEL_DIR`; nunca absoluta.
- `confirmada_en` es la fecha del traspaso, no la fecha de la asignación original; los días en mano
  usan `Serie.asignada_en`.

### `traspasos.LineaTraspaso`

```python
class LineaTraspaso(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT,
                               related_name="lineas_traspaso")
    solicitud = models.ForeignKey(SolicitudTraspaso, on_delete=models.CASCADE,
                                  related_name="lineas")
    material = models.ForeignKey("materiales.Material", on_delete=models.PROTECT,
                                 related_name="lineas_traspaso")
    lote = models.CharField(max_length=50, blank=True, default="")
    serie = models.ForeignKey("series.Serie", on_delete=models.PROTECT,
                              null=True, blank=True, related_name="lineas_traspaso")
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_traspaso_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=True) | Q(cantidad=1),
                name="linea_traspaso_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="linea_traspaso_cantidad_no_negativa",
            ),
            models.UniqueConstraint(
                fields=["solicitud", "serie"],
                condition=Q(serie__isnull=False),
                name="linea_traspaso_serie_unica",
            ),
            models.UniqueConstraint(
                fields=["solicitud", "material"],
                condition=Q(serie__isnull=True),
                name="linea_traspaso_no_seriada_unica",
            ),
        ]
        indexes = [
            models.Index(fields=["solicitud", "material"], name="linea_traspaso_solicitud_material"),
            models.Index(fields=["tenant", "material"], name="linea_traspaso_tenant_material"),
            models.Index(fields=["serie"], name="linea_traspaso_serie"),
        ]
```

- `tenant` se copia de `solicitud.tenant`; nunca del cliente.
- Seriado: `serie` no nula y `cantidad=1`; no seriado: `serie` nula y `cantidad>0`.
- Una serie aparece como máximo una vez por solicitud.
- Los no seriados se agregan por material en una sola línea.
- No hay campo de dirección: **todas las líneas se mueven del origen al destino**; las dos hojas del
  Excel son proyecciones de la misma lista canónica.

### `series.Serie` (campos añadidos por 009)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `tecnico` | FK `tecnicos.Tecnico` | Sí | `PROTECT`, `related_name="series"`; técnico custodio actual |
| `asignada_en` | `DateTimeField` | Sí | Inicio de la custodia actual; se reinicia en cada traspaso |

**Restricciones**

- `CheckConstraint(serie_tecnico_coherente_estado)`:
  - `ASIGNADA` exige `tecnico` y `asignada_en` no nulos.
  - `DISPONIBLE` y `RESERVADA` exigen ambos nulos.
- `CheckConstraint(serie_tecnico_mismo_tenant)` no es posible con un `CheckConstraint`; se valida en
  el servicio: `tecnico.tenant_id == serie.tenant_id`.
- `Index(tecnico, estado, name="serie_tecnico_estado")`.
- `Index(tecnico, material, name="serie_tecnico_material")`.

**Reglas**

- 004 crea `DISPONIBLE` con `tecnico=None` y `asignada_en=None`.
- 005 crea `ASIGNADA` con `tecnico` y `asignada_en` del stock inicial.
- 008 confirma una asignación: `ASIGNADA`, `tecnico=solicitud.tecnico`, `asignada_en=ahora`.
- 009 confirma un traspaso: cambia `tecnico` al destino y reinicia `asignada_en=ahora`; el estado
  sigue `ASIGNADA`.
- 011 devuelve a stock general: `DISPONIBLE`, `tecnico=None`, `asignada_en=None`.
- La serie no cambia de tenant, región ni material.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 009 |
|---|---|---|
| `series.Serie` | 004 | Custodia actual, estado y material; 009 cambia `tecnico`/`asignada_en`. |
| `stock.StockTecnico` | 008 | Disponibilidad del origen y actualización de ambos técnicos. |
| `stock.StockGeneral` | 008 | **No se lee ni se escribe.** |
| `tecnicos.Tecnico` | 003 | Origen y destino; tenant, NIF y activo. |
| `materiales.Material` | 002 | Catálogo, lote y tipo seriado. |
| `asignaciones.SolicitudAsignacion` | 006/007 | Origen histórico de la custodia; no se modifica. |
| `auditoria.RegistroCambio` | 001 | Auditoría compartida. |

## Migraciones

1. `series/migrations/0003_serie_tecnico_asignada_en.py`: añade `tecnico`, `asignada_en`, las
   restricciones de coherencia y los índices; rellena datos existentes de forma segura
   (`ASIGNADA` desde stock inicial o asignaciones confirmadas) antes de activar la restricción. Si no
   hay forma fiable de rellenar, la migración se detiene y se documenta la deuda.
2. `traspasos/migrations/0001_initial.py`: `SolicitudTraspaso` y `LineaTraspaso` con restricciones e
   índices. No crea traspasos.
3. `traspasos/migrations/0002_rls.py`: RLS de solicitud por `tenant_id`/`region_id` y de línea por
   `tenant_id`. Si la infraestructura de 001 no está disponible, se registra la deuda.
4. No se modifican tablas de stock, asignaciones, recojos, conciliaciones ni series fuera de 0003.

## Servicios (lógica de negocio)

Viven en `traspasos/services.py`; las vistas solo orquestan.

### Estados

```text
BORRADOR ── enviar ──▶ ENVIADA ── confirmar ──▶ CONFIRMADA
   │                       └──── rechazar ────▶ RECHAZADA
   └── cancelar ─────────────────────────────▶ CANCELADA
```

- `CONFIRMADA`, `RECHAZADA` y `CANCELADA` son terminales.
- No se reabre una solicitud.
- Enviar, confirmar, rechazar y cancelar exigen el estado previo exacto y lo revalidan bajo bloqueo.

### Excepciones

- `PermisoDenegado`: “No tienes permiso para crear traspasos” / “No tienes permiso para gestionar
  traspasos”.
- `TecnicosDistintoTenant`: “Los técnicos deben ser del mismo tenant”.
- `OrigenDestinoIguales`: “El técnico origen y destino no pueden ser el mismo”.
- `TecnicoNoExiste`: “El técnico no existe” / “El técnico destino no está activo”.
- `MaterialNoExiste`: “El material no existe”.
- `SerieNoEnTecnico`: “La serie no está asignada al técnico origen”.
- `SerieReservada`: “La serie está reservada en otro traspaso”.
- `StockTecnicoInsuficiente`: “La cantidad supera el stock del técnico”.
- `CuadreIncorrecto`: “Lo que sale debe cuadrar con lo que entra”.
- `EstadoTraspasoInvalido`: “Solo se pueden enviar traspasos en borrador”, “Solo se pueden cancelar
  traspasos en borrador”, “Solo se pueden confirmar traspasos enviados” o “Solo se pueden rechazar
  traspasos enviados”.
- `MotivoRechazoRequerido`: “El motivo de rechazo es obligatorio”.
- `NoEncontrado`: “El traspaso no existe”.
- `ArchivoNoDisponible` / `HashNoCoincide`: “El archivo no está disponible” / “El archivo fue
  modificado, descarga bloqueada”.

### Alcance y permisos

- `validar_cuenta_tenant(actor, tenant)`: exige `USUARIO_TENANT`, cuenta activa y `actor.tenant_id ==
  tenant.id`.
- `validar_cuenta_almacen(actor, region)`: reutiliza la validación de 007; exige
  `RESPONSABLE_ALMACEN`, región activa y almacén activo.
- El Administrador de plataforma no crea, envía, confirma ni rechaza traspasos.
- No se usan permisos Django por cadena; los servicios validan rol y alcance.

### Técnicos

- `validar_tecnicos(origen, destino, tenant)`:
  - Ambos existen y pertenecen al tenant.
  - `origen.id != destino.id`.
  - El destino está activo; el origen puede estar inactivo si aún tiene stock, para permitir vaciarlo.
- `tecnicos_para_traspaso(tenant)`: solo activos del tenant, ordenados por NIF.

### Disponibilidad y reservas

- `calcular_reservado_tecnico(tecnico, material)`:
  - Suma líneas no seriadas (`serie__isnull=True`) de solicitudes `ENVIADA` del técnico y material.
  - Cuenta 1 por cada línea seriada (`serie__isnull=False`).
- `calcular_disponible_tecnico(tecnico, material)`:
  - `max(0, StockTecnico.cantidad - calcular_reservado_tecnico(...))`.
  - Material sin stock devuelve `0`.
- `series_disponibles_para_traspaso(tecnico, material, q="")`:
  - `Serie.estado == ASIGNADA`, `Serie.tecnico == tecnico`, mismo tenant y material.
  - Excluye series referenciadas por `LineaTraspaso` de solicitudes `ENVIADA`.
  - Busca por número si `q` no está vacío; ordena por número.
- `validar_serie_en_tecnico(serie, origen, material)`:
  - Estado `ASIGNADA`, `serie.tecnico_id == origen.id`, mismo tenant y material.
  - Si otra solicitud `ENVIADA` la referencia, `SerieReservada`.
- `validar_disponibilidad_lineas(origen, lineas)`:
  - Seriados: cada serie disponible y no reservada.
  - No seriados: suma por material y compara con `calcular_disponible_tecnico`.
  - No crea reservas.

### Cuadre

La solicitud tiene una sola lista canónica de líneas. Las dos hojas del Excel se construyen desde
ella; el cuadre compara las dos proyecciones antes de guardar el archivo y en la confirmación.

```python
@dataclass(frozen=True)
class MovimientoTraspaso:
    material_id: int
    lote: str
    serie_id: int | None
    cantidad: int

@dataclass(frozen=True)
class CuadreTraspaso:
    salida: list[MovimientoTraspaso]
    entrada: list[MovimientoTraspaso]
```

- `construir_movimientos(lineas) -> CuadreTraspaso`: genera salida y entrada idénticas a partir de
  las líneas.
- `validar_cuadre_traspaso(cuadre)`:
  - Misma cantidad de movimientos seriados en ambos lados y cada `serie_id` exactamente una vez.
  - Mismo `material_id` y `lote` por serie.
  - Totales no seriados por material iguales en ambos lados.
  - Sin movimientos extra ni faltantes.
  - Si no cuadra, `CuadreIncorrecto`.
- La validación se ejecuta al crear, al enviar y al confirmar; una proyección manipulada o una línea
  perdida aborta todo el traspaso.
- No se agrega una segunda lista de “entrada” al formulario: la entrada es una proyección de la
  misma línea y el cuadre es un invariante verificable.

### Creación

- `crear_solicitud_traspaso(tenant, origen, destino, fecha, lineas, actor)`:
  - Valida cuenta, tenant, técnicos, materiales, disponibilidad y cuadre.
  - En `transaction.atomic`: crea `SolicitudTraspaso` en `BORRADOR` con `region =
    tenant.region`, `creado_por=actor`; crea las líneas con `tenant` y `lote` del catálogo; audita
    `SolicitudTraspaso/alta` y `LineaTraspaso/alta`.
  - No reserva series ni cantidades y no genera Excel.
  - Devuelve la solicitud.
- `actualizar_lineas_borrador(solicitud, lineas, actor)`:
  - Solo `BORRADOR` y mismo tenant.
  - Reemplaza las líneas en una transacción, revalidando disponibilidad y cuadre; audita bajas y
    altas. No toca stock ni series.

### Envío y Excel

- `enviar_solicitud_traspaso(solicitud, actor)`:
  - Solo `BORRADOR`; valida cuenta del tenant.
  - En `transaction.atomic`:
    - Bloquea la solicitud, el `Tenant`, las filas de `StockTecnico` de origen y destino ordenadas
      por `(material_id, tecnico_id)` y las series por `id`.
    - Revalida técnicos, disponibilidad, series y cuadre dentro del bloqueo.
    - Cambia a `ENVIADA`, fija `enviada_en` y `actualizado_por`.
    - Genera el Excel de dos hojas y calcula el hash; guarda `excel_ruta`/`excel_hash`.
    - Audita `SolicitudTraspaso/estado` y `SolicitudTraspaso/excel`.
  - Si la generación o el guardado del archivo falla, revierte la transacción y elimina el archivo
    parcial.
  - No envía correo ni encola tareas en 009.
- `generar_excel_traspaso(solicitud) -> (ruta, hash)` en `traspasos/excel.py`:
  - Hoja 1 `Desasignación` con movimiento Z32, Centro/Almacén de la región, NIF del origen, tenant,
    región, ID y fecha.
  - Hoja 2 `Asignación` con Z31, mismos parámetros y NIF del destino.
  - Tabla de seriales: código, descripción, lote, serie y cantidad 1.
  - Tabla de material menor: código, descripción, lote y cantidad agregada.
  - Ambas hojas usan la misma lista canónica y el mismo orden.
  - Nombre seguro `traspasos/<tenant_id>/traspaso-<id>-<hash>.xlsx`; hash SHA-256 de los bytes.
- `verificar_hash_excel(solicitud, contenido)`:
  - Recalcula SHA-256 y compara con `hmac.compare_digest`; si no coincide, `HashNoCoincide`.
  - No regenera el Excel.

### Confirmación

- `confirmar_traspaso(solicitud, actor)`:
  - Valida cuenta de almacén de la región del tenant y estado `ENVIADA`.
  - En `transaction.atomic`:
    - Bloquea `SolicitudTraspaso`, `Tenant`, las filas de `StockTecnico` de origen y destino
      ordenadas por `(material_id, tecnico_id)`, y las series por `id`.
    - Revalida que cada serie siga `ASIGNADA` al origen y que las cantidades estén disponibles.
    - Valida el cuadre de nuevo.
    - Por cada serie: `tecnico = destino`, `asignada_en = ahora`; el estado sigue `ASIGNADA`.
    - Por material: `decrementar_stock_tecnico(origen, material, total, actor)` e
      `incrementar_stock_tecnico(destino, material, total, actor)`.
    - Cambia a `CONFIRMADA`, fija `confirmada_en` y `actualizado_por`.
    - Audita `SolicitudTraspaso/estado`, `Serie/tecnico` y `Serie/asignada_en`.
  - **No** lee ni escribe `StockGeneral`; el total del tenant no cambia.
  - Devuelve el resultado con series, totales y fechas.
- `revalidar_traspaso(solicitud)`:
  - Verifica que las líneas sigan completas, las series en el origen y el stock suficiente.
  - Si algo cambió desde el envío, aborta con `SerieNoEnTecnico`, `SerieReservada`,
    `StockTecnicoInsuficiente` o `CuadreIncorrecto`.

### Rechazo y cancelación

- `rechazar_traspaso(solicitud, comentario, actor)`:
  - Solo `ENVIADA`; comentario obligatorio, sin solo espacios, máximo 1000 caracteres.
  - En `transaction.atomic`: `RECHAZADA`, `rechazada_en`, `motivo_rechazo`, `actualizado_por`;
    audita `SolicitudTraspaso/estado` y `SolicitudTraspaso/motivo_rechazo`.
  - No cambia series, stock ni Excel; la reserva se libera porque la solicitud deja de estar
    `ENVIADA`.
- `cancelar_traspaso(solicitud, actor)`:
  - Solo `BORRADOR`; `CANCELADA`, `cancelada_en`, `actualizado_por`; auditoría.
  - No hay reservas que liberar.

### Consultas

- `listar_traspasos(tenant, estado=None, q="")`: filtra por tenant y ordena por fecha descendente.
- `obtener_traspaso(tenant, traspaso_id)`: filtra por tenant; si no existe o es ajeno, `404`.
- `obtener_traspaso_almacen(region, traspaso_id)`: filtra por región; `404` si es ajeno.
- `detalle_traspaso(solicitud)`: líneas agrupadas por material, series, totales, estado y Excel.
- `resumen_cuadre(solicitud)`: totales de salida y entrada por material para la vista previa.

## Interfaz y endpoints

| Ruta | Método | Rol | Función |
|---|---|---|---|
| `/traspasos/` | GET | Tenant | Listado paginado con filtro por estado |
| `/traspasos/nuevo/` | GET/POST | Tenant | Crear borrador |
| `/traspasos/<id>/` | GET | Tenant | Detalle, líneas, cuadre y Excel |
| `/traspasos/<id>/editar/` | GET/POST | Tenant | Editar líneas en borrador |
| `/traspasos/<id>/enviar/` | POST | Tenant | Validar, reservar y generar Excel |
| `/traspasos/<id>/cancelar/` | POST | Tenant | Cancelar borrador |
| `/traspasos/<id>/excel/` | GET | Tenant | Descargar Excel verificando hash |
| `/traspasos/series-tecnico/` | GET | Tenant | Fragmento HTMX con series del origen |
| `/traspasos/validar-disponibilidad/` | POST | Tenant | Validación en tiempo real |
| `/almacen/traspasos/` | GET | Almacén | Bandeja de la región |
| `/almacen/traspasos/<id>/` | GET | Almacén | Detalle y cuadre |
| `/almacen/traspasos/<id>/excel/` | GET | Almacén | Descarga verificada |
| `/almacen/traspasos/<id>/confirmar/` | POST | Almacén | Confirmar y mover custodia/stock |
| `/almacen/traspasos/<id>/rechazar/` | POST | Almacén | Rechazar con motivo |

- Todas las rutas exigen sesión y validan rol/tenant/región en el servicio.
- No hay ruta `GET` para confirmar, rechazar, enviar ni cancelar.
- Las respuestas ajenas son `404`; los estados inválidos, `409`; el motivo faltante, `400`.
- La descarga usa `Content-Disposition` con nombre seguro y no expone la ruta física.
- No se aceptan `tenant_id`, `region_id`, NIF, tipo de material ni lote del cliente.
- Las series se eligen de un selector del origen; nunca se escriben a mano.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cuenta del tenant y tenant activo | Servicio | “No tienes permiso para crear traspasos” |
| Cuenta de almacén y región | Servicio (007) | “No tienes permiso para gestionar traspasos” |
| Técnicos del mismo tenant | Servicio | “Los técnicos deben ser del mismo tenant” |
| Origen y destino distintos | Servicio y `CheckConstraint` | “El técnico origen y destino no pueden ser el mismo” |
| Destino activo | Servicio | “El técnico destino no está activo” |
| Serie asignada al origen | Servicio | “La serie no está asignada al técnico origen” |
| Serie no reservada | Servicio | “La serie está reservada en otro traspaso” |
| Cantidad no supera disponible | Servicio | “La cantidad supera el stock del técnico” |
| Cuadre de series y cantidades | Servicio y proyecciones | “Lo que sale debe cuadrar con lo que entra” |
| Estado para enviar/cancelar | Servicio | “Solo se pueden enviar/cancelar traspasos en borrador” |
| Estado para confirmar/rechazar | Servicio | “Solo se pueden confirmar/rechazar traspasos enviados” |
| Motivo de rechazo | Servicio y formulario | “El motivo de rechazo es obligatorio” |
| Serie no nula y cantidad 1 | `CheckConstraint` | Violación de restricción de base |
| No seriado con cantidad > 0 | `CheckConstraint` | Violación de restricción de base |
| Una serie por solicitud | `UniqueConstraint` | Violación de restricción de base |
| no seriado único por material | `UniqueConstraint` | Violación de restricción de base |

## Transacciones y concurrencia

- Orden de bloqueo: `SolicitudTraspaso` → `Tenant` → `StockTecnico` por `(material_id, tecnico_id)`
  → `Serie` por `id`.
- Es compatible con 008: 008 bloquea `Tenant` → `StockGeneral` → `StockTecnico` por `material_id` →
  `Serie`; 009 no toca `StockGeneral` y ordena el stock por material antes que por técnico.
- Al enviar, se bloquean la solicitud, el tenant, el stock de origen y las series candidatas; se
  revalida dentro del bloqueo para que dos envíos no reserven la misma serie.
- Al confirmar, se bloquean solicitud, tenant, stock de ambos técnicos y series; se revalida que el
  origen aún las tenga y que el stock alcance.
- Las reservas no son una tabla: se derivan de `ENVIADA`. Al confirmar, rechazar o cancelar, la
  solicitud cambia de estado y la reserva desaparece.
- No se usan decrementos con `F()` ciego; se usan los servicios de 008, que bloquean, validan y
  auditan.
- Si dos traspasos compiten por la misma serie o cantidad, el segundo falla con `SerieReservada` o
  `StockTecnicoInsuficiente` y revierte completo.
- La generación del Excel ocurre dentro de la transacción de envío; si falla, se revierte el estado
  y se elimina el archivo parcial.

## Excel: contrato y corrección documental

- Se respeta `04-contratos/excel-traspaso.md` en estructura, hojas, columnas, metadatos, hash y
  descarga.
- Se corrige el contrato en dos puntos:
  1. El Excel se genera **al enviar** (`BORRADOR→ENVIADA`), no al crear el borrador; así refleja la
     lista definitiva y no se regenera un archivo inmutable.
  2. El **envío por correo** no forma parte de 009; la spec 009 no lo define. Queda como deuda
     documental para una spec posterior. 009 almacena y sirve el Excel para descarga verificada.
- El archivo se guarda con nombre seguro y hash; no se audita su contenido binario.

## Auditoría y RLS

- Eventos:
  - `SolicitudTraspaso/alta` al crear.
  - `LineaTraspaso/alta` y `LineaTraspaso/baja` al crear o editar borrador.
  - `SolicitudTraspaso/estado` al enviar, confirmar, rechazar y cancelar.
  - `SolicitudTraspaso/excel` al guardar ruta/hash.
  - `SolicitudTraspaso/motivo_rechazo` al rechazar.
  - `Serie/tecnico` y `Serie/asignada_en` por cada serie al confirmar.
  - `StockTecnico/cantidad` por material y técnico: lo escribe 008 al usar sus servicios.
- El actor es el usuario de la sesión; nunca se inventa un usuario.
- No se auditan contraseñas, tokens, secretos, binarios, rutas absolutas ni datos de otro tenant.
- RLS:
  - `traspasos_solicitudtraspaso`: por `tenant_id` y `region_id`.
  - `traspasos_lineatraspaso`: por `tenant_id`.
  - Si la infraestructura de 001 no está disponible, se registra la deuda y el ORM filtra por
    tenant/región.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Días en mano

- 009 **no** crea un contador ni una tabla de días en mano.
- Al confirmar un traspaso, cada serie recibe `asignada_en = ahora`; el conteo en el destino empieza
  en 0 y se reinicia en cada traspaso.
- 006 debe calcular los días desde `Serie.asignada_en` (con respaldo en
  `SolicitudAsignacion.confirmada_en` solo para datos históricos sin custodia). Esta corrección se
  aplica en los documentos de 006.
- 005 fija `Serie.asignada_en` al crear el stock inicial; 008 lo fija al confirmar una asignación;
  011 lo limpia al devolver.
- El total de series del tenant no cambia; solo cambia el técnico custodio.

## Pruebas

Un caso por criterio de aceptación, más servicios, Excel, concurrencia, auditoría y aislamiento.

| CA | Prueba principal |
|---|---|
| CA-01 | `test_traspaso_mismo_tenant_genera_excel_dos_hojas` |
| CA-02 | `test_origen_destino_iguales_se_rechaza` |
| CA-03 | `test_solo_cede_lo_que_tiene_asignado` |
| CA-04 | `test_cuadre_series_incorrecto_rechaza` |
| CA-05 | `test_cuadre_cantidades_incorrecto_rechaza` |
| CA-06 | `test_confirmar_cambia_tecnico_de_series` |
| CA-07 | `test_rechazar_no_cambia_nada` |
| CA-08 | `test_stock_general_invariable` |
| CA-09 | `test_dias_en_mano_reinician_al_traspasar` |

Además:

- **Servicios**: crear, editar borrador, enviar, confirmar, rechazar y cancelar; estados inválidos;
  cuenta de otro tenant; técnico de otro tenant; material inexistente; serie de otro técnico;
  cantidad insuficiente; serie reservada; motivo vacío.
- **Cuadre**: series duplicadas, serie que sale y no entra, cantidades desiguales, material distinto,
  lote distinto, línea extra y línea faltante.
- **Excel**: dos hojas, metadatos Z32/Z31, NIF correcto, tablas de seriales y material menor, hash
  estable, descarga con hash alterado bloqueada, nombre seguro y sin ruta absoluta.
- **Concurrencia**: dos envíos que compiten por la misma serie; dos confirmaciones de la misma
  solicitud; dos traspasos que vacían el mismo stock; orden de bloqueo sin interbloqueo;
  confirmación y rechazo simultáneos.
- **Auditoría**: un registro por estado, uno por serie y los de stock de 008; actor correcto; sin
  secretos; sin duplicar el estado de la solicitud.
- **Aislamiento**: tenant A no ve ni opera traspasos de B; almacén de otra región recibe `404`;
  series/stock de otro tenant no se consultan.
- **Stock general**: comparar `StockGeneral` antes y después de crear, enviar, confirmar, rechazar y
  cancelar; siempre idéntico.
- **Rendimiento**: traspaso de 100 series en menos de 2 segundos y sin una consulta por serie.

## Correcciones documentales necesarias

Estas correcciones se aplican antes de implementar 009 (principio VIII):

| Documento | Corrección |
|---|---|
| `004-recojo-de-materiales/data-model.md` | Añadir `Serie.tecnico`, `Serie.asignada_en`, restricción de coherencia e índices; documentar que 005/008/009/011 los actualizan. |
| `005-stock-inicial-de-tecnicos/data-model.md` y `plan.md` | Al crear una serie `ASIGNADA`, fijar `tecnico` y `asignada_en` desde la línea y la carga. |
| `006-solicitud-de-asignacion/plan.md`, `research.md` y `tasks.md` | Calcular días en mano desde `Serie.asignada_en`, con respaldo en `confirmada_en` solo para datos históricos; actualizar pruebas. |
| `008-confirmacion-y-actualizacion-de-stock/plan.md`, `data-model.md`, `contracts/` y `tasks.md` | Al confirmar, fijar `Serie.tecnico = solicitud.tecnico` y `Serie.asignada_en = ahora`, auditar ambos campos y probarlo. |
| `011-logistica-inversa-y-devoluciones/plan.md` | Al devolver, limpiar `Serie.tecnico` y `Serie.asignada_en` al pasar a `DISPONIBLE`. |
| `04-contratos/excel-traspaso.md` | Generar el Excel al enviar, no al crear; el correo queda fuera de 009 y se documenta como deuda. |
| `009-traspaso-entre-tecnicos/spec.md` §11 | Sustituir “actualizar la FK de técnico en el modelo de series” por la referencia a `Serie.tecnico`/`Serie.asignada_en` y a la migración de `series`. |

## Decisiones y riesgos

- **Custodia en `Serie`**: `tecnico` + `asignada_en` es la fuente única para CA-06 y CA-09. Alternativa
  descartada: deducir el técnico de la última `LineaAsignacion`, que no refleja traspasos y rompe los
  días en mano.
- **Sin tabla de reservas**: la reserva se deriva de `ENVIADA`; menos estado duplicado. La
  concurrencia se resuelve con bloqueo y revalidación. Alternativa descartada: una tabla de reservas
  que habría que limpiar en cada transición.
- **Una lista canónica de líneas**: las dos hojas del Excel se generan de la misma lista; el cuadre
  compara las proyecciones. Alternativa descartada: pedir dos listas (salida y entrada) que el usuario
  podría desincronizar.
- **Excel al enviar**: refleja la lista definitiva y evita regenerar un archivo inmutable. Alternativa
  descartada: generarlo al crear y regenerarlo en cada edición.
- **Sin correo en 009**: la spec no lo pide; el almacén consulta la bandeja. Alternativa descartada:
  duplicar la infraestructura de correo de 007.
- **Sin permisos Django**: los roles se validan en servicios, como en 006/007.
- **Riesgo de deadlock**: orden de bloqueo documentado y pruebas de concurrencia.
- **Riesgo de migración de series**: los datos existentes deben rellenarse antes de la restricción; si
  no es posible, la migración se detiene y se documenta.
- **Riesgo de cuadre estricto**: se rechaza cualquier diferencia; no hay tolerancia.
- **Riesgo de alcance**: no se implementan correos, tareas Celery, conciliaciones ni devoluciones.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| Añadir `tecnico`/`asignada_en` a `Serie` | Es la única forma de cumplir el cambio de técnico y el reinicio de días en mano; no duplica series ni cambia su identidad. |
| Reservas derivadas de `ENVIADA` | Evita una tabla de reservas paralela; la solicitud es la fuente de verdad. |
| Proyecciones de cuadre | No crea una segunda lista persistida; solo verifica que ambas hojas del Excel representen la misma lista canónica. |
| Rutas de almacén en 009 | La spec exige confirmación humana del almacén; se añaden rutas mínimas, sin duplicar la bandeja de 007. |
| Sin correo/Celery | La spec 009 no lo pide; se evita duplicar 007 y se registra como deuda. |

## Criterios de salida

- `research.md`, `data-model.md`, `contracts/` y `quickstart.md` creados y coherentes con este plan.
- Plan sin `F()` ciego, sin tocar `StockGeneral`, sin permisos Django por cadena y sin correo/Celery.
- Las correcciones documentales de 004/005/006/008/011 y del contrato de Excel están registradas y se
  aplican antes de implementar.
- `tasks.md` derivado de este plan cubre CA-01…CA-09 con al menos una prueba por criterio.
- No se implementa código en esta fase.
