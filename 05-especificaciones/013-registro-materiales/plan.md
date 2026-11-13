# Plan técnico: 013 Registro de Materiales

**Branch**: `013-registro-materiales` | **Date**: 2026-11-13 | **Spec**:
`05-especificaciones/013-registro-materiales/spec.md`

**Input**: Spec en `05-especificaciones/013-registro-materiales/spec.md`

## Summary

Mejorar el módulo **013 Registro de Materiales** para que el tenant cargue órdenes de forma masiva,
registre el material usado por orden y controle el saldo mensual:

```text
disponible = saldo inicial + despachos del almacén
saldo final = disponible − material usado en órdenes
```

Los despachos ya existen en `DespachoAlmacen` dentro de 013 y son la única fuente de entradas; no se
registran de nuevo desde la pantalla de materiales. El módulo agrega bloqueo de saldos negativos,
advertencias por cantidades atípicas, panel de pendientes, dashboard, cierre mensual con checklist,
reapertura con motivo y exportación a Excel/CSV.

Es independiente de la conciliación del Excel del almacén y no modifica stock, series, asignaciones,
traspasos ni recojos.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX; carga masiva, materiales, entradas, dashboard, cierre y exportación |
| App | `registro_materiales` (013) |
| Catálogo | `materiales.Material`; habilitación por tenant |
| Despachos | `DespachoAlmacen` existente en 013; solo lectura para el cálculo |
| Stock | **No se lee ni se modifica** |
| Conciliación | **No se lee, genera ni modifica** |
| Saldo | Inicial manual o heredado del cierre anterior |
| Bloqueo | Uso que dejaría saldo negativo se rechaza |
| Advertencia | Cantidad > 3× promedio de últimos 3 meses; configurable |
| Cierre | Checklist, congelamiento, respaldo externo y reapertura |
| Exportación | Excel (`openpyxl`) y CSV (`csv` estándar) |
| Auditoría | `auditoria.RegistroCambio` con `tenant` |
| Dependencias nuevas | Ninguna |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL`, `ContextoUsuarioMiddleware`, `Tenant`, roles y
  `auditoria.RegistroCambio` con `tenant`.
- **002**: `materiales.Material` con `codigo`, `descripcion`, `lote` y `es_seriado`.
- **003**: `tecnicos.Tecnico` con `tenant`, `nif` y `activo`.
- **013 base**: `MaterialHabilitado`, `SaldoInicialPeriodo`, `DespachoAlmacen`,
  `OrdenLiquidacion` y `UsoMaterialOrden` existentes o creados una sola vez en este módulo.
- **Infraestructura**: PostgreSQL con rol sin `SUPERUSER` ni `BYPASSRLS`.

Si falta cualquiera, la implementación se detiene y se reporta.

### Orden de implementación

1. Verificar/crear la base de 013 y `DespachoAlmacen`.
2. Carga masiva de órdenes y panel de pendientes.
3. Registro de materiales con bloqueo de negativos y advertencias.
4. Saldos, dashboard y exportaciones.
5. Cierre mensual y reapertura.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | Todas las tablas llevan `tenant`; las consultas filtran por la sesión; un dato ajeno se trata como inexistente. RLS como respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | Solo `USUARIO_TENANT` opera el módulo; técnicos y materiales se validan contra el tenant. Admin y almacén no operan. |
| III. Invariantes de stock | PASA | 013 no lee ni escribe `StockGeneral`/`StockTecnico`; el saldo es un registro paralelo. |
| IV. Identidad y unicidad de series | PASA | 013 no crea ni modifica series. |
| V. Integridad transaccional | PASA | Carga de órdenes, guardado de uso, saldo y cierre son atómicos; un fallo revierte datos y auditoría. |
| VI. Auditoría inmutable y trazabilidad | PASA | Se auditan órdenes, usos, saldos, catálogo, cierre y reapertura con valor anterior/nuevo. |
| VII. Autoridad del reporte de Lari | PASA | 013 no procesa el reporte de Lari ni conciliaciones. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA tiene prueba; sin dependencias nuevas; lógica en `services.py`. |

**Post-design re-check**: PASA. Se reutiliza `DespachoAlmacen`, no se duplica el registro de
despachos, se bloquea el negativo, se agrega cierre auditable y no se toca stock ni conciliación.

## Project Structure

```text
registro_materiales/
├── __init__.py
├── apps.py
├── models.py
├── services.py
├── carga.py
├── dashboard.py
├── cierre.py
├── exportacion.py
├── forms.py
├── views.py
├── urls.py
├── management/
│   └── commands/
│       └── respaldar_bd.py
└── migrations/
    ├── 0001_initial.py
    ├── 0002_cierre.py
    └── 0003_rls.py

templates/
└── registro_materiales/
    ├── menu.html
    ├── cargar_ordenes.html
    ├── _resumen_carga.html
    ├── pendientes.html
    ├── registrar_materiales.html
    ├── _catalogo_orden.html
    ├── entradas.html
    ├── dashboard.html
    ├── cierre.html
    ├── historial.html
    └── _exportacion.html

tests/
├── unit/
│   ├── test_registro_carga.py
│   ├── test_registro_materiales.py
│   ├── test_registro_saldos.py
│   └── test_registro_exportacion.py
├── integration/
│   ├── test_carga_ordenes.py
│   ├── test_materiales_uso.py
│   ├── test_bloqueo_negativo.py
│   ├── test_dashboard.py
│   ├── test_cierre_mensual.py
│   ├── test_auditoria.py
│   ├── test_concurrencia.py
│   └── test_aislamiento.py
└── contract/
    └── test_registro_http.py
```

También se modifican:

- `config/settings/base.py`: registrar `registro_materiales`, `REGISTRO_FACTOR_ADVERTENCIA=3`,
  `REGISTRO_MESES_PROMEDIO=3` y `REGISTRO_BACKUP_REQUERIDO=True`.
- `registro_materiales/management/commands/respaldar_bd.py`: comando de operaciones que genera el
  respaldo y emite la referencia usada en el cierre.
- `config/urls.py`: incluir `registro_materiales.urls`.
- `templates/base.html`: enlace “Registrar materiales”.
- `03-reglas-de-dominio/registro-materiales.md`: actualizar con el flujo aprobado.
- No se modifican modelos, servicios ni migraciones de otras apps.

## Modelo de datos

### `registro_materiales.MaterialHabilitado`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `material` | FK `Material` | `PROTECT` |
| `activo` | `BooleanField` | `default=True` |
| `orden` | `PositiveIntegerField` | `default=0` |
| `creado_por` / `actualizado_por` | FK `Usuario` | `PROTECT` |
| `creado_en` / `actualizado_en` | `DateTimeField` | automáticos |

- `UniqueConstraint(tenant, material)`.
- Deshabilitar conserva historial y no borra.

### `registro_materiales.SaldoInicialPeriodo`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `material` | FK `Material` | `PROTECT` |
| `periodo` | `CharField(7)` | `YYYY-MM` |
| `cantidad` | `PositiveIntegerField` | `>=0` |
| `creado_por` / `actualizado_por` | FK `Usuario` | `PROTECT` |
| `creado_en` / `actualizado_en` | `DateTimeField` | automáticos |

- `UniqueConstraint(tenant, material, periodo)`.
- Manual prevalece; si no existe, se hereda del cierre anterior.
- El cambio se audita.

### `registro_materiales.DespachoAlmacen` (existente)

| Campo | Uso en 013 |
|---|---|
| `tenant` | Alcance |
| `material` | Material |
| `fecha` | Define el mes |
| `cantidad` | Suma al disponible |

- No se crea una segunda tabla.
- No se registra desde la pantalla de materiales.
- Se lee en modo agregado por `tenant`, `material` y mes.
- Si la tabla ya existe, no se modifica su estructura.
- Si no existe en un entorno nuevo, se crea una sola vez en la migración base de 013.

### `registro_materiales.CargaOrdenes`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `tecnico` | FK `Tecnico` | `PROTECT` |
| `periodo` | `CharField(7)` | Mes seleccionado |
| `hash_texto` | `CharField(64)` | SHA-256 del texto pegado |
| `total_leidas` | `PositiveIntegerField` | — |
| `total_nuevas` | `PositiveIntegerField` | — |
| `total_omitidas` | `PositiveIntegerField` | — |
| `total_otro_tecnico` | `PositiveIntegerField` | — |
| `creado_por` | FK `Usuario` | `PROTECT` |
| `creado_en` | `DateTimeField` | `auto_now_add` |
| `deshecha_en` | `DateTimeField` | Nulo |
| `deshecha_por` | FK `Usuario` | Nulo |
| `motivo_deshacer` | `TextField` | Opcional |

- Permite deshacer solo las órdenes nuevas del lote sin materiales.
- No guarda el texto completo; guarda hash y conteos.

### `registro_materiales.OrdenLiquidacion`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `tecnico` | FK `Tecnico` | `PROTECT` |
| `numero_original` | `CharField(30)` | Texto tal como se ingresó |
| `numero_normalizado` | `CharField(30)` | Mayúsculas, sin espacios |
| `periodo` | `CharField(7)` | Mes de carga; editable al registrar materiales |
| `fecha_instalacion` | `DateField` | Nulo hasta registrar materiales |
| `carga` | FK `CargaOrdenes` | Nulo para alta manual |
| `creado_por` / `actualizado_por` | FK `Usuario` | `PROTECT` |
| `creado_en` / `actualizado_en` | `DateTimeField` | automáticos |

- `UniqueConstraint(tenant, tecnico, periodo, numero_normalizado)`.
- `CheckConstraint(numero_normalizado regex ^[A-Z0-9]{1,30}$)`.
- `CheckConstraint(periodo regex)`.
- El mismo número puede existir para otro técnico o en otro mes.
- La fecha de instalación puede cambiar el periodo; se revalida la clave.
- `pendiente = no tiene usos con cantidad > 0`.

### `registro_materiales.UsoMaterialOrden`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `orden` | FK `OrdenLiquidacion` | `CASCADE` |
| `tecnico` | FK `Tecnico` | Igual a `orden.tecnico` |
| `material` | FK `Material` | Habilitado |
| `cantidad` | `PositiveIntegerField` | `default=0` |
| `creado_por` / `actualizado_por` | FK `Usuario` | `PROTECT` |
| `creado_en` / `actualizado_en` | `DateTimeField` | automáticos |

- `UniqueConstraint(orden, material)`.
- `CheckConstraint(cantidad >= 0)`.
- Una línea existente a 0 se conserva; no se borra.
- El técnico de la línea se valida contra la orden.

### `registro_materiales.AdvertenciaUso`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `uso` | FK `UsoMaterialOrden` | `CASCADE` |
| `tipo` | `CharField(20)` | `CANTIDAD_ATIPICA` |
| `mensaje` | `TextField` | Detalle |
| `resuelta` | `BooleanField` | `default=False` |
| `justificacion` | `TextField` | Opcional |
| `resuelta_por` | FK `Usuario` | Nulo |
| `resuelta_en` | `DateTimeField` | Nulo |
| `creada_en` | `DateTimeField` | `auto_now_add` |

- No bloquea el guardado.
- Bloquea el cierre si no está resuelta o justificada.

### `registro_materiales.CierreMensual`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `periodo` | `CharField(7)` | `YYYY-MM` |
| `estado` | `CharField(20)` | `ABIERTO` / `CERRADO` |
| `version` | `PositiveIntegerField` | `default=1` |
| `cerrado_por` | FK `Usuario` | Nulo |
| `cerrado_en` | `DateTimeField` | Nulo |
| `reabierto_por` | FK `Usuario` | Nulo |
| `reabierto_en` | `DateTimeField` | Nulo |
| `motivo_reapertura` | `TextField` | Opcional |
| `backup_ref` | `CharField(255)` | Referencia del respaldo |
| `backup_en` | `DateTimeField` | Nulo |
| `actualizado_en` | `DateTimeField` | `auto_now` |

- `UniqueConstraint(tenant, periodo)`.
- `CheckConstraint(estado IN ('ABIERTO','CERRADO'))`.
- Un mes sin fila se considera abierto.
- Cerrar exige backup_ref.

### `registro_materiales.SaldoMensualMaterial`

| Campo | Tipo | Regla |
|---|---|---|
| `cierre` | FK `CierreMensual` | `CASCADE` |
| `tenant` | FK `Tenant` | `PROTECT` |
| `material` | FK `Material` | `PROTECT` |
| `saldo_inicial` | `IntegerField` | Puede ser 0 |
| `despachos` | `IntegerField` | `>=0` |
| `usado` | `IntegerField` | `>=0` |
| `saldo_final` | `IntegerField` | Puede ser negativo si hay alerta |

- `UniqueConstraint(cierre, material)`.
- Es la foto congelada del cierre.
- El saldo final de un cierre es el inicial del mes siguiente.

### `registro_materiales.JustificacionCierre`

| Campo | Tipo | Regla |
|---|---|---|
| `cierre` | FK `CierreMensual` | `CASCADE` |
| `tenant` | FK `Tenant` | `PROTECT` |
| `tipo` | `CharField(30)` | `ORDEN_SIN_MATERIALES`, `SALDO_NEGATIVO`, `ADVERTENCIA` |
| `referencia` | `CharField(100)` | ID o número |
| `motivo` | `TextField` | Obligatorio |
| `creado_por` | FK `Usuario` | `PROTECT` |
| `creado_en` | `DateTimeField` | `auto_now_add` |

- Permite cerrar con un pendiente justificado.
- No justifica errores de cálculo; solo pendientes revisados.

### Entidades externas consumidas

| Entidad | Dueña | Uso |
|---|---|---|
| `materiales.Material` | 002 | Catálogo |
| `tecnicos.Tecnico` | 003 | Técnico |
| `tenants.Tenant` | 001 | Alcance |
| `auditoria.RegistroCambio` | 001 | Auditoría |

## Migraciones

1. `registro_materiales/migrations/0001_initial.py`: `MaterialHabilitado`, `SaldoInicialPeriodo`,
   `DespachoAlmacen` (solo si no existe), `CargaOrdenes`, `OrdenLiquidacion`, `UsoMaterialOrden`,
   `AdvertenciaUso`.
2. `registro_materiales/migrations/0002_cierre.py`: `CierreMensual`, `SaldoMensualMaterial`,
   `JustificacionCierre`.
3. `registro_materiales/migrations/0003_rls.py`: RLS por `tenant_id` en todas las tablas.
4. No se modifican migraciones de otras apps.
5. No se cargan datos iniciales por migración.

## Servicios (lógica de negocio)

Viven en `registro_materiales/services.py`, `carga.py`, `dashboard.py`, `cierre.py` y
`exportacion.py`; las vistas solo orquestan.

### Excepciones

- `PermisoDenegado`: “No tienes permiso para registrar materiales”.
- `TecnicoNoExiste`: “El técnico no pertenece a tu tenant”.
- `MaterialNoHabilitado` / `MaterialInactivo`.
- `CantidadInvalida`: “La cantidad debe ser un número entero mayor o igual a 0”.
- `NumeroOrdenInvalido`: número 1–30 alfanumérico.
- `PeriodoInvalido`: “El periodo debe tener el formato AAAA-MM”.
- `SaldoInsuficiente`: “El uso supera el disponible del mes”.
- `PeriodoCerrado`: “El mes está cerrado; solicita reapertura”.
- `CargaNoDeshacible`: “No se puede deshacer: hay órdenes con materiales registrados”.
- `CierreBloqueado`: “El cierre tiene pendientes sin resolver o justificar”.
- `BackupRequerido`: “Debes registrar la referencia del respaldo antes de cerrar”.
- `NoEncontrado`.

### Catálogo habilitado

- `materiales_habilitados(tenant, incluir_inactivos=False)`.
- `habilitar_material(tenant, material, actor)`.
- `deshabilitar_material(tenant, material, actor)`.
- `MaterialHabilitado` se reutiliza si existe; si falta, se crea en la migración base.
- Un material inactivo conserva historial y no se ofrece en nuevas órdenes.

### Carga masiva

- `procesar_lista(texto) -> ListaNormalizada`:
  - `strip`, descartar vacías.
  - Rechazar líneas con espacios internos, tabs, comas o más de un token.
  - Normalizar a mayúsculas para comparar, conservar original.
  - Deduplicar sin distinguir mayúsculas.
- `previsualizar_carga(tenant, tecnico, periodo, texto) -> ResumenCarga`:
  - Compara con órdenes del técnico/mes y con órdenes de otros técnicos.
  - Devuelve leídas, nuevas, omitidas y también-existen-para-otro-técnico.
- `confirmar_carga(tenant, tecnico, periodo, texto, actor) -> CargaOrdenes`:
  - En transacción crea `CargaOrdenes` y las órdenes nuevas.
  - No modifica órdenes existentes.
- `deshacer_carga(carga, actor, motivo="")`:
  - Solo si las órdenes del lote no tienen usos con cantidad > 0.
  - Elimina las órdenes nuevas del lote y audita.
  - Si alguna tiene materiales, `CargaNoDeshacible` con la lista.

### Búsqueda y registro de materiales

- `buscar_orden(tenant, tecnico, periodo, numero)`:
  - Búsqueda exacta sin distinguir mayúsculas sobre `numero_normalizado`.
  - Devuelve orden o `None`.
- `crear_orden_manual(...)` si no existe al registrar materiales.
- `guardar_uso(orden, fecha_instalacion, cantidades, actor)`:
  1. Exigir mes abierto (`CierreMensual` no CERRADO).
  2. Validar fecha, técnico, materiales habilitados y cantidades.
  3. Calcular el periodo de la fecha; si cambia, revalidar la clave.
  4. Calcular `disponible = saldo_inicial + despachos` del periodo por material.
  5. Calcular uso total del periodo por material, excluyendo el uso actual de esta orden, y sumar
     las cantidades nuevas.
  6. Si algún material supera el disponible, `SaldoInsuficiente` con disponible/usado/faltante.
  7. Comparar cada cantidad con el promedio mensual de los últimos 3 meses cerrados del material;
     si supera `REGISTRO_FACTOR_ADVERTENCIA`, crear `AdvertenciaUso`. Sin historial no advierte.
  8. Crear/actualizar usos; conservar líneas a 0; auditar.
  9. Actualizar `fecha_instalacion` y `periodo` de la orden.
- `resolver_advertencia(advertencia, justificacion, actor)`:
  - Exige justificación no vacía.
  - Marca `resuelta`, `justificacion`, `resuelta_por` y `resuelta_en`; audita.
  - No modifica el uso ni el saldo.

### Saldos

- `registrar_saldo_inicial(...)`:
  - Exigir mes abierto.
  - Validar material habilitado y cantidad.
  - Crear/actualizar y auditar.
  - No permitir que el nuevo saldo deje el mes en negativo (si ya hay uso).
- `saldo_inicial_efectivo(tenant, material, periodo)`:
  - Manual si existe.
  - Si no, el `SaldoMensualMaterial` del cierre anterior.
  - Si no hay cierre, el saldo final calculado del mes anterior.
  - Si no hay datos, 0.
- `saldo_final(...)`:
  - `inicial + despachos - usado`; puede ser negativo para alerta, pero el guardado de uso bloquea
    que se genere por uso nuevo.

### Despachos

- `despachos_del_periodo(tenant, periodo)`:
  - Agrega `DespachoAlmacen` por material y mes.
  - Solo lectura.
  - No crea, edita ni borra despachos.
- `validar_periodo_abierto(tenant, periodo)`:
  - Se invoca desde el servicio existente de alta/edición de `DespachoAlmacen`.
  - Si el mes está `CERRADO`, lanza `PeriodoCerrado`.
- Si `DespachoAlmacen` tiene campos adicionales, se ignoran para el cálculo.

### Dashboard

- `dashboard_mensual(tenant, periodo, tecnico=None, material=None, desde=None, hasta=None)`:
  - Materiales habilitados activos más los que tengan datos.
  - Inicial, despachos, usado, final y alerta.
  - Detalle por técnico.
  - Totales de órdenes y técnicos con uso.
  - Sin N+1.
- Si se filtra por técnico, se muestra su uso y el saldo global del material.

### Pendientes

- `ordenes_pendientes(tenant, periodo=None, dias=None)`:
  - Órdenes sin usos con cantidad > 0.
  - Filtro por antigüedad sobre `creado_en` o `fecha_instalacion` si existe.
  - Ordenadas por antigüedad.

### Cierre

- `lista_chequeo(tenant, periodo)`:
  - Órdenes sin materiales.
  - Materiales con saldo final negativo.
  - Advertencias sin resolver; una advertencia con `resuelta=True` o una `JustificacionCierre`
    `ADVERTENCIA` cuenta como resuelta.
- La resolución de advertencias usa `resolver_advertencia` (definido en la sección de materiales).
- `justificar_pendiente(cierre, tipo, referencia, motivo, actor)`:
  - Si el tipo es `ADVERTENCIA`, marca además la advertencia como resuelta.
- `validar_backup_ref(backup_ref)`:
  - No vacío y con formato `backups/<archivo>` o referencia emitida por `respaldar_bd`.
  - Si no es válido, `BackupRequerido`.
- `cerrar_mes(tenant, periodo, backup_ref, actor)`:
  - Exigir checklist resuelto/justificado y ejecutar `validar_backup_ref`.
  - En transacción: crear/actualizar `CierreMensual` `CERRADO`, snapshot por material en
    `SaldoMensualMaterial`, auditoría.
  - No permite cerrar si falta backup.
- `reabrir_mes(cierre, motivo, actor)`:
  - Exigir motivo; estado `ABIERTO`, versión +1, auditoría.
  - Al reabrir, el snapshot anterior queda como histórico; al recerrar se reemplaza con auditoría de
    los valores anteriores.
- `respaldar_bd` (management command fuera de la web): genera el respaldo y emite `backup_ref`.
- Los servicios de uso, saldo y el servicio existente de despacho deben rechazar meses `CERRADO`
  con `PeriodoCerrado`.

### Exportación

- `exportar_reporte_mensual(tenant, periodo, formato) -> ArchivoReporte`:
  - Excel/CSV con inicial, despachos, usado, final y detalle por técnico.
- `exportar_detalle_ordenes(tenant, periodo, formato) -> ArchivoReporte`:
  - Excel/CSV con técnico, orden, fecha, materiales y cantidades.
- `formato` en `xlsx`/`csv`; sin archivos persistidos.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/registro-materiales/` | GET | Menú del módulo |
| `/registro-materiales/ordenes/cargar/` | GET/POST | Carga masiva y confirmación |
| `/registro-materiales/ordenes/cargar/preview/` | POST | Resumen antes de guardar |
| `/registro-materiales/ordenes/cargas/<id>/deshacer/` | POST | Deshacer carga |
| `/registro-materiales/ordenes/pendientes/` | GET | Panel de pendientes |
| `/registro-materiales/catalogo/` | GET/POST | Catálogo habilitado; activar/desactivar |
| `/registro-materiales/materiales/` | GET/POST | Buscar orden y registrar materiales |
| `/registro-materiales/materiales/contexto/` | GET | Fragmento HTMX con orden o catálogo |
| `/registro-materiales/materiales/guardar/` | POST | Guardar uso |
| `/registro-materiales/ordenes/<id>/historial/` | GET | Historial |
| `/registro-materiales/entradas/` | GET | Saldo inicial y despachos del mes |
| `/registro-materiales/saldo-inicial/guardar/` | POST | Saldo inicial |
| `/registro-materiales/dashboard/` | GET | Dashboard mensual |
| `/registro-materiales/cierre/` | GET | Checklist y estado |
| `/registro-materiales/cierre/cerrar/` | POST | Cerrar mes |
| `/registro-materiales/cierre/reabrir/` | POST | Reabrir mes |
| `/registro-materiales/cierre/justificar/` | POST | Justificar pendiente |
| `/registro-materiales/advertencias/<id>/resolver/` | POST | Resolver advertencia |
| `/registro-materiales/exportar/reporte/` | GET | Excel/CSV del reporte |
| `/registro-materiales/exportar/ordenes/` | GET | Excel/CSV de órdenes |

- No hay formulario de despacho en este módulo; los despachos se consultan desde
  `DespachoAlmacen`.
- No hay `GET` para acciones de escritura.
- Un recurso ajeno devuelve `404`; un rol incorrecto `403`; un mes cerrado `409`.

### Pantallas

- **Menú**: Registrar órdenes, Registrar materiales, Catálogo, Pendientes, Entradas, Dashboard,
  Cierre, Exportar.
- **Catálogo**: materiales habilitados con activar/desactivar.
- **Cargar órdenes**: técnico, mes, textarea, resumen, confirmar, deshacer.
- **Registrar materiales**: técnico, mes, búsqueda, fecha, catálogo y cantidades.
- **Pendientes**: órdenes sin materiales, filtro por antigüedad.
- **Entradas**: saldo inicial editable y despachos del mes en solo lectura.
- **Dashboard**: tarjetas, tabla por material, detalle por técnico, filtros y alertas.
- **Cierre**: checklist, justificaciones, respaldo, cerrar/reabrir.
- **Historial**: cambios de orden y usos.

## Validaciones

| Regla | Dónde | Mensaje |
|---|---|---|
| Cantidad entera ≥ 0 | Formulario, servicio y check | “La cantidad debe ser un número entero mayor o igual a 0” |
| Número 1–30 alfanumérico | Servicio y check | “El número de orden es obligatorio y debe tener entre 1 y 30 caracteres alfanuméricos” |
| Periodo `YYYY-MM` | Servicio y check | “El periodo debe tener el formato AAAA-MM” |
| Orden única por técnico/mes/número | Servicio y unique | Si existe, se abre para editar |
| Uso no supera disponible | Servicio | “El uso supera el disponible del mes” |
| Mes abierto | Servicio | “El mes está cerrado; solicita reapertura” |
| Técnico del tenant | Servicio | “El técnico no pertenece a tu tenant” |
| Material habilitado/activo | Servicio | “El material no está habilitado para tu tenant” |
| Cierre con pendientes | Servicio | “El cierre tiene pendientes sin resolver o justificar” |
| Backup requerido | Servicio | “Debes registrar la referencia del respaldo antes de cerrar” |

## Transacciones y concurrencia

- Carga masiva, guardado de uso, saldo, cierre y reapertura son transacciones.
- La restricción única de la orden y el bloqueo de la fila de cierre evitan duplicados y carreras.
- El guardado de uso bloquea `Tenant`, la orden y el `CierreMensual` del periodo.
- Dos cargas simultáneas de la misma lista: la clave única y la comparación de existentes dejan una
  sola orden por técnico/mes/número.
- Dos guardados de uso simultáneos del mismo material: se recalcula el disponible dentro del bloqueo;
  el segundo puede fallar con `SaldoInsuficiente`.
- La auditoría se inserta en la misma transacción.

## Auditoría y RLS

- Eventos:
  - `CargaOrdenes/alta` y `/deshecha`.
  - `OrdenLiquidacion/alta`, `/numero_orden`, `/fecha_instalacion` y `/periodo`.
  - `UsoMaterialOrden/alta` y `/cantidad`.
  - `SaldoInicialPeriodo/alta` y `/cantidad`.
  - `MaterialHabilitado/alta` y `/activo`.
  - `AdvertenciaUso/alta` y `/resuelta`.
  - `CierreMensual/alta`, `/cerrado`, `/reabierto`.
  - `JustificacionCierre/alta`.
- El actor es el usuario de la sesión; `tenant` se toma del actor/entidad.
- No se auditan secretos ni datos de otro tenant.
- RLS por `tenant_id` en todas las tablas; si 001 no está disponible, deuda y filtrado ORM.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Pruebas

Un caso por criterio de aceptación, más cálculos, concurrencia y aislamiento.

| CA | Prueba principal |
|---|---|
| CA-01 | `test_menu_y_aislamiento` |
| CA-02 | `test_catalogo_habilitado_en_orden` |
| CA-03 | `test_normalizacion_lista` |
| CA-04 | `test_carga_idempotente` |
| CA-05 | `test_orden_otro_tecnico_se_crea` |
| CA-06 | `test_resumen_carga` |
| CA-07 | `test_deshacer_carga_sin_materiales` |
| CA-08 | `test_orden_existente_se_abre` |
| CA-09 | `test_cambio_de_mes_revalida` |
| CA-10 | `test_cantidad_cero_no_suma` |
| CA-11 | `test_cantidad_invalida` |
| CA-12 | `test_bloqueo_saldo_negativo` |
| CA-13 | `test_advertencia_cantidad_atipica` |
| CA-14 | `test_saldo_final` |
| CA-15 | `test_herencia_saldo` |
| CA-16 | `test_saldo_manual_prevalece` |
| CA-17 | `test_despachos_desde_despachoalmacen` |
| CA-18 | `test_historial_edicion` |
| CA-19 | `test_ordenes_pendientes` |
| CA-20 | `test_cierre_bloqueado_por_pendientes` |
| CA-21 | `test_cierre_traspasa_saldo` |
| CA-22 | `test_reapertura_con_motivo` |
| CA-23 | `test_exportacion_excel_csv` |

Además:

- Carga con líneas inválidas, duplicadas, vacías y espacios.
- Deshacer con una orden con materiales: bloqueo.
- Orden de otro técnico/mes: resumen y creación.
- Uso que deja saldo 0: permitido; uso que deja negativo: bloqueado.
- Advertencia con y sin historial.
- Cierre sin backup: bloqueado.
- Reapertura y recálculo.
- Exportación de tenant vs datos ajenos.
- RLS e aislamiento.
- Rendimiento: 100 materiales, 1 000 órdenes y 5 000 usos sin N+1.

## Correcciones documentales necesarias

| Documento | Corrección |
|---|---|
| `013-registro-materiales/spec.md` | Reemplazada por el flujo aprobado. |
| `013-registro-materiales/plan.md` | Este documento. |
| `013-registro-materiales/data-model.md` | Actualizado a las tablas y cálculos aprobados. |
| `013-registro-materiales/contracts/` | Actualizados a carga masiva, materiales, dashboard, cierre y exportación. |
| `013-registro-materiales/quickstart.md` | Actualizado a los escenarios aprobados. |
| `013-registro-materiales/tasks.md` | Actualizado a las nuevas tareas. |
| `03-reglas-de-dominio/registro-materiales.md` | Actualizar con carga masiva, bloqueo de negativos, advertencias y cierre. |

## Decisiones y riesgos

- **DespachoAlmacen reutilizado**: no hay doble registro. Alternativa descartada: nueva tabla de
  despachos.
- **Orden por técnico/mes/número**: permite el mismo número para otros técnicos y meses.
- **Carga masiva idempotente**: pegar la lista completa cada día es seguro.
- **Deshacer solo sin materiales**: protege la integridad; se audita.
- **Bloqueo de negativos**: se valida contra el disponible del mes completo, no solo la orden.
- **Advertencia atípica**: 3× promedio de los últimos 3 meses; configurable.
- **Cierre con respaldo externo**: la app no ejecuta `pg_dump`; registra la referencia.
- **Mes cerrado**: cualquier cambio exige reapertura con motivo.
- **Riesgo de promedios sin historial**: no se advierte si no hay datos.
- **Riesgo de cargas grandes**: procesamiento por lotes y pruebas de rendimiento.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| Reutilizar `DespachoAlmacen` | No duplica datos ni funciones; solo lee cantidades existentes. |
| Carga masiva con lote | Permite deshacer sin borrar órdenes con materiales; queda auditado. |
| Cierre con snapshot | No modifica stock ni conciliación; conserva el saldo histórico. |
| Advertencia sin bloqueo | La revisión humana decide; el cierre exige resolver o justificar. |
| Exportación Excel/CSV | Usa `openpyxl` y la librería estándar; no agrega dependencias. |

## Criterios de salida

- Spec, plan, data-model, contracts, quickstart y tasks actualizados al flujo aprobado.
- No se crea una segunda tabla de despachos.
- No se modifica stock, series, asignaciones, traspasos ni conciliaciones.
- Cada CA tiene al menos una prueba.
- No se implementa código en esta fase documental.
