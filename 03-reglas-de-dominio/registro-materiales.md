# Registro de materiales

Reglas de dominio para el registro de materiales usados por los técnicos y el cálculo del saldo mensual.

## 1. Propósito

Permitir que cada tenant controle, mes a mes, el material que entra por despachos del almacén, el que usan sus técnicos en las órdenes y el saldo resultante.

## 2. Independencia de la conciliación

- Este registro no es la conciliación del Excel del almacén.
- No lee, genera ni modifica conciliaciones.
- No modifica el stock general ni el stock por técnico.
- Solo usa el recojo registrado en el sistema como respaldo del despacho.

## 3. Definiciones

| Término | Significado |
|---|---|
| Material habilitado | Material del catálogo que un tenant puede usar en este módulo |
| Saldo inicial | Cantidad de un material al inicio de un mes |
| Despacho | Salida de material del almacén, vinculada a un recojo |
| Uso | Cantidad de material consumida por un técnico en una orden |
| Saldo final | Resultado de `saldo inicial + despachos - uso` |
| Orden de liquidación | Orden identificada por número, técnico y fecha |
| Periodo | Mes de la orden o del saldo, en formato `YYYY-MM` |

## 4. Catálogo habilitado

- El catálogo es fijo por tenant.
- Solo se puede registrar uso o saldo de materiales habilitados y activos.
- Deshabilitar un material no borra su historial.
- Un material deshabilitado no se puede usar en nuevas órdenes.

## 5. Saldo inicial

- Se registra por tenant, material y periodo.
- La cantidad es un entero ≥ 0.
- Solo hay un saldo inicial por tenant, material y periodo.
- Si el periodo no tiene saldo inicial, se usa el saldo final del periodo anterior.
- Si no existe periodo anterior, el saldo inicial es 0.
- Si la cuenta del tenant carga un saldo inicial manual, ese valor prevalece y queda auditado.
- El saldo final resultante se convierte en el saldo inicial del mes siguiente cuando este no tenga carga manual.

## 6. Despachos del almacén

- Se registran individualmente.
- Cada despacho tiene fecha, material, cantidad y referencia al recojo.
- El recojo y su línea deben pertenecer al tenant.
- La cantidad acumulada de despachos de una línea no puede superar la cantidad registrada en esa línea.
- Un despacho con cantidad 0 se conserva, pero no suma.
- Los despachos se agrupan por el mes de su fecha.

## 7. Uso por técnico

- El uso se registra por orden, técnico `LAXXXX` y material.
- Solo hay una línea por orden y material.
- Vacío o 0 significa que el material no se usó.
- El técnico de la línea debe coincidir con el técnico de la orden.
- El periodo de uso se obtiene de la fecha de liquidación de la orden.

## 8. Órdenes de liquidación

- Una orden se identifica por tenant, técnico, número de orden y periodo.
- El número de orden es obligatorio.
- La orden es única por técnico y mes.
- Si la orden ya existe, se abre para editar.
- La misma orden puede existir para otro técnico o en otro mes.
- Cambiar la fecha a otro mes recalcula el periodo y revalida la unicidad.

## 9. Cálculo mensual

Para un tenant, material y periodo:

```text
usado      = suma de uso de las órdenes del periodo
despachos  = suma de despachos con fecha dentro del periodo
inicial    = saldo inicial del periodo, si existe;
             si no, saldo final del periodo anterior;
             si no hay anterior, 0
final      = inicial + despachos - usado
```

- El reporte muestra el total por material.
- El reporte muestra el detalle de uso por técnico.
- Un saldo final negativo se muestra con alerta; no se oculta.

## 10. Historial y auditoría

- Toda edición de orden, saldo inicial o despacho registra usuario, fecha, valor anterior y valor nuevo.
- No se borran órdenes, usos, saldos ni despachos.
- Las correcciones se registran como cambios auditados.
- El historial es de solo inserción.

## 11. Aislamiento multitenant

- Un tenant nunca ve ni modifica datos de otro.
- El tenant se obtiene de la cuenta autenticada.
- Las claves únicas incluyen el tenant.
- Un dato de otro tenant se trata como inexistente.

## 12. Validaciones

- Cantidad entera ≥ 0.
- Periodo con formato `YYYY-MM`.
- Número de orden obligatorio.
- Técnico del tenant y con formato `LAXXXX`.
- Material habilitado para el tenant.
- Recojo y línea del tenant.
- Cantidad despachada dentro de la línea del recojo.
- Técnico de la línea igual al técnico de la orden.
