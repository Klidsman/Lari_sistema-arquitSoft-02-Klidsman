# Plan técnico: 010 Conciliación de Stock

**Branch**: `010-conciliacion-de-stock` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/010-conciliacion-de-stock/spec.md`

**Input**: Spec en `05-especificaciones/010-conciliacion-de-stock/spec.md`

## Summary

Implementar la conciliación del stock del tenant contra el reporte diario de Lari. El tenant carga un
Excel `.xlsx` con la hoja `GENERAL`; el sistema valida el archivo, filtra los técnicos del tenant,
compara series y cantidades, y crea una conciliación `EN_REVISION` **sin modificar stock**. El tenant
revisa las diferencias categorizadas y aprueba o rechaza. Al aprobar, el reporte de Lari prevalece:
las series faltantes se crean, las no reportadas se marcan `INSTALADA`, las series reportadas en otro
técnico se reasignan y el stock de fungibles se fija a la cantidad reportada. Todo ocurre en una sola
transacción; el stock general no se toca. Si el stock cambió entre la carga y la aprobación, se
recalculan las diferencias y se exige revisar de nuevo.

La spec 010 tiene dos contradicciones que este plan resuelve y corrige en los documentos:
1. El reporte de Lari es regional y contiene técnicos de varios tenants. Las filas de técnicos de
   **otro tenant de la misma región se ignoran**; las de técnicos desconocidos o de otra región
   rechazan el archivo. RF-48/CA-12 se interpretan como “técnico fuera del padrón regional”.
2. `series.Serie` no tiene estado terminal `INSTALADA`. Se añade como estado de liquidación,
   coherente con 012 y con la regla de que una serie no se elimina.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX; carga, listado, detalle, aprobación y rechazo |
| App nueva | `conciliaciones` |
| Excel | `openpyxl`; solo `.xlsx`; hoja `GENERAL` |
| Stock | Servicios de 008; **nunca** se escribe `StockGeneral` |
| Series | `series.Serie`; nuevo estado terminal `INSTALADA` |
| Aprobación | Una transacción; todo o nada |
| Recálculo | Huella del stock afectado; si cambia, recalcula y exige revisar |
| Bloqueos | `select_for_update` en orden estable |
| Auditoría | `auditoria.RegistroCambio` en la misma transacción |
| Correo/Celery | Fuera de alcance; la carga y aprobación son síncronas |
| Dependencias nuevas | Ninguna |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL`, `ContextoUsuarioMiddleware`, `Tenant`, `Region`, roles y auditoría.
- **002**: `Material` con `codigo`, `descripcion`, `lote` y `es_seriado`.
- **003**: `Tecnico` con `tenant`, `nif`, `nombre` y `activo`.
- **004**: `series.Serie` con `numero`, `tenant`, `region`, `material`, `lote`, `estado`,
  `tecnico` y `asignada_en`; estado `INSTALADA` y `series.services.crear_serie`.
- **005/008**: `StockTecnico` y servicios `incrementar_stock_tecnico`/`decrementar_stock_tecnico`;
  series de stock inicial con custodia.
- **009**: la custodia de series y los servicios de traspaso ya usan `Serie.tecnico/asignada_en`.
- **Infraestructura**: PostgreSQL con rol sin `SUPERUSER` ni `BYPASSRLS`.

Si falta cualquiera, la implementación se detiene y se reporta.

### Orden de implementación

1. Correcciones documentales de 010, 004, 009 y 012; migración de `Serie.estado=INSTALADA`.
2. App `conciliaciones`: modelos, migraciones, lectura/validación del Excel, diferencias.
3. Carga y recálculo; luego aprobación/rechazo.
4. 011/012 consumen `INSTALADA` y la custodia sin duplicar lógica.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | `Conciliacion`, diferencias y materiales no catalogados llevan `tenant`/`region`; el tenant sale de la sesión. Las filas de otros tenants de la región se ignoran y nunca se muestran. RLS como respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | La región se fija desde `tenant.region`; técnicos desconocidos o de otra región rechazan el archivo; el Administrador no opera conciliaciones. |
| III. Invariantes de stock | PASA | Cargar no modifica stock. Aprobar fija el stock técnico al reporte y no toca `StockGeneral`. No se asigna de más: el reporte es la fuente contractual y la aprobación es humana. |
| IV. Identidad y unicidad de series | PASA | Se usa `series.Serie`; las series faltantes se crean, las no reportadas pasan a `INSTALADA` y no se eliminan. La unicidad global y el formato se validan. |
| V. Integridad transaccional | PASA | La carga es atómica; la aprobación aplica series, stock y auditoría en una sola transacción. Un fallo revierte todo. |
| VI. Auditoría inmutable y trazabilidad | PASA | `Conciliacion/estado`, `Conciliacion/archivo`, `Conciliacion/recalculo`, `Serie/alta`, `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en` y `StockTecnico/cantidad` con valor anterior y nuevo. Sin secretos ni binarios. |
| VII. Autoridad del reporte de Lari y aprobación humana | PASA | Cargar no modifica stock; el reporte prevalece al aprobar; la aprobación es humana y completa. No hay integración directa ni automatismo. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA-01…CA-12 tiene prueba. Solo se usa `openpyxl`; no se agregan dependencias, correo ni Celery. La lógica vive en `conciliaciones/services.py`. |

**Post-design re-check**: PASA. El diseño resuelve el reporte regional sin filtrar silenciosamente
datos de otros tenants, añade un estado terminal sin borrar series, no toca el stock general y exige
recálculo si el stock cambió.

## Project Structure

```text
conciliaciones/
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
    └── 0004_serie_instalada.py

templates/
└── conciliaciones/
    ├── listado.html
    ├── cargar.html
    └── detalle.html

tests/
├── unit/
│   ├── test_conciliacion_excel.py
│   ├── test_conciliacion_servicios.py
│   └── test_conciliacion_comparacion.py
├── integration/
│   ├── test_conciliacion_carga.py
│   ├── test_conciliacion_aprobacion.py
│   ├── test_conciliacion_rechazo.py
│   ├── test_conciliacion_recalculo.py
│   ├── test_conciliacion_concurrencia.py
│   └── test_conciliacion_auditoria.py
└── contract/
    └── test_conciliacion_http.py
```

También se modifican:

- `config/settings/base.py`: registrar `conciliaciones` y `CONCILIACIONES_DIR`.
- `config/urls.py`: incluir `conciliaciones.urls`.
- `templates/base.html`: enlace a conciliaciones para `USUARIO_TENANT`.
- `series/models.py` y `series/migrations/`: estado `INSTALADA` y coherencia de custodia.
- `05-especificaciones/010-conciliacion-de-stock/plan.md`: este documento.
- No se crean tareas Celery ni se modifica `StockGeneral`.

## Modelo de datos

### `conciliaciones.Conciliacion`

```python
class Conciliacion(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT,
                               related_name="conciliaciones")
    region = models.ForeignKey("tenants.Region", on_delete=models.PROTECT,
                               related_name="conciliaciones")
    estado = models.CharField(max_length=20, choices=EstadoConciliacion.choices,
                              default=EstadoConciliacion.EN_REVISION)
    archivo_nombre = models.CharField(max_length=255)
    archivo_ruta = models.CharField(max_length=255, blank=True, default="")
    hash_sha256 = models.CharField(max_length=64)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_rechazo = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True, default="")
    huella_stock = models.CharField(max_length=64)
    requiere_revision = models.BooleanField(default=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="conciliaciones_creadas")
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     null=True, blank=True,
                                     related_name="conciliaciones_aprobadas")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                        null=True, blank=True, related_name="+")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                condition=Q(estado="EN_REVISION"),
                name="conciliacion_una_en_revision_por_tenant",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["EN_REVISION", "APROBADA", "RECHAZADA"]),
                name="conciliacion_estado_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "estado"], name="conciliacion_tenant_estado"),
            models.Index(fields=["region", "fecha_carga"], name="conciliacion_region_fecha"),
        ]
```

- Solo una `EN_REVISION` por tenant, impuesta por índice parcial.
- `archivo_ruta` es relativa a `CONCILIACIONES_DIR`/`MEDIA_ROOT`; nunca absoluta.
- `hash_sha256` es el SHA-256 del archivo original.
- `huella_stock` resume el stock y las series de los técnicos afectados; detecta cambios entre la
  carga y la aprobación.
- `requiere_revision` se activa tras un recálculo por cambios.
- `APROBADA` y `RECHAZADA` son terminales.

### `conciliaciones.DiferenciaSerie`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT`; copiado de la conciliación |
| `conciliacion` | FK `Conciliacion` | `CASCADE`; `related_name="diferencias_series"` |
| `tecnico` | FK `Tecnico` | Técnico del tenant según el reporte |
| `material` | FK `Material` | `PROTECT`; material del catálogo |
| `numero` | `CharField(12)` | Serie normalizada; formato `^[A-Z0-9]{12}$` |
| `tipo` | `CharField(24)` | `EN_REPORTE_NO_SISTEMA`, `EN_SISTEMA_NO_REPORTE`, `EN_OTRO_TECNICO` |
| `tecnico_sistema` | FK `Tecnico` | Nulo salvo `EN_OTRO_TECNICO`; técnico actual |
| `lote` | `CharField(50)` | Copia del reporte; informativo |

- `UniqueConstraint(conciliacion, tipo, numero)` para no repetir la misma serie en el mismo grupo.
- Índices `(conciliacion, tipo)` y `(tenant, numero)`.
- `EN_OTRO_TECNICO` no es un grupo nuevo visible: se muestra dentro de “técnicos con
  inconsistencias” y permite reasignar en la aprobación.

### `conciliaciones.DiferenciaCantidad`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `conciliacion` | FK `Conciliacion` | `CASCADE` |
| `tecnico` | FK `Tecnico` | Técnico presente en el reporte |
| `material` | FK `Material` | Material no seriado del catálogo |
| `cantidad_sistema` | `IntegerField` | `>= 0` |
| `cantidad_reporte` | `IntegerField` | `>= 0` |
| `diferencia` | `IntegerField` | `cantidad_reporte - cantidad_sistema` |

- `UniqueConstraint(conciliacion, tecnico, material)`.
- Índice `(conciliacion, tecnico)` y `(tenant, material)`.

### `conciliaciones.MaterialNoCatalogado`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `conciliacion` | FK `Conciliacion` | `CASCADE` |
| `codigo` | `CharField(50)` | Código del reporte |
| `descripcion` | `CharField(255)` | Texto breve del reporte |
| `tecnico_nif` | `CharField(20)` | NIF del reporte, si aplica |
| `filas` | `PositiveIntegerField` | Filas afectadas |

- `UniqueConstraint(conciliacion, codigo)`.
- Bloquea la aprobación hasta que el material se cree en el catálogo y se recalcule.

### `series.Serie` (cambio de estado)

- Se añade `INSTALADA` a `EstadoSerie.choices`.
- `CheckConstraint(serie_estado_valido)` incluye `DISPONIBLE`, `RESERVADA`, `ASIGNADA`,
  `INSTALADA`.
- `INSTALADA` es terminal: `tecnico=None`, `asignada_en=None`; no vuelve al stock disponible.
- La restricción de coherencia de 009 se amplía: `INSTALADA` exige ambos nulos.
- Migración `series/migrations/0004_serie_instalada.py`: actualiza la restricción y no cambia datos.
- 012 usa `INSTALADA` para el conteo de liquidados/instalados.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 010 |
|---|---|---|
| `series.Serie` | 004 | Crear, reasignar y marcar `INSTALADA`; no se elimina. |
| `stock.StockTecnico` | 008 | Leer y ajustar cantidades de técnicos; **nunca** `StockGeneral`. |
| `tecnicos.Tecnico` | 003 | Identificar NIF y tenant; validar región. |
| `materiales.Material` | 002 | Catálogo, lote y tipo seriado. |
| `tenants.Tenant` / `Region` | 001 | Alcance, RLS y parámetros del reporte. |
| `auditoria.RegistroCambio` | 001 | Auditoría compartida. |

## Migraciones

1. `series/migrations/0004_serie_instalada.py`: añade `INSTALADA` a choices/check y amplía la
   coherencia de custodia; no modifica series existentes.
2. `conciliaciones/migrations/0001_initial.py`: `Conciliacion`, `DiferenciaSerie`,
   `DiferenciaCantidad` y `MaterialNoCatalogado` con restricciones e índices.
3. `conciliaciones/migrations/0002_rls.py`: RLS por `tenant_id`/`region_id` en conciliación y por
   `tenant_id` en diferencias y materiales no catalogados; si 001 no está disponible, deuda.
4. No se modifican tablas de stock, asignaciones, recojos ni traspasos.

## Servicios (lógica de negocio)

Viven en `conciliaciones/services.py`; las vistas solo orquestan.

### Excepciones

- `PermisoDenegado`: “No tienes permiso para cargar conciliaciones”.
- `ConciliacionEnRevision`: “Ya hay una conciliación en revisión”.
- `FormatoInvalido`: “El archivo debe ser un Excel .xlsx válido”.
- `HojaGeneralAusente`: “El archivo no contiene la hoja GENERAL”.
- `ColumnasFaltantes`: “Faltan columnas requeridas en la hoja GENERAL”.
- `TecnicosFueraRegion`: “El reporte contiene técnicos que no pertenecen a la región”.
- `TecnicoFormatoInvalido`: “El NIF del técnico no tiene el formato LAXXXX”.
- `MaterialNoExiste`: “El reporte contiene materiales que no existen en el catálogo”.
- `SerieFormatoInvalido`: “La serie no tiene el formato correcto”.
- `SerieDuplicada`: “La serie está duplicada en el reporte”.
- `SerieInstalada`: “La serie está instalada y no puede reasignarse”.
- `SerieFueraTenant`: “La serie no pertenece a este tenant”; no se revela su propietario.
- `EstadoConciliacionInvalido`: “Solo se puede aprobar o rechazar una conciliación en revisión”.
- `AprobacionBloqueada`: “Aprobación bloqueada: hay materiales que no existen en el catálogo”.
- `HuboCambios`: “Hubo cambios, revise de nuevo”.
- `NoEncontrado`: “La conciliación no existe”.
- `ArchivoNoDisponible`: “El archivo no está disponible”.

### Validación de alcance

- `validar_cuenta_tenant(actor, tenant)`: `USUARIO_TENANT`, cuenta activa, tenant activo y
  `actor.tenant_id == tenant.id`.
- `validar_puede_cargar(tenant)`: exige que no exista una conciliación `EN_REVISION`.
- El Administrador de plataforma no carga, aprueba ni rechaza conciliaciones.

### Lectura del Excel

- `leer_reporte(archivo) -> ReporteLeido`:
  - Acepta solo `.xlsx`; rechaza `.xls`, CSV u otros.
  - Abre con `openpyxl` y lee exclusivamente la hoja `GENERAL`.
  - Columnas requeridas: `Material`, `Lote`, `Libre utilización`, `Número de serie`,
    `Nº ident.fis.1`, `Texto breve material`.
  - Normaliza encabezados (espacios, mayúsculas) y valores vacíos.
  - Devuelve filas tipadas y errores de formato; no escribe en base.
- `ReporteLeido`: `filas`, `errores`, `columnas`, `total_filas`.

### Validación del reporte

- `clasificar_tecnicos(tenant, filas) -> ClasificacionTecnicos`:
  - NIF con formato `LAXXXX`; si no, `TecnicoFormatoInvalido`.
  - Técnico del tenant: se procesa.
  - Técnico de otro tenant de la **misma región**: se ignora silenciosamente.
  - Técnico desconocido o de otra región: `TecnicosFueraRegion` y se rechaza el archivo completo.
- `validar_filas(tenant, filas)`:
  - Material existe; si no, se registra en `MaterialNoCatalogado` y se permite la carga.
  - Serie con formato; duplicada en el reporte; material seriado con serie y no seriado sin serie.
  - Técnico presente con material no seriado: cantidad `Libre utilización` entera `>= 0`.
  - Serie instalada en el sistema: `SerieInstalada` (no se reasigna).
  - Serie existente en otro tenant: `SerieFueraTenant`; no se revela el tenant ni se reasigna.
- No se aceptan filas de técnicos de otro tenant en las diferencias ni en la aprobación.

### Comparación

- `construir_estado_sistema(tenant, tecnicos_presentes) -> EstadoSistema`:
  - Series `ASIGNADA` por técnico/material.
  - `StockTecnico` por técnico/material.
- `comparar_series(tenant, tecnicos_presentes, filas) -> list[DiferenciaSerie]`:
  - `EN_REPORTE_NO_SISTEMA`: número no existe en el sistema; se creará.
  - `EN_SISTEMA_NO_REPORTE`: serie `ASIGNADA` de un técnico presente que no aparece en el reporte;
    se marcará `INSTALADA`.
  - `EN_OTRO_TECNICO`: número existe en el sistema, pero con otro técnico; se reasignará.
  - Una serie `INSTALADA` reportada produce `SerieInstalada`.
- `comparar_cantidades(tenant, tecnicos_presentes, filas) -> list[DiferenciaCantidad]`:
  - Solo no seriados.
  - Material ausente para un técnico presente se asume `0`.
  - Técnico ausente no se compara ni se modifica.
- `calcular_huella_stock(tenant, tecnicos_presentes) -> str`:
  - SHA-256 de un JSON canónico y ordenado con técnicos, materiales, cantidades y series.
  - Se guarda al cargar y se recalcula al aprobar.

### Carga

- `crear_conciliacion(tenant, archivo, actor)`:
  1. Valida cuenta y que no haya otra `EN_REVISION`.
  2. Lee y valida el archivo; clasifica técnicos; calcula diferencias y huella.
  3. Guarda el archivo en `CONCILIACIONES_DIR` con nombre relativo seguro y hash SHA-256.
  4. En `transaction.atomic`: crea `Conciliacion` `EN_REVISION`, diferencias, materiales no
     catalogados; audita `Conciliacion/alta` y `Conciliacion/archivo`.
  5. **No** modifica series, `StockTecnico` ni `StockGeneral`.
  6. Devuelve la conciliación.
- `recalcular_diferencias(conciliacion, actor)`:
  - Solo `EN_REVISION`.
  - Relee el archivo guardado, revalida, recalcula diferencias y huella.
  - En una transacción: reemplaza diferencias y materiales no catalogados, actualiza huella y
    `requiere_revision=True`; audita `Conciliacion/recalculo`.
  - No modifica stock.

### Aprobación

- `aprobar_conciliacion(conciliacion, actor)`:
  1. Valida cuenta y `EN_REVISION`.
  2. Si `huella_stock` actual difiere de la guardada: llama a `recalcular_diferencias` en su propia
     transacción y lanza `HuboCambios`; no aplica ningún ajuste. El tenant debe revisar y aprobar de
     nuevo.
  3. Si hay `MaterialNoCatalogado`, lanza `AprobacionBloqueada`.
  4. En `transaction.atomic`:
     - Bloquear `Conciliacion`, `Tenant`, `StockTecnico` de todos los técnicos afectados por
       `(material_id, tecnico_id)` y series por `id`; recalcular la huella dentro del bloqueo y
       abortar si cambió.
     - Revalidar técnicos, materiales, series y cuadre.
     - Series del reporte que no existen: crear con `series.services.crear_serie(...,
       estado=ASIGNADA, tecnico=tecnico, asignada_en=ahora)`; auditar `Serie/alta`.
     - Series existentes en otro técnico: reasignar `tecnico` y reiniciar `asignada_en`; auditar
       `Serie/tecnico` y `Serie/asignada_en`.
     - Series `ASIGNADA` de técnicos presentes no reportadas: `INSTALADA`, limpiar
       `tecnico`/`asignada_en`; auditar `Serie/estado`.
     - No seriados: fijar `StockTecnico` a la cantidad reportada usando incrementos/decrementos de
       008 según la diferencia; si el material no aparece para un técnico presente, la cantidad es
       `0`.
     - Seriados: fijar `StockTecnico` al número de series `ASIGNADA` del técnico/material; usar
       008 para el delta.
     - Cambiar a `APROBADA`, `fecha_aprobacion`, `aprobado_por`, `requiere_revision=False`; auditar
       `Conciliacion/estado`.
  5. **No** toca `StockGeneral`; no elimina series.
  6. Devuelve `ResultadoConciliacion` con conteos y ajustes.

### Rechazo

- `rechazar_conciliacion(conciliacion, actor, motivo="")`:
  - Solo `EN_REVISION`.
  - En `transaction.atomic`: `RECHAZADA`, `fecha_rechazo`, `motivo_rechazo`; audita
    `Conciliacion/estado` y el motivo.
  - No modifica series ni stock.

### Consultas

- `listar_conciliaciones(tenant, estado=None)`.
- `obtener_conciliacion(tenant, conciliacion_id)`.
- `detalle_conciliacion(conciliacion)`: diferencias agrupadas, materiales no catalogados, alertas,
  `requiere_revision`.
- `alertas_conciliacion(conciliacion)`:
  - Material ajeno: `EN_REPORTE_NO_SISTEMA`.
  - Técnicos con inconsistencias: técnicos con más diferencias o `EN_OTRO_TECNICO`.
  - Series faltantes: `EN_SISTEMA_NO_REPORTE`.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/conciliaciones/` | GET | Listado paginado con filtro por estado |
| `/conciliaciones/cargar/` | GET/POST | Formulario y carga del `.xlsx` |
| `/conciliaciones/<id>/` | GET | Detalle, diferencias, alertas y aviso de cambios |
| `/conciliaciones/<id>/recalcular/` | POST | Recalcular diferencias |
| `/conciliaciones/<id>/aprobar/` | POST | Aprobar y aplicar ajustes |
| `/conciliaciones/<id>/rechazar/` | POST | Rechazar con motivo opcional |

- `GET` solo para listado, carga y detalle.
- `POST` para cargar, recalcular, aprobar y rechazar; CSRF obligatorio.
- Un recurso de otro tenant devuelve `404`; un rol incorrecto, `403`; un estado inválido, `409`;
  un archivo inválido, `400`; un cambio de stock, `409` con “Hubo cambios, revise de nuevo”.
- No se acepta `tenant_id`, `region_id` ni estado del cliente.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cuenta del tenant | Servicio | “No tienes permiso para cargar conciliaciones” |
| Una sola en revisión | Servicio e índice parcial | “Ya hay una conciliación en revisión” |
| Archivo `.xlsx` | Servicio | “El archivo debe ser un Excel .xlsx válido” |
| Hoja `GENERAL` y columnas | Servicio | “El archivo no contiene la hoja GENERAL” / “Faltan columnas requeridas” |
| Técnico de otro tenant de la región | Servicio | Se ignora silenciosamente |
| Técnico desconocido o de otra región | Servicio | “El reporte contiene técnicos que no pertenecen a la región” |
| NIF `LAXXXX` | Servicio | “El NIF del técnico no tiene el formato LAXXXX” |
| Material no catalogado | Servicio | Se registra; la aprobación se bloquea con “Aprobación bloqueada…” |
| Serie con formato | Servicio | “La serie no tiene el formato correcto” |
| Serie duplicada | Servicio | “La serie está duplicada en el reporte” |
| Serie `INSTALADA` reportada | Servicio | “La serie está instalada y no puede reasignarse” |
| Serie de otro tenant | Servicio | “La serie no pertenece a este tenant” |
| Solo una aprobación/rechazo | Servicio | “Solo se puede aprobar o rechazar una conciliación en revisión” |
| Cambios entre carga y aprobación | Servicio | “Hubo cambios, revise de nuevo” |
| Todo o nada | Transacción | Si falla, se revierte todo |

## Transacciones y concurrencia

- La carga crea conciliación, diferencias y archivo en una transacción; no toca stock.
- La aprobación es una sola transacción; cualquier fallo revierte series, stock, estado y auditoría.
- Orden de bloqueo: `Conciliacion` → `Tenant` → `StockTecnico` por `(material_id, tecnico_id)` →
  `Serie` por `id`.
- Compatible con 008/009: no se toca `StockGeneral`; el stock se ajusta con los servicios de 008.
- Dos cargas simultáneas: el índice parcial deja una sola `EN_REVISION`; la segunda recibe `409`.
- Dos aprobaciones simultáneas: la segunda espera el bloqueo y detecta el estado `APROBADA` o la
  huella cambiada.
- Si el stock cambia entre carga y aprobación, se recalcula y se exige revisar; no se aplica nada.
- La huella se calcula dentro del bloqueo antes de escribir.

## Auditoría y RLS

- Eventos:
  - `Conciliacion/alta`: tenant, región, archivo, hash, actor.
  - `Conciliacion/archivo`: ruta relativa y hash.
  - `Conciliacion/estado`: `EN_REVISION→APROBADA` o `→RECHAZADA`, con fechas y actor.
  - `Conciliacion/recalculo`: motivo, cambios detectados, actor.
  - `Conciliacion/motivo_rechazo`: motivo, si existe.
  - `Serie/alta`: serie creada desde el reporte.
  - `Serie/estado`: `ASIGNADA→INSTALADA` por serie no reportada.
  - `Serie/tecnico` y `Serie/asignada_en`: reasignación.
  - `StockTecnico/cantidad`: lo escribe 008 al ajustar; no se duplica.
- Cada ajuste registra valor anterior y nuevo (RF-46).
- No se auditan secretos, binarios, rutas absolutas ni datos de otro tenant.
- RLS:
  - `conciliaciones_conciliacion`: `tenant_id` y `region_id`.
  - `conciliaciones_diferenciaserie`, `conciliaciones_diferenciacantidad` y
    `conciliaciones_materialnocatalogado`: `tenant_id`.
  - Si 001 no está disponible, deuda registrada y filtrado ORM.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Pruebas

Un caso por criterio de aceptación, más Excel, servicios, concurrencia, auditoría y aislamiento.

| CA | Prueba principal |
|---|---|
| CA-01 | `test_cargar_reporte_crea_conciliacion_en_revision` |
| CA-02 | `test_solo_una_conciliacion_en_revision` |
| CA-03 | `test_tecnico_ausente_se_ignora` |
| CA-04 | `test_material_ausente_se_asume_0` |
| CA-05 | `test_diferencias_series_se_muestran_dos_grupos` |
| CA-06 | `test_alertas_categorizadas` |
| CA-07 | `test_aprobacion_bloquea_si_material_no_existe` |
| CA-08 | `test_aprobacion_todo_o_nada` |
| CA-09 | `test_ajustes_al_aprobar` |
| CA-10 | `test_auditoria_ajustes` |
| CA-11 | `test_recalculo_si_hubo_cambios` |
| CA-12 | `test_tecnico_fuera_region_rechaza_archivo` |

Además:

- **Excel**: `.xlsx` válido, `.xls` rechazado, hoja `GENERAL` ausente, columnas faltantes, valores
  inválidos, series duplicadas, formato de serie y NIF.
- **Servicios**: clasificación de técnicos, materiales no catalogados, diferencias de series y
  cantidades, alertas, huella estable, recálculo.
- **Aprobación**: crear series, reasignar, marcar `INSTALADA`, fijar fungibles, stock general
  invariante, no eliminar series, no tocar técnicos ausentes salvo reasignaciones puntuales.
- **Concurrencia**: dos cargas, dos aprobaciones, cambio de stock entre carga y aprobación,
  bloqueo sin interbloqueo.
- **Auditoría**: todos los eventos, valores anterior/nuevo, actor, sin secretos ni binarios.
- **Aislamiento**: tenant A no ve conciliaciones de B; filas de otros tenants no se muestran;
  región ajena devuelve `404`.
- **Rendimiento**: reporte de 10 000 filas y 1 000 series en tiempo razonable, sin N+1.

## Correcciones documentales necesarias

| Documento | Corrección |
|---|---|
| `010-conciliacion-de-stock/spec.md` §5.1, §5.3, §5.9, RF-48, CA-12 | Precisar que las filas de otros tenants de la misma región se ignoran; las de técnicos desconocidos o de otra región rechazan el archivo. |
| `010-conciliacion-de-stock/spec.md` HU-18 y §8 | Aceptar solo Excel `.xlsx`; no CSV ni texto tabulado. |
| `04-contratos/excel-conciliacion.md` §2, §5.3, §6 | Solo `.xlsx`; aclarar técnicos de otros tenants de la región vs desconocidos/fuera de región. |
| `004-recojo-de-materiales/data-model.md`, `plan.md` y `tasks.md` | Añadir `INSTALADA` a `EstadoSerie`, choices y check; ampliar la coherencia de custodia. |
| `009-traspaso-entre-tecnicos/data-model.md` | Ampliar `serie_tecnico_coherente_estado` para admitir `INSTALADA` sin custodia. |
| `012-reportes-mensuales/plan.md` | Usar `INSTALADA` en lugar de `INSTALADO` para el conteo de liquidados. |

## Decisiones y riesgos

- **Reporte regional**: las filas de otros tenants se ignoran; rechazar todo el archivo por incluirlas
  haría imposible la carga. Se rechazan técnicos desconocidos o de otra región. Corrige la
  contradicción de la spec.
- **Estado `INSTALADA`**: evita borrar series y permite reportes históricos. Alternativa descartada:
  eliminar la serie, que rompe la trazabilidad.
- **Una lista de diferencias persistida**: permite revisar sin recalcular en cada vista.
  Alternativa descartada: calcular solo al vuelo y no detectar cambios.
- **Huella de stock**: detecta cambios entre carga y aprobación de forma barata. Alternativa
  descartada: comparar todas las filas en cada aprobación.
- **Aprobación con servicios de 008**: mantiene bloqueo y auditoría de stock. Alternativa descartada:
  escribir `StockTecnico` directamente.
- **Sin correo/Celery**: la spec no lo pide; la operación es síncrona.
- **Materiales no catalogados**: se registran al cargar y bloquean la aprobación; no se rechaza la
  carga para permitir corregir el catálogo.
- **Series en otro técnico**: se reasignan al técnico reportado; se muestran como inconsistencia y
  ajustan el stock de ambos técnicos.
- **Riesgo de reportes grandes**: lectura por lotes, índices y pruebas de rendimiento.
- **Riesgo de series instaladas reportadas**: se rechaza la fila; no se resucita una serie liquidada.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| Estado terminal `INSTALADA` | No elimina series ni duplica identidad; agrega el estado de liquidación que 012 ya espera. |
| Tercer tipo `EN_OTRO_TECNICO` | No crea una serie nueva: reasigna la existente y mantiene la unicidad global. |
| Huella de stock | No duplica el stock; solo detecta cambios para exigir revisión. |
| Persistir diferencias | No duplica el stock; es una vista materializada de la comparación, regenerable desde el archivo. |
| Sin correo/Celery | La spec no lo pide; evita duplicar 007 y mantiene la simplicidad. |

## Criterios de salida

- `research.md`, `data-model.md`, `contracts/` y `quickstart.md` creados y coherentes con este plan.
- Plan sin escrituras a `StockGeneral`, sin borrar series, sin correo/Celery y sin permisos Django.
- Correcciones de 010/004/009/012 y del contrato de Excel registradas y aplicadas antes de implementar.
- `tasks.md` derivado de este plan cubre CA-01…CA-12 con al menos una prueba por criterio.
- No se implementa código en esta fase.
