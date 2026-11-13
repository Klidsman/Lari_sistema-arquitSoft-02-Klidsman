# Investigación y decisiones: 013 Registro de Materiales

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/013-registro-materiales/spec.md`

Resuelve las incógnitas del plan y fija las decisiones de cálculo, unicidad, catálogo y auditoría. No
hay `NEEDS CLARIFICATION` pendientes; las correcciones y deudas se listan al final.

## Contexto de dependencias

| Dependencia | Estado esperado | Uso en 013 |
|---|---|---|
| 001 — acceso, tenants y auditoría | Implementada | Cuenta, tenant, roles, `RegistroCambio` con `tenant` |
| 002 — materiales | Implementada | Catálogo compartido `materiales.Material` |
| 003 — técnicos | Implementada | Técnico `LAXXXX` del tenant |
| 004 — recojos | Implementada | `Recojo` y `LineaRecojo` como respaldo del despacho |
| 005/008 — stock | Implementadas | **No se usan**: 013 no lee ni modifica stock |
| 010 — conciliación | Implementada | **No se usa**: 013 es independiente |
| PostgreSQL 16+ | Infraestructura | Restricciones, bloqueos, transacciones y RLS |

## Decisiones

### D-01. Catálogo compartido y habilitación por tenant

- **Decisión**: `MaterialHabilitado` referencia `materiales.Material`; no copia código, descripción ni
  lote. Un material deshabilitado conserva historial y no se ofrece en nuevas órdenes.
- **Justificación**: el catálogo es global (constitución) y 002 es la fuente. Copiarlo duplicaría
  datos y rompería la unicidad.
- **Alternativas descartadas**: tabla de materiales por tenant (duplica el catálogo); usar el catálogo
  global sin habilitación (el tenant vería materiales que no usa).

### D-02. Unicidad de la orden

- **Decisión**: clave única `(tenant, tecnico, periodo, numero_orden)`. El mismo técnico puede tener
  varias órdenes en el mes con números distintos; la misma orden puede existir en otro técnico o mes.
- **Justificación**: el flujo pide registrar una orden, guardar, limpiar el número y repetir con el
  siguiente número para el mismo técnico. Si la clave fuera solo técnico/mes, no se podrían registrar
  varias órdenes.
- **Alternativas descartadas**: una sola orden por técnico/mes (contradice el flujo); incluir la fecha
  exacta (el periodo es el mes, no el día).

### D-03. Herencia del saldo inicial

- **Decisión**: si hay `SaldoInicialPeriodo` manual, prevalece. Si no, se calcula el saldo final del
  periodo anterior; si no hay datos anteriores, 0. La búsqueda itera desde el periodo más antiguo con
  datos (manual, despacho o uso) hasta el anterior, sin recursión infinita.
- **Justificación**: la spec exige herencia y un saldo inicial 0 si no hay periodo anterior. Iterar
  desde el primer dato evita recursión y permite auditar/entender el cálculo.
- **Alternativas descartadas**: recursión sin límite (puede colgarse); persistir un saldo final por mes
  (tabla extra y posible desincronización).

### D-04. Despacho vinculado a recojo

- **Decisión**: todo despacho referencia `Recojo` y `LineaRecojo` del tenant; el material debe ser el
  de la línea. La suma de despachos de una línea, excluyendo el que se edita, no supera
  `LineaRecojo.cantidad`.
- **Justificación**: RF-70/75 y regla de dominio. El recojo es el respaldo del material que sale del
  almacén. No se modifica el recojo ni el stock.
- **Alternativas descartadas**: despacho libre sin recojo (sin respaldo); descontar del stock (fuera
  de alcance); permitir exceder la línea (inventario imposible).

### D-05. Independencia del stock y la conciliación

- **Decisión**: 013 no lee ni escribe `StockGeneral`, `StockTecnico`, `Serie` ni `Conciliacion`; solo
  usa `Recojo`/`LineaRecojo` como referencia.
- **Justificación**: la spec lo declara independiente y la constitución separa conciliación de stock.
- **Alternativas descartadas**: sincronizar el saldo con stock (mezcla dos modelos); leer la
  conciliación (fuera de alcance).

### D-06. Auditoría compartida

- **Decisión**: usar `auditoria.RegistroCambio` con `tenant`; no crear un modelo de auditoría en 013.
- **Justificación**: patrón del sistema y trazabilidad única. El plan anterior duplicaba
  `RegistroCambio`.
- **Alternativas descartadas**: tabla de historial propia (duplica y se desincroniza).

### D-07. Sin borrado y líneas en 0

- **Decisión**: no se borran órdenes, usos, saldos ni despachos. Un uso que pasa a 0 se conserva con
  `cantidad=0` y se audita; las líneas nuevas con 0 no se crean.
- **Justificación**: la spec prohíbe el borrado y exige historial. Conservar la línea con 0 mantiene la
  clave única y la trazabilidad.
- **Alternativas descartadas**: borrar la línea al poner 0 (pierde historia); crear todas las líneas
  con 0 (ruido innecesario).

### D-08. Aislamiento y RLS

- **Decisión**: todas las tablas llevan `tenant`; las consultas filtran por la sesión; un dato ajeno
  se trata como inexistente. RLS por `tenant_id` como respaldo.
- **Justificación**: principio I; el módulo maneja datos operativos del tenant.
- **Alternativas descartadas**: confiar solo en la vista; claves únicas sin tenant.

### D-09. Roles sin permisos Django

- **Decisión**: el servicio exige `USUARIO_TENANT`; no se crean permisos Django por cadena.
- **Justificación**: patrón de 006/007/009/010/011/012; el rol es del dominio.
- **Alternativas descartadas**: `registro_materiales.registrar` (no refleja alcance por tenant).

### D-10. Periodo derivado de la fecha

- **Decisión**: `periodo = fecha_liquidacion.strftime("%Y-%m")`; una orden no acepta un periodo
  distinto del derivado. Cambiar la fecha a otro mes recalcula el periodo y revalida la unicidad.
- **Justificación**: RF y regla 3; evita inconsistencias entre fecha y periodo.
- **Alternativas descartadas**: permitir periodo manual (puede contradecir la fecha).

### D-11. Número de orden

- **Decisión**: normalizar `strip`, mayúsculas, sin espacios internos; 1–30 alfanuméricos
  (`^[A-Z0-9]{1,30}$`).
- **Justificación**: decisión confirmada en la spec. La normalización evita duplicados por espacios o
  minúsculas.
- **Alternativas descartadas**: permitir cualquier texto (claves ambiguas); limitar a solo dígitos
  (la spec permite alfanumérico).

### D-12. Concurrencia

- **Decisión**: bloquear `Tenant`, orden existente y línea de recojo; usar las restricciones únicas
  como última defensa. Dos despachos de la misma línea se serializan y no exceden la cantidad.
- **Justificación**: doble clic y dos sesiones son casos borde de la spec.
- **Alternativas descartadas**: validar solo antes de la transacción (condición de carrera); `F()`
  ciego (puede superar el límite).

### D-13. Reporte mensual

- **Decisión**: incluir materiales habilitados activos y los que tengan saldo, despacho o uso en el
  periodo. Totales por material y detalle por técnico. Saldo final negativo se muestra con alerta, no
  se bloquea.
- **Justificación**: el tenant necesita ver lo que usa y lo que tuvo movimiento; un material
  deshabilitado con historial no debe desaparecer del reporte.
- **Alternativas descartadas**: incluir todo el catálogo global (ruido); ocultar negativos (pierde
  señal).

### D-14. Rendimiento

- **Decisión**: agregaciones SQL, `select_related`, índices por tenant/material/periodo y caché por
  request para el saldo inicial heredado. Reporte de 100 materiales y 1 000 usos en tiempo razonable.
- **Justificación**: requisito de rendimiento y herencia de saldos.
- **Alternativas descartadas**: N+1 por material/técnico; recursión sin caché.

### D-15. Alcance

- **Decisión**: 013 no exporta Excel/PDF, no importa entradas por Excel, no modifica stock, recojos,
  asignaciones, traspasos ni catálogo.
- **Justificación**: la spec lo excluye expresamente.
- **Alternativas descartadas**: agregar exportación (fuera de spec); sincronizar stock (contradice la
  independencia).

## Correcciones documentales necesarias

1. `013-registro-materiales/spec.md` §5.4 y regla 4: aclarar que la unicidad es por tenant, técnico,
   periodo y número; se permiten varias órdenes del mismo técnico en el mes con números distintos.
2. `013-registro-materiales/plan.md`: reemplazar el plan anterior; usar `materiales.Material`,
   `recojos.LineaRecojo`, auditoría compartida y roles sin permisos Django.
3. `03-reglas-de-dominio/catalogo-de-materiales.md`: sigue vacío; 002 es la fuente vigente (deuda
   existente, no se resuelve en 013).

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| Herencia de saldo en cadenas largas | Iterar desde el primer dato, limitar con `REGISTRO_MATERIALES_PERIODOS_MAX` y cachear por request |
| Saldo final negativo | Se muestra con alerta; no bloquea |
| Material deshabilitado con historial | Se conserva y se muestra en órdenes existentes; no en nuevas |
| Despacho con cantidad 0 | Se registra; no suma |
| RLS no disponible | Deuda; el ORM filtra por tenant |
| Catálogo compartido sin documentar | Deuda de `03-reglas-de-dominio/catalogo-de-materiales.md`; se usa 002 |
| Reporte con muchos datos | Agregaciones e índices; prueba de rendimiento |

## Conclusión

No quedan incógnitas bloqueantes. El módulo usa el catálogo compartido, define una clave de orden que
permite varias órdenes por técnico/mes, calcula el saldo con herencia iterativa, vincula cada despacho
al recojo y no toca stock ni conciliación.
