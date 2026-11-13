# Investigación y decisiones: 013 Registro de Materiales

**Fase**: 0 | **Fecha**: 2026-11-13 | **Spec**:
`05-especificaciones/013-registro-materiales/spec.md`

Resuelve las incógnitas del plan aprobado. No hay `NEEDS CLARIFICATION` pendientes.

## Contexto de dependencias

| Dependencia | Estado | Uso en 013 |
|---|---|---|
| 001 — acceso, tenants y auditoría | Implementada | Cuenta, tenant, roles y `RegistroCambio` |
| 002 — materiales | Implementada | Catálogo compartido |
| 003 — técnicos | Implementada | Técnico `LAXXXX` |
| 013 base | Existente | `MaterialHabilitado`, `SaldoInicialPeriodo`, `DespachoAlmacen`, `OrdenLiquidacion`, `UsoMaterialOrden` |
| PostgreSQL 16+ | Infraestructura | Restricciones, bloqueos, transacciones y RLS |

**No depende de 004.** Los despachos ya están en `DespachoAlmacen` dentro de 013.

## Decisiones

### D-01. Reutilizar `DespachoAlmacen`

- **Decisión**: 013 usa la tabla existente `DespachoAlmacen` como única fuente de despachos. No se
  crea otra tabla ni se registra el despacho desde la pantalla de materiales.
- **Justificación**: evita doble registro y respeta la implementación existente.
- **Alternativas descartadas**: nueva tabla de despachos (duplica); integración con 004 (no es el
  módulo que el usuario usa).

### D-02. Solo cantidad y fecha del despacho

- **Decisión**: para el cálculo se usan `tenant`, `material`, `fecha` y `cantidad`. Cualquier otro
  campo del modelo existente se ignora. La alta/edición existente llama a `validar_periodo_abierto`;
  si el mes está cerrado, lanza `PeriodoCerrado`.
- **Justificación**: el usuario solo necesita la cantidad recogida en el mes y el cierre debe ser real.
- **Alternativas descartadas**: exigir recojo/línea (no aplica); permitir editar despachos cerrados
  (rompe el congelamiento).

### D-03. Carga masiva con mes

- **Decisión**: la pantalla de carga pide técnico y mes (por defecto el actual). La identidad de la
  orden es `(tenant, técnico, periodo, número)`.
- **Justificación**: permite comparar contra el mes correcto y que pegar la lista completa cada día
  sea seguro.
- **Alternativas descartadas**: órdenes sin mes hasta el registro de materiales (complica unicidad y
  resumen).

### D-04. Mismo número para varios técnicos o meses

- **Decisión**: el número puede existir para otro técnico o en otro mes. Para el mismo técnico y mes
  no se repite.
- **Justificación**: una orden puede ser realizada por un técnico y al día siguiente por otro, y el
  número puede reaparecer en otro mes.
- **Alternativas descartadas**: número global único (impide el caso real).

### D-05. Normalización y deduplicación

- **Decisión**: `strip`, descartar vacías, rechazar líneas con espacios internos/tabs/comas o más de
  un token, deduplicar sin distinguir mayúsculas. Se conserva el original y se compara el normalizado.
- **Justificación**: el pegado puede traer ruido; la comparación debe ser estable.
- **Alternativas descartadas**: aceptar líneas con varios valores (ambigüedad); comparar con
  mayúsculas (duplicados falsos).

### D-06. Resumen antes de guardar

- **Decisión**: mostrar leídas, nuevas, omitidas y cuántas también existen para otro técnico.
- **Justificación**: el usuario confirma antes de crear datos.
- **Alternativas descartadas**: guardar directo (errores de pegado).

### D-07. Deshacer carga

- **Decisión**: solo se puede deshacer un lote si sus órdenes nuevas no tienen usos con cantidad > 0.
  Se eliminan las órdenes del lote y se audita.
- **Justificación**: permite corregir una carga equivocada sin dejar basura.
- **Alternativas descartadas**: anular sin borrar (complica la clave única); borrar con materiales
  (pierde historial).

### D-08. Fecha de instalación editable

- **Decisión**: al registrar materiales se ingresa una sola fecha por orden; por defecto hoy. Puede
  cambiar el periodo y se revalida la clave.
- **Justificación**: el mes de la orden puede corregirse al registrar el uso.
- **Alternativas descartadas**: fecha fija al cargar (impediría corregir); fecha por línea (no tiene
  sentido).

### D-09. Bloqueo de saldo negativo

- **Decisión**: al guardar un uso, se calcula el disponible del mes por material y el uso total
  (incluyendo otros técnicos). Si el nuevo total supera el disponible, se rechaza con detalle.
- **Justificación**: prioridad aprobada y control de inventario.
- **Alternativas descartadas**: permitir negativo con alerta (el usuario pidió bloquear); validar solo
  la orden (ignora el consumo de otros técnicos).

### D-10. Advertencia de cantidad atípica

- **Decisión**: si la cantidad supera `3 × promedio mensual de los últimos 3 meses cerrados` del
  material, se crea una advertencia. El promedio usa el total mensual usado por material, no el
  promedio por orden. No bloquea. Umbral configurable.
- **Justificación**: detecta errores de digitación sin frenar la operación.
- **Alternativas descartadas**: bloquear (demasiado rígido); no avisar (errores pasan); promedio por
  orden (distorsiona materiales con muchas órdenes).

### D-11. Órdenes pendientes

- **Decisión**: una orden sin usos con cantidad > 0 es pendiente. Se filtra por antigüedad y técnico.
- **Justificación**: permite completar el mes antes del cierre.
- **Alternativas descartadas**: considerar pendiente solo si no existe fila de uso (una fila en 0
  sigue pendiente).

### D-12. Cierre con checklist

- **Decisión**: antes de cerrar se revisan órdenes sin materiales, saldos negativos y advertencias sin
  resolver. Cada punto se resuelve o justifica. Las advertencias se resuelven con
  `resolver_advertencia` o con una `JustificacionCierre` de tipo `ADVERTENCIA`. Se exige un
  `backup_ref` válido emitido por el comando externo `respaldar_bd`.
- **Justificación**: el cierre debe ser confiable y auditable; una referencia arbitraria no prueba que
  exista respaldo.
- **Alternativas descartadas**: cerrar sin checklist (errores quedan congelados); backup automático
  desde la app (riesgo y permisos); aceptar cualquier texto como backup.

### D-13. Congelamiento y traspaso

- **Decisión**: al cerrar se guarda `SaldoMensualMaterial` por material; el saldo final es el inicial
  del mes siguiente. Un mes cerrado bloquea cambios. Al reabrir y recerrar, el snapshot se reemplaza
  y los valores anteriores quedan en la auditoría y en la versión del cierre.
- **Justificación**: el saldo histórico no debe cambiar por ediciones posteriores, pero la corrección
  debe ser trazable.
- **Alternativas descartadas**: recalcular siempre (cambia el pasado); copiar solo totales (pierde
  detalle por material); no versionar la reapertura (no se sabe qué cambió).

### D-14. Reapertura

- **Decisión**: reabrir exige motivo, registra actor y fecha, y deja el mes abierto para corregir.
- **Justificación**: permite corregir sin perder trazabilidad.
- **Alternativas descartadas**: editar directo un mes cerrado (rompe el congelamiento).

### D-15. Exportación y alcance

- **Decisión**: exportar reporte mensual y detalle de órdenes a Excel o CSV. No se exportan otros
  módulos. No se modifica stock, series, asignaciones, traspasos ni conciliaciones.
- **Justificación**: pedido explícito y alcance acotado.
- **Alternativas descartadas**: PDF (no solicitado); exportar todo el sistema (fuera de alcance).

### D-16. Búsqueda de materiales por mes

- **Decisión**: la pantalla de materiales pide técnico y mes; la búsqueda del número es exacta dentro
  de ese mes. Si el número existe para el mismo técnico en otro mes, es otra orden y no se muestra.
- **Justificación**: la orden se identifica por técnico, mes y número; sin mes la búsqueda sería
  ambigua.
- **Alternativas descartadas**: buscar en todos los meses y abrir la primera coincidencia (ambigua).

### D-17. Catálogo habilitado

- **Decisión**: el catálogo se administra desde una pantalla de activar/desactivar. Si
  `MaterialHabilitado` no existe en el entorno, se crea una sola vez en la migración base.
- **Justificación**: el catálogo es la lista de materiales que el tenant puede usar.
- **Alternativas descartadas**: asumir que el catálogo está cargado sin pantalla (no verificable).

## Correcciones documentales aplicadas

1. `013/spec.md`: reemplazada por el flujo aprobado (carga masiva, despachos existentes, bloqueo,
   advertencias, cierre, reapertura, exportación).
2. `013/plan.md`: reemplazado por este plan.
3. `013/data-model.md`: actualizado con `CargaOrdenes`, cierre y snapshots.
4. `013/contracts/`, `quickstart.md` y `tasks.md`: actualizados al nuevo flujo.
5. `03-reglas-de-dominio/registro-materiales.md`: se actualiza con las reglas aprobadas.

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| `DespachoAlmacen` con campos extra | Se ignoran para el cálculo; no se modifica su estructura |
| Promedio sin historial | No se advierte hasta tener datos de meses cerrados anteriores |
| Backup de base de datos | Comando externo `respaldar_bd`; la app valida y registra la referencia |
| Reapertura y recierre | El snapshot se reemplaza con auditoría; la versión del cierre conserva el cambio |
| Cargas muy grandes | Procesamiento por lotes y pruebas de rendimiento |
| RLS no disponible | Deuda; el ORM filtra por tenant |
| Cambio de mes de una orden con uso | Recalcula ambos meses y bloquea si alguno está cerrado |
| Cierre con pendientes | Solo se permite con justificación explícita |

## Conclusión

No quedan incógnitas bloqueantes. El módulo reutiliza los despachos existentes, evita doble registro,
bloquea negativos, advierte cantidades atípicas y cierra el mes con un snapshot auditable.
