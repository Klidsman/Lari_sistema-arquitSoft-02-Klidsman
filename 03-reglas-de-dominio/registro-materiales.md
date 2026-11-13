# Registro de materiales

Reglas de dominio para el registro de materiales usados por los técnicos y el saldo mensual.

## 1. Propósito

Permitir que cada tenant controle, mes a mes, el material que entra por los despachos del almacén,
el que usan sus técnicos en las órdenes y el saldo resultante.

```text
disponible = saldo inicial + despachos del almacén
saldo final = disponible - uso del mes
```

El saldo final de un mes es el saldo inicial del mes siguiente, salvo carga manual.

## 2. Independencia de la conciliación y del stock

- Este registro no es la conciliación del Excel del almacén.
- No lee, genera ni modifica conciliaciones.
- No modifica el stock general ni el stock por técnico.
- No modifica recojos, asignaciones, traspasos ni el catálogo compartido.

## 3. Definiciones

| Término | Significado |
|---|---|
| Material habilitado | Material del catálogo que un tenant puede usar en este módulo |
| Saldo inicial | Cantidad de un material al inicio de un mes |
| Despacho | Cantidad recogida en el mes, registrada en `DespachoAlmacen` |
| Uso | Cantidad de material consumida por un técnico en una orden |
| Disponible | Saldo inicial + despachos del mes |
| Saldo final | Disponible - uso del mes |
| Orden | Orden identificada por número, técnico y mes |
| Periodo | Mes de la orden o saldo, en formato `YYYY-MM` |

## 4. Catálogo habilitado

- El catálogo es fijo por tenant.
- Solo se puede registrar uso o saldo de materiales habilitados y activos.
- Deshabilitar un material no borra su historial.
- Un material deshabilitado no se puede usar en nuevas órdenes.
- El catálogo referencia `materiales.Material`; no duplica códigos ni descripciones.

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
- El número es obligatorio, de 1 a 30 caracteres alfanuméricos, sin espacios internos.
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

## 8. Despachos del almacén

- Los despachos ya se registran en `DespachoAlmacen`.
- El módulo solo lee `tenant`, `material`, `fecha` y `cantidad`.
- No se registra el despacho otra vez desde la pantalla de materiales.
- La fecha define el mes al que suma.
- Un despacho con cantidad 0 se conserva, pero no suma.
- No se modifica la estructura de `DespachoAlmacen` desde este flujo.
- El alta/edición existente de `DespachoAlmacen` valida `PeriodoCerrado`; no se edita un despacho de un mes cerrado.

## 9. Saldo inicial y cálculo mensual

```text
inicial = saldo manual del mes, si existe
si no, saldo final del cierre anterior
si no hay anterior, 0

despachos = suma de DespachoAlmacen del mes

usado = suma de uso de las órdenes del mes

final = inicial + despachos - usado
```

- Un saldo final negativo se muestra con alerta.
- El uso nuevo no puede dejar el mes en negativo.
- El saldo final de un mes cerrado se congela y pasa al mes siguiente.

## 10. Bloqueo de saldos negativos

- Antes de guardar un uso se calcula el disponible del mes.
- Se calcula el uso total del mes, incluyendo otros técnicos.
- Si el uso nuevo supera el disponible, no se guarda.
- Se muestra material, disponible, usado y faltante.
- No se permite un saldo inicial que deje el mes en negativo si ya hay uso.

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
- Número de orden obligatorio, 1–30 alfanumérico.
- Técnico del tenant.
- Material habilitado y activo.
- Orden única por técnico/mes/número.
- Uso no supera el disponible.
- Mes abierto para editar.
- Cierre con checklist y referencia de respaldo válida.
- Reapertura con motivo y actualización auditada del snapshot.
