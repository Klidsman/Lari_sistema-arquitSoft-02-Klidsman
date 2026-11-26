# Registro de materiales

Reglas de dominio para el registro de materiales usados por los técnicos y el saldo mensual.

## 1. Propósito

Permitir que cada tenant controle, mes a mes, el material que entra por las asignaciones confirmadas del almacén,
el que usan sus técnicos en las órdenes y el saldo resultante.

```text
disponible = saldo inicial + asignaciones confirmadas del almacén
saldo final = disponible - uso del mes
```

El saldo final de un mes es el saldo inicial del mes siguiente. El saldo inicial operativo se carga en Stock inicial; el saldo manual queda solo como dato histórico.

## 2. Independencia de la conciliación y alcance del stock

- Este registro no es la conciliación del Excel del almacén.
- No lee, genera ni modifica conciliaciones.
- Cada uso descuenta el stock del técnico en la misma transacción mediante un movimiento `CONSUMO`.
- En materiales seriados se seleccionan las series usadas y pasan a `INSTALADA`.
- No modifica el stock general.
- No modifica recojos, asignaciones, traspasos ni el catálogo compartido.

## 3. Definiciones

| Término | Significado |
|---|---|
| Material habilitado | Material del catálogo que un tenant puede usar en este módulo |
| Saldo inicial | Cantidad de un material al inicio de un mes |
| Asignación confirmada | Cantidad confirmada por el almacén en el mes |
| Uso | Cantidad de material consumida por un técnico en una orden |
| Disponible | Saldo inicial + asignaciones confirmadas del mes |
| Saldo final | Disponible - uso del mes |
| Orden | Orden identificada por número, técnico y mes |
| Periodo | Mes de la orden o saldo, en formato `YYYY-MM` |

## 4. Materiales disponibles

- No hay habilitación manual de materiales.
- El formulario muestra los materiales con stock en `StockTecnico` del técnico o series `ASIGNADA`.
- Un material que ya tiene uso en la orden sigue visible para poder editarlo.
- El catálogo referencia `materiales.Material`; no duplica códigos ni descripciones.
- `MaterialHabilitado` queda como dato histórico y no participa del flujo nuevo.

## 5. Carga masiva de órdenes

- El tenant selecciona técnico y mes; por defecto el actual.
- El formato de la lista es libre: cualquier texto o número, una orden por línea.
- Se eliminan espacios al inicio y al final.
- Se descartan líneas vacías.
- Se rechazan líneas con más de un valor, espacios internos, tabs o comas.
- Se eliminan duplicados dentro de la lista sin distinguir mayúsculas/minúsculas.
- Se compara contra las órdenes existentes.
- Las órdenes ya existentes para el mismo técnico y mes se omiten.
- Las órdenes nuevas se cargan con el técnico seleccionado.
- El mismo número puede existir para otro técnico o en otro mes.
- Si el número existe para otro técnico, se crea para el técnico seleccionado y se informa en el resumen.
- Antes de guardar se muestra: leídas, nuevas, omitidas y cuántas también existen para otro técnico.
- Deshacer carga solo es posible si las órdenes nuevas no tienen materiales; se audita.
- Pegar la lista completa varias veces solo agrega las órdenes nuevas.

## 6. Orden de liquidación

- Se identifica por tenant, técnico, periodo y número.
- El número es obligatorio, de 1 a 30 caracteres alfanuméricos, con guiones o guiones bajos simples entre bloques, sin espacios internos ni separadores consecutivos.
- La orden es única por técnico y mes; el mismo número puede existir para otro técnico o en otro mes.
- Al registrar materiales se selecciona técnico y mes; la búsqueda es exacta dentro de ese mes.
- Si el número existe para el mismo técnico en otro mes, es otra orden y no se muestra.
- Si la orden ya existe para el técnico y mes, se abre para editar.
- La fecha de instalación se registra al cargar materiales; por defecto hoy y editable.
- Cambiar la fecha a otro mes recalcula el periodo y revalida la unicidad.
- Una orden sin materiales registrados es pendiente.

## 7. Uso por técnico

- El uso se registra por orden, técnico y material.
- Solo hay una línea por orden y material.
- Vacío o 0 significa que el material no se usó.
- El técnico de la línea debe coincidir con el de la orden.
- El periodo de uso se obtiene de la fecha de instalación de la orden.
- El uso se descuenta del disponible del mes.

## 8. Asignaciones confirmadas del almacén

- La fuente es `LineaAsignacion` de solicitudes con estado `CONFIRMADA`.
- El mes se determina por `SolicitudAsignacion.confirmada_en`.
- Para cada material se suma `LineaAsignacion.cantidad`.
- Las solicitudes enviadas, rechazadas o canceladas no suman.
- No se registra la asignación otra vez desde la pantalla de materiales.
- `DespachoAlmacen` queda como tabla histórica y no participa del cálculo.

## 9. Saldo inicial y cálculo mensual

```text
inicial = saldo manual histórico del mes, si existe
si no, saldo final del cierre anterior
si no hay anterior, stock actual + usado - asignaciones_confirmadas

asignaciones_confirmadas = suma de LineaAsignacion de solicitudes CONFIRMADA del mes

usado = suma de uso de las órdenes del mes

final = inicial + asignaciones_confirmadas - usado = stock actual
```

- Un saldo final negativo se muestra con alerta.
- El uso nuevo no puede dejar el mes en negativo.
- El saldo final de un mes cerrado se congela y pasa al mes siguiente.

## 10. Bloqueo de saldos negativos

- Antes de guardar un uso se calcula el disponible del mes.
- Se calcula el uso total del mes, incluyendo otros técnicos.
- Si el uso nuevo supera el disponible, no se guarda.
- Se muestra material, disponible, usado y faltante.
- El saldo inicial operativo se carga en Stock inicial; ya no se registra manualmente desde este módulo.

## 11. Advertencias

- Si una cantidad supera 3 veces el promedio mensual de los últimos 3 meses cerrados del material, se registra una advertencia.
- El promedio usa el total mensual usado por material, no el promedio por orden.
- El umbral es configurable.
- La advertencia no bloquea el guardado.
- Se resuelve con `resolver_advertencia` o con una justificación de cierre.
- Sin historial de meses cerrados no se advierte.

## 12. Historial y auditoría

- Toda edición de orden, uso o saldo registra usuario, fecha, valor anterior y valor nuevo.
- No se borran órdenes, usos, saldos ni despachos.
- La única excepción es deshacer una carga de órdenes nuevas sin materiales, que se audita.
- El historial es de solo inserción.

## 13. Cierre mensual

- Antes de cerrar se revisa:
  - órdenes del mes sin materiales;
  - materiales con saldo negativo;
  - advertencias sin resolver.
- Cada punto debe resolverse o justificarse.
- Las advertencias se resuelven con `resolver_advertencia` o con una `JustificacionCierre`.
- Se exige una referencia válida del respaldo emitida por `respaldar_bd`.
- Al cerrar se congela el saldo por material.
- Un mes cerrado no admite cambios de órdenes, usos, saldos ni despachos.
- La reapertura exige motivo y queda auditada; al recerrar se actualiza el snapshot con auditoría.

## 14. Exportación

- Se puede exportar el reporte mensual y el detalle de órdenes.
- Formatos: Excel y CSV.
- Solo se exportan datos del tenant.

## 15. Aislamiento multitenant

- Un tenant nunca ve ni modifica datos de otro.
- El tenant se obtiene de la cuenta autenticada.
- Las claves únicas incluyen el tenant.
- Un dato de otro tenant se trata como inexistente.

## 16. Validaciones

- Cantidad entera ≥ 0.
- Periodo con formato `YYYY-MM`.
- Número de orden obligatorio, 1–30 alfanumérico con guiones o guiones bajos simples.
- Técnico del tenant.
- Material habilitado y activo.
- Orden única por técnico/mes/número.
- Uso no supera el disponible.
- Mes abierto para editar.
- Cierre con checklist y referencia de respaldo válida.
- Reapertura con motivo y actualización auditada del snapshot.
