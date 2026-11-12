# Investigación y decisiones: 009 Traspaso entre Técnicos

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/009-traspaso-entre-tecnicos/spec.md`

Este documento resuelve las incógnitas técnicas del plan. No quedan `NEEDS CLARIFICATION`
pendientes; las deudas documentales se listan al final.

## Contexto de dependencias

| Dependencia | Estado esperado | Uso en 009 |
|---|---|---|
| 001 — acceso, tenants y auditoría | Implementada | Roles, middleware, tenant, región y `RegistroCambio` |
| 002 — materiales | Implementada | Catálogo, lote y `es_seriado` |
| 003 — técnicos | Implementada | Origen y destino, tenant, NIF y activo |
| 004 — series | Implementada | `Serie.numero`, estado, tenant, material y custodia |
| 005 — stock inicial | Implementada | Series `ASIGNADA` con técnico y fecha de custodia |
| 006/007 — asignaciones | Implementadas | `SolicitudAsignacion`, confirmación y `validar_cuenta_almacen` |
| 008 — stock | Implementada | `StockTecnico` y servicios de incremento/decremento; nunca `StockGeneral` |
| PostgreSQL 16+ | Infraestructura | Restricciones, bloqueos, transacciones y RLS |

## Decisiones

### D-01. Custodia en `series.Serie`

- **Decisión**: añadir a `Serie` los campos `tecnico` (FK nullable a `tecnicos.Tecnico`) y
  `asignada_en` (DateTime nullable). `ASIGNADA` exige ambos; `DISPONIBLE` y `RESERVADA` exigen ambos
  nulos.
- **Justificación**: la spec 009 exige cambiar el técnico de la serie (CA-06) y reiniciar los días en
  mano (CA-09). Sin estos campos, la custodia solo podría deducirse de la última asignación, que no
  refleja traspasos ni devoluciones. Es la fuente única y evita otra tabla de custodia.
- **Alternativas descartadas**: deducir el técnico de `LineaAsignacion` (no refleja traspasos);
  una tabla `CustodiaSerie` con historial (más compleja y no es lo que pide la spec; la auditoría ya
  conserva el historial); un campo `dias_en_mano` (se desincroniza).

### D-02. Reservas derivadas de solicitudes `ENVIADA`

- **Decisión**: no se crea una tabla de reservas. El reservado de un técnico y material se calcula
  sumando líneas no seriadas y contando 1 por línea seriada de solicitudes `ENVIADA` del técnico
  origen. `Disponible = max(0, StockTecnico - Reservado)`.
- **Justificación**: la solicitud es la fuente de verdad; al confirmar, rechazar o cancelar, el
  estado deja de ser `ENVIADA` y la reserva desaparece sin limpieza adicional.
- **Alternativas descartadas**: una tabla `ReservaTraspaso` (estado duplicado y limpieza propensa a
  errores); marcar `Serie.estado=RESERVADA` en un traspaso (rompe el significado de “en custodia del
  técnico” y bloquea la devolución).

### D-03. Una lista canónica de líneas y cuadre por proyecciones

- **Decisión**: la solicitud tiene una sola lista de líneas. Las hojas de Desasignación y Asignación
  se construyen desde esa lista. `validar_cuadre_traspaso` compara las dos proyecciones: mismas
  series, mismos materiales/lotes y mismas cantidades no seriadas.
- **Justificación**: evita pedir dos listas al usuario y garantiza que el Excel sea coherente. El
  cuadre sigue siendo verificable y detecta líneas perdidas, duplicadas o manipuladas.
- **Alternativas descartadas**: dos listas persistidas (el usuario podría descuadrarlas y duplicar
  estado); confiar solo en la generación del Excel (no habría validación independiente).

### D-04. Excel al enviar y sin correo en 009

- **Decisión**: el Excel se genera al pasar de `BORRADOR` a `ENVIADA`, se guarda con hash SHA-256 y se
  sirve para descarga verificada. 009 no envía correo ni encola tareas.
- **Justificación**: el archivo debe reflejar la lista definitiva; generarlo al crear obligaría a
  regenerarlo en cada edición y rompería su inmutabilidad. La spec 009 no define correo; añadirlo
  duplicaría la infraestructura de 007 y violaría el alcance.
- **Alternativas descartadas**: generar al crear (archivo obsoleto tras editar); reutilizar
  `EnvioCorreo` de 007 (su modelo está atado a `SolicitudAsignacion`); enviar en una tarea Celery
  (fuera de alcance).

### D-05. Stock general intocable

- **Decisión**: 009 nunca lee ni escribe `StockGeneral`. Al confirmar, decrementa `StockTecnico` del
  origen e incrementa el del destino usando los servicios de 008. El total del tenant no cambia.
- **Justificación**: RF-38 y principio III. Los servicios de 008 bloquean, validan y auditan.
- **Alternativas descartadas**: actualizar `StockGeneral` para “cuadrar” (rompe la invariante);
  escribir `StockTecnico` con `update()` o `F()` (evita auditoría y validación).

### D-06. Orden de bloqueo

- **Decisión**: `SolicitudTraspaso` → `Tenant` → `StockTecnico` por `(material_id, tecnico_id)` →
  `Serie` por `id`.
- **Justificación**: 008 bloquea `Tenant` → `StockGeneral` → `StockTecnico` por `material_id` →
  `Serie`. 009 no toca `StockGeneral` y ordena primero por material, lo que evita ciclos con la
  confirmación de asignaciones y con recoJos.
- **Alternativas descartadas**: bloquear por técnico y luego material (puede ciclar con 008); no
  bloquear y confiar en el estado (dos envíos podrían reservar la misma serie).

### D-07. Máquina de estados

- **Decisión**: `BORRADOR → ENVIADA → CONFIRMADA | RECHAZADA`; `BORRADOR → CANCELADA`. Los estados
  finales no se reabren.
- **Justificación**: la spec lista esos estados y no define cancelación tras el envío. Cancelar en
  `ENVIADA` requeriría liberar reservas y podría competir con la confirmación del almacén.
- **Alternativas descartadas**: permitir cancelar `ENVIADA` (más casuística); permitir reabrir
  `RECHAZADA` (rompe la trazabilidad).

### D-08. Disponibilidad y selector de series

- **Decisión**: la disponibilidad de no seriados se calcula por material y descuenta las reservas
  `ENVIADA`. El selector de series muestra solo `Serie.estado=ASIGNADA`, con
  `Serie.tecnico=origen`, del material elegido y sin líneas en solicitudes `ENVIADA`.
- **Justificación**: RF-35 y CA-03. La serie es la unidad de disponibilidad para materiales seriados;
  no se puede validar solo con el total de `StockTecnico`.
- **Alternativas descartadas**: permitir seleccionar cualquier serie del tenant (riesgo de robar
  custodia); validar solo la cantidad total (no detecta series reservadas).

### D-09. Roles sin permisos Django

- **Decisión**: los servicios validan `USUARIO_TENANT` para crear/enviar/cancelar y
  `RESPONSABLE_ALMACEN` para confirmar/rechazar. No se crean permisos Django por cadena ni se confía
  en la vista.
- **Justificación**: patrón de 006/007 y constitución; los roles son del dominio, no permisos
  genéricos.
- **Alternativas descartadas**: `traspasos.add_solicitudtraspaso` (no refleja el alcance por tenant y
  se desincroniza del rol).

### D-10. Días en mano desde `Serie.asignada_en`

- **Decisión**: `Serie.asignada_en` marca el inicio de la custodia actual. 005 lo fija al crear el
  stock inicial, 008 al confirmar una asignación, 009 al confirmar un traspaso y 011 lo limpia al
  devolver. 006 calcula los días desde `Serie.asignada_en`, con respaldo en
  `SolicitudAsignacion.confirmada_en` solo para datos históricos sin custodia.
- **Justificación**: CA-09 exige reiniciar el conteo en el destino; `confirmada_en` de la asignación
  original no sirve después de un traspaso.
- **Alternativas descartadas**: un contador por técnico (se desincroniza); seguir usando
  `confirmada_en` (mostraría días del técnico anterior).

### D-11. `LineaTraspaso.serie` como FK y `tenant` explícito

- **Decisión**: `serie` es FK a `series.Serie` (nullable), no un `CharField`. `LineaTraspaso` lleva
  `tenant` copiado de la solicitud. Una serie aparece como máximo una vez por solicitud y un material
  no seriado tiene una sola línea agregada.
- **Justificación**: la FK preserva la identidad y permite validar custodia; `tenant` cumple la
  restricción constitucional de tablas operativas y habilita RLS. Las restricciones únicas evitan
  duplicados.
- **Alternativas descartadas**: guardar el número como texto (pierde la relación y permite series
  inexistentes); no poner `tenant` en la línea (incumple la constitución).

### D-12. Atomicidad y limpieza del Excel

- **Decisión**: creación, edición de borrador, envío, confirmación, rechazo y cancelación usan
  `transaction.atomic`. El Excel se genera dentro de la transacción de envío; si falla, se revierte el
  estado y se elimina el archivo parcial.
- **Justificación**: no puede quedar una solicitud `ENVIADA` sin Excel ni un Excel huérfano. Un fallo
  de auditoría también revierte.
- **Alternativas descartadas**: generar el Excel después del commit (estado inconsistente si falla);
  generarlo en una tarea (la respuesta al usuario quedaría sin archivo).

### D-13. RLS como respaldo

- **Decisión**: `traspasos_solicitudtraspaso` por `tenant_id` y `region_id`;
  `traspasos_lineatraspaso` por `tenant_id`. Si la infraestructura de 001 no está disponible, se
  registra la deuda y el ORM filtra por tenant/región.
- **Justificación**: principio I y patrón de 001/004/005/007/008.
- **Alternativas descartadas**: omitir RLS (pierde el respaldo); crear políticas ad hoc sin el
  middleware de 001 (inoperantes).

### D-14. Sin correo, Celery ni notificaciones

- **Decisión**: 009 no envía correos, no usa Celery ni publica eventos SSE. El almacén consulta su
  bandeja de traspasos.
- **Justificación**: la spec 009 no lo pide y la constitución prohíbe funcionalidad fuera de spec. Se
  evita duplicar 007.
- **Alternativas descartadas**: extender `EnvioCorreo` (cambio de modelo de 007); publicar eventos
  (no hay bandeja en tiempo real en la spec).

### D-15. Rendimiento

- **Decisión**: validar y confirmar un traspaso de 100 series en menos de 2 segundos, con consultas
  agregadas por material y sin una consulta por línea. Usar `select_related`/`prefetch_related` y
  bloqueos por lote.
- **Justificación**: requisito 6.2 de la spec y coherencia con 008.
- **Alternativas descartadas**: procesar línea por línea con consultas individuales (N+1).

## Correcciones documentales necesarias

1. `004-recojo-de-materiales/data-model.md`: añadir `Serie.tecnico`, `Serie.asignada_en`, restricción
   de coherencia e índices.
2. `005-stock-inicial-de-tecnicos/data-model.md` y `plan.md`: fijar `tecnico` y `asignada_en` al crear
   series `ASIGNADA`.
3. `006-solicitud-de-asignacion/plan.md`, `research.md` y `tasks.md`: calcular días en mano desde
   `Serie.asignada_en`, con respaldo en `confirmada_en` solo para datos históricos.
4. `008-confirmacion-y-actualizacion-de-stock/plan.md`, `data-model.md`, `contracts/` y `tasks.md`:
   fijar `Serie.tecnico`/`Serie.asignada_en` y auditarlos al confirmar.
5. `011-logistica-inversa-y-devoluciones/plan.md`: limpiar `Serie.tecnico`/`Serie.asignada_en` al
   devolver.
6. `04-contratos/excel-traspaso.md`: generar el Excel al enviar y dejar el correo fuera de 009.
7. `009-traspaso-entre-tecnicos/spec.md` §11: sustituir la referencia genérica a la FK por los campos
   concretos y la migración de `series`.

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| Datos históricos de `Serie` sin `tecnico`/`asignada_en` | Rellenar en la migración desde stock inicial y asignaciones confirmadas; si no es fiable, detener y documentar |
| Correo del Excel al almacén | Fuera de alcance de 009; registrar como deuda y no duplicar 007 |
| Confirmación de 009 en la bandeja de 007 | 009 expone sus propias rutas de almacén; no se modifica la bandeja de 007 |
| Concurrencia entre envíos y confirmaciones | Orden de bloqueo y revalidación bajo bloqueo |
| Cuadre estricto | Se rechaza cualquier diferencia; no hay tolerancia |
| RLS no disponible | Deuda registrada; el ORM sigue filtrando por tenant/región |
| Migración de series en una app ajena | Documentada como cambio transversal coordinado con 004/005/008/011 |

## Conclusión

No quedan incógnitas bloqueantes. El traspaso mueve custodia y stock técnico sin tocar el stock
general, usa una lista canónica para el cuadre y el Excel, deriva las reservas de `ENVIADA` y deja la
custodia de series en una única fuente compatible con 004/005/006/008/011.
