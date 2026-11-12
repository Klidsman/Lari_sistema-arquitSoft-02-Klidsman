# Contrato HTTP: recojos

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/004-recojo-de-materiales/spec.md`

Aplicación server-rendered con HTMX. Todas las rutas comparten cookie de sesión, CSRF, el
middleware de contexto y la autenticación de la spec 001. Los errores de negocio se devuelven como
HTML parcial (HTMX) o página completa, con el mensaje exacto indicado. Los permisos se validan en
el servidor; ocultar un control no es una autorización.

## Convenciones

- **Autenticación**: cookie de sesión de Django. Una sesión `pendiente_2fa` no accede a estas
  rutas (se redirige a `/login/2fa/`).
- **Roles**: `ADMIN` = Administrador de plataforma; `TENANT` = cuenta del tenant;
  `ALMACEN` = Responsable de almacén.
- **CSRF**: obligatorio en todo `POST`.
- **Tenant**: se obtiene de la sesión (`request.tenant`/`actor.tenant`). Ninguna ruta acepta ni usa
  `tenant_id`, `region_id`, `almacen_id` ni equivalentes del cliente.
- **Formato de error**: HTML con el texto indicado; en peticiones HTMX, un fragmento con el mismo
  texto y el código de estado correspondiente.
- **Códigos**: `200` lectura o vista previa; `302` redirección tras `POST` exitoso; `400`
  validación; `401` sin sesión; `403` rol no autorizado o tenant suspendido; `404` recojo o
  material inexistente; `405` método no permitido (incluye `DELETE`); `409` conflicto de serie
  existente detectado en la base durante el guardado.
- **Fechas**: `fecha` en formato ISO `YYYY-MM-DD`.
- **Sin edición ni borrado**: no existen rutas `PUT`, `PATCH` ni `DELETE`; los métodos no
  permitidos responden `405`.

## Matriz de permisos

| Ruta | ADMIN | TENANT | ALMACEN |
|---|---|---|---|
| `GET /recojos/` | No (`403`) | Sí | No (`403`) |
| `GET /recojos/nuevo/` | No (`403`) | Sí | No (`403`) |
| `POST /recojos/nuevo/` | No (`403`) | Sí | No (`403`) |
| `GET /recojos/<id>/` | No (`403`) | Sí (solo su tenant) | No (`403`) |
| `POST /recojos/validar-series/` | No (`403`) | Sí | No (`403`) |

- El Administrador de plataforma no registra ni consulta recojos; su consulta es la auditoría
  administrativa de 001.
- El Responsable de almacén no registra ni consulta recojos.
- La autorización se revalida en el servicio; forzar la URL o el `POST` no cambia el resultado.
- Si el tenant está suspendido, la cuenta recibe `403` "El tenant está suspendido".

## Rutas

### `GET /recojos/`

Listado paginado de los recojos del tenant de la sesión.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Parámetros | `page` (opcional) |
| Comportamiento | Devuelve todos los recojos del tenant, sin filtros de fecha |
| Orden | `fecha` descendente, `id` descendente |
| Paginación | 50 filas por página |
| Respuesta | `200` con identificador, fecha, número de líneas, total de series, total de cantidad y enlace al detalle |
| Sesión ausente | `401` o redirección a `/login/` |
| Rol incorrecto | `403` "No tienes permiso para registrar recojos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

- El listado no muestra recojos de otro tenant ni datos de stock por técnico.
- Los totales se calculan en la consulta; no se expone información de otros tenants.

### `GET /recojos/nuevo/`

Formulario de alta de recojo.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Respuesta | `200` con el formulario, fecha inicial hoy y una línea vacía |
| Contenido | Fecha; líneas con selector de material, tipo y lote de solo lectura, series para seriados o cantidad para no seriados; botón Agregar línea; vista previa HTMX |
| Roles incorrectos | `403` "No tienes permiso para registrar recojos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

- El selector de material usa `GET /materiales/buscar/?q=` de la spec 002 y copia `data-lote` y
  `data-tipo`; el usuario no puede editar el tipo ni el lote.
- El formulario no incluye campos de tenant, región ni almacén.
- El botón Guardar usa `hx-disabled-elt` para evitar el doble envío; el servidor revalida siempre.

### `POST /recojos/nuevo/`

Registra un recojo completo o no registra ninguno.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | `fecha`, `lineas-TOTAL_FORMS`, `lineas-INITIAL_FORMS`, `lineas-MIN_NUM_FORMS`, `lineas-MAX_NUM_FORMS`, `lineas-<n>-material_id`, `lineas-<n>-series`, `lineas-<n>-cantidad`, `csrfmiddlewaretoken` |
| Campos no aceptados | `tenant`, `tenant_id`, `region`, `region_id`, `almacen`, `almacen_id`; se ignoran y el alcance sale de la sesión |
| Éxito | `302` al detalle `/recojos/<id>/`; recojo, líneas y series creados; stock incrementado; auditoría en la misma transacción |
| Sin líneas | `400` "El recojo debe tener al menos una línea" |
| Fecha ausente o inválida | `400` "La fecha es obligatoria" / "La fecha no es válida" |
| Material inexistente | `400` "El material no existe en el catálogo" |
| Seriado sin series | `400` "Debe indicar al menos una serie" |
| Serie con formato inválido | `400` "La serie debe tener 12 caracteres alfanuméricos" |
| Serie duplicada en el mismo recojo | `400` "La serie está duplicada en el recojo" |
| Serie ya existente en el sistema | `400` "La serie ya está registrada en el sistema" |
| Conflicto de unicidad detectado en la base | `409` "La serie ya está registrada en el sistema" |
| Cantidad no seriada <= 0 | `400` "La cantidad debe ser mayor a 0" |
| Cantidad distinta de 1 en seriado | `400` "Para un material seriado la cantidad debe ser 1" |
| Series en material no seriado | `400` "Un material no seriado no admite series" |
| Error de stock | `400` "No se guardó el recojo; corrige los errores"; no queda nada escrito |
| Rol incorrecto | `403` "No tienes permiso para registrar recojos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Región sin almacén | `400` "La región del tenant no tiene almacén configurado" |
| `PUT`/`PATCH`/`DELETE` | `405`; la ruta solo acepta `GET` y `POST` |

- La respuesta `400` vuelve a mostrar el formulario con los valores ingresados y los estados por
  serie; no se guarda nada.
- La vista previa no es autoridad: el `POST` revalida formato, duplicados y existencia.
- El mensaje de serie existente es uniforme y no revela el tenant, la región ni el recojo de
  origen.
- El alta siempre usa la región del tenant; forzar `region_id` no cambia el recojo.
- El recojo es inmutable después del alta; no hay ruta de edición ni de borrado.

### `GET /recojos/<id>/`

Detalle y confirmación del recojo.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Respuesta | `200` con identificador, fecha, tenant, región, total de series, total de cantidad y líneas con material, descripción, lote, serie o cantidad |
| Recojo de otro tenant | `404` "El recojo no existe" |
| Recojo inexistente | `404` "El recojo no existe" |
| Rol incorrecto | `403` "No tienes permiso para registrar recojos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Otros métodos | `405` |

- No se muestran datos de otros tenants, de stock por técnico ni de asignaciones.
- El detalle es la confirmación de salida descrita en la spec: ID, fecha, tenant, región, total de
  series y total de cantidad.
- La página no ofrece editar ni borrar.

### `POST /recojos/validar-series/`

Vista previa en tiempo real de las series de una línea seriada. El detalle del fragmento está en
`contracts/validacion-series.md`.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | `material_id`, `series` (texto con una serie por línea), `csrfmiddlewaretoken` |
| Respuesta | `200` con fragmento HTML de filas `data-serie` y `data-estado` |
| Estados | `valida`, `invalida`, `duplicada`, `ya_existe` |
| Series vacías | `200` con el estado vacío "No se ingresaron series" |
| Material inexistente | `404` "El material no existe en el catálogo" |
| Material no seriado | `400` "El material no es seriado; indique la cantidad" |
| Rol incorrecto | `403` "No tienes permiso para registrar recojos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| Método distinto de `POST` | `405` |

- El endpoint no escribe en la base de datos.
- No revela tenant, región ni recojo de origen de una serie existente.
- La respuesta no incluye datos de stock, de otros tenants ni del creador.
- El formulario solo invoca este endpoint para materiales seriados.

## Reglas transversales verificadas en el servidor

1. Ninguna ruta acepta `tenant_id`, `region_id` ni `almacen_id`; el tenant y la región salen de la
   sesión.
2. Un recojo de otro tenant se trata como inexistente (`404`), sin revelar su existencia ni su
   propietario.
3. La región del recojo y de cada serie se fija desde `tenant.region`; no se puede cambiar por
   ninguna vía.
4. Toda serie se normaliza antes de validar y de escribir; el formato de 12 caracteres se impone
   también en la base.
5. La unicidad de serie es global y se impone en la base; el mensaje es uniforme.
6. Todo recojo se guarda completo o no se guarda; cualquier error revierte líneas, series, stock y
   auditoría.
7. El alta del recojo y los incrementos de stock dejan auditoría en la misma transacción; no se
   auditan secretos.
8. Un recojo no se edita ni se borra; `DELETE` responde `405`.
9. El listado y el detalle solo muestran recojos del tenant de la sesión.
10. El tipo de un material con recojos o stock no se puede cambiar; 004 registra la verificación de
    movimientos en 002.

## Pruebas de contrato asociadas

- Alta válida de un recojo seriado: `302`, detalle con totales, stock incrementado y auditoría.
- Alta válida de un recojo no seriado: `302`, cantidad sumada al stock y sin series.
- Sin líneas: `400` "El recojo debe tener al menos una línea".
- Fecha ausente o inválida: `400` con el mensaje correspondiente.
- Serie con formato inválido, duplicada en el recojo o ya existente: `400` con el mensaje exacto y
  sin escritura.
- Serie existente detectada en la base por concurrencia: `409` con el mensaje uniforme.
- Material inexistente, no seriado con series o seriado con cantidad distinta de 1: `400`.
- Recojo de otro tenant: `404` "El recojo no existe".
- `ADMIN` y `ALMACEN`: `403` en las cuatro rutas.
- Tenant suspendido: `403` "El tenant está suspendido".
- `DELETE` en cualquier ruta: `405`.
- Vista previa: `200` con estados, sin escritura y sin datos de tenant.
- Listado: 50 filas por página, orden por fecha e identificador, solo recojos del tenant.
- Detalle: muestra región y totales; no muestra datos de otro tenant.
