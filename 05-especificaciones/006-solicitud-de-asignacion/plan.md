# Plan técnico: 006 Solicitud de Asignación

**Branch**: `006-solicitud-de-asignacion` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

**Input**: Spec en `05-especificaciones/006-solicitud-de-asignacion/spec.md`

## Summary

Implementar la creación de solicitudes de asignación de un técnico, con series elegidas del
inventario general y cantidades de materiales no seriados, validando la disponibilidad real
(`Stock General - Reservado`) y reservando los materiales al enviar la solicitud. La solicitud pasa
de `BORRADOR` a `ENVIADA` en una transacción; las series seleccionadas pasan a `RESERVADA`; se
genera un Excel de asignación con los metadatos de la región, se calcula su SHA-256 y se conserva
inmutable para que la spec 007 lo envíe al almacén. La cuenta del tenant puede cancelar un borrador;
el almacén confirma o rechaza en 007. Los días en mano se calculan desde la confirmación y la alerta
de custodia se muestra al crear una nueva solicitud sin bloquearla.

El diseño reutiliza la cuenta única, el middleware, los roles y la auditoría de la spec 001; el
catálogo global de materiales de la spec 002; los técnicos de la spec 003; `series.Serie` y sus
estados de la spec 004; y `stock.StockGeneral`/`StockTecnico` de la spec 008. **No crea otra tabla
de series, no escribe `StockGeneral` ni `StockTecnico`, no implementa el envío de correo ni la
confirmación del almacén** (spec 007) y no modifica recojos, traspasos ni conciliaciones.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX + plantillas; sin SPA ni API REST |
| Excel | `openpyxl`; solo `.xlsx`; archivo inmutable con SHA-256 |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |
| Cola | No se usa Celery en 006; el envío de correo pertenece a 007 |
| Apps | Nueva app `asignaciones`; consumidor de `acceso`, `auditoria`, `materiales`, `tecnicos`, `series` y `stock` |
| Rutas | `asignaciones/urls.py` incluido desde `config/urls.py` con el prefijo `/asignaciones/` |
| Plantillas | `templates/asignaciones/` |
| Pruebas | `tests/{unit,integration,contract}/` |
| Dependencias nuevas | Ninguna |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL = "acceso.Usuario"`, `tenants.Region`, `tenants.Almacen`,
  `tenants.Tenant`, `ContextoUsuarioMiddleware` con `request.usuario`, roles
  `ADMIN_PLATAFORMA`, `USUARIO_TENANT`, `RESPONSABLE_ALMACEN`, `auditoria.RegistroCambio` y
  `auditoria.services.registrar_cambio`. El almacén de la región aporta `centro`,
  `codigo_almacen` y `buzon`.
- **002**: `materiales.Material` con `codigo` único global, `descripcion`, `lote` y `es_seriado`.
- **003**: `tecnicos.Tecnico` con `tenant`, `nif` único global, `nombre`, `activo`, y los servicios
  `normalizar_nif`, `validar_nif`, `obtener_tecnico_por_nif` y `tecnicos_para_operacion`.
- **004**: app `series` con `series.Serie`, `EstadoSerie` (`DISPONIBLE`, `RESERVADA`,
  `ASIGNADA`), `series.services.normalizar_numero`, `validar_numero`, `series_existentes` y
  `crear_serie`. 006 no crea otra tabla ni otra columna de series.
- **008 (parte fundacional)**: `stock.StockGeneral`, `stock.StockTecnico` y
  `stock.services.obtener_stock_general`/`calcular_disponible`. La confirmación de asignaciones y
  la actualización de stock no son prerrequisito de 006; las implementa 007/008.
- **007 (solo contrato de integración)**: el envío de correo, la bandeja del almacén, la
  confirmación/rechazo y el campo `SolicitudAsignacion.confirmada_en` se completan en 007. 006
  deja el modelo y los servicios preparados para esa integración.

Si falta cualquiera de estos prerrequisitos, la implementación se detiene y se reporta; no se
sustituye con una tabla o un servicio local.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | El tenant sale de `request.usuario`/`request.tenant`, nunca de campos ocultos, URLs ni archivos. Toda consulta filtra por tenant; una solicitud o línea de otro tenant responde `404`. `LineaAsignacion.tenant` es una FK denormalizada para RLS y respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | El técnico se valida dentro del tenant y la región se copia de `tenant.region` como instantánea. El almacén solo aporta parámetros de la región. El Administrador de plataforma no opera asignaciones. |
| III. Invariantes de stock | PASA | La solicitud no modifica `StockGeneral` ni `StockTecnico`; solo reserva lógicamente al pasar a `ENVIADA`. La disponibilidad se calcula descontando lo reservado. El movimiento físico de stock ocurre únicamente en la confirmación de 007/008. Los seriados generan una línea por serie con cantidad 1; los no seriados, una línea por material con la cantidad agregada. |
| IV. Identidad y unicidad de series | PASA | Se usa `series.Serie`; la unicidad global la impone `unique(numero)`. El selector solo muestra `DISPONIBLE` y el envío cambia a `RESERVADA` en la misma transacción. No se escriben series manualmente ni se crea otra tabla de series. |
| V. Integridad transaccional | PASA | Creación, envío, reserva y generación de Excel se ejecutan en una sola `transaction.atomic`. Si falla una línea, una serie, el Excel o la auditoría, se revierte todo y se elimina el archivo generado. |
| VI. Auditoría inmutable y trazabilidad | PASA | Se auditan alta, cambio de estado, reserva de series y generación del Excel en la misma transacción. Nunca se auditan contraseñas, tokens ni secretos. La auditoría de stock la escribe 008. |
| VII. Autoridad del reporte de Lari | N/A | 006 no procesa el reporte de Lari ni conciliaciones. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA-01…CA-11 tiene al menos una prueba. No se agregan dependencias; la lógica vive en `asignaciones/services.py` y `asignaciones/excel.py`, y es testeable sin interfaz. No se implementa edición de borrador porque la spec no la pide. |

**Post-design re-check**: PASA. El diseño final no introduce una tabla de reservas: el reservado se
deriva de las solicitudes `ENVIADA`. No modifica stock, no usa `tenant_id` del cliente, no expone
JSON ni una API REST y no duplica la tabla de series.

## Project Structure

```text
asignaciones/
├── __init__.py
├── apps.py
├── excel.py
├── forms.py
├── models.py
├── services.py
├── urls.py
├── views.py
└── migrations/
    ├── 0001_initial.py
    └── 0002_rls.py

templates/asignaciones/
├── lista.html
├── formulario.html
├── detalle.html
├── _linea_form.html
├── _series_disponibles.html
├── _validacion_disponibilidad.html
└── _alerta_cupo.html

tests/
├── unit/
│   ├── test_asignacion_validaciones.py
│   ├── test_asignacion_disponibilidad.py
│   ├── test_asignacion_excel.py
│   └── test_asignacion_servicios.py
├── integration/
│   ├── test_asignacion_creacion.py
│   ├── test_asignacion_reserva.py
│   ├── test_asignacion_excel.py
│   ├── test_asignacion_custodia.py
│   ├── test_asignacion_concurrencia.py
│   ├── test_asignacion_auditoria.py
│   └── test_asignacion_aislamiento.py
└── contract/
    ├── test_asignacion_lista_http.py
    ├── test_asignacion_creacion_http.py
    ├── test_asignacion_series_http.py
    ├── test_asignacion_validacion_http.py
    └── test_asignacion_permisos_http.py
```

También se modifican:

- `config/settings/base.py`: registrar `asignaciones` en `INSTALLED_APPS`; agregar
  `MOVIMIENTO_ASIGNACION = "Z31"`, `DIAS_ALERTA_CUSTODIA = 20` y
  `ASIGNACIONES_EXCEL_DIR = "asignaciones"` (valores configurables por entorno).
- `config/urls.py`: incluir `asignaciones.urls` bajo `/asignaciones/`.
- `templates/base.html`: enlace a Asignaciones visible solo para `USUARIO_TENANT` con tenant
  activo.
- `05-especificaciones/007-envio-y-revision-del-almacen/plan.md`: al implementar 007, sustituir
  permisos Django por roles explícitos y hacer que la confirmación use `confirmada_en` y los
  servicios de 008, sin duplicar la actualización de stock.

## Modelo de datos

### `asignaciones.SolicitudAsignacion`

```python
class SolicitudAsignacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion",
    )
    fecha = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=[
            ("BORRADOR", "Borrador"),
            ("ENVIADA", "Enviada"),
            ("CONFIRMADA", "Confirmada"),
            ("RECHAZADA", "Rechazada"),
            ("CANCELADA", "Cancelada"),
        ],
        default="BORRADOR",
    )
    excel_ruta = models.CharField(max_length=255, blank=True, default="")
    excel_hash = models.CharField(max_length=64, blank=True, default="")
    excel_generado_en = models.DateTimeField(null=True, blank=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    confirmada_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion_actualizadas",
        null=True,
        blank=True,
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(estado__in=[
                    "BORRADOR", "ENVIADA", "CONFIRMADA", "RECHAZADA", "CANCELADA",
                ]),
                name="solicitud_asignacion_estado_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "estado"], name="solicitud_asign_tenant_estado"),
            models.Index(fields=["tecnico", "fecha"], name="solicitud_asign_tecnico_fecha"),
            models.Index(fields=["region", "fecha"], name="solicitud_asign_region_fecha"),
        ]
```

- `tenant` y `region` se fijan desde la sesión y `tenant.region`; el cliente nunca los envía.
- `estado` solo cambia por los servicios de 006 (borrador, envío, cancelación) y por 007
  (confirmación/rechazo). No hay transición desde `RECHAZADA`, `CONFIRMADA` o `CANCELADA`.
- `excel_ruta` guarda la ruta relativa a `MEDIA_ROOT`; `excel_hash` guarda SHA-256 hexadecimal.
- `excel_generado_en`, `enviada_en` y `confirmada_en` son marcas de tiempo; `confirmada_en` la
  escribe 007 dentro de la confirmación y 006 la usa para calcular días en mano.
- `creado_por` y `actualizado_por` son `PROTECT`; la desactivación de la cuenta no borra la
  solicitud.

### `asignaciones.LineaAsignacion`

```python
class LineaAsignacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    solicitud = models.ForeignKey(
        SolicitudAsignacion,
        on_delete=models.PROTECT,
        related_name="lineas",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    serie = models.ForeignKey(
        "series.Serie",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_asignacion_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=True) | Q(cantidad=1),
                name="linea_asignacion_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="linea_asignacion_cantidad_no_negativa",
            ),
            models.UniqueConstraint(
                fields=["solicitud", "serie"],
                condition=Q(serie__isnull=False),
                name="linea_asignacion_serie_unica_en_solicitud",
            ),
            models.UniqueConstraint(
                fields=["solicitud", "material"],
                condition=Q(serie__isnull=True),
                name="linea_asignacion_no_seriada_unica",
            ),
        ]
        indexes = [
            models.Index(fields=["solicitud", "material"], name="linea_asign_solicitud_material"),
            models.Index(fields=["tenant", "material"], name="linea_asign_tenant_material"),
            models.Index(fields=["serie"], name="linea_asign_serie"),
        ]
```

- `tenant` se fija desde `solicitud.tenant`; el servicio nunca lo acepta del cliente.
- `serie` es FK, no `OneToOneField`: una serie puede aparecer en una solicitud rechazada y luego
  volver a asignarse. La unicidad dentro de una solicitud la impone
  `linea_asignacion_serie_unica_en_solicitud`; la disponibilidad global la impone el estado de
  `series.Serie`.
- Para seriados, `serie` no es nula y `cantidad=1`. Para no seriados, `serie` es nula y
  `cantidad>0`; una sola línea por material en la solicitud.
- `lote` se copia de `material.lote`; no se acepta del cliente.
- No se crea una tabla de reservas: el reservado de no seriados se calcula con las líneas de
  solicitudes `ENVIADA`.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 006 |
|---|---|---|
| `series.Serie` | 004 | Inventario de series; `DISPONIBLE` se selecciona, `RESERVADA` al enviar y `ASIGNADA` al confirmar 007/008. |
| `stock.StockGeneral` | 008 | Stock general del tenant; 006 **solo lee** para calcular disponibilidad. |
| `stock.StockTecnico` | 008 | No se lee ni modifica en 006; la actualización ocurre en 008 al confirmar. |
| `tecnicos.Tecnico` | 003 | Destinatario; solo activos del tenant. |
| `materiales.Material` | 002 | Catálogo global; origen de descripción, lote y tipo. |
| `auditoria.RegistroCambio` | 001 | Auditoría inmutable compartida. |

## Migraciones

- `asignaciones/migrations/0001_initial.py`: `SolicitudAsignacion` y `LineaAsignacion` con
  restricciones e índices.
- `asignaciones/migrations/0002_rls.py`: políticas RLS por `tenant_id` para
  `asignaciones_solicitudasignacion` y `asignaciones_lineaasignacion`, si la infraestructura RLS
  de 001 está disponible. Si no, se registra la deuda en `research.md` y no se inventa una
  infraestructura paralela.
- No se crean solicitudes ni líneas por migración.
- No se modifican tablas de stock, series, recojos, traspasos ni conciliaciones.

## Servicios (lógica de negocio)

Viven en `asignaciones/services.py`; la generación del Excel puede vivir en
`asignaciones/excel.py` e invocarse desde el servicio. Las vistas, formularios y plantillas no
contienen lógica de negocio.

### Excepciones

- `ValidacionAsignacion`: contiene `errores` (lista de `ErrorValidacion`) y se usa para `400`.
- `PermisoDenegado`: rol, cuenta o alcance incorrecto; `403`.
- `TenantSuspendido`: tenant `SUSPENDIDO`; `403`.
- `SolicitudNoExiste`: solicitud o línea inexistente o de otro tenant; `404`.
- `TecnicoNoDisponible`: técnico inexistente, de otro tenant o inactivo; `400`.
- `MaterialNoExiste`: el material no existe en el catálogo; `400`.
- `SerieNoDisponible`: la serie no está `DISPONIBLE` o no pertenece al tenant/material; `400`.
- `SerieDuplicada`: la serie se repite en la solicitud; `400`.
- `CantidadInvalida`: cantidad no numérica, cero o negativa; `400`.
- `CantidadExcedeDisponible`: la cantidad supera `Stock General - Reservado`; `400`.
- `EstadoSolicitudInvalido`: la operación no aplica al estado actual; `409`.
- `ExcelAsignacionInvalido`: no se pudo generar o firmar el Excel; `500` interno, sin exponer
  detalles técnicos.

### Permisos y alcance

- `validar_cuenta_tenant(actor)`:
  - Exige `actor.rol == Rol.USUARIO_TENANT`.
  - Exige `actor.is_active`.
  - Exige `actor.tenant` y `actor.tenant.estado == "ACTIVO"`; si no, `TenantSuspendido` con
    "El tenant está suspendido".
  - Cualquier otro rol lanza `PermisoDenegado` con "No tienes permiso para crear asignaciones".
  - Devuelve el tenant de la sesión. No acepta `tenant_id` externo.
- `obtener_solicitud(tenant, solicitud_id)`:
  - Busca con `SolicitudAsignacion.objects.filter(tenant=tenant, id=solicitud_id)`.
  - Si no existe o es de otro tenant, `SolicitudNoExiste` con "La solicitud no existe".
- `listar_solicitudes(tenant, estado=None)`:
  - Filtra siempre por tenant, opcionalmente por estado, ordena por `fecha` y `id` descendente.
- `obtener_detalle_solicitud(tenant, solicitud_id)`:
  - Precarga `lineas__material` y `lineas__serie`; evita N+1.

### Validación de líneas

- `normalizar_lineas_solicitud(tenant, lineas)`:
  - Resuelve cada material por `id` en el catálogo global.
  - Para seriados, recibe una lista de `serie_ids`, las consulta con
    `Serie.objects.filter(tenant=tenant, material=material, id__in=...)`, exige que todas existan,
    no se repitan y estén `DISPONIBLE`; genera una `LineaValidada` por serie con `cantidad=1`.
  - Para no seriados, exige que no haya series y que la cantidad sea un entero `> 0`; agrupa
    varias líneas del mismo material sumando cantidades.
  - Copia `lote` de `material.lote` y conserva `filas_origen` para los mensajes.
- `validar_lineas_solicitud(tenant, lineas)`:
  - Exige al menos una línea: "La solicitud debe tener al menos una línea".
  - Material inexistente: "El material no existe en el catálogo".
  - Seriado sin series: "Debe indicar al menos una serie".
  - No seriado con series: "El material no es seriado y no admite series".
  - Serie repetida: "La serie está duplicada en la solicitud".
  - Serie no disponible: "La serie no está disponible".
  - Cantidad no entera: "La cantidad debe ser un número entero".
  - Cantidad `<= 0`: "La cantidad debe ser mayor a 0".
  - No escribe en la base.
- `validar_tecnico_para_asignacion(tenant, tecnico_id)`:
  - Busca el técnico por `id` dentro del tenant y exige `activo=True`.
  - Si no, `TecnicoNoDisponible` con "El técnico está desactivado" o
    "El técnico no existe en este tenant".

### Disponibilidad

- `calcular_reservado(tenant, material)`:
  - Suma `cantidad` de `LineaAsignacion` no seriadas cuya `solicitud.tenant == tenant`,
    `solicitud.estado == "ENVIADA"` y `material == material`.
  - Una sola consulta agregada; no una por línea.
- `calcular_disponible(tenant, material)`:
  - `max(0, stock_general.cantidad - calcular_reservado(tenant, material))`.
  - Si no existe `StockGeneral`, el stock es 0.
- `validar_cantidad_disponible(tenant, material, cantidad)`:
  - Si `cantidad > calcular_disponible`, `CantidadExcedeDisponible` con
    "La cantidad supera el stock disponible".
- `series_disponibles_para_asignacion(tenant, material, q="", excluir_ids=None)`:
  - Filtra por `tenant`, `material` y `estado=EstadoSerie.DISPONIBLE`.
  - Excluye `excluir_ids` y aplica `q` por `numero` o por código/descripción del material.
  - Ordena por `numero`; devuelve un queryset paginado (20 por página en el selector).
- `validar_series_disponibles(tenant, material, series)`:
  - Verifica que todas pertenezcan al tenant y material y sigan `DISPONIBLE`.
  - No revela el tenant de una serie ajena; usa "La serie no está disponible".

### Creación y envío

- `crear_borrador_solicitud(tenant, tecnico_id, fecha, lineas, actor)`:
  - `validar_cuenta_tenant(actor)`.
  - `validar_tecnico_para_asignacion`.
  - Normaliza y valida las líneas.
  - En `transaction.atomic`, crea `SolicitudAsignacion` en `BORRADOR`, con región de la sesión y
    `creado_por=actor`, y sus `LineaAsignacion`; audita `SolicitudAsignacion/alta` y
    `LineaAsignacion/alta`.
  - No reserva series ni cantidades, no genera Excel.
- `enviar_solicitud(solicitud, actor)`:
  - `validar_cuenta_tenant(actor)`; exige `estado == "BORRADOR"`; si no,
    `EstadoSolicitudInvalido` con "Solo se pueden enviar solicitudes en borrador".
  - En `transaction.atomic`:
    - Bloquea el `Tenant` con `select_for_update` y relee la solicitud.
    - Bloquea con `select_for_update` las `StockGeneral` de los materiales no seriados y las
      `Serie` seleccionadas, en orden de id, para evitar interbloqueos.
    - Revalida disponibilidad y estado de cada serie dentro de la transacción.
    - Cambia cada serie a `RESERVADA` con `actualizado_por=actor` y audita
      `Serie/estado` (`DISPONIBLE`→`RESERVADA`).
    - Genera el Excel, calcula el hash y guarda `excel_ruta`, `excel_hash` y
      `excel_generado_en`.
    - Cambia la solicitud a `ENVIADA`, fija `enviada_en` y `actualizado_por`, y audita
      `SolicitudAsignacion/estado` (`BORRADOR`→`ENVIADA`) con totales y hash.
  - Si algo falla, revierte la transacción y elimina el archivo generado.
  - No modifica `StockGeneral` ni `StockTecnico`; la reserva es lógica y se deriva del estado
    `ENVIADA`.
- `crear_y_enviar_solicitud(tenant, tecnico_id, fecha, lineas, actor)`:
  - Ejecuta creación y envío en una sola `transaction.atomic`; si el envío falla, no queda ni
    borrador ni archivo.
  - Es la operación que usa el botón "Enviar" del formulario y la que cubre CA-01.

### Cancelación

- `cancelar_solicitud(solicitud, actor)`:
  - `validar_cuenta_tenant(actor)`; exige `estado == "BORRADOR"`; si no,
    `EstadoSolicitudInvalido` con "Solo se pueden cancelar solicitudes en borrador".
  - En `transaction.atomic`, cambia a `CANCELADA`, fija `actualizado_por` y audita
    `SolicitudAsignacion/estado` (`BORRADOR`→`CANCELADA`).
  - No libera series ni cantidades porque el borrador no reservó.
  - No se implementa edición de borrador: la spec no la pide; para corregir se cancela y se crea
    una nueva.

### Días en mano y alerta de cupo

- `dias_en_mano_serie(linea, hoy=None)`:
  - Exige que la solicitud esté `CONFIRMADA` y tenga `confirmada_en`.
  - Devuelve `(hoy - confirmada_en.date()).days`; si no está confirmada, devuelve `None`.
- `series_en_custodia_tecnico(tecnico)`:
  - Recorre las líneas seriadas de solicitudes `CONFIRMADA` del técnico cuya `Serie.estado` sea
    `ASIGNADA`; conserva la confirmación más reciente por serie.
  - Devuelve una estructura con serie, material, `confirmada_en`, días en mano.
  - 009/011 deberán actualizar la fuente de custodia cuando muevan o devuelvan series; hasta
    entonces esta consulta cubre las asignaciones confirmadas por 007/008.
- `calcular_alerta_cupo(tecnico)`:
  - Devuelve `AlertaCupo` si alguna serie en custodia supera
    `settings.DIAS_ALERTA_CUSTODIA` (20 por defecto).
  - El mensaje es "El técnico supera los 20 días en mano" y no bloquea la creación ni el envío.
  - La alerta se calcula por equipo seriado, no por suma de días de todos los equipos; se corrige
    la redacción de `spec.md` §11 en las correcciones documentales.

### Consultas y totales

- `totales_solicitud(solicitud)`:
  - `total_lineas`, `total_series` (líneas con serie) y `total_cantidad` (suma de líneas no
    seriadas).
- `estado_solicitud(solicitud)` no se duplica: se usa el campo `estado`.

## Permisos

- **Crear, ver, enviar y cancelar**: únicamente `USUARIO_TENANT` activo con tenant `ACTIVO`.
- **Administrador de plataforma**: `403` en todas las rutas de 006 con
  "No tienes permiso para crear asignaciones".
- **Responsable de almacén**: `403` en todas las rutas de 006; opera en 007.
- **Tenant suspendido**: `403` con "El tenant está suspendido".
- **Cuenta inactiva**: no puede iniciar sesión; si la sesión existiera, el servicio la rechaza.
- **Datos de otro tenant**: `404` con "La solicitud no existe", sin revelar el propietario.
- **Anónimo**: redirección al login.
- Los permisos se validan en la vista y de nuevo en el servicio. No se usan permisos Django
  (`asignaciones.add_*`) ni grupos sembrados en migraciones; la autorización es por rol explícito
  y alcance de tenant, igual que en 001, 004 y 005.
- No se acepta `tenant_id`, `region_id`, `creado_por`, `nif` ni `estado` desde formularios, URLs,
  archivos o peticiones HTMX.

## Interfaz y endpoints

| Ruta | Método | Función | Éxito | Errores principales |
|---|---|---|---|---|
| `/asignaciones/` | GET | Listado paginado con filtro por estado | `200` | `403`, `405` |
| `/asignaciones/nueva/` | GET | Formulario de creación | `200` | `403`, `405` |
| `/asignaciones/nueva/` | POST | Guardar borrador o crear y enviar | `302` al detalle | `400`, `403`, `409`, `405` |
| `/asignaciones/<int:solicitud_id>/` | GET | Detalle de la solicitud | `200` | `403`, `404`, `405` |
| `/asignaciones/<int:solicitud_id>/enviar/` | POST | Enviar un borrador | `302` al detalle | `400`, `403`, `404`, `409`, `405` |
| `/asignaciones/<int:solicitud_id>/cancelar/` | POST | Cancelar un borrador | `302` al detalle | `403`, `404`, `409`, `405` |
| `/asignaciones/series-disponibles/` | GET | Fragmento HTMX de series disponibles | `200` | `400`, `403`, `405` |
| `/asignaciones/validar-disponibilidad/` | POST | Fragmento HTMX de disponibilidad y cupo | `200` | `400`, `403`, `405` |

- No existe `GET /asignaciones/<id>/editar/` ni ruta de borrado. `DELETE`, `PUT` y `PATCH`
  responden `405` en todas las rutas.
- La descarga y el envío por correo del Excel pertenecen a 007. 006 no expone una ruta de correo.
- `series-disponibles` y `validar-disponibilidad` devuelven **fragmentos HTML/HTMX**, nunca JSON.
- El formulario tiene una sola solicitud y un solo técnico; las líneas se agregan/eliminan en el
  cliente. Un botón "Guardar borrador" crea un `BORRADOR`; un botón "Enviar" ejecuta
  `crear_y_enviar_solicitud` y redirige al detalle.
- El selector de técnico usa `tecnicos.services.tecnicos_para_operacion` (solo activos). El
  selector de material usa `/materiales/buscar/` de 002.
- La pantalla de detalle muestra técnico, NIF, fecha, estado, líneas agrupadas, totales, hash del
  Excel y, si la solicitud está confirmada, los días en mano por serie y la alerta de cupo.
- La alerta de cupo se muestra como aviso no intrusivo; no deshabilita "Enviar".

## Integraciones

- **001 Tenants y acceso**: `Tenant`, `Region`, `Almacen`, `Usuario`, `ContextoUsuarioMiddleware`,
  `request.usuario`, `RegistroCambio` y `registrar_cambio`. Los parámetros `centro`,
  `codigo_almacen` y `buzon` salen del almacén de la región; nunca del cliente.
- **002 Materiales**: `Material.codigo`, `descripcion`, `lote`, `es_seriado`; el selector reutiliza
  `buscar_materiales` y `/materiales/buscar/`. Descripción y lote del Excel se toman del catálogo.
- **003 Técnicos**: `Tecnico` del tenant; solo activos en el formulario. El NIF se copia al Excel y
  no es editable.
- **004 Series**: `series.Serie` y `EstadoSerie`. 006 cambia `DISPONIBLE`→`RESERVADA` al enviar;
  007/008 cambian `RESERVADA`→`ASIGNADA` o `RESERVADA`→`DISPONIBLE` al confirmar/rechazar.
- **008 Stock**: 006 solo lee `StockGeneral`; no escribe `StockGeneral` ni `StockTecnico`. La
  confirmación de 007 llama a `stock.services.actualizar_stock_confirmacion_asignacion` y audita
  los movimientos.
- **007 Envío y revisión**: recibe el Excel generado, lo envía al buzón del almacén, confirma o
  rechaza y fija `confirmada_en`. 006 deja preparados los campos y la auditoría; no implementa
  correo, Celery, WebSocket ni bandeja.
- **009 Traspasos y 011 Logística inversa**: consumen las series `ASIGNADA` y el stock del técnico.
  006 no implementa sus transiciones; cuando 009/011 muevan una serie deberán actualizar la fuente
  de custodia usada para días en mano.
- **Lari**: no hay integración directa. El Excel de asignación es un formato de salida; el reporte
  de Lari se procesa en 010.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje | Respuesta |
|---|---|---|---|
| Cuenta y tenant de la sesión | Vista y servicio | "No tienes permiso para crear asignaciones" | `403` |
| Tenant suspendido | Servicio | "El tenant está suspendido" | `403` |
| Solicitud de otro tenant | Servicio | "La solicitud no existe" | `404` |
| Técnico activo del tenant | Servicio | "El técnico está desactivado" / "El técnico no existe en este tenant" | `400` |
| Al menos una línea | Servicio y formulario | "La solicitud debe tener al menos una línea" | `400` |
| Material existe | Servicio | "El material no existe en el catálogo" | `400` |
| Seriado requiere series | Servicio y formulario | "Debe indicar al menos una serie" | `400` |
| No seriado no admite series | Servicio y formulario | "El material no es seriado y no admite series" | `400` |
| Serie `DISPONIBLE` | Servicio y estado de serie | "La serie no está disponible" | `400` |
| Serie duplicada en la solicitud | Servicio y `UniqueConstraint` | "La serie está duplicada en la solicitud" | `400` |
| Cantidad entera `> 0` | Servicio y `CheckConstraint` | "La cantidad debe ser mayor a 0" / "La cantidad debe ser un número entero" | `400` |
| Cantidad no supera disponible | Servicio | "La cantidad supera el stock disponible" | `400` |
| Disponible = Stock - Reservado | Servicio | Cálculo interno | — |
| Solo `BORRADOR` se envía | Servicio | "Solo se pueden enviar solicitudes en borrador" | `409` |
| Solo `BORRADOR` se cancela | Servicio | "Solo se pueden cancelar solicitudes en borrador" | `409` |
| Serie con cantidad distinta de 1 | `CheckConstraint` | Violación de restricción | `400` |
| Línea sin serie ni cantidad | `CheckConstraint` | Violación de restricción | `400` |
| Línea no seriada duplicada | `UniqueConstraint` | Violación de restricción | `400` |
| Serie duplicada en la solicitud | `UniqueConstraint` | Violación de restricción | `400` |
| Alerta de cupo máximo | Servicio (no bloquea) | "El técnico supera los 20 días en mano" | Aviso |
| Error al generar Excel | Servicio | "No se pudo generar el Excel de asignación" | `500` interno |

## Transacciones y concurrencia

- La creación del borrador y sus líneas se ejecuta en una sola `transaction.atomic`.
- El envío de la solicitud, la reserva de series, la generación del Excel y la auditoría se
  ejecutan en una sola `transaction.atomic`.
- **Envío concurrente del mismo tenant**: se bloquea el `Tenant` con `select_for_update`; el
  segundo envío espera, relee el estado y recalcula la disponibilidad. Esto evita dos reservas
  simultáneas del mismo material no seriado.
- **Series concurrentes**: se bloquean las `Serie` seleccionadas con `select_for_update`, en orden
  de id. La primera las cambia a `RESERVADA`; la segunda, al releer, recibe
  "La serie no está disponible". La unicidad global de `numero` sigue siendo respaldo.
- **Stock no seriado**: se bloquean las filas de `StockGeneral` de los materiales afectados, en
  orden de id, y se recalcula `Reservado` dentro de la transacción. No se usan bloqueos de
  aplicación ni cachés.
- **Excel**: se genera en memoria, se calcula el hash y se escribe el archivo antes de confirmar
  la transacción. Si la transacción falla, se elimina el archivo en el manejo de la excepción; si
  el proceso muere entre la escritura y el commit, el archivo huérfano se detecta por no tener
  solicitud `ENVIADA` y se puede limpiar con una tarea de mantenimiento documentada.
- La validación previa (HTMX o formulario) no es autoridad; el envío revalida dentro de la
  transacción.
- No hay reserva de stock físico en 006: `StockGeneral` y `StockTecnico` solo cambian en la
  confirmación de 007/008.

## Generación del Excel

- `generar_excel_asignacion(solicitud)` en `asignaciones/excel.py`:
  - Usa `openpyxl` y un libro nuevo; no usa macros ni fórmulas.
  - Metadatos: `Movimiento=settings.MOVIMIENTO_ASIGNACION` (`Z31`), `Centro=region.almacen.centro`,
    `Almacén=region.almacen.codigo_almacen`, `NIF=solicitud.tecnico.nif`,
    `Fecha de solicitud=solicitud.fecha.isoformat()`, `Tenant=tenant.codigo`,
    `Región=region.codigo`, `ID de solicitud=solicitud.id`.
  - Tabla de seriales: una fila por línea seriada con código, descripción, lote, serie y cantidad 1.
  - Tabla de material menor: una fila por línea no seriada con código, descripción, lote y cantidad.
  - Escribe los bytes, calcula `hashlib.sha256(bytes).hexdigest()` y devuelve `(contenido, hash)`.
- `guardar_excel_asignacion(solicitud, contenido, hash)`:
  - Guarda en `MEDIA_ROOT/ASIGNACIONES_EXCEL_DIR/<tenant.codigo>/<solicitud.id>/<uuid>.xlsx`.
  - `excel_ruta` se guarda relativa a `MEDIA_ROOT`; el nombre no incluye datos personales.
  - El archivo es de solo lectura y no se regenera una vez `ENVIADA`.
- La descarga y la verificación de hash pertenecen a 007.
- El contrato detallado está en `contracts/excel-asignacion-generado.md`.

## Auditoría

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Alta de solicitud | `SolicitudAsignacion` | `alta` | — | fecha, NIF, estado BORRADOR, líneas, series, cantidad |
| Alta de línea | `LineaAsignacion` | `alta` | — | material, lote, serie o cantidad |
| Envío | `SolicitudAsignacion` | `estado` | `BORRADOR` | `ENVIADA`; incluye totales y hash |
| Reserva de serie | `Serie` | `estado` | `DISPONIBLE` | `RESERVADA` |
| Generación de Excel | `SolicitudAsignacion` | `excel` | — | ruta relativa y hash |
| Cancelación | `SolicitudAsignacion` | `estado` | `BORRADOR` | `CANCELADA` |
| Confirmación | `SolicitudAsignacion` | `estado` | `ENVIADA` | `CONFIRMADA` (007) |
| Rechazo | `SolicitudAsignacion` | `estado` | `ENVIADA` | `RECHAZADA` (007) |
| Cambio de serie al confirmar/rechazar | `Serie` | `estado` | `RESERVADA` | `ASIGNADA`/`DISPONIBLE` (007/008) |
| Movimiento de stock | `StockGeneral`/`StockTecnico` | `cantidad` | anterior | nueva (008) |

- Todos los registros se escriben en la misma transacción que el cambio. Si la operación falla,
  no se escribe auditoría.
- La auditoría de stock es responsabilidad de 008; 006 no la duplica.
- No se auditan contraseñas, tokens, secretos TOTP, `token_hash` ni contenido del Excel; solo
  nombre, ruta y hash.
- No se escribe `tenant_id` como campo separado; el tenant se deduce del usuario y de la entidad.
- La auditoría no revela datos de otros tenants.

## RLS y aislamiento

- `asignaciones_solicitudasignacion` y `asignaciones_lineaasignacion` llevan `tenant_id` y
  políticas RLS por tenant, si la infraestructura de 001 está disponible.
- `LineaAsignacion.tenant` se fija desde `solicitud.tenant`; el servicio nunca lo acepta del
  cliente.
- Todas las consultas de listado, detalle, validación y selector filtran por
  `tenant=request.usuario.tenant`.
- `series_serie` y `stock_stockgeneral` tienen sus propias políticas, propiedad de 004 y 008. 006
  no las duplica.
- Si RLS no está listo, el filtrado de aplicación sigue siendo obligatorio y la deuda se registra
  en `research.md`; no se implementa una RLS paralela.

## Pruebas

**Puerta**: cada CA-01…CA-11 tiene al menos una prueba. Las pruebas se escriben primero y deben
fallar antes de implementar. Todas corren sobre PostgreSQL, nunca SQLite.

### Unitarias

- `tests/unit/test_asignacion_validaciones.py`:
  - material seriado con series y no seriado con cantidad;
  - seriado sin series, no seriado con series, cantidad cero, negativa y no entera;
  - agrupación de no seriados por material;
  - expansión de series a líneas con cantidad 1;
  - duplicado de serie dentro de la solicitud;
  - técnico inactivo y de otro tenant;
  - lote tomado del catálogo.
- `tests/unit/test_asignacion_disponibilidad.py`:
  - `Disponible = Stock General - Reservado`;
  - reservado solo de solicitudes `ENVIADA`, no de borradores ni rechazadas;
  - cantidad igual al disponible se acepta y cantidad mayor se rechaza;
  - `calcular_alerta_cupo` con 0, 19, 20 y 25 días;
  - `dias_en_mano_serie` desde `confirmada_en`, no desde `fecha`.
- `tests/unit/test_asignacion_excel.py`:
  - metadatos Z31, centro, almacén, NIF, fecha, tenant, región e ID;
  - tabla de seriales y de material menor;
  - hash SHA-256 estable y hexadecimal de 64 caracteres;
  - no se incluyen datos de otras solicitudes ni del tenant ajeno;
  - nombre de archivo seguro y ruta relativa.
- `tests/unit/test_asignacion_servicios.py`:
  - `validar_cuenta_tenant` con los tres roles, cuenta inactiva y tenant suspendido;
  - `obtener_solicitud` con solicitud propia, inexistente y ajena;
  - `listar_solicitudes` filtra por tenant y estado;
  - `totales_solicitud`;
  - transiciones de estado permitidas y rechazadas.

### Integración

- `tests/integration/test_asignacion_creacion.py`:
  - **CA-01** `test_crear_y_enviar_solicitud_valida`: una solicitud con series y no seriados se
    crea `ENVIADA`, las series quedan `RESERVADA`, el Excel existe y no se modificó el stock.
  - `test_crear_borrador_no_reserva_ni_genera_excel`.
  - `test_cancelar_borrador_no_libera_series`.
  - `test_solicitud_sin_lineas_rechazada`.
  - `test_tecnico_inactivo_rechazado`.
- `tests/integration/test_asignacion_reserva.py`:
  - **CA-02** `test_selector_solo_muestra_series_disponibles`: con series `DISPONIBLE`,
    `RESERVADA` y `ASIGNADA` del mismo tenant y material, el selector devuelve solo la primera.
  - **CA-03** `test_cantidad_excede_disponible_se_rechaza`.
  - **CA-04** `test_disponible_descuenta_reservado`.
  - **CA-05** `test_series_pasan_a_reservada_al_enviar`.
  - **CA-10** `test_serie_asignada_no_aparece_en_selector`.
  - **CA-11** `test_serie_reservada_no_aparece_en_selector`.
  - `test_otra_solicitud_no_puede_reservar_la_misma_serie`.
  - `test_stock_general_y_tecnico_no_cambian_al_enviar`.
- `tests/integration/test_asignacion_excel.py`:
  - **CA-06** `test_excel_metadatos_z31_centro_almacen_y_nif`;
  - **CA-07** `test_nif_se_copia_del_tecnico_y_no_del_formulario`;
  - `test_hash_del_excel_coincide_con_el_archivo`;
  - `test_excel_no_se_regenera_despues_de_enviar`.
- `tests/integration/test_asignacion_custodia.py`:
  - **CA-08** `test_dias_en_mano_inician_al_confirmar` usando una solicitud con
    `confirmada_en` fijado por el fixture de 007;
  - **CA-09** `test_alerta_cupo_maximo_se_muestra` con una serie de 25 días;
  - `test_alerta_cupo_no_bloquea_el_envio`;
  - `test_dias_en_mano_no_cuentan_series_devueltas`.
- `tests/integration/test_asignacion_concurrencia.py`:
  - dos envíos concurrentes del mismo tenant no sobrepasan el disponible;
  - dos envíos concurrentes de la misma serie dejan una sola `RESERVADA`;
  - un envío fallido revierte series, solicitud, Excel y auditoría.
- `tests/integration/test_asignacion_auditoria.py`:
  - alta de solicitud y de cada línea;
  - envío con totales y hash;
  - una reserva `Serie/estado` por serie;
  - cancelación;
  - ausencia de secretos y de `tenant_id` separado;
  - la auditoría se conserva al desactivar la cuenta o suspender el tenant.
- `tests/integration/test_asignacion_aislamiento.py`:
  - solicitud de otro tenant responde `404`;
  - Admin y Almacén reciben `403`;
  - tenant suspendido recibe `403`;
  - `tenant_id`/`region_id`/`nif` forzados se ignoran;
  - RLS por tenant si la infraestructura está disponible.

### Contrato HTTP

- `tests/contract/test_asignacion_lista_http.py`: listado paginado, filtro por estado, columnas y
  totales, `403`, `405`.
- `tests/contract/test_asignacion_creacion_http.py`: `GET/POST /asignaciones/nueva/`, guardar
  borrador (`302`), crear y enviar (`302`), `400` con errores por línea, `409` por estado, `403`,
  `405`, NIF no editable y ausencia de `tenant_id`/`region_id` en el formulario.
- `tests/contract/test_asignacion_series_http.py`: **CA-02** `GET /asignaciones/series-disponibles/`
  devuelve fragmento con solo `DISPONIBLE`, búsqueda, paginación, `data-serie` y sin JSON.
- `tests/contract/test_asignacion_validacion_http.py`: `POST /asignaciones/validar-disponibilidad/`
  devuelve fragmento con `data-valido`, `data-disponible`, `data-alerta-cupo` y errores; no escribe
  ni reserva; `400`/`403`/`405`.
- `tests/contract/test_asignacion_permisos_http.py`: matriz completa de las 8 rutas para
  `ADMIN_PLATAFORMA`, `RESPONSABLE_ALMACEN`, `USUARIO_TENANT`, tenant suspendido y anónimo.

### Restricciones de base de datos

- Insertar una línea con serie y `cantidad != 1` falla.
- Insertar una línea sin serie y `cantidad <= 0` falla.
- Insertar dos líneas con la misma serie en la misma solicitud falla.
- Insertar dos líneas no seriadas del mismo material en la misma solicitud falla.
- Insertar una línea con `tenant` distinto de la solicitud es posible a nivel de base, pero el
  servicio fija el tenant correcto; una prueba lo verifica.
- Insertar una serie con formato inválido falla en `series.Serie`.

### Rendimiento

- `django_assert_num_queries` para:
  - listado paginado a 50 sin N+1;
  - detalle con `select_related`/`prefetch_related`;
  - validación de disponibilidad con una consulta de stock y una de reservado;
  - selector de series con una consulta paginada;
  - envío con una consulta de series y una de stock por material, no por línea.
- La validación de disponibilidad debe responder en menos de 1 segundo en el escenario de prueba.

## Decisiones y riesgos

- **Reserva lógica, no tabla de reservas**: el reservado de no seriados se calcula con las líneas
  de solicitudes `ENVIADA`; el de series es el estado `RESERVADA`. Evita duplicar stock y mantiene
  una sola fuente de verdad.
- **No se modifica stock en 006**: `StockGeneral` y `StockTecnico` solo cambian al confirmar
  007/008. Esto respeta la constitución y evita descuadres si el almacén rechaza.
- **Excel al enviar, no al crear borrador**: el borrador no es un documento firme. El Excel se
  genera en la transición `BORRADOR`→`ENVIADA`, que es la acción que la spec describe como
  "crear la solicitud" en CA-01. Se corrige la redacción de §5.5.
- **Sin edición de borrador**: la spec no la pide; se puede cancelar y crear otra. Si el negocio
  la requiere, se agrega en una spec posterior.
- **Series centralizadas**: `LineaAsignacion.serie` es FK a `series.Serie`; no hay columna de
  texto ni tabla duplicada. La FK permite reutilizar una serie tras un rechazo o devolución; la
  unicidad dentro de la solicitud y el estado de la serie cubren la integridad.
- **Días en mano desde `confirmada_en`**: 007 fija la fecha de confirmación; 006 no inventa una
  fecha de asignación al crear. Hasta que 007 esté implementada, las pruebas usan el fixture de
  confirmación.
- **Alerta por equipo**: se alerta si algún seriado supera 20 días, no si la suma de días de todos
  los equipos supera 20. La suma produciría alertas con dos equipos de 11 días y no identificaría
  el equipo en riesgo; se corrige la redacción de `spec.md` §11.
- **HTMX sin JSON**: la validación y el selector devuelven fragmentos HTML, coherentes con 001,
  004 y 005. No se agrega una API REST.
- **Permisos por rol**: no se usan permisos Django ni grupos; se mantiene el patrón de 001/004/005.
- **Sin Celery en 006**: la generación del Excel es síncrona y transaccional; el envío de correo,
  la bandeja y las notificaciones son de 007.
- **Riesgo de Excel huérfano**: si el proceso muere después de escribir el archivo y antes del
  commit, queda un archivo sin solicitud. Se documenta una limpieza por mantenimiento; no se
  empeora la transacción por un fallo de disco.
- **Riesgo de custodia futura**: 009 y 011 deberán actualizar la fuente de días en mano cuando
  transfieran o devuelvan series; 006 cubre la asignación confirmada por 007/008 y deja la consulta
  aislada para que esas specs la extiendan.
- **Riesgo de RLS no disponible**: se registra la deuda y se mantiene el filtrado de aplicación.

## Complexity Tracking

No se identifican violaciones a la constitución. Las decisiones que agregan complejidad están
justificadas:

| Decisión | Por qué | Alternativa rechazada |
|---|---|---|
| Reserva calculada desde solicitudes `ENVIADA` | Evita una tabla de reservas y mantiene el stock como única fuente de verdad | Tabla `ReservaStock` con estados propios, que duplicaría la lógica de 008 |
| Bloqueo de tenant, series y stock al enviar | Evita sobreasignación en envíos concurrentes sin usar bloqueos de aplicación | Confiar solo en la validación previa, que puede quedar obsoleta entre la vista y el guardado |
| Excel generado al enviar | El borrador puede no ser el documento definitivo; el Excel debe corresponder a lo reservado | Generar el Excel al crear el borrador y regenerarlo al enviar, con dos archivos y dos hashes |
| Alerta por equipo | Identifica el equipo que supera 20 días y coincide con RF-63 | Sumar días de todos los equipos, que dispara la alerta sin un equipo culpable |

## Correcciones documentales requeridas antes de implementar

1. `05-especificaciones/006-solicitud-de-asignacion/spec.md` §5.5 y CA-01: aclarar que el Excel se
   genera al enviar la solicitud (`BORRADOR`→`ENVIADA`) y que "crear" en CA-01 significa
   "crear y enviar"; el borrador no genera Excel.
2. `05-especificaciones/006-solicitud-de-asignacion/spec.md` §11: cambiar "sumando días en mano de
   todos los seriados" por "revisando cada equipo seriado; se alerta si alguno supera 20 días".
3. `04-contratos/excel-asignacion.md` §2 y §8: precisar que el Excel se genera al enviar, no al
   guardar el borrador, y que su descarga/verificación pertenece a 007.
4. `05-especificaciones/007-envio-y-revision-del-almacen/plan.md`: al implementar 007, reemplazar
   los permisos Django por roles explícitos, eliminar la duplicación de la actualización de stock
   (usar los servicios de 008) y fijar `SolicitudAsignacion.confirmada_en` al confirmar.
5. `05-especificaciones/009-traspaso-entre-tecnicos/plan.md` y
   `05-especificaciones/011-logistica-inversa-y-devoluciones/plan.md`: al implementarlas, definir
   cómo actualizan la fuente de custodia de series para que el cálculo de días en mano de 006 siga
   siendo correcto después de un traspaso o devolución.
