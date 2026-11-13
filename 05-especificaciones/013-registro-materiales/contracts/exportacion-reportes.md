# Contrato: exportación de reportes de 013

013 exporta el reporte mensual y el detalle de órdenes a Excel o CSV. Los archivos se generan en
memoria y se descargan; no se persisten en el servidor.

## Formatos

| Formato | Implementación |
|---|---|
| `xlsx` | `openpyxl` |
| `csv` | `csv` estándar, UTF-8 con BOM para Excel |

## Reporte mensual

Nombre: `reporte-materiales-<periodo>.xlsx` o `.csv`.

Contenido:

| Columna | Origen |
|---|---|
| Material | `material.codigo` |
| Descripción | `material.descripcion` |
| Saldo inicial | cálculo del periodo |
| Despachos | suma de `DespachoAlmacen` del mes |
| Usado | suma de `UsoMaterialOrden` del mes |
| Saldo final | inicial + despachos − usado |
| Alerta | “Sí” si el saldo final es negativo |
| Técnico | detalle por técnico, una fila por técnico/material |

- Se filtran solo datos del tenant.
- Si se solicita un técnico, se incluye su detalle y el saldo global del material.
- Un periodo sin datos genera encabezados y filas en 0 para materiales habilitados.

## Detalle de órdenes

Nombre: `ordenes-materiales-<periodo>.xlsx` o `.csv`.

Contenido:

| Columna | Origen |
|---|---|
| Técnico | `orden.tecnico.nif` |
| Número de orden | `orden.numero_original` |
| Fecha de instalación | `orden.fecha_instalacion` |
| Material | `uso.material.codigo` |
| Descripción | `uso.material.descripcion` |
| Cantidad usada | `uso.cantidad` |

- Solo órdenes del tenant y del periodo.
- Las órdenes sin materiales pueden incluirse con cantidad 0 si el reporte lo solicita.
- No se incluyen datos de otro tenant.

## Reglas

- No se persisten archivos ni se calcula hash.
- No se incluyen secretos ni rutas físicas.
- Los valores se escriben como texto/número, sin fórmulas ni macros.
- El archivo se descarga con `Content-Disposition` seguro.
- La exportación no modifica datos.

## Pruebas de contrato

- El reporte contiene los totales correctos por material y el detalle por técnico.
- El detalle contiene una fila por orden/material.
- Los despachos coinciden con `DespachoAlmacen`.
- El CSV se abre correctamente en Excel.
- Un tenant no ve datos de otro.
- Un periodo sin datos genera un archivo válido.
