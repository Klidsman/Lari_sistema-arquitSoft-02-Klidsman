# Contrato HTTP: 007 Envío y Revisión del Almacén

Rutas expuestas por `asignaciones/urls.py` bajo el prefijo `/almacen/`. Todas usan cookie de sesión
de Django, CSRF en `POST`, plantillas HTML y HTMX. No existe API REST ni respuesta JSON.

## Reglas generales

- **Autenticación**: `@login_required`; sin sesión, `302` a `/acceso/login/?next=...`.
- **Roles**:
  - `RESPONSABLE_ALMACEN`: bandeja, detalle, previsualización, confirmar, rechazar, descargar,
    históricos de su región y SSE.
  - `ADMIN_PLATAFORMA`: solo `/almacen/excels-historicos/` y su descarga, con alcance global.
  - `USUARIO_TENANT`: `403` en todas las rutas de `/almacen/`.
- **Aislamiento**: la región sale de `request.usuario.region`. Nunca se acepta `region_id`,
  `tenant_id`, `destinatario`, `hash` ni `estado` del cliente. Solicitud de otra región o
  inexistente: `404` con "La solicitud no existe".
- **Métodos**: método no permitido en una ruta existente responde `405`.
- **CSRF**: ausente o inválido en `POST` responde `403`.
- **Estados**: `409` para estado incorrecto o hash alterado; `400` para motivo inválido.
- **Contenido**: HTML `text/html; charset=utf-8`; descargas
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; SSE `text/event-stream`.
- **Mensajes exactos**:
  - "No tienes permiso para gestionar despachos"
  - "La solicitud no existe"
  - "Solo se pueden confirmar solicitudes enviadas"
  - "Solo se pueden rechazar solicitudes enviadas"
  - "Debe indicar el motivo del rechazo"
  - "El motivo del rechazo no puede superar los 1000 caracteres"
  - "El archivo fue modificado, descarga bloqueada"

## Rutas

| Ruta | Método | Rol | Éxito |
|---|---|---|---|
| `/almacen/bandeja/` | GET | Almacén | `200` HTML |
| `/almacen/solicitudes/<int:id>/` | GET | Almacén | `200` HTML |
| `/almacen/solicitudes/<int:id>/previsualizar/` | GET | Almacén | `200` fragmento HTML |
| `/almacen/solicitudes/<int:id>/confirmar/` | POST | Almacén | `302` a `/almacen/solicitudes/<id>/` |
| `/almacen/solicitudes/<int:id>/rechazar/` | POST | Almacén | `302` a `/almacen/solicitudes/<id>/` |
| `/almacen/solicitudes/<int:id>/descargar-excel/` | GET | Almacén | `200` `.xlsx` |
| `/almacen/excels-historicos/` | GET | Almacén / Admin | `200` HTML |
| `/almacen/excels-historicos/<int:id>/descargar/` | GET | Almacén / Admin | `200` `.xlsx` |
| `/almacen/notificaciones/sse/` | GET | Almacén | `200` `text/event-stream` |
| `/almacen/notificaciones/pendientes/` | GET | Almacén | `200` fragmento HTML |

## `GET /almacen/bandeja/`

**Parámetros**: `estado` opcional en `ENVIADA`, `CONFIRMADA`, `RECHAZADA`; `page` opcional.

**Respuesta `200`**:

- Tabla con una fila por solicitud: `data-solicitud-id`, fecha de envío, tenant, técnico,
  `data-total-series`, `data-total-cantidad`, estado y acciones.
- Filtro por estado y paginación de 50.
- Badge `data-pendientes` con el número de `ENVIADA`.
- Contenedor `data-sse-url="/almacen/notificaciones/sse/"` y
  `data-poll-url="/almacen/notificaciones/pendientes/"`.
- No muestra `BORRADOR` ni `CANCELADA`; no incluye datos de otra región.

**Errores**: `403` si el rol no es `RESPONSABLE_ALMACEN`; `302` sin sesión; `405` para `POST`,
`PUT`, `PATCH` o `DELETE`.

## `GET /almacen/solicitudes/<id>/`

**Respuesta `200`**:

- Cabecera: ID, fecha, tenant, técnico, NIF, estado, región.
- Líneas agrupadas por material, con serie o cantidad y lote.
- Totales de series y cantidades.
- Hash SHA-256, enlace de descarga y último intento de envío (estado y fecha).
- Si `RECHAZADA`: `motivo_rechazo` y `rechazada_en`.
- Si `ENVIADA`: botones "Confirmar" y "Rechazar".
- Si `CONFIRMADA`: `confirmada_en`.
- Nunca muestra el enlace de edición ni de cancelación del tenant.

**Errores**: `404` por solicitud ajena, inexistente o en `BORRADOR`/`CANCELADA`; `403` por rol;
`405` para métodos de escritura.

## `GET /almacen/solicitudes/<id>/previsualizar/`

**Respuesta `200`**: fragmento HTML con el mismo contenido del detalle, sin `<html>` ni
navegación, apto para un modal HTMX. Incluye `data-solicitud-id`, líneas, totales y hash.

**Errores**: los mismos que el detalle.

## `POST /almacen/solicitudes/<id>/confirmar/`

**Cuerpo**: vacío o `csrfmiddlewaretoken`. Se ignoran `tenant_id`, `region_id`, `estado` y
cualquier otro campo forzado.

**Respuesta `302`**: redirección al detalle. Efectos:

- `estado` pasa de `ENVIADA` a `CONFIRMADA`.
- `confirmada_en` se fija.
- 008 cambia series `RESERVADA→ASIGNADA` y actualiza stock en la misma transacción.

**Errores**:

- `409` "Solo se pueden confirmar solicitudes enviadas" si el estado no es `ENVIADA`.
- `404` si la solicitud no existe o es de otra región.
- `403` si el rol no es `RESPONSABLE_ALMACEN`, la cuenta está inactiva o la región no está activa.
- `405` para `GET`, `PUT`, `PATCH` o `DELETE`.
- Si 008 falla por stock insuficiente, `409` con el mensaje de 008 y sin cambios persistidos.

## `POST /almacen/solicitudes/<id>/rechazar/`

**Cuerpo**: `motivo` obligatorio (máximo 1000 caracteres) y `csrfmiddlewaretoken`.

**Respuesta `302`**: redirección al detalle. Efectos:

- `estado` pasa de `ENVIADA` a `RECHAZADA`.
- `motivo_rechazo` y `rechazada_en` se guardan.
- Cada serie de las líneas seriadas pasa de `RESERVADA` a `DISPONIBLE`.
- El tenant recibe el aviso en el detalle de 006 y un correo best-effort.

**Errores**:

- `400` "Debe indicar el motivo del rechazo" si el motivo está vacío o solo tiene espacios.
- `400` "El motivo del rechazo no puede superar los 1000 caracteres" si excede el límite.
- `409` "Solo se pueden rechazar solicitudes enviadas" si el estado no es `ENVIADA`.
- `404`, `403` y `405` como en la confirmación.
- Un fallo de correo al tenant **no** revierte el rechazo.

## `GET /almacen/solicitudes/<id>/descargar-excel/`

**Respuesta `200`**: archivo `.xlsx` con `Content-Disposition: attachment; filename="asignacion-<id>.xlsx"`.

- Verifica que la ruta esté dentro de `MEDIA_ROOT` y que el SHA-256 del archivo coincida con
  `solicitud.excel_hash`.

**Errores**: `404` si la solicitud no tiene Excel o está fuera de alcance; `409` si el hash no
coincide; `403`/`405` según las reglas generales.

## `GET /almacen/excels-historicos/`

**Parámetros**: `fecha_desde`, `fecha_hasta` (`YYYY-MM-DD`), `tenant` (id validado), `tecnico` (id
validado), `estado`, `page`.

**Respuesta `200`**:

- Tabla de solicitudes con Excel: ID, fecha, tenant, técnico, estado, `hash_sha256`, estado del
  último envío y acción de descarga.
- Solo solicitudes con `excel_ruta` no vacía.
- Almacén: solo su región. Admin: todas las regiones.
- Paginación de 50; filtros inválidos se ignoran o responden `400` sin romper la vista.

**Errores**: `403` para `USUARIO_TENANT`; `302` sin sesión; `405` para métodos de escritura.

## `GET /almacen/excels-historicos/<id>/descargar/`

Mismo contrato de descarga y verificación que
`/almacen/solicitudes/<id>/descargar-excel/`, con el alcance de la búsqueda histórica. `404` si la
solicitud no tiene Excel o está fuera de alcance; `409` si el hash no coincide.

## `GET /almacen/notificaciones/pendientes/`

**Respuesta `200`**: fragmento HTML con `data-pendientes`, `data-ultima-solicitud-id` y el enlace a
la bandeja. Se consulta cada 30 s si SSE no está disponible.

**Errores**: `403` por rol; `302` sin sesión; `405` para métodos de escritura.

## Matriz de permisos

| Ruta | Almacén | Admin | Tenant | Anónimo |
|---|---|---|---|---|
| `/almacen/bandeja/` | `200` | `403` | `403` | `302` |
| `/almacen/solicitudes/<id>/` | `200`/`404` | `403` | `403` | `302` |
| `/almacen/solicitudes/<id>/previsualizar/` | `200`/`404` | `403` | `403` | `302` |
| `/almacen/solicitudes/<id>/confirmar/` | `302`/`404`/`409` | `403` | `403` | `302` |
| `/almacen/solicitudes/<id>/rechazar/` | `302`/`400`/`404`/`409` | `403` | `403` | `302` |
| `/almacen/solicitudes/<id>/descargar-excel/` | `200`/`404`/`409` | `403` | `403` | `302` |
| `/almacen/excels-historicos/` | `200` | `200` | `403` | `302` |
| `/almacen/excels-historicos/<id>/descargar/` | `200`/`404`/`409` | `200`/`404`/`409` | `403` | `302` |
| `/almacen/notificaciones/sse/` | `200` | `403` | `403` | `302` |
| `/almacen/notificaciones/pendientes/` | `200` | `403` | `403` | `302` |
