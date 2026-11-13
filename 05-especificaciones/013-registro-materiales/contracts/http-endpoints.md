# Contrato: endpoints de 013

Todas las rutas exigen sesión y rol `USUARIO_TENANT`. El tenant sale de la sesión; no se acepta
`tenant_id` del cliente.

| Ruta | Método | Respuesta |
|---|---|---|
| `/registro-materiales/` | `GET` | Menú del módulo |
| `/registro-materiales/ordenes/cargar/` | `GET` | Formulario de carga masiva |
| `/registro-materiales/ordenes/cargar/preview/` | `POST` | Resumen antes de guardar |
| `/registro-materiales/ordenes/cargar/` | `POST` | Confirma la carga |
| `/registro-materiales/ordenes/cargas/<id>/deshacer/` | `POST` | Deshace la carga |
| `/registro-materiales/ordenes/pendientes/` | `GET` | Órdenes sin materiales |
| `/registro-materiales/catalogo/` | `GET`/`POST` | Catálogo habilitado; activar/desactivar |
| `/registro-materiales/materiales/` | `GET` | Buscar orden y registrar materiales |
| `/registro-materiales/materiales/contexto/` | `GET` | Fragmento HTMX con orden o catálogo |
| `/registro-materiales/materiales/guardar/` | `POST` | Guardar uso |
| `/registro-materiales/ordenes/<id>/historial/` | `GET` | Historial de la orden |
| `/registro-materiales/entradas/` | `GET` | Saldo inicial y despachos del mes |
| `/registro-materiales/saldo-inicial/guardar/` | `POST` | Guardar saldo inicial |
| `/registro-materiales/dashboard/` | `GET` | Dashboard mensual |
| `/registro-materiales/cierre/` | `GET` | Checklist y estado |
| `/registro-materiales/cierre/cerrar/` | `POST` | Cerrar mes |
| `/registro-materiales/cierre/reabrir/` | `POST` | Reabrir mes |
| `/registro-materiales/cierre/justificar/` | `POST` | Justificar pendiente |
| `/registro-materiales/advertencias/<id>/resolver/` | `POST` | Resolver o justificar advertencia |
| `/registro-materiales/exportar/reporte/` | `GET` | Excel/CSV del reporte |
| `/registro-materiales/exportar/ordenes/` | `GET` | Excel/CSV del detalle de órdenes |

- No hay ruta para registrar despachos desde materiales; `DespachoAlmacen` se consulta.
- No hay `GET` para acciones de escritura.
- Un recurso ajeno devuelve `404`; un rol incorrecto `403`; mes cerrado `409`.
- No se expone la ruta física de los archivos exportados.

## Carga masiva

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `tecnico` | select | Sí | Técnico del tenant |
| `periodo` | select | Sí | `YYYY-MM`; por defecto el actual |
| `texto` | textarea | Sí | Una orden por línea |

- El preview devuelve leídas, nuevas, omitidas y también-existen-para-otro-técnico.
- Confirmar crea solo las nuevas.
- Deshacer solo si no hay materiales.

## Materiales

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `tecnico` | select | Sí | Técnico del tenant |
| `periodo` | select | Sí | `YYYY-MM`; por defecto el actual |
| `numero_orden` | text | Sí | Búsqueda exacta dentro del mes, sin distinguir mayúsculas |
| `fecha_instalacion` | date | Sí | Por defecto hoy |
| `cantidades[<material_id>]` | number | No | Entero ≥ 0; vacío = 0 |

- Si la orden no existe en el mes seleccionado, se muestra el catálogo en 0 y se crea al guardar.
- Si existe, se abre para editar.
- Si el número existe para el mismo técnico en otro mes, no se muestra; se debe cambiar el mes.
- El sistema puede rechazar por saldo insuficiente o mes cerrado.

## Saldo inicial

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `periodo` | select | Sí | `YYYY-MM` |
| `material` | select | Sí | Habilitado |
| `cantidad` | number | Sí | Entero ≥ 0 |

- Los despachos se muestran en solo lectura desde `DespachoAlmacen`.
- No hay formulario de despacho en esta pantalla.

## Cierre

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `periodo` | select | Sí | `YYYY-MM` |
| `backup_ref` | text | Sí al cerrar | Referencia emitida por `respaldar_bd`; no vacía y con formato válido |
| `motivo` | text | Sí al reabrir | Motivo de reapertura |

## Exportación

| Parámetro | Valores |
|---|---|
| `formato` | `xlsx` o `csv` |
| `tipo` | `reporte` o `ordenes` |
| `periodo` | `YYYY-MM` |

- `Content-Disposition` con nombre seguro.
- No se persiste el archivo.

## Errores

| Situación | Código | Mensaje |
|---|---|---|
| Sin sesión | `302` | — |
| Rol incorrecto | `403` | “No tienes permiso para registrar materiales” |
| Recurso ajeno | `404` | “El registro no existe” |
| Cantidad inválida | `400` | “La cantidad debe ser un número entero mayor o igual a 0” |
| Número inválido | `400` | “El número de orden es obligatorio y debe tener entre 1 y 30 caracteres alfanuméricos” |
| Periodo inválido | `400` | “El periodo debe tener el formato AAAA-MM” |
| Saldo insuficiente | `409` | “El uso supera el disponible del mes” |
| Mes cerrado | `409` | “El mes está cerrado; solicita reapertura” |
| Deshacer con materiales | `409` | “No se puede deshacer: hay órdenes con materiales registrados” |
| Cierre con pendientes | `409` | “El cierre tiene pendientes sin resolver o justificar” |
| Sin backup | `400` | “Debes registrar la referencia del respaldo antes de cerrar” |

## Pruebas de contrato

- Rutas de carga, preview, confirmación y deshacer.
- Rutas de materiales y validación de saldo negativo.
- Rutas de entradas sin formulario de despacho.
- Rutas de dashboard, cierre y reapertura.
- Exportación Excel/CSV.
- Ningún tenant ve datos de otro.
