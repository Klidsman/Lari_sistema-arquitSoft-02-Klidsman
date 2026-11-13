# Plan técnico: 008 Confirmación y Actualización de Stock

**Branch**: `008-confirmacion-y-actualizacion-de-stock` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/008-confirmacion-y-actualizacion-de-stock/spec.md`

**Input**: Spec en `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/spec.md`

## Summary

Implementar los modelos y servicios de stock del sistema y la actualización atómica que ocurre
cuando el Responsable de almacén confirma una solicitud de asignación: las series pasan de
`RESERVADA` a `ASIGNADA`, el stock del técnico sube y el stock general del tenant baja, con
auditoría completa. 008 es la única dueña de `StockGeneral`, `StockTecnico`, de sus movimientos y de
la transición de series al confirmar; 007 solo orquesta la confirmación, fija `confirmada_en` y
cambia el estado de la solicitud.

La parte fundacional (`StockGeneral`, `incrementar_stock_general`, `StockTecnico`,
`incrementar_stock_tecnico` y `decrementar_stock_tecnico`) es prerrequisito de 004 y 005. La parte
de confirmación (`actualizar_stock_confirmacion_asignacion`) se implementa después de 006 y 007. El
stock nunca queda negativo: toda resta valida existencia suficiente antes de escribir.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Sin endpoints propios; servicios internos consumidos por 004, 005, 006, 007, 009 y 010 |
| Stock | `stock.StockGeneral` por tenant/material y `stock.StockTecnico` por tenant/técnico/material |
| Series | `series.Serie` de 004; 008 cambia `RESERVADA→ASIGNADA`, fija `tecnico` y `asignada_en` al confirmar |
| Bloqueos | `select_for_update` en orden estable; sin `F()` ciego para decrementos |
| Transacciones | La confirmación completa ocurre en la transacción abierta por 007 |
| Auditoría | `auditoria.RegistroCambio` en la misma transacción |
| Días en mano | Se calculan desde `Serie.asignada_en`, que 008 fija al confirmar; 006 lo usa y respalda en `confirmada_en` solo para datos históricos |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |
| Apps | `stock` (nueva) y consumidores `series`, `tecnicos`, `tenants`, `asignaciones` y `auditoria` |
| Dependencias nuevas | Ninguna |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware`, `tenants.Tenant`,
  `tenants.Region`, roles y `auditoria.RegistroCambio`/`registrar_cambio`.
- **002**: `materiales.Material` con `codigo`, `descripcion`, `lote` y `es_seriado`.
- **003**: `tecnicos.Tecnico` con `tenant`, `nif`, `nombre` y `activo`.
- **004**: `series.Serie` con `estado` y `EstadoSerie` (`DISPONIBLE`, `RESERVADA`, `ASIGNADA`).
- **006**: `asignaciones.SolicitudAsignacion` con `tenant`, `region`, `tecnico`, `estado`,
  `confirmada_en` y `LineaAsignacion` con `material`, `serie` y `cantidad`.
- **007**: `confirmar_solicitud` abre la transacción, valida el rol y llama a
  `stock.services.actualizar_stock_confirmacion_asignacion`; 007 no escribe stock.
- **Infraestructura**: PostgreSQL con un rol de aplicación sin `SUPERUSER` ni `BYPASSRLS`.

Si falta cualquiera de estos prerrequisitos, la implementación se detiene y se reporta.

### Orden de implementación en el proyecto

1. **Fundacional de 008**: `StockGeneral`, `StockTecnico`, `incrementar_stock_general`,
   `incrementar_stock_tecnico`, `decrementar_stock_tecnico` y consultas. Bloquea 004 y 005.
2. **Consumidores**: 004 (recojos) y 005 (stock inicial) usan los servicios fundacionales.
3. **Confirmación**: 006 genera la solicitud y el Excel; 007 confirma; 008 mueve stock y series.
4. **Posteriores**: 009 (traspasos), 010 (conciliación) y 011 (logística inversa) reutilizan los
   servicios de 008.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | `StockGeneral` y `StockTecnico` llevan `tenant_id` y filtran por él; en `StockTecnico` se copia y valida desde `tecnico.tenant`. La confirmación usa `solicitud.tenant` y `solicitud.region`, nunca datos del cliente. El stock de otro tenant no se lee ni se escribe. RLS como respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | El técnico pertenece al tenant de la solicitud; la confirmación no acepta `tenant_id` ni `region_id` externos. El almacén solo confirma solicitudes de su región vía 007. |
| III. Invariantes de stock | PASA | `StockGeneral` y `StockTecnico` tienen `cantidad >= 0`. Toda resta valida existencia suficiente y usa bloqueo; nunca se crea stock con cantidad negativa. El stock general solo baja con asignaciones confirmadas. |
| IV. Identidad y unicidad de series | PASA | Se usa `series.Serie`; la confirmación exige que cada serie esté `RESERVADA`, pertenezca al tenant/material, cambia a `ASIGNADA` y fija `tecnico`/`asignada_en`. No se crea otra tabla ni otro número. |
| V. Integridad transaccional | PASA | La confirmación completa (series + stock técnico + stock general + auditoría) ocurre en la transacción de 007. Cualquier fallo revierte todo; no hay actualizaciones parciales. |
| VI. Auditoría inmutable y trazabilidad | PASA | Se auditan `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en`, `StockGeneral/cantidad` y `StockTecnico/cantidad` con valor anterior y nuevo, actor y fecha. Sin secretos ni contenido binario. |
| VII. Autoridad del reporte de Lari y aprobación humana | PASA | La actualización de stock solo ocurre tras la confirmación humana del almacén; 008 no confirma automáticamente ni procesa el reporte de Lari. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA-01…CA-07 tiene al menos una prueba. No se agregan dependencias ni endpoints; la lógica vive en `stock/services.py`, es testeable sin interfaz y respeta la propiedad de 007 sobre el estado de la solicitud. |

**Post-design re-check**: PASA. El diseño final elimina el error de `cantidad=-1`, valida stock
suficiente, no duplica la escritura de stock en 007, no crea una tabla de reservas y no implementa
una API paralela. `StockGeneral` y `StockTecnico` llevan `tenant_id`; en `StockTecnico` se copia y
valida desde `tecnico.tenant`, por lo que se cumple la restricción constitucional de tenencia
explícita en toda tabla operativa.

## Project Structure

```text
stock/
├── __init__.py
├── apps.py
├── models.py
├── services.py
├── migrations/
│   ├── 0001_initial.py
│   └── 0002_rls.py

tests/
├── unit/
│   ├── test_stock_servicios.py
│   └── test_stock_validaciones.py
├── integration/
│   ├── test_stock_incrementos.py
│   ├── test_stock_decrementos.py
│   ├── test_stock_confirmacion.py
│   ├── test_stock_concurrencia.py
│   └── test_stock_auditoria.py
└── contract/
    ├── test_stock_servicios_contrato.py
    └── test_stock_confirmacion_contrato.py
```

También se modifican:

- `config/settings/base.py`: registrar `stock` en `INSTALLED_APPS`.
- `asignaciones/services.py` (007): llamar a
  `stock.services.actualizar_stock_confirmacion_asignacion` dentro de la transacción de
  confirmación; 007 no escribe stock.
- `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/plan.md`: este documento.
- No se crean vistas, plantillas, rutas ni tareas Celery.

## Modelo de datos

### `stock.StockGeneral`

```python
class StockGeneral(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="stock_general",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="stock_general",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "material"],
                name="stock_general_tenant_material_unico",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="stock_general_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "material"], name="stock_general_tenant_material"),
        ]
```

- Una fila por tenant y material; el lote no forma parte de la clave.
- `cantidad` es la suma de series `DISPONIBLE` y cantidades no seriadas del tenant.
- `cantidad >= 0` es una restricción de base y una validación de servicio.
- No se elimina: se ajusta con un movimiento auditado.

### `stock.StockTecnico`

```python
class StockTecnico(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="stock_tecnico",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tecnico", "material"],
                name="stock_tecnico_tecnico_material_unico",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="stock_tecnico_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "material"], name="stock_tecnico_tenant_material"),
            models.Index(fields=["tecnico", "material"], name="stock_tecnico_tecnico_material"),
        ]
```

- Una fila por técnico y material; `tenant` se copia siempre de `tecnico.tenant` y se valida en el
  servicio. La clave única sigue siendo `(tecnico, material)` porque un técnico pertenece a un solo
  tenant.
- `tenant` es obligatorio por la constitución («toda tabla operativa lleva `tenant_id`») y permite
  filtrar y aplicar RLS directamente, sin subconsultas a `tecnicos`.
- Representa la custodia actual del técnico.
- No se elimina: se ajusta con un movimiento auditado.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 008 |
|---|---|---|
| `series.Serie` | 004 | `RESERVADA→ASIGNADA` al confirmar; fija `tecnico` y `asignada_en`; validación de pertenencia y estado. |
| `asignaciones.SolicitudAsignacion` / `LineaAsignacion` | 006 | Origen de líneas, tenant, técnico y `estado`. 008 no cambia el estado de la solicitud. |
| `tecnicos.Tecnico` | 003 | Destinatario del stock; validación de tenant. |
| `materiales.Material` | 002 | Clave del stock y tipo seriado/no seriado. |
| `tenants.Tenant` / `Region` | 001 | Alcance y bloqueo; la región no se escribe en stock. |
| `auditoria.RegistroCambio` | 001 | Auditoría compartida. |

## Migraciones

- `stock/migrations/0001_initial.py`: `StockGeneral` y `StockTecnico` con restricciones e índices.
  No crea stock ni series por migración.
- `stock/migrations/0002_rls.py`: política RLS de `stock_general` y `stock_tecnico` por
  `tenant_id`, si la infraestructura de 001 está disponible. Si no, se registra la deuda en
  `research.md`.
- No se modifican tablas de series, asignaciones, recojos, traspasos ni conciliaciones.

## Servicios (lógica de negocio)

Viven en `stock/services.py`; no hay vistas ni endpoints propios. Las apps consumidoras validan sus
permisos y llaman a estos servicios dentro de su propia transacción.

### Excepciones

- `StockInsuficiente`: no hay cantidad suficiente; `409` cuando la propaga 007.
- `CantidadInvalida`: cantidad no entera, cero o negativa; `400`.
- `StockNoExiste`: stock o material inexistente; `404`/`400` según el consumidor.
- `TecnicoNoExiste`: técnico inexistente o de otro tenant; `400`.
- `SerieNoReservada`: la serie no está `RESERVADA`, no pertenece al tenant/material o ya fue
  asignada; `409`.
- `ConfirmacionStockInvalida`: la solicitud no es `ENVIADA`, no tiene líneas o está incompleta;
  `409`.
- `TenantNoCoincide`: el técnico o el material no pertenecen al tenant de la solicitud; `403`.

Mensajes exactos: “La cantidad debe ser mayor a 0”, “El tenant no tiene suficiente stock general”,
“El técnico no tiene suficiente stock”, “La serie no está reservada para esta asignación” y
“No se puede confirmar el stock de la asignación”.

### Servicios fundacionales

- `obtener_stock_general(tenant, material)`:
  - Devuelve la fila o `0` si no existe; nunca crea por lectura.
- `obtener_stock_tecnico(tecnico, material)`:
  - Devuelve la fila o `0` si no existe.
- `calcular_reservado(tenant, material)`:
  - Suma solo líneas no seriadas de solicitudes `ENVIADA`; las seriadas se reservan por estado de
    `Serie`, no por cantidad.
- `calcular_disponible(tenant, material)`:
  - `max(0, StockGeneral - Reservado)`; material sin stock general devuelve `0`.
- `incrementar_stock_general(tenant, material, cantidad, actor)`:
  - Exige entero `> 0`; en `transaction.atomic` bloquea la fila con `select_for_update` o la crea
    dentro de un bloqueo del `Tenant`; suma y audita `StockGeneral/cantidad`.
- `decrementar_stock_general(tenant, material, cantidad, actor)`:
  - Exige entero `> 0`; bloquea la fila, valida `cantidad_disponible >= cantidad`, resta y audita.
  - Si no existe o no alcanza, lanza `StockInsuficiente`; **nunca** crea con cantidad negativa.
- `incrementar_stock_tecnico(tecnico, material, cantidad, actor)`:
  - Exige entero `> 0`; bloquea/crea la fila; valida que el técnico exista; suma y audita.
- `decrementar_stock_tecnico(tecnico, material, cantidad, actor)`:
  - Exige entero `> 0`; bloquea, valida suficiente, resta y audita; nunca deja negativo.
- Todos los servicios fundacionales son idempotentes respecto de su propia transacción y no
  aceptan cantidades negativas como forma de decremento.

### Confirmación de asignación

- `actualizar_stock_confirmacion_asignacion(solicitud, actor)`:
  - Debe invocarse dentro de la transacción de 007; si se llama fuera, abre su propio
    `transaction.atomic` y exige que la solicitud siga `ENVIADA`.
  - Valida:
    - La solicitud está `ENVIADA` y tiene al menos una línea.
    - El técnico pertenece al tenant de la solicitud.
    - Cada línea seriada tiene `serie.estado == RESERVADA` y pertenece al tenant/material.
    - Cada línea no seriada tiene `cantidad > 0`.
    - El stock general alcanza la cantidad agregada por material (series + no seriados).
  - Bloquea en orden estable: `Tenant` → `StockGeneral` por `material_id` → `StockTecnico` del
    mismo tenant por `material_id` → `Serie` por `id`. No bloquea la solicitud: la bloquea 007 antes
    de llamar.
  - Agrega por material:
    - Seriados: `cantidad += 1` por serie.
    - No seriados: `cantidad += cantidad` de la línea.
  - Aplica:
    - Cada serie: `RESERVADA→ASIGNADA`, `tecnico=solicitud.tecnico`, `asignada_en=ahora`.
    - `StockTecnico`: incrementa la cantidad agregada; crea si no existe con
      `tenant = solicitud.tenant`.
    - `StockGeneral`: decrementa la cantidad agregada; si no alcanza, `StockInsuficiente` y revierte.
  - Audita:
    - `Serie/estado`, `Serie/tecnico` y `Serie/asignada_en` por cada serie.
    - `StockTecnico/cantidad` por cada material agregado, con valor anterior y nuevo.
    - `StockGeneral/cantidad` por cada material agregado, con valor anterior y nuevo.
  - No cambia `SolicitudAsignacion.estado` ni `confirmada_en`: eso lo hace 007.
  - No escribe `StockTecnico` por línea individual ni una fila de stock por serie; agrega por
    material para rendimiento y auditoría legible.
  - Devuelve `ResultadoConfirmacionStock` con solicitud, series actualizadas, cambios por material
    y `confirmada_en` de la solicitud (solo lectura).

### Días en mano

- 008 **no** crea un contador ni una tabla de días en mano.
- 007 fija `SolicitudAsignacion.confirmada_en` en la misma transacción.
- 008 fija `Serie.asignada_en = ahora` y `Serie.tecnico = solicitud.tecnico` al confirmar; es la fuente
  del conteo actual de cada serie.
- 006 calcula los días a demanda desde `Serie.asignada_en`, con respaldo en `confirmada_en` solo para
  datos históricos sin custodia.
- `ResultadoConfirmacionStock` expone `confirmada_en` para verificar que quedó fijado; no lo escribe
  ni lo modifica.

## Permisos y alcance

- Los servicios de 008 son internos y no tienen permisos propios; el consumidor valida rol y
  alcance antes de llamarlos.
- 007 valida `RESPONSABLE_ALMACEN` y la región de la solicitud.
- 004 valida la cuenta del tenant y su región; 005 valida el Administrador.
- Todo servicio vuelve a validar que el técnico y el material pertenezcan al tenant de la solicitud
  o del actor; nunca acepta `tenant_id` del cliente.
- El Administrador de plataforma no confirma ni opera stock.
- Los servicios no exponen datos de otro tenant ni mensajes que revelen su existencia.

## Interfaz e integración

008 no expone endpoints. Los contratos son internos y viven en `contracts/`.

| Consumidor | Servicio | Cuándo |
|---|---|---|
| 004 Recojos | `incrementar_stock_general` | Al registrar un recojo |
| 005 Stock inicial | `incrementar_stock_tecnico` / `decrementar_stock_tecnico` | Al cargar, editar o eliminar líneas |
| 006 Asignaciones | `obtener_stock_general` / `calcular_disponible` | Al validar disponibilidad |
| 007 Confirmación | `actualizar_stock_confirmacion_asignacion` | Dentro de `confirmar_solicitud` |
| 009 Traspasos | `incrementar_stock_tecnico` / `decrementar_stock_tecnico` | Al mover stock entre técnicos |
| 010 Conciliación | `calcular_disponible` y ajustes | Al aprobar una conciliación |
| 011 Logística inversa | `incrementar_stock_general` / `decrementar_stock_tecnico` | Al devolver material |

### Secuencia de confirmación

```text
007.confirmar_solicitud(solicitud, actor)
├── valida rol, región y estado ENVIADA
├── transaction.atomic
│   ├── select_for_update(SolicitudAsignacion)
│   ├── 008.actualizar_stock_confirmacion_asignacion(solicitud, actor)
│   │   ├── valida técnico, series RESERVADA y stock suficiente
│   │   ├── bloquea Tenant → StockGeneral → StockTecnico → Serie
│   │   ├── series RESERVADA → ASIGNADA (con tecnico y asignada_en)
│   │   ├── StockTecnico += cantidad agregada
│   │   ├── StockGeneral -= cantidad agregada
│   │   └── audita Serie/estado, Serie/tecnico, Serie/asignada_en, StockTecnico/cantidad y StockGeneral/cantidad
│   ├── solicitud.estado = CONFIRMADA
│   ├── solicitud.confirmada_en = ahora
│   └── audita SolicitudAsignacion/estado
└── publica evento y notifica al tenant después del commit
```

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cantidad entera > 0 | Servicio | “La cantidad debe ser mayor a 0” |
| Stock general suficiente | Servicio y `CheckConstraint` | “El tenant no tiene suficiente stock general” |
| Stock técnico suficiente | Servicio y `CheckConstraint` | “El técnico no tiene suficiente stock” |
| Cantidad no negativa | `CheckConstraint` | Violación de restricción de base |
| Serie `RESERVADA` y del tenant/material | Servicio | “La serie no está reservada para esta asignación” |
| Técnico del tenant de la solicitud | Servicio | “El técnico no pertenece a este tenant” |
| Solicitud `ENVIADA` y con líneas | Servicio | “No se puede confirmar el stock de la asignación” |
| Unicidad tenant/material y técnico/material | `UniqueConstraint` | Violación de restricción de base |

## Transacciones y concurrencia

- La confirmación es una sola transacción iniciada por 007. 008 no confirma ni hace commit por su
  cuenta.
- Orden de bloqueo: `SolicitudAsignacion` (007) → `Tenant` → `StockGeneral` por `material_id` →
  `StockTecnico` del mismo tenant por `material_id` → `Serie` por `id`.
- El orden es estable y ascendente para evitar interbloqueos entre 006 (envío), 007 (confirmación),
  004 (recojo) y 009 (traspaso).
- Un decremento nunca usa `F()` ciego: bloquea, valida y luego resta. Así se evita que dos
  confirmaciones dejen el stock negativo.
- Si dos confirmaciones compiten por el mismo stock, la segunda espera el bloqueo; si ya no alcanza,
  `StockInsuficiente` y toda la transacción se revierte.
- Si una serie ya no está `RESERVADA`, se revierte la confirmación completa; no se acepta una
  confirmación parcial.
- Los servicios fundacionales usan `select_for_update` sobre la fila de stock; si la fila no existe,
  se crea dentro de un bloqueo del `Tenant` para evitar duplicados por concurrencia.
- La restricción `cantidad >= 0` es la última defensa: si una lógica intentara dejar negativo, la
  base rechaza y la transacción se revierte.

## Auditoría y RLS

- Auditoría transaccional con `auditoria.services.registrar_cambio`:
  - `Serie/estado`: `RESERVADA→ASIGNADA` por serie.
  - `Serie/tecnico`: técnico anterior y nuevo por serie.
  - `Serie/asignada_en`: fecha anterior y nueva por serie.
  - `StockTecnico/cantidad`: valor anterior y nuevo por material.
  - `StockGeneral/cantidad`: valor anterior y nuevo por material.
- El actor es el usuario de la sesión que confirma (007); no se inventa un usuario del sistema.
- 008 no audita el estado de la solicitud; lo hace 007.
- 004 y 005 auditan sus propias entidades y los cambios de stock que provocan.
- Nunca se auditan secretos, tokens, contraseñas ni contenido binario.
- RLS:
  - `stock_general`: política por `tenant_id`.
  - `stock_tecnico`: política por `tenant_id`, copiado y validado desde `tecnico.tenant`.
  - Si la infraestructura de 001 no está disponible, se registra la deuda y el ORM filtra por
    `tenant_id` y `tecnico`.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Pruebas

Un caso por criterio de aceptación, más pruebas de servicios, concurrencia y auditoría.

| CA | Prueba principal |
|---|---|
| CA-01 | `test_series_pasan_a_asignada_al_confirmar` |
| CA-02 | `test_stock_tecnico_sube_con_series_y_no_seriados` |
| CA-03 | `test_stock_general_baja_con_series_y_no_seriados` |
| CA-04 | `test_confirmacion_fallida_revierte_todo` |
| CA-05 | `test_dias_en_mano_inician_en_serie_asignada_en` |
| CA-06 | `test_auditoria_completa_de_series_y_stock` |
| CA-07 | `test_no_seriados_actualizan_cantidad_agregada` |

Además:

- **Servicios**: incrementar/decrementar stock general y técnico, creación si no existe, validación
  de suficiente, cantidad cero/negativa, material/técnico inexistente y mensajes exactos.
- **Contrato interno**: firmas, tipos de retorno, excepciones y transaccionalidad de cada servicio.
- **Concurrencia**: dos confirmaciones simultáneas dejan un solo movimiento; dos decrementos no
  dejan stock negativo; orden de bloqueo sin interbloqueo; series duplicadas rechazadas.
- **Auditoría**: una entrada por serie y por material agregado; valores anterior/nuevo correctos;
  sin secretos; la auditoría de la solicitud la escribe 007 y no se duplica.
- **Rendimiento**: confirmación de 100 series en menos de 2 segundos y sin una consulta por línea.
- **Base de datos**: insertar cantidad negativa falla; duplicar `(tenant, material)` o
  `(tecnico, material)` falla.
- **Integración con 007**: 007 llama al servicio dentro de su transacción; si 008 falla, la
  solicitud sigue `ENVIADA`; si 007 falla después, el stock se revierte.

## Decisiones y riesgos

- **008 es dueña única del stock y de `RESERVADA→ASIGNADA`**: evita que 007 duplique escrituras y
  mantiene una sola fuente de verdad. 007 solo fija `confirmada_en` y el estado de la solicitud.
- **Sin cantidades negativas**: se elimina el `cantidad=-1` del plan anterior; toda resta valida
  stock suficiente y la base impone `>= 0`. Alternativa descartada: crear con negativo y corregir
  después, que rompe los invariantes y oculta errores.
- **Bloqueo y validación, no `F()` ciego**: un decremento debe leer el valor bajo bloqueo para
  decidir si alcanza. `F()` acelera pero no evita el negativo sin una condición adicional.
- **Agregación por material**: reduce consultas y produce una auditoría legible; el detalle por
  serie queda en `Serie/estado`. Alternativa descartada: una fila de stock por serie, que
  duplicaría el inventario.
- **Días en mano desde la custodia**: `Serie.asignada_en` se fija al confirmar y 006 calcula a demanda;
  `confirmada_en` solo respalda datos históricos. Alternativa descartada: un contador en 008 que se
  desincroniza o seguir usando `confirmada_en`, que no se reinicia con los traspasos de 009.
- **Sin endpoints**: 008 es un módulo de servicios consumido por 004–011. Alternativa descartada:
  una API de stock que nadie pidió y que ampliaría la superficie de permisos.
- **Fundacional antes de 004/005**: el orden evita que cada spec cree su propio stock. Ya está
  reflejado en `06-plan-implementacion/desglose-tareas.md`.
- **Riesgo de deadlock**: se mitiga con el orden estable de bloqueo y pruebas de concurrencia.
- **Riesgo de stock insuficiente al confirmar**: se detecta antes de escribir y se revierte la
  confirmación; el almacén ve el error y la solicitud sigue `ENVIADA`.
- **Riesgo de RLS no disponible**: se registra la deuda; el filtrado por tenant en el ORM sigue
  siendo obligatorio.

## Correcciones documentales aplicadas

1. `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/plan.md`: se eliminó
   `cantidad=-1`; ahora se valida stock suficiente y se usa `decrementar_stock_general`/
   `decrementar_stock_tecnico` sin cantidades negativas.
2. Se dejó explícito que 008 es dueña de `RESERVADA→ASIGNADA`, de `StockGeneral`/`StockTecnico` y de
   su auditoría; 007 solo fija `confirmada_en` y el estado de la solicitud.
3. Se alineó la parte fundacional con 004 y 005: `StockGeneral`/`incrementar_stock_general` antes de
   004; `StockTecnico`/incrementos/decrementos antes de 005.
4. Se retiró la afirmación de «no se usan bloqueos»; ahora se usa `select_for_update` en orden
   estable y se prueba concurrencia.
5. Se agregó `tenant` a `StockTecnico`, copiado y validado desde `tecnico.tenant`, para cumplir la
   restricción constitucional de que toda tabla operativa lleva `tenant_id` y permitir RLS directa.
6. Se alineó con 009: al confirmar, 008 fija `Serie.tecnico` y `Serie.asignada_en`, los audita y los
   expone en el resultado; 006 calcula los días en mano desde `Serie.asignada_en`.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| Servicios internos sin endpoints | La spec 008 no pide interfaz; los consumidores validan permisos y 008 mantiene la lógica en `services.py`. |
| `StockTecnico` con `tenant` copiado de `tecnico.tenant` | Cumple la restricción constitucional de que toda tabla operativa lleva `tenant_id`, permite RLS directa y se mantiene coherente con 005. El servicio valida la coincidencia; no es una segunda fuente de verdad porque nunca se acepta del cliente. |
| Agregación por material en la confirmación | No crea stock paralelo: sigue usando una fila por tenant/material y una por técnico/material; solo agrupa escrituras y auditoría. |

## Criterios de salida

- `research.md`, `data-model.md`, `contracts/` y `quickstart.md` creados y coherentes con este plan.
- Plan sin `cantidad=-1`, sin `F()` ciego y sin afirmar que no se usan bloqueos.
- `tasks.md` derivado de este plan cubre CA-01…CA-07 con al menos una prueba por criterio.
- No se implementa código en esta fase.
