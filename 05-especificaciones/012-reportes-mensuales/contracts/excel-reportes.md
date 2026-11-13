# Contrato: Excel de reportes de 012

Las exportaciones se generan en memoria con `openpyxl` y se descargan. No se persisten archivos ni se
calcula hash; el contenido se deriva de datos ya auditados.

## Exportación de auditoría

- Nombre: `auditoria-<tenant|global>-<anio>-<mes>.xlsx`.
- Una hoja: `Auditoría`.
- Filtro: `RegistroCambio.fecha` en `[inicio, fin)` y `tenant` si no es global.
- Orden: `fecha`, `id`.

| Columna | Origen |
|---|---|
| Fecha | `RegistroCambio.fecha` |
| Usuario | `RegistroCambio.usuario` (email o nombre) |
| Entidad | `RegistroCambio.entidad` |
| Acción | `RegistroCambio.campo` |
| Valor anterior | `RegistroCambio.valor_anterior` |
| Valor nuevo | `RegistroCambio.valor_nuevo` |

- No se incluyen contraseñas, tokens, secretos, binarios ni rutas absolutas.
- Un tenant solo ve sus registros; el global incluye los registros con `tenant=NULL` y los de todos
  los tenants.
- Si no hay registros, el archivo se genera con encabezados y sin filas.

## Exportación de conciliación

- Nombre: `conciliacion-<tenant|global>-<anio>-<mes>.xlsx`.
- Una hoja: `Conciliación`.
- Filtro: `Conciliacion.fecha_carga` en `[inicio, fin)` y tenant si no es global.
- Orden: `fecha_carga`, `id`.

| Columna | Origen |
|---|---|
| Fecha | `Conciliacion.fecha_carga` |
| Estado | `Conciliacion.estado` |
| Tenant | `Conciliacion.tenant.codigo` (solo en el global) |
| Diferencias series | conteo de `DiferenciaSerie` |
| Diferencias cantidades | conteo de `DiferenciaCantidad` |
| Ajustes aplicados | `Conciliacion.ajustes_aplicados` |

- En el reporte de un tenant no se incluye la columna Tenant.
- `ajustes_aplicados` es 0 si la conciliación no está aprobada.
- Si no hay conciliaciones, el archivo se genera con encabezados y sin filas.

## Reglas de formato

- Encabezados en negrita y anchos razonables.
- Fechas con formato `dd-mm-yyyy`; horas con formato local.
- Valores anteriores/nuevos se escriben como texto, sin interpretar fórmulas.
- No se usan macros ni fórmulas.
- No se incluyen datos de otro tenant ni rutas físicas.
- El binario no se guarda en base ni en auditoría.

## Pruebas de contrato

- La auditoría contiene una fila por `RegistroCambio` del mes y tenant.
- La conciliación contiene una fila por conciliación del mes y tenant.
- Los conteos de diferencias y `ajustes_aplicados` coinciden con la base.
- El reporte de tenant no contiene filas de otro tenant; el global sí incluye todos.
- Un mes sin datos genera un archivo con encabezados.
- No hay secretos, binarios ni rutas absolutas.
