# Investigación y decisiones: 008 Confirmación y Actualización de Stock

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/008-confirmacion-y-actualizacion-de-stock/spec.md`

Este documento resuelve las incógnitas técnicas del plan y fija las decisiones que no deben quedar a
criterio de la implementación. No hay `NEEDS CLARIFICATION` pendientes.

## Contexto de dependencias

| Dependencia | Estado esperado | Uso en 008 |
|---|---|---|
| 001 — acceso, tenants y auditoría | Implementada | Roles, middleware, tenant, región y `RegistroCambio` |
| 002 — materiales | Implementada | `Material.codigo`, `es_seriado`, `lote` |
| 003 — técnicos | Implementada | `Tecnico.tenant`, `nif`, `activo` |
| 004 — series | Implementada | `Serie.estado`, `DISPONIBLE`, `RESERVADA`, `ASIGNADA` |
| 006 — solicitudes de asignación | Implementada | `SolicitudAsignacion`, `LineaAsignacion`, `estado`, `confirmada_en` |
| 007 — confirmación del almacén | Implementada | `confirmar_solicitud` llama a 008 dentro de su transacción |
| 004 y 005 | Consumidoras | Usan los servicios fundacionales de 008 |
| PostgreSQL 16+ | Infraestructura | Restricciones, bloqueos, transacciones y RLS |

## Decisiones

### D-01. Propiedad única del stock y de la transición de series

- **Decisión**: 008 es dueña de `StockGeneral`, `StockTecnico`, de sus movimientos y de la
  transición `RESERVADA→ASIGNADA`. 007 solo abre la transacción, valida el rol y la región, fija
  `SolicitudAsignacion.estado="CONFIRMADA"` y `confirmada_en`; no escribe stock ni series.
- **Justificación**: evita dos escritores del mismo dato y cumple la separación de la spec 007. La
  auditoría de cada cambio queda en su dueño.
- **Alternativas descartadas**: que 007 actualice stock y series (duplica lógica y auditoría); que
  008 cambie el estado de la solicitud (rompe la propiedad de 006/007).

### D-02. Sin cantidades negativas

- **Decisión**: `StockGeneral.cantidad` y `StockTecnico.cantidad` tienen `CheckConstraint >= 0`. Los
  decrementos validan existencia suficiente antes de restar y lanzan `StockInsuficiente`. Nunca se
  crea una fila con `cantidad=-1` ni se usa un negativo como señal.
- **Justificación**: el principio III exige invariantes de stock. Crear con negativo y corregir
  después rompe el invariante y oculta errores de concurrencia.
- **Alternativas descartadas**: `cantidad=-1` al decrementar (el plan anterior lo hacía y es
  incorrecto); permitir negativos temporales y conciliar (viola el principio III).

### D-03. Bloqueo y validación, no `F()` ciego

- **Decisión**: cada decremento bloquea la fila con `select_for_update`, lee la cantidad, valida que
  alcance y recién entonces resta. No se usa `F()` ciego para decrementos.
- **Justificación**: `F()` evita lecturas obsoletas, pero sin una condición adicional puede dejar el
  stock negativo o requerir una excepción de base poco legible. El bloqueo permite devolver un
  mensaje de negocio claro y mantener la transacción corta.
- **Alternativas descartadas**: `F()` con `filter(cantidad__gte=...)` (posible, pero menos legible y
  no informa qué material falló); bloqueo optimista con versión (más complejo sin necesidad).

### D-04. Orden estable de bloqueo

- **Decisión**: el orden es `SolicitudAsignacion` (007) → `Tenant` → `StockGeneral` por
  `material_id` ascendente → `StockTecnico` por `material_id` ascendente → `Serie` por `id`
  ascendente.
- **Justificación**: 006 bloquea `Tenant` → `StockGeneral` → `Serie`; 007 bloquea la solicitud y
  luego llama a 008. Con el mismo orden base se evitan ciclos entre envío, confirmación, recojo y
  traspaso.
- **Alternativas descartadas**: bloquear series antes que stock (puede ciclar con 006); no bloquear
  y confiar en la restricción (falla con error de base y poca trazabilidad).

### D-05. Agregación por material

- **Decisión**: la confirmación agrupa las líneas por material y escribe una sola vez
  `StockTecnico` y `StockGeneral` por material, sumando series (1 cada una) y cantidades no
  seriadas.
- **Justificación**: evita una consulta y una escritura por línea, mantiene una fila por
  tenant/material y una auditoría legible. El detalle por serie queda en `Serie/estado`.
- **Alternativas descartadas**: una fila de stock por serie (duplica el inventario); una escritura
  por línea (más lenta y con auditoría redundante).

### D-06. Auditoría por serie y por material

- **Decisión**: se audita `Serie/estado` por cada serie (`RESERVADA→ASIGNADA`) y
  `StockTecnico/cantidad`/`StockGeneral/cantidad` una vez por material agregado, con valor anterior
  y nuevo.
- **Justificación**: CA-06 exige los tres tipos de registro; agregar por material evita duplicar la
  misma fila de stock por cada serie.
- **Alternativas descartadas**: auditar stock por línea (registros redundantes); auditar solo el
  total (pierde el detalle por material).

### D-07. Días en mano sin campo propio

- **Decisión**: `SolicitudAsignacion.confirmada_en` es la única fuente; lo escribe 007 en la misma
  transacción y 006 calcula los días a demanda. 008 no crea contador ni tabla.
- **Justificación**: CA-05 se cumple con `confirmada_en`; un contador duplicado se desincroniza y
  agrega escrituras.
- **Alternativas descartadas**: un campo `dias_en_mano` que habría que actualizar a diario; calcular
  desde `enviada_en` (no refleja la confirmación).

### D-08. Sin endpoints propios

- **Decisión**: 008 expone solo servicios internos en `stock/services.py`; no crea vistas, rutas,
  plantillas ni tareas Celery.
- **Justificación**: la spec no pide interfaz; los consumidores validan permisos y alcance. Mantiene
  la simplicidad y evita una API de stock no solicitada.
- **Alternativas descartadas**: endpoints REST de stock (fuera de alcance y con nueva superficie de
  permisos); tareas asíncronas (la confirmación debe ser transaccional e inmediata).

### D-09. Cálculo de reservado

- **Decisión**: el reservado de no seriados se calcula sumando líneas no seriadas de solicitudes
  `ENVIADA`; las series se reservan por su estado `RESERVADA`. `Disponible = max(0, StockGeneral -
  Reservado)`.
- **Justificación**: 006 no crea una tabla de reservas y la confirmación debe descontar exactamente
  lo reservado. El `max(0, ...)` evita disponibles negativos por datos históricos.
- **Alternativas descartadas**: una tabla de reservas (duplica el estado); contar también
  `CONFIRMADA` (ya movió stock y descontaría dos veces).

### D-10. `StockTecnico` con `tenant` obligatorio

- **Decisión**: `StockTecnico` tiene `tenant`, `tecnico`, `material` y `cantidad`. El servicio copia
  `tenant` desde `tecnico.tenant` y rechaza cualquier discrepancia; la clave única sigue siendo
  `(tecnico, material)`.
- **Justificación**: la constitución exige que toda tabla operativa lleve `tenant_id`. Tenerlo en la
  fila permite filtrar y aplicar RLS directamente, sin subconsultas a `tecnicos`, y no contradice a
  005 porque el tenant sigue derivándose del técnico y nunca se acepta del cliente.
- **Alternativas descartadas**: derivar el tenant solo por la relación (incumple la restricción de
  `tenant_id` y complica la política RLS); aceptar `tenant` del cliente (riesgo de fuga).

### D-11. RLS como respaldo

- **Decisión**: `stock_general` tiene política por `tenant_id`; `stock_tecnico` por el tenant del
  técnico. Si la infraestructura de 001 no está disponible, se registra la deuda y el ORM filtra por
  tenant/técnico.
- **Justificación**: principio I y patrón de 001/004/005. No se inventa una infraestructura RLS
  paralela.
- **Alternativas descartadas**: omitir RLS (pierde el respaldo); crear políticas ad hoc sin el
  middleware de 001 (inoperantes).

### D-12. Propagación transaccional

- **Decisión**: `actualizar_stock_confirmacion_asignacion` se ejecuta dentro de la transacción
  abierta por 007. Si se llama fuera de una transacción, abre un `transaction.atomic` propio y exige
  que la solicitud siga `ENVIADA`.
- **Justificación**: la confirmación completa debe ser todo o nada. Un `atomic` anidado crea un
  savepoint y no confirma por separado; el commit lo hace 007.
- **Alternativas descartadas**: que 008 haga commit (rompe la atomicidad de la confirmación); que
  007 escriba stock (duplica propiedad).

### D-13. Idempotencia de la confirmación

- **Decisión**: la confirmación exige `SolicitudAsignacion.estado == "ENVIADA"` y series
  `RESERVADA`. Una segunda confirmación recibe `409` desde 007 y no vuelve a mover stock.
- **Justificación**: evita dobles descuentos por doble clic o reintento.
- **Alternativas descartadas**: permitir confirmar de nuevo y detectar por diferencias (complejo y
  propenso a errores); usar un lock en Redis (no persistente).

### D-14. Rechazo fuera de 008

- **Decisión**: 008 no participa en el rechazo. 007 cambia la solicitud a `RECHAZADA` y libera las
  series `RESERVADA→DISPONIBLE`; las cantidades no seriadas se liberan porque el reservado solo
  cuenta `ENVIADA`.
- **Justificación**: el rechazo no mueve stock físico ni crea stock técnico; no hay nada que
  actualizar en las tablas de stock.
- **Alternativas descartadas**: que 008 libere series (duplica la transición de 007); crear una
  reserva persistente para borrarla (complejidad innecesaria).

### D-15. Rendimiento

- **Decisión**: la confirmación de 100 series debe resolverse en menos de 2 segundos, con consultas
  agregadas por material y sin una consulta por línea. Se usan `select_related`/`prefetch_related`
  y bloqueos por lote cuando el volumen lo justifique.
- **Justificación**: requisito 6.2 de la spec.
- **Alternativas descartadas**: procesar línea por línea con consultas individuales (lento y con
  N+1).

## Correcciones documentales aplicadas

1. Se eliminó `cantidad=-1` del plan anterior; toda resta valida stock suficiente y la base impone
   `>= 0`.
2. Se dejó explícito que 008 es dueña de `RESERVADA→ASIGNADA`, del stock y de su auditoría, y que
   007 solo fija `confirmada_en` y el estado de la solicitud.
3. Se alineó el orden fundacional: `StockGeneral`/`incrementar_stock_general` antes de 004;
   `StockTecnico`/incrementos/decrementos antes de 005.
4. Se retiró la afirmación de «no se usan bloqueos»; ahora se usa `select_for_update` en orden
   estable y se prueba concurrencia.
5. Se agregó `tenant` a `StockTecnico`, copiado y validado desde `tecnico.tenant`, para cumplir la
   restricción constitucional de que toda tabla operativa lleva `tenant_id` y simplificar la RLS.

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| Infraestructura RLS de 001 no disponible | Registrar en este documento y mantener filtrado en ORM |
| `StockTecnico.tenant` copiado del técnico | Validación en servicio y RLS por `tenant_id`; si la fila existente no coincide, `TenantNoCoincide` |
| Confirmación con stock insuficiente | Se revierte toda la transacción y la solicitud sigue `ENVIADA`; el almacén ve el error |
| Concurrencia entre 004, 006, 007 y 009 | Orden estable de bloqueo y pruebas de interbloqueo |
| Volumen alto de series | Agregación por material y bloqueo por lote; prueba de 100 series < 2 s |

## Conclusión

No quedan incógnitas bloqueantes. 008 queda como la única dueña del stock y de la transición de
series al confirmar, sin cantidades negativas, sin endpoints y con auditoría transaccional completa.
