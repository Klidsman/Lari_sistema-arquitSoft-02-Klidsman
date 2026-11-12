# Contrato HTTP: asignaciones

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

Aplicación server-rendered con HTMX. Todas las rutas comparten cookie de sesión, CSRF, el
middleware de contexto y la autenticación de la spec 001. Los errores de negocio se devuelven como
página completa o fragmento HTML, con el mensaje exacto indicado. Los permisos se validan en el
servidor; ocultar un botón no es una autorización.

## Convenciones

- **Autenticación**: cookie de sesión de Django. Una sesión `pendiente_2fa` no accede a estas rutas.
- **Roles**: `ADMIN` = Administrador de plataforma; `TENANT` = cuenta del tenant;
  `ALMACEN` = Responsable de almacén.
- **CSRF**: obligatorio en todo `POST`.
- **Tenant**: se obtiene de la sesión (`request.usuario.tenant`). Ninguna ruta acepta ni usa
  `tenant_id`, `region_id`, `nif` ni `estado` del cliente.
- **Formato**: HTML; en peticiones HTMX, fragmento con el mismo texto y el código correspondiente.
- **Códigos**: `200` lectura o fragmento; `302` redirección tras `POST` exitoso; `400` validación;
  `401` sin sesión; `403` rol no autorizado o tenant suspendido; `404` solicitud inexistente o de
  otro tenant; `405` método no permitido; `409` operación no aplicable al estado actual; `500`
  error interno de generación de Excel sin detalles técnicos.
- **Fechas**: `YYYY-MM-DD`.
- **Sin edición ni borrado**: no hay `GET .../editar/`; `PUT`, `PATCH` y `DELETE` responden `405`.
- **Sin API REST ni JSON**: los fragmentos HTMX usan atributos `data-*`; ver
  `contracts/selector-series.md` y `contracts/validacion-disponibilidad.md`.
- **Excel**: 006 lo genera y lo conserva; su descarga, envío por correo y verificación de hash
  pertenecen a la spec 007.

## Matriz de permisos

| Ruta | ADMIN | TENANT | ALMACEN |
|---|---|---|---|
| `GET /asignaciones/` | No (`403`) | Sí | No (`403`) |
| `GET /asignaciones/nueva/` | No (`403`) | Sí | No (`403`) |
| `POST /asignaciones/nueva/` | No (`403`) | Sí | No (`403`) |
| `GET /asignaciones/<id>/` | No (`403`) | Sí (solo su tenant) | No (`403`) |
| `POST /asignaciones/<id>/enviar/` | No (`403`) | Sí (solo su tenant) | No (`403`) |
| `POST /asignaciones/<id>/cancelar/` | No (`403`) | Sí (solo su tenant) | No (`403`) |
| `GET /asignaciones/series-disponibles/` | No (`403`) | Sí | No (`403`) |
| `POST /asignaciones/validar-disponibilidad/` | No (`403`) | Sí | No (`403`) |

- La autorización se revalida en el servicio; forzar la URL o el `POST` no cambia el resultado.
- El Administrador de plataforma y el Responsable de almacén reciben
  `403` "No tienes permiso para crear asignaciones".
- Si el tenant está suspendido, toda cuenta del tenant recibe `403` "El tenant está suspendido".
- Una solicitud de otro tenant responde `404` "La solicitud no existe".

## Rutas

### `GET /asignaciones/`

Listado paginado de las solicitudes del tenant de la sesión.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Parámetros | `page` (opcional), `estado` (opcional: `BORRADOR`, `ENVIADA`, `CONFIRMADA`, `RECHAZADA`, `CANCELADA`) |
| Comportamiento | Devuelve solo solicitudes del tenant; `estado` inválido se ignora o responde `400` |
| Orden | `fecha` descendente, `id` descendente |
| Paginación | 50 filas por página |
| Respuesta | `200` con ID, fecha, técnico, NIF, estado, totales y enlace al detalle |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

- El listado no muestra solicitudes de otro tenant ni datos de stock del técnico.
- Los totales (`total_lineas`, `total_series`, `total_cantidad`) se calculan en la consulta.

### `GET /asignaciones/nueva/`

Formulario de alta.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Respuesta | `200` con el formulario, fecha inicial hoy y una línea vacía |
| Contenido | Técnico (solo activos del tenant), fecha, líneas con material, tipo y lote de solo lectura, selector de series para seriados o cantidad para no seriados, botones "Guardar borrador" y "Enviar" |
| Alerta de cupo | Si algún equipo en custodia supera 20 días, se muestra un aviso no intrusivo; no deshabilita "Enviar" |
| Técnico y NIF | El selector muestra NIF y nombre; el NIF se muestra de solo lectura y no se envía como campo editable |
| Materiales | El selector usa `GET /materiales/buscar/?q=` de 002 y copia `data-lote`, `data-tipo` y `data-descripcion` |
| Campos ausentes | El formulario no incluye `tenant`, `region`, `almacen`, `nif` ni `estado` |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

- El botón Guardar usa `hx-disabled-elt` para evitar doble envío; el servidor revalida siempre.
- El selector de series es `GET /asignaciones/series-disponibles/` y no escribe.

### `POST /asignaciones/nueva/`

Crea un borrador o crea y envía, según la acción elegida.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | `accion` (`borrador` o `enviar`), `tecnico_id`, `fecha`, `lineas-TOTAL_FORMS`, `lineas-INITIAL_FORMS`, `lineas-MIN_NUM_FORMS`, `lineas-MAX_NUM_FORMS`, `lineas-<n>-material_id`, `lineas-<n>-serie_ids`, `lineas-<n>-cantidad`, `csrfmiddlewaretoken` |
| Campos no aceptados | `tenant`, `tenant_id`, `region`, `region_id`, `almacen`, `almacen_id`, `nif`, `estado`, `excel_ruta`, `excel_hash`; se ignoran y el alcance sale de la sesión |
| Éxito `borrador` | `302` al detalle; solicitud `BORRADOR`; sin reserva ni Excel |
| Éxito `enviar` | `302` al detalle; solicitud `ENVIADA`; series `RESERVADA`; Excel generado; auditoría en la misma transacción |
| Sin líneas | `400` "La solicitud debe tener al menos una línea" |
| Fecha ausente o inválida | `400` "La fecha es obligatoria" / "La fecha no es válida" |
| Técnico inexistente, ajeno o inactivo | `400` "El técnico no existe en este tenant" / "El técnico está desactivado" |
| Material inexistente | `400` "El material no existe en el catálogo" |
| Seriado sin series | `400` "Debe indicar al menos una serie" |
| No seriado con series | `400` "El material no es seriado y no admite series" |
| Serie repetida | `400` "La serie está duplicada en la solicitud" |
| Serie no disponible o ajena | `400` "La serie no está disponible" |
| Cantidad no entera | `400` "La cantidad debe ser un número entero" |
| Cantidad `<= 0` | `400` "La cantidad debe ser mayor a 0" |
| Cantidad sobre el disponible | `400` "La cantidad supera el stock disponible" |
| Acción inválida | `400` "La acción no es válida" |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

- Un `POST` con `accion=enviar` es la operación crear-y-enviar que cubre CA-01.
- Si el envío falla, no queda ni borrador ni archivo; la transacción es única.
- Los errores se muestran junto a la línea que los origina y en un resumen general.
- El NIF nunca se toma del formulario; se copia de `Tecnico.nif`.

### `GET /asignaciones/<int:solicitud_id>/`

Detalle de una solicitud.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Alcance | Solo solicitudes del tenant de la sesión |
| Respuesta | `200` con ID, técnico, NIF, fecha, estado, líneas agrupadas, totales, ruta y hash del Excel |
| Confirmada | Si está `CONFIRMADA`, muestra días en mano por serie y la alerta de cupo si aplica |
| Borrador | Muestra "Enviar" y "Cancelar"; no muestra Excel porque no existe |
| Enviada | Muestra el hash y el enlace de descarga de 007 si esa feature está implementada; 006 no expone la descarga |
| Inexistente o ajena | `404` "La solicitud no existe" |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

### `POST /asignaciones/<int:solicitud_id>/enviar/`

Envía un borrador.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | Solo `csrfmiddlewaretoken` |
| Éxito | `302` al detalle; `BORRADOR`→`ENVIADA`; series `RESERVADA`; Excel generado y auditado |
| Estado distinto | `409` "Solo se pueden enviar solicitudes en borrador" |
| Revalidación | Disponibilidad y series se recalculan dentro de la transacción con bloqueo |
| Inexistente o ajena | `404` "La solicitud no existe" |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

- Reenviar una solicitud ya `ENVIADA`, `CONFIRMADA`, `RECHAZADA` o `CANCELADA` responde `409`.
- Un envío fallido no deja series reservadas ni archivo.

### `POST /asignaciones/<int:solicitud_id>/cancelar/`

Cancela un borrador.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | Solo `csrfmiddlewaretoken` |
| Éxito | `302` al detalle; `BORRADOR`→`CANCELADA`; auditoría en la misma transacción |
| Estado distinto | `409` "Solo se pueden cancelar solicitudes en borrador" |
| Efecto sobre series y cantidades | Ninguno: el borrador no reservó |
| Inexistente o ajena | `404` "La solicitud no existe" |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

### `GET /asignaciones/series-disponibles/`

Fragmento HTMX del selector de series. Contrato detallado en `contracts/selector-series.md`.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Parámetros | `material_id`, `q` (opcional), `page` (opcional), `excluir` (opcional, ids separados por coma) |
| Respuesta | `200` `text/html` con series `DISPONIBLE` del tenant y material; 20 por página |
| Material inexistente o no seriado | `400` "El material no existe en el catálogo" / "El material no es seriado" |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Otros métodos | `405` |

### `POST /asignaciones/validar-disponibilidad/`

Fragmento HTMX de disponibilidad y alerta. Contrato detallado en
`contracts/validacion-disponibilidad.md`.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | `tecnico_id`, `lineas-TOTAL_FORMS`, `lineas-<n>-material_id`, `lineas-<n>-cantidad`, `csrfmiddlewaretoken` |
| Respuesta | `200` `text/html` con `data-valido`, `data-disponible`, `data-alerta-cupo` y errores por línea |
| Escritura | Ninguna; no crea, no reserva, no modifica stock |
| Errores de formato | `400` con el mensaje correspondiente |
| Rol incorrecto | `403` "No tienes permiso para crear asignaciones" |
| Otros métodos | `405` |
