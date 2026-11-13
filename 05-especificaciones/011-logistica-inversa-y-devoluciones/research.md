# Investigación y decisiones: 011 Logística Inversa y Devoluciones

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/011-logistica-inversa-y-devoluciones/spec.md`

Resuelve las incógnitas del plan. No hay `NEEDS CLARIFICATION` pendientes; las deudas y correcciones
documentales se listan al final.

## Contexto de dependencias

| Dependencia | Estado esperado | Uso en 011 |
|---|---|---|
| 001 — acceso y tenants | Implementada | Cuenta, tenant, región, roles y auditoría |
| 002 — materiales | Implementada | Código, descripción y lote para el acta |
| 003 — técnicos | Implementada | Técnico que devuelve, NIF y tenant |
| 004 — series | Implementada | `Serie`, `EstadoSerie` y `crear_serie` |
| 005/008 — stock | Implementadas | `StockTecnico`, `StockGeneral` y servicios de ajuste |
| 009 — traspasos | Implementada | Custodia y reservas por traspaso `ENVIADA` |
| 010 — conciliación | Implementada | Estado `INSTALADA` y semántica de liquidación |
| PostgreSQL 16+ | Infraestructura | Restricciones, bloqueos, transacciones y RLS |

## Decisiones

### D-01. Devolución: del técnico al stock general

- **Decisión**: una devolución exige series `ASIGNADA` al técnico; por cada serie, el estado pasa a
  `DISPONIBLE`, se limpian `tecnico`/`asignada_en`, se decrementa `StockTecnico` y se incrementa
  `StockGeneral` por material.
- **Justificación**: RF-65, CA-01 y CA-02. La serie vuelve a estar disponible y puede reasignarse. El
  total del tenant no cambia.
- **Alternativas descartadas**: dejar la serie `ASIGNADA` sin técnico (inconsistente); devolverla
  solo a nivel lógico sin mover stock (descuadra).

### D-02. Baja: saca del stock donde está, no de ambos

- **Decisión**: una baja acepta una serie `ASIGNADA` o `DISPONIBLE`. Si está `ASIGNADA`, decrementa
  `StockTecnico`; si está `DISPONIBLE`, decrementa `StockGeneral`. Luego pasa a `INACTIVA` y limpia
  custodia. No toca el otro nivel de stock.
- **Justificación**: RF-66. El plan anterior decrementaba ambos y descuadraba el total. La serie sale
  una sola vez del inventario disponible.
- **Alternativas descartadas**: decrementar ambos (doble salida); eliminar la serie (pierde
  trazabilidad); devolverla al general y luego restarla (pasos innecesarios).

### D-03. `INACTIVA` distinta de `INSTALADA`

- **Decisión**: añadir `INACTIVA` como estado terminal para bajas/recuperaciones. `INSTALADA` queda
  para la liquidación por conciliación (010). Ambas exigen custodia nula y no se reasignan.
- **Justificación**: la causa de la baja y la liquidación por reporte son hechos distintos; 012 puede
  contarlos por separado. Borrar la serie rompe la trazabilidad.
- **Alternativas descartadas**: usar `INSTALADA` para todo (pierde la causa); usar `INACTIVO` sin
  distinguir liquidación (confunde reportes); eliminar (viola la constitución).

### D-04. FK a `series.Serie`, no número en texto

- **Decisión**: `LineaDevolucion.serie` y `BajaEquipo.serie` son FK a `series.Serie`. Las líneas
  llevan `tenant`; la baja lleva `tenant` y `region`.
- **Justificación**: preserva la identidad, la unicidad global y el aislamiento; permite validar
  estado/custodia y cumple la restricción de `tenant_id` en tablas operativas.
- **Alternativas descartadas**: `CharField` (permite series inexistentes y duplica la clave); no
  poner `tenant` en las líneas (incumple la constitución y complica RLS).

### D-05. Acta automática al registrar, sin correo del sistema

- **Decisión**: el acta se genera dentro de la transacción de la devolución, se guarda con nombre
  relativo seguro y hash SHA-256, y se descarga verificando el hash. No se envía por correo desde el
  sistema.
- **Justificación**: el contrato del acta dice que se genera automáticamente al registrar. Generarla
  a demanda permitiría que el contenido cambie o se desincronice. El envío a Lari lo hace el tenant.
- **Alternativas descartadas**: generarla a demanda (menos fiable); enviarla por correo (fuera de
  spec y duplicaría 007); generarla después del commit (devolución sin acta si falla).

### D-06. Una baja por serie

- **Decisión**: `BajaEquipo.serie` es `OneToOneField`; una serie no puede tener dos bajas.
- **Justificación**: `INACTIVA` es terminal y no se reasigna; una segunda baja es un error. La base
  resuelve la concurrencia.
- **Alternativas descartadas**: FK normal con validación de servicio (dos bajas simultáneas podrían
  pasar); borrar la baja anterior (pierde historia).

### D-07. Series reservadas no se devuelven ni se dan de baja

- **Decisión**: si una serie está referenciada por una `LineaTraspaso` de solicitud `ENVIADA`, la
  devolución y la baja fallan con `SerieReservada`.
- **Justificación**: el traspaso pendiente ya reservó esa custodia; devolverla o darla de baja
  dejaría el traspaso inconsistente. El tenant debe rechazar/cancelar el traspaso primero.
- **Alternativas descartadas**: liberar la reserva automáticamente (modifica otra spec);
  ignorar la reserva (permite doble movimiento).

### D-08. Orden de bloqueo

- **Decisión**: `Tenant` → `StockGeneral` por `material_id` → `StockTecnico` por `material_id` →
  `Serie` por `id`.
- **Justificación**: es el orden de 008 y evita ciclos con confirmación de asignaciones, recojos y
  conciliación. 009 bloquea el stock por `(material, técnico)`, compatible.
- **Alternativas descartadas**: bloquear series antes que stock (puede ciclar); no bloquear y confiar
  en el estado (dos operaciones podrían mover la misma serie).

### D-09. Auditoría completa

- **Decisión**: auditar `Devolucion/alta`, `LineaDevolucion/alta`, `Devolucion/acta`,
  `BajaEquipo/alta`, `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en` y los cambios de stock de
  008.
- **Justificación**: RF-46/CA-06 y principio VI. Cada ajuste debe tener valor anterior y nuevo.
- **Alternativas descartadas**: auditar solo la cabecera (pierde el detalle por serie).

### D-10. RLS y aislamiento

- **Decisión**: devoluciones y bajas por `tenant_id`/`region_id`; líneas por `tenant_id`. Si 001 no
  está disponible, deuda y filtrado ORM.
- **Justificación**: principio I y patrón 001/004/005/007/008/009/010.
- **Alternativas descartadas**: omitir RLS; políticas ad hoc sin middleware (inoperantes).

### D-11. Roles sin permisos Django

- **Decisión**: los servicios exigen `USUARIO_TENANT` y pertenencia al tenant. No se crean permisos
  Django por cadena.
- **Justificación**: patrón de 006/007/009/010; el rol es del dominio.
- **Alternativas descartadas**: `add_devolucion`/`add_bajaequipo` (no reflejan el alcance por tenant).

### D-12. Fecha de devolución

- **Decisión**: `fecha` es obligatoria, por defecto hoy y no puede ser futura. Se usa en el acta.
- **Justificación**: el acta requiere una fecha válida y no tiene sentido devolver a futuro.
- **Alternativas descartadas**: `auto_now_add` (impide registrar devoluciones del día anterior);
  permitir futuras (datos inconsistentes).

### D-13. Concurrencia

- **Decisión**: bloquear tenant, stock y series; revalidar dentro del bloqueo. Dos devoluciones o
  bajas simultáneas dejan una sola operación válida.
- **Justificación**: RF-65/66 y principio V. La restricción única de baja es la última defensa.
- **Alternativas descartadas**: validar solo antes de la transacción (condición de carrera); usar
  `F()` ciego (puede dejar stock negativo).

### D-14. Rendimiento

- **Decisión**: agrupar stock por material y usar `bulk_create` para líneas; devolución de 100 series
  en menos de 2 segundos, sin N+1.
- **Justificación**: requisito de rendimiento y coherencia con 008/009.
- **Alternativas descartadas**: una consulta por serie (N+1); generar el acta fuera de la transacción
  (estado inconsistente).

### D-15. Alcance

- **Decisión**: 011 solo maneja series (materiales seriados) y no implementa devoluciones masivas ni
  actas de bajas. Las bajas se registran una por serie.
- **Justificación**: la spec habla de equipos/series; los no seriados no tienen custodia por serie.
  No se agrega funcionalidad no pedida.
- **Alternativas descartadas**: devolución de cantidades no seriadas (no hay trazabilidad unitaria);
  acta de bajas (el contrato solo define acta de devoluciones).

## Correcciones documentales necesarias

1. `011-logistica-inversa-y-devoluciones/plan.md`: reemplazar `serie` CharField por FK, añadir
   `tenant`/`region`, corregir la baja para tocar un solo nivel de stock y generar el acta al
   registrar.
2. `004-recojo-de-materiales/data-model.md`, `plan.md` y `tasks.md`: añadir `INACTIVA` a
   `EstadoSerie`, choices y check; ampliar la coherencia de custodia.
3. `009-traspaso-entre-tecnicos/data-model.md`: permitir `INACTIVA` sin custodia.
4. `012-reportes-mensuales/plan.md`: distinguir `INSTALADA` e `INACTIVA` si el reporte las cuenta
   por separado.
5. `04-contratos/acta-devoluciones.md`: confirmar generación automática y que el envío lo hace el
   tenant.

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| Series reservadas en traspaso | Se rechaza la devolución/baja hasta liberar la reserva |
| Acta fallida | Se revierte la devolución y se elimina el archivo parcial |
| Series `INACTIVA` en reportes | 012 las cuenta según su regla; no vuelven a stock |
| RLS no disponible | Deuda registrada; el ORM filtra por tenant/región |
| Bajas masivas | No hay operación masiva; se monitorea el stock |
| Devolución de no seriados | Fuera de alcance: no hay custodia unitaria |

## Conclusión

No quedan incógnitas bloqueantes. La devolución mueve stock al general y libera custodia; la baja saca
la serie del nivel correcto y la deja `INACTIVA`; el acta se genera de forma atómica; y ninguna
operación elimina series ni cruza tenants.
