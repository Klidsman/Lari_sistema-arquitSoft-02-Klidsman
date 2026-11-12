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
| `GET/POST /materiales/nuevo/` | Sí | Sí | Sí |
| `GET /materiales/<id>/editar/` | Sí | Sí | Sí |
| `POST /materiales/<id>/editar/` | Sí | Solo si es creador | Solo si es creador |

- Crear está permitido a cualquier cuenta autenticada y activa.
- Editar descripción y lote está permitido al creador o a `ADMIN`.

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
| Petición (`POST`) | `codigo`, `descripcion`, `lote` (opcional), `tipo` (`SERIADO`/`NO_SERIADO`), `csrfmiddlewaretoken` |
| Éxito | `302` al listado o al detalle; material creado; auditoría `alta` |
| Código inválido (10/12 dígitos, letras, espacios o guiones internos) | `400` `"El código debe tener 11 dígitos"` |
| Código duplicado | `409` `"El material ya existe"` |
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
| No es creador ni `ADMIN` | `403` `"No tienes permiso para editar este material"` |
| Intento de enviar `codigo` | `400` `"El código no se puede cambiar"` |
| Descripción vacía o solo espacios | `400` `"La descripción es obligatoria"` |
| Lote > 50 caracteres | `400` `"El lote no puede superar los 50 caracteres"` |
| Cambio de tipo con stock o movimientos | `400` `"El tipo no se puede cambiar: el material tiene movimientos"` |
| `DELETE` u otro método | `405`; no existe ruta de borrado |

## Reglas transversales verificadas en el servidor

1. Ninguna ruta acepta `tenant_id` ni `region_id`; el catálogo es global.
2. El código no se puede cambiar por ninguna vía; el formulario de edición no lo incluye y el
   servicio rechaza la clave si se fuerza.
3. El mensaje de duplicado es uniforme y no indica qué cuenta ni tenant creó el material.
4. Toda alta y todo cambio de descripción, lote o tipo deja auditoría en la misma transacción.
5. Un material no se elimina por ninguna ruta; `DELETE` responde `405`.
6. La verificación de creador/administrador se repite en el servicio, no solo en la vista.
7. El fragmento de búsqueda nunca devuelve datos de stock ni de tenants, solo los campos del
   material definidos en su contrato.
