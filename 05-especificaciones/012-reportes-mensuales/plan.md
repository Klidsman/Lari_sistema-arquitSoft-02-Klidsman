# Plan técnico: 012 Reportes Mensuales

**Branch**: `012-reportes-mensuales` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/012-reportes-mensuales/spec.md`

**Input**: Spec en `05-especificaciones/012-reportes-mensuales/spec.md`

## Summary

Implementar los reportes mensuales del sistema: un corte de totales por mes/año y por tenant o global
(solicitados, asignados, liquidados/instalados, devueltos, no justificado y % de merma), y la
exportación a Excel del reporte de auditoría y del reporte de conciliación del mes. El corte se
calcula y se guarda para consulta histórica; las exportaciones se generan a demanda y se descargan sin
persistir archivos. 012 es de solo lectura sobre stock, series, asignaciones y conciliaciones: no
modifica ninguna de esas entidades.

La spec deja tres puntos que este plan resuelve y corrige en los documentos:
1. **Métricas**: “solicitados” y “asignados” no pueden ser el mismo dato. Se definen unidades
   solicitadas en el mes y unidades efectivamente asignadas por confirmación en el mes.
2. **Merma**: si los liquidados/instalados o devueltos del mes superan los asignados, el no justificado
   se acota a 0 para no reportar una merma negativa; se documenta la regla.
3. **Auditoría por tenant**: `RegistroCambio` no tiene `tenant_id`, así que un tenant no puede filtrar
   su auditoría. Se añade `tenant` nullable al registro de auditoría y se puebla desde el servicio.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX; listado, generación, detalle y descargas |
| App nueva | `reportes` |
| Modelo persistido | `CorteMensual` (totales por mes/año y tenant/global) |
| Exportaciones | `openpyxl` a `bytes`; descarga directa, sin archivos persistidos |
| Alcance | Tenant propio o global (Administrador de plataforma) |
| Stock | Solo lectura; 012 no modifica stock, series ni conciliaciones |
| Auditoría | Solo lectura; requiere `RegistroCambio.tenant` para el alcance del tenant |
| Transacciones | Generación/regeneración del corte atómicas; exportaciones de solo lectura |
| Bloqueos | `select_for_update` al regenerar un corte |
| Días/mes | Calendario, zona horaria configurada, rango `[inicio, fin)` |
| Correo/Celery | Fuera de alcance; descarga directa |
| Dependencias nuevas | Ninguna |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL`, `ContextoUsuarioMiddleware`, `Tenant`, `Region`, roles y
  `auditoria.RegistroCambio` con `tenant` nullable.
- **002/003**: `Material` y `Tecnico` con tenant.
- **004**: `Serie` y `EstadoSerie` (`INSTALADA`, `INACTIVA`).
- **005/008**: `StockTecnico`, `StockGeneral` y auditoría de stock.
- **006/007/008**: `SolicitudAsignacion` con `fecha`, `confirmada_en` y `LineaAsignacion` con
  `serie`/`cantidad`.
- **009/010/011**: traspasos, `Conciliacion` con diferencias y `ajustes_aplicados`, y `Devolucion`/
  `LineaDevolucion` con fecha y series.
- **Infraestructura**: PostgreSQL con rol sin `SUPERUSER` ni `BYPASSRLS`.

Si falta cualquiera, la implementación se detiene y se reporta.

### Orden de implementación

1. Correcciones documentales: `RegistroCambio.tenant`, `Conciliacion.ajustes_aplicados` y definición
   de métricas en 012.
2. App `reportes`: `CorteMensual`, migraciones y servicio de cálculo.
3. Generación/regeneración y pantallas.
4. Exportaciones de auditoría y conciliación.
5. 013 consume los reportes sin duplicar cálculos.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | El corte y las exportaciones filtran por tenant de la sesión; el global es solo del Administrador. `RegistroCambio.tenant` permite filtrar auditoría sin deducirla del actor. RLS como respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | El Administrador puede ver el global y cualquier tenant; el tenant solo el suyo. No se acepta `tenant_id` del cliente. |
| III. Invariantes de stock | PASA | 012 es solo lectura; no modifica stock, series ni conciliaciones. Los totales se calculan desde datos ya auditados. |
| IV. Identidad y unicidad de series | PASA | Los conteos usan `Serie` y sus estados; no crean ni duplican series. |
| V. Integridad transaccional | PASA | Generar/regenerar un corte es atómico y único por mes/año/alcance. Las exportaciones son de solo lectura. |
| VI. Auditoría inmutable y trazabilidad | PASA | Se audita el alta y la regeneración del corte; las exportaciones no alteran datos. No se auditan binarios. |
| VII. Autoridad del reporte de Lari | PASA | El reporte de conciliación refleja 010 sin reinterpretar el reporte; el corte usa datos auditados. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA-01…CA-04 tiene prueba. Solo `openpyxl`; sin Celery ni dependencias nuevas. |

**Post-design re-check**: PASA. Se resuelve la ambigüedad de métricas, se evita la merma negativa, se
corrige el índice único global y se añade el `tenant` que faltaba para exportar auditoría por tenant.

## Project Structure

```text
reportes/
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

templates/
└── reportes/
    ├── cortes_listado.html
    ├── corte_formulario.html
    └── corte_detalle.html

tests/
├── unit/
│   ├── test_reportes_servicios.py
│   └── test_reportes_excel.py
├── integration/
│   ├── test_corte_mensual.py
│   ├── test_exportacion_auditoria.py
│   ├── test_exportacion_conciliacion.py
│   ├── test_reportes_auditoria.py
│   └── test_reportes_concurrencia.py
└── contract/
    └── test_reportes_http.py
```

También se modifican:

- `config/settings/base.py`: registrar `reportes` y `REPORTES_ZONA_HORARIA` si se parametriza.
- `config/urls.py`: incluir `reportes.urls`.
- `templates/base.html`: enlace a reportes para los roles autorizados.
- `auditoria/models.py` y migración de 001: `RegistroCambio.tenant` nullable.
- `conciliaciones/models.py` y migración de 010: `Conciliacion.ajustes_aplicados`.
- `05-especificaciones/012-reportes-mensuales/plan.md`: este documento.
- No se crean tareas Celery ni se modifican entidades de stock.

## Modelo de datos

### `reportes.CorteMensual`

```python
class CorteMensual(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT,
                               related_name="cortes_mensuales", null=True, blank=True)
    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField()
    solicitados = models.PositiveIntegerField(default=0)
    asignados = models.PositiveIntegerField(default=0)
    liquidados_instalados = models.PositiveIntegerField(default=0)
    devueltos = models.PositiveIntegerField(default=0)
    no_justificado = models.PositiveIntegerField(default=0)
    porcentaje_merma = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    version = models.PositiveIntegerField(default=1)
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                     related_name="cortes_generados")
    generado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                        null=True, blank=True, related_name="+")
    actualizado_en = models.DateTimeField(auto_now=True)
    regenerado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "anio", "mes"],
                condition=Q(tenant__isnull=False),
                name="corte_tenant_anio_mes_unico",
            ),
            models.UniqueConstraint(
                fields=["anio", "mes"],
                condition=Q(tenant__isnull=True),
                name="corte_global_anio_mes_unico",
            ),
            models.CheckConstraint(
                condition=Q(mes__gte=1) & Q(mes__lte=12),
                name="corte_mes_valido",
            ),
            models.CheckConstraint(
                condition=Q(anio__gte=2000) & Q(anio__lte=2100),
                name="corte_anio_valido",
            ),
            models.CheckConstraint(
                condition=Q(porcentaje_merma__gte=0) & Q(porcentaje_merma__lte=100),
                name="corte_merma_valida",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "anio", "mes"], name="corte_tenant_anio_mes"),
            models.Index(fields=["anio", "mes"], name="corte_anio_mes"),
        ]
```

- `tenant=None` significa corte global; solo el Administrador lo genera y lo ve.
- `anio`/`mes` son calendario; `mes` 1–12.
- `no_justificado` y `porcentaje_merma` se calculan con la regla de `plan.md`.
- `version` aumenta al regenerar; `regenerado_en` guarda la última regeneración.
- No se elimina; el histórico se conserva.

### `auditoria.RegistroCambio` (campo añadido)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `tenant` | FK `tenants.Tenant` | Sí | `PROTECT`, `related_name="registros_cambio"`; nulo para acciones globales de plataforma |

- Índice `(tenant, fecha)`.
- `registrar_cambio` lo puebla desde el actor o, si no tiene tenant, desde un registro de entidades
  auditables que conoce el modelo y su ruta de tenant; si no puede determinarlo, `None`.
- Permite exportar la auditoría de un tenant sin deducirla del usuario.

### `conciliaciones.Conciliacion` (campo añadido)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `ajustes_aplicados` | `PositiveIntegerField` | No | `default=0`; se fija al aprobar con el total de series creadas/reasignadas/instaladas y ajustes de cantidad |

- 012 lo usa para la columna “Ajustes aplicados” del reporte de conciliación.
- Si una conciliación no está aprobada, es `0`.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 012 |
|---|---|---|
| `asignaciones.SolicitudAsignacion` / `LineaAsignacion` | 006/007 | Solicitados y asignados |
| `series.Serie` / `EstadoSerie` | 004/010/011 | Liquidados/instalados; no se modifica |
| `logistica_inversa.Devolucion` / `LineaDevolucion` | 011 | Devueltos |
| `auditoria.RegistroCambio` | 001 | Exportación de auditoría |
| `conciliaciones.Conciliacion` | 010 | Exportación de conciliación |
| `stock.StockTecnico` / `StockGeneral` | 008 | **Solo lectura, no se usan para el corte principal** |
| `tenants.Tenant` / `Region` | 001 | Alcance y RLS |

## Migraciones

1. `auditoria/migrations/000X_registro_cambio_tenant.py`: añade `tenant` nullable e índice
   `(tenant, fecha)`; rellena desde el actor/entidad cuando sea posible y deja `None` para globales.
2. `conciliaciones/migrations/000X_conciliacion_ajustes.py`: añade `ajustes_aplicados`.
3. `reportes/migrations/0001_initial.py`: `CorteMensual` con restricciones e índices.
4. `reportes/migrations/0002_rls.py`: RLS de `CorteMensual` por `tenant_id`; las filas globales se
   reservan al Administrador. Si 001 no está disponible, deuda.
5. No se modifican tablas de stock, series, asignaciones ni conciliaciones más allá de los campos
   indicados.

## Servicios (lógica de negocio)

Viven en `reportes/services.py`; las vistas solo orquestan.

### Excepciones

- `PermisoDenegado`: “No tienes permiso para generar este corte” / “Solo el administrador puede
  generar cortes globales”.
- `CorteExistente`: “Ya existe un corte para este mes/año”.
- `CorteNoExiste`: “El corte no existe”.
- `MesInvalido`: “El mes debe estar entre 1 y 12”.
- `AnioInvalido`: “El año no es válido”.
- `SinDatos`: no es error: los totales pueden ser 0.

### Alcance

- `validar_cuenta_admin(actor)`: `ADMIN_PLATAFORMA`.
- `validar_cuenta_tenant_o_admin(actor, tenant)`:
  - Admin: cualquier tenant o global.
  - `USUARIO_TENANT`: solo su tenant; global prohibido.
- `resolver_alcance(actor, tenant)`:
  - Si `tenant` es `None`, exige Admin y devuelve alcance global.
  - Si hay tenant, exige Admin o cuenta de ese tenant.

### Rango del mes

- `rango_mes(mes, anio) -> (inicio, fin)`:
  - Valida mes 1–12 y año 2000–2100.
  - Usa `timezone.make_aware` con la zona configurada; `fin` es el primer instante del mes siguiente.
  - Todos los filtros de fecha usan `[inicio, fin)`.

### Cálculo del corte

- `calcular_totales(tenant, mes, anio) -> TotalesCorte`:
  - `solicitados`: unidades de `LineaAsignacion` de solicitudes con `fecha` en el mes y estado
    `ENVIADA`, `CONFIRMADA` o `RECHAZADA`; cada serie suma 1 y cada no seriado suma su `cantidad`.
  - `asignados`: unidades de `LineaAsignacion` de solicitudes `CONFIRMADA` con `confirmada_en` en el
    mes; misma regla de unidades.
  - `liquidados_instalados`: series distintas con `RegistroCambio` `entidad="Serie"`,
    `campo="estado"`, `valor_nuevo="INSTALADA"` y `fecha` en el mes; filtro por tenant si aplica.
  - `devueltos`: filas de `LineaDevolucion` de devoluciones con `fecha` en el mes; filtro por tenant.
  - `no_justificado = max(0, asignados - liquidados_instalados - devueltos)`.
  - `porcentaje_merma = 0` si `asignados=0`; si no,
    `round(no_justificado / asignados * 100, 2)`.
- `TotalesCorte`: dataclass con los seis valores.
- Las consultas usan agregaciones y `distinct` para no contar dos veces una serie.

### Generación y regeneración

- `generar_corte(tenant, mes, anio, actor) -> CorteMensual`:
  1. Resolver alcance y validar mes/año.
  2. Rechazar si ya existe el corte (`CorteExistente`).
  3. Calcular totales.
  4. `transaction.atomic`: crear `CorteMensual` con `generado_por=actor`; auditar
     `CorteMensual/alta`.
  5. Devolver el corte.
- `regenerar_corte(corte, actor) -> CorteMensual`:
  1. Resolver alcance sobre `corte.tenant`.
  2. `transaction.atomic`: bloquear el corte con `select_for_update`, recalcular, actualizar campos,
     `version += 1`, `regenerado_en=ahora`, `actualizado_por=actor`; auditar
     `CorteMensual/regenerado` con valores anterior y nuevo.
  3. Devolver el corte.
- No se permite regenerar un corte global desde una cuenta de tenant.

### Exportación de auditoría

- `exportar_auditoria(tenant, mes, anio, actor) -> ArchivoReporte`:
  - Resolver alcance y validar mes/año.
  - Filtrar `RegistroCambio` por `fecha` en el mes y `tenant` (o todos si global).
  - Ordenar por `fecha`, `id`.
  - Generar un `.xlsx` en memoria con columnas: Fecha, Usuario, Entidad, Acción (`campo`),
    Valor anterior, Valor nuevo.
  - `ArchivoReporte`: `nombre`, `contenido` (bytes), `content_type`.
  - No persiste el archivo ni audita su contenido.
- Para el tenant, el filtro es `tenant_id=tenant.id`; nunca por `usuario.tenant` solamente.

### Exportación de conciliación

- `exportar_conciliacion(tenant, mes, anio, actor) -> ArchivoReporte`:
  - Filtrar `Conciliacion` por `fecha_carga` en el mes y tenant (o todos si global).
  - Columnas: Fecha, Estado, Tenant (solo global), Diferencias series, Diferencias cantidades,
    Ajustes aplicados.
  - `diferencias_series` y `diferencias_cantidades` son conteos de las tablas relacionadas.
  - `ajustes_aplicados` es el campo de 010; `0` si no está aprobada.
  - Generar el `.xlsx` en memoria; no persistir.

### Consultas

- `listar_cortes(tenant, anio=None)`:
  - Tenant: solo sus cortes.
  - Admin: globales y, si indica tenant, los de ese tenant.
- `obtener_corte(tenant, corte_id)`:
  - Filtra por alcance; `CorteNoExiste` si es ajeno.
- `detalle_corte(corte)`.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/reportes/cortes/` | GET | Listado de cortes según alcance |
| `/reportes/cortes/generar/` | GET/POST | Formulario y generación |
| `/reportes/cortes/<id>/` | GET | Detalle del corte |
| `/reportes/cortes/<id>/regenerar/` | POST | Regenerar el corte |
| `/reportes/cortes/<id>/exportar/auditoria/` | GET | Descargar auditoría del mes |
| `/reportes/cortes/<id>/exportar/conciliacion/` | GET | Descargar conciliación del mes |

- `GET` para descargas; no hay `POST` de exportación.
- El Administrador puede elegir tenant o global; el tenant no ve el selector global.
- No se acepta `tenant_id` en la URL para cuentas de tenant.
- Un corte ajeno devuelve `404`; un rol incorrecto, `403`; un mes/año inválido, `400`; un duplicado,
  `409`.
- Las descargas usan `Content-Disposition` con un nombre seguro y no exponen rutas.

### Pantallas

- **Listado**: mes/año, tenant (admin), solicitados, asignados, liquidados/instalados, devueltos,
  no justificado y % merma; filtro por año.
- **Generar**: mes, año y tenant/global (solo admin).
- **Detalle**: totales, % merma, versión, fechas y botones Regenerar, Exportar auditoría y Exportar
  conciliación.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Admin para global | Servicio | “Solo el administrador puede generar cortes globales” |
| Tenant solo su alcance | Servicio | “No tienes permiso para generar este corte” |
| Mes 1–12 | Servicio y `CheckConstraint` | “El mes debe estar entre 1 y 12” |
| Año 2000–2100 | Servicio y `CheckConstraint` | “El año no es válido” |
| Un corte por mes/año/alcance | Servicio y restricciones parciales | “Ya existe un corte para este mes/año” |
| Merma 0–100 | Cálculo y `CheckConstraint` | Violación de restricción de base |
| Asignados 0 | Cálculo | Merma 0, sin división por cero |
| No justificado negativo | Cálculo | Se acota a 0 |

## Transacciones y concurrencia

- Generar y regenerar son transacciones atómicas; cualquier fallo revierte el corte y su auditoría.
- Las exportaciones son de solo lectura y no bloquean stock.
- Dos generaciones simultáneas del mismo alcance/mes: las restricciones parciales dejan una sola; la
  segunda recibe `409`.
- Dos regeneraciones simultáneas: `select_for_update` serializa y la segunda ve la versión actualizada.
- El cálculo no usa bloqueos de stock: lee datos ya confirmados/auditados.
- El rango del mes es `[inicio, fin)` para no incluir el primer instante del mes siguiente.

## Auditoría y RLS

- Eventos:
  - `CorteMensual/alta`: alcance (tenant/global), mes, año, totales, actor.
  - `CorteMensual/regenerado`: valores anteriores y nuevos, versión, actor.
- No se auditan los archivos exportados ni su contenido; la exportación no cambia datos.
- RLS de `CorteMensual`:
  - Filas de tenant: por `tenant_id`.
  - Filas globales (`tenant_id IS NULL`): solo visibles para el Administrador.
  - Si la infraestructura de 001 no está disponible, deuda y filtrado ORM.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Pruebas

Un caso por criterio de aceptación, más cálculo, exportaciones, concurrencia y aislamiento.

| CA | Prueba principal |
|---|---|
| CA-01 | `test_corte_mensual_con_totales` |
| CA-02 | `test_calculo_merma_correcto` |
| CA-03 | `test_exportar_auditoria_excel` |
| CA-04 | `test_exportar_conciliacion_excel` |

Además:

- **Cálculo**: mes sin datos (todos 0, merma 0), asignados 0, no justificado negativo acotado a 0,
  series/números no seriados, filtro por tenant y global.
- **Corte**: duplicado por tenant y global, mes/año inválidos, regeneración con versión y auditoría,
  corte ajeno.
- **Auditoría**: exportación con `RegistroCambio.tenant`, sin registros de otro tenant, columnas y
  orden, sin secretos.
- **Conciliación**: conteos de diferencias, `ajustes_aplicados`, estados, filtro por mes/tenant.
- **Concurrencia**: dos generaciones, dos regeneraciones, sin duplicados ni interbloqueo.
- **Aislamiento**: tenant A no ve cortes/exportaciones de B; global solo admin.
- **Rendimiento**: corte de un mes con 10 000 líneas y exportación de 5 000 registros en tiempo
  razonable, sin N+1.

## Correcciones documentales necesarias

| Documento | Corrección |
|---|---|
| `012-reportes-mensuales/spec.md` §5.1, §5.2 y §9 | Definir solicitados/asignados, acotar no justificado a 0 y aclarar que el corte se guarda y las exportaciones se generan a demanda. |
| `012-reportes-mensuales/plan.md` | Este documento reemplaza el plan anterior. |
| `001-tenants-y-acceso/data-model.md` y contrato de auditoría | Añadir `RegistroCambio.tenant` nullable e índice `(tenant, fecha)`; el servicio lo puebla. |
| `010-conciliacion-de-stock/data-model.md` y `plan.md` | Añadir `Conciliacion.ajustes_aplicados` y fijarlo al aprobar. |
| `004-recojo-de-materiales/data-model.md` | Recordar que `INSTALADA` es la fuente de liquidados/instalados; `INACTIVA` es baja y no se suma. |

## Decisiones y riesgos

- **Corte persistido, exportaciones en memoria**: el corte es histórico y auditable; los Excel se
  generan a demanda y no dejan archivos huérfanos. Alternativa descartada: persistir cada Excel.
- **Global con `tenant=None` y restricciones parciales**: evita duplicados globales que un
  `UniqueConstraint(tenant, mes, anio)` no detectaría por los NULL de PostgreSQL.
- **Auditoría con tenant**: sin el campo, el filtro por tenant sería una deducción insegura.
  Alternativa descartada: filtrar por `usuario.tenant`, que falla con acciones del almacén/admin.
- **Métrica de solicitados/asignados**: solicitados = pedidos no borrador; asignados = confirmados en
  el mes. Evita reportar el mismo número dos veces.
- **Merma acotada**: evita porcentajes negativos cuando los eventos del mes superan los asignados;
  se documenta y se prueba.
- **Sin cortes por región**: la spec solo pide tenant/global. Alternativa descartada: agregar región
  sin requisito.
- **Riesgo de consultas lentas**: agregaciones, índices y pruebas de rendimiento.
- **Riesgo de auditoría incompleta**: `RegistroCambio.tenant` debe poblarse en todas las specs;
  se verifica con pruebas y se registra la deuda si falta.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| Añadir `tenant` a `RegistroCambio` | No duplica auditoría; permite el aislamiento y la exportación por tenant. |
| Añadir `ajustes_aplicados` a `Conciliacion` | No cambia la conciliación; guarda un conteo derivado de la aprobación. |
| Restricciones parciales para global | Refuerzan la unicidad sin tablas nuevas. |
| Exportaciones en memoria | No persisten datos ni añaden infraestructura. |
| Sin Celery/correo | La spec no lo pide; la generación es síncrona. |

## Criterios de salida

- `research.md`, `data-model.md`, `contracts/` y `quickstart.md` creados y coherentes con este plan.
- Plan sin escrituras a stock/series/conciliaciones, sin Celery/correo y sin permisos Django.
- Correcciones de 012/001/010 registradas y aplicadas antes de implementar.
- `tasks.md` derivado de este plan cubre CA-01…CA-04 con al menos una prueba por criterio.
- No se implementa código en esta fase.
