# Contrato: endpoints de 013

Todas las rutas exigen sesión y rol `USUARIO_TENANT`. El tenant sale de la sesión; no se acepta
`tenant_id` del cliente.

| Ruta | Método | Respuesta |
|---|---|---|
| `/registro-materiales/` | `GET` | `200` con pantalla de registro por orden |
| `/registro-materiales/orden/contexto/` | `GET` | `200` fragmento HTMX con orden existente o catálogo |
| `/registro-materiales/orden/guardar/` | `POST` | `302`/fragmento con éxito; `400` por validación |
| `/registro-materiales/ordenes/<id>/historial/` | `GET` | `200` con historial de la orden y usos |
| `/registro-materiales/materiales/` | `GET` | `200` con catálogo habilitado |
| `/registro-materiales/materiales/<id>/activar/` | `POST` | `302`; activa el material |
| `/registro-materiales/materiales/<id>/desactivar/` | `POST` | `302`; desactiva el material |
| `/registro-materiales/entradas/` | `GET` | `200` con saldos y despachos del periodo |
| `/registro-materiales/saldo-inicial/guardar/` | `POST` | `302`; `400` por validación |
| `/registro-materiales/despachos/guardar/` | `POST` | `302`; `400` por validación |
| `/registro-materiales/despachos/<id>/editar/` | `POST` | `302`; `400` por validación |
| `/registro-materiales/recojos/buscar/` | `GET` | `200` fragmento/JSON con recojos y líneas del tenant |
| `/registro-materiales/reporte/` | `GET` | `200` con reporte mensual |

- No hay exportación Excel/PDF.
- No hay `GET` para acciones de escritura; devuelven `405`.
- Un recurso ajeno devuelve `404`; un rol incorrecto, `403`.
- No se expone la existencia de datos de otro tenant.

## Registro por orden

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `tecnico` | select | Sí | Técnico del tenant |
| `numero_orden` | text | Sí | 1–30 alfanuméricos; se normaliza |
| `fecha_liquidacion` | date | Sí | Define el periodo |
| `cantidades[<material_id>]` | number | No | Entero ≥ 0; vacío = 0 |

- Al enviar el contexto, se devuelve la orden existente o el catálogo habilitado con 0.
- Guardar conserva técnico/fecha, limpia número y enfoca el campo.
- Cambiar de técnico reinicia el formulario.
- Los materiales deshabilitados no aparecen para nuevas órdenes; las líneas históricas se muestran.

## Entradas

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `periodo` | text/select | Sí | `YYYY-MM` |
| `material` | select | Sí | Habilitado |
| `cantidad` | number | Sí | Entero ≥ 0 |
| `recojo` | select | Sí | Del tenant |
| `recojo_linea` | select | Sí | Del recojo |
| `fecha` | date | Sí | Periodo del despacho |

- El saldo inicial se guarda por material/periodo.
- El despacho se valida contra la línea del recojo.

## Catálogo

- Lista los materiales del catálogo compartido con estado habilitado/inactivo.
- Activar/desactivar no borra historial.
- El tenant no puede crear materiales en 013.

## Errores

| Situación | Código | Mensaje |
|---|---|---|
| Sin sesión | `302` a login | — |
| Rol incorrecto | `403` | “No tienes permiso para registrar materiales” |
| Recurso ajeno | `404` | “El registro no existe” |
| Cantidad inválida | `400` | “La cantidad debe ser un número entero mayor o igual a 0” |
| Número inválido | `400` | “El número de orden es obligatorio y debe tener entre 1 y 30 caracteres alfanuméricos” |
| Periodo inválido | `400` | “El periodo debe tener el formato AAAA-MM” |
| Técnico ajeno | `400` | “El técnico no pertenece a tu tenant” |
| Material no habilitado/inactivo | `400` | “El material no está habilitado para tu tenant” / “El material está deshabilitado” |
| Técnico de línea distinto | `400` | “El técnico de la línea no coincide con el técnico de la orden” |
| Recojo ajeno | `400` | “El recojo no pertenece a tu tenant” |
| Línea ajena | `400` | “La línea de recojo no pertenece al recojo” |
| Material distinto | `400` | “El material no coincide con la línea de recojo” |
| Despacho excede línea | `400` | “La cantidad despachada supera la cantidad del recojo” |

## Pruebas de contrato

- Cada ruta devuelve los códigos indicados para rol correcto, ajeno y validación fallida.
- El formulario ignora `tenant_id` enviado.
- El menú solo aparece para `USUARIO_TENANT`.
- El contexto devuelve catálogo en 0 o la orden existente.
- No hay rutas de exportación.
