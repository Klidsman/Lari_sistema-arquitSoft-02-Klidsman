# Contrato HTTP: materiales

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/002-materiales/spec.md`

Aplicación server-rendered con HTMX. Todas las rutas comparten cookie de sesión, CSRF, el
middleware de contexto y la autenticación de la spec 001. Los errores de negocio se devuelven
como HTML parcial (HTMX) o página completa, con el mensaje exacto indicado. Los permisos se
validan en el servidor; ocultar un control no es una autorización.

## Convenciones

- **Autenticación**: cookie de sesión de Django. Una sesión `pendiente_2fa` no accede a estas
  rutas (se redirige a `/login/2fa/`).
- **Roles**: `ADMIN` = Administrador de plataforma; `TENANT` = cuenta del tenant;
  `ALMACEN` = Responsable de almacén.
- **CSRF**: obligatorio en todo `POST`.
- **Catálogo**: global; ninguna ruta acepta ni usa `tenant_id`/`region_id`.
- **Formato de error**: HTML con el texto indicado; en peticiones HTMX, un fragmento con el
  mismo texto y el código de estado correspondiente.
- **Códigos**: `200` lectura; `302` redirección tras `POST` exitoso; `400` validación; `401`
  sin sesión; `403` sin permiso; `404` material inexistente; `405` método no permitido
  (incluye `DELETE`); `409` código duplicado.

## Matriz de permisos

| Ruta | ADMIN | TENANT | ALMACEN |
|---|---|---|---|
| `GET /materiales/` | Sí | Sí | Sí |
| `GET /materiales/buscar/` | Sí | Sí | Sí |
| `GET/POST /materiales/nuevo/` | No | No | Sí |
| `GET /materiales/<id>/editar/` | Sí | Sí | Sí |
| `POST /materiales/<id>/editar/` | Sí | No | Sí (cualquier material activo) |
| `POST /materiales/<id>/baja/` | No | No | Sí |

- Crear y dar de baja está permitido únicamente al Responsable de almacén
  (`RESPONSABLE_ALMACEN`), con cuenta activa.
- Cualquier Responsable de almacén puede dar de baja cualquier material, aunque lo haya
  creado otra cuenta.
- Editar descripción y lote está permitido a cualquier Responsable de almacén activo o a
  `ADMIN`. La cuenta de tenant no edita materiales.

## Rutas

### `GET /materiales/`

Listado paginado del catálogo.

| Aspecto | Contrato |
|---|---|
| Acceso | Cualquier cuenta autenticada y activa |
| Parámetros | `q` (opcional), `page` (opcional) |
| Comportamiento | Sin `q` devuelve el catálogo completo; con `q` filtra por código **o** descripción (`icontains`); orden por `codigo` |
| Paginación | 50 filas por página |
| Respuesta | `200` con código, descripción, lote, tipo, creador y fecha |
| Sesión ausente | `401` o redirección a `/login/` |

### `GET /materiales/buscar/?q=&limit=`

Fragmento HTMX de autocompletado consumido por las specs 004, 005, 006, 009 y 013. El detalle
de la respuesta está en `contracts/busqueda-materiales.md`.

| Aspecto | Contrato |
|---|---|
| Acceso | Cualquier cuenta autenticada y activa |
| Parámetros | `q` (opcional), `limit` (opcional, por defecto 20, máximo 50) |
| Respuesta | `200` con fragmento HTML de filas `data-*` |
| Catálogo vacío o sin coincidencias | `200` con el estado vacío explícito |
| Sesión ausente | `401` o redirección a `/login/` |

### `GET/POST /materiales/nuevo/`

Alta de material.

| Aspecto | Contrato |
|---|---|
| Acceso | Cualquier cuenta autenticada y activa |
| Acceso | Solo Responsable de almacén activo |
| Petición (`POST`) | `codigo`, `descripcion`, `lote` (opcional), `tipo` (`SERIADO`/`NO_SERIADO`), `csrfmiddlewaretoken` |
| Éxito | `302` al listado o al detalle; material creado; auditoría `alta` |
| Rol distinto de almacén | `403` `"Solo el Responsable de almacén puede registrar materiales"` |
| Código inválido (10/12 dígitos, letras, espacios o guiones internos) | `400` `"El código debe tener 11 dígitos"` |
| Código de un material activo | `409` `"El material ya existe"` |
| Código de un material dado de baja | `302`; reactiva la misma fila con los nuevos datos y audita la reactivación |
| Descripción vacía o solo espacios | `400` `"La descripción es obligatoria"` |
| Descripción > 100 caracteres | `400` `"La descripción no puede superar los 100 caracteres"` |
| Lote > 50 caracteres | `400` `"El lote no puede superar los 50 caracteres"` |
| Tipo ausente o inválido | `400` `"El tipo es obligatorio"` |
| Doble envío | La segunda petición responde `409` `"El material ya existe"`; no crea duplicado |
| `DELETE` u otro método | `405` |

### `GET/POST /materiales/<id>/editar/`

Edición de descripción, lote y, cuando la regla lo permita, tipo. El código nunca se edita.

| Aspecto | Contrato |
|---|---|
| Acceso | Creador del material o `ADMIN` |
| Petición (`POST`) | `descripcion`, `lote`, `tipo` opcional; `csrfmiddlewaretoken` |
| Éxito | `302` al listado; cambios y auditoría por campo en la misma transacción |
| Material inexistente | `404` |
| Cuenta de tenant | `403` `"No tienes permiso para editar este material"` |
| Intento de enviar `codigo` | `400` `"El código no se puede cambiar"` |
| Descripción vacía o solo espacios | `400` `"La descripción es obligatoria"` |
| Lote > 50 caracteres | `400` `"El lote no puede superar los 50 caracteres"` |
| Cambio de tipo con stock o movimientos | `400` `"El tipo no se puede cambiar: el material tiene movimientos"` |
| `DELETE` u otro método | `405`; no existe ruta de borrado |

### `POST /materiales/<id>/baja/`

Baja lógica del material. No borra la fila ni su auditoría.

| Aspecto | Contrato |
|---|---|
| Acceso | Responsable de almacén activo |
| Petición | `csrfmiddlewaretoken` |
| Éxito | `302` al listado; `activo=False`; el material deja de aparecer en listados y búsquedas; auditoría `activo` `True` → `False` |
| Cualquier almacén | Puede dar de baja un material creado por otra cuenta |
| Rol distinto de almacén | `403` `"Solo el Responsable de almacén puede dar de baja materiales"` |
| Material ya dado de baja | `200` sin cambios ni auditoría nueva |
| Material inexistente | `404` |
| `DELETE` u otro método | `405` |

## Reglas transversales verificadas en el servidor

1. Ninguna ruta acepta `tenant_id` ni `region_id`; el catálogo es global.
2. El código no se puede cambiar por ninguna vía; el formulario de edición no lo incluye y el
   servicio rechaza la clave si se fuerza.
3. El mensaje de duplicado es uniforme y no indica qué cuenta ni tenant creó el material.
4. Toda alta y todo cambio de descripción, lote o tipo deja auditoría en la misma transacción.
5. Un material no se borra físicamente: la baja es lógica (`activo=False`), conserva la fila y
   su auditoría, y `DELETE` responde `405`.
6. La verificación de creador/administrador se repite en el servicio, no solo en la vista.
7. El fragmento de búsqueda nunca devuelve datos de stock ni de tenants, solo los campos del
   material definidos en su contrato, y solo incluye materiales activos.
8. Solo el Responsable de almacén crea y da de baja materiales; el servicio lo revalida aunque
   se fuerce la petición.
