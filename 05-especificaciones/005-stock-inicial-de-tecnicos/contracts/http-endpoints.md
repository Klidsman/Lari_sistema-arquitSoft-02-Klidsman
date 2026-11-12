# Contrato HTTP: 005 Stock Inicial de Técnicos

**Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/005-stock-inicial-de-tecnicos/spec.md`

Este contrato define las rutas, permisos, peticiones, respuestas y errores de la interfaz web de
stock inicial. La interfaz es Django + HTMX; no hay API REST ni JSON.

## 1. Reglas comunes

- **Autenticación**: todas las rutas exigen sesión iniciada. Si no hay sesión, redirección `302` al
  login.
- **Rol**: solo `USUARIO_TENANT` activo. `ADMIN_PLATAFORMA` y `RESPONSABLE_ALMACEN` reciben `403`.
- **Tenant**: se obtiene de `request.usuario.tenant`. Si el tenant está `SUSPENDIDO`, `403`. Nunca se
  acepta `tenant_id`, `region_id` ni `almacen_id` de la petición.
- **CSRF**: todos los `POST` exigen token CSRF válido; sin él, `403`.
- **Métodos**: las rutas solo aceptan los métodos indicados. Cualquier otro método responde `405`.
- **Contenido**: las respuestas de página son `text/html; charset=utf-8`; las de validación previa
  son fragmentos HTML/HTMX. No se usa JSON.
- **Fechas**: ISO 8601 en auditoría y resúmenes; la interfaz puede mostrarlas en formato local.
- **Aislamiento**: una carga o línea de otro tenant responde `404`, nunca `403`, para no revelar su
  existencia.
- **Errores de negocio**: se renderizan en la misma página o fragmento, con el mensaje exacto de la
  tabla del §8. No se devuelven trazas ni datos internos.
- **Redirección de éxito**: `302` al detalle de la carga recién creada o editada.
- **Sin rutas de borrado**: no existe `DELETE` de la carga ni del stock inicial. `DELETE`, `PUT` y
  `PATCH` responden `405`.

## 2. `GET /stock-inicial/`

**Función**: mostrar el estado del stock inicial del tenant.

**Permisos**: `USUARIO_TENANT` activo; tenant activo.

**Respuesta `200`**:

- Si no está cargado:
  - aviso "El stock inicial se carga una sola vez por tenant";
  - dos opciones: `GET /stock-inicial/` con formulario de Excel y enlace a
    `GET /stock-inicial/formulario/`;
  - no se muestra el detalle ni la edición.
- Si está cargado:
  - fecha y método;
  - totales: técnicos, líneas, series y cantidad;
  - nombre y hash del archivo (si es Excel);
  - enlace a `GET /stock-inicial/<id>/` y a `GET /stock-inicial/<id>/editar/`.

**Errores**:

| Caso | Código | Mensaje |
|---|---|---|
| Sin sesión | `302` | Redirección al login |
| Rol no autorizado | `403` | "No tienes permiso para cargar stock inicial" |
| Tenant suspendido | `403` | "El tenant está suspendido" |
| Método no permitido | `405` | — |

## 3. `POST /stock-inicial/validar-excel/`

**Función**: validar un Excel sin escribir en la base. Devuelve un fragmento HTML/HTMX.

**Permisos**: `USUARIO_TENANT` activo; tenant activo.

**Petición**:

- `Content-Type: multipart/form-data`.
- Campo `archivo`: archivo `.xlsx` obligatorio.
- No se acepta `tenant_id`, `region_id` ni `carga_id`.

**Respuesta `200`**: fragmento `text/html` con:

- `data-valido="true|false"`;
- `data-filas-validas="<n>"`;
- `data-filas-error="<n>"`;
- `data-total-tecnicos="<n>"`;
- `data-total-series="<n>"`;
- `data-total-cantidad="<n>"`;
- una tabla de errores con `data-fila`, `data-campo` y `data-mensaje`;
- un resumen de líneas válidas (técnico, material, lote, serie o cantidad).

El detalle del fragmento está en `contracts/validacion-excel.md`.

**Respuesta `400`**: archivo ausente, no `.xlsx`, ilegible, sin columnas obligatorias o sin filas.
El fragmento contiene el mensaje exacto.

**No escribe**: no crea `CargaStockInicial`, `LineaStockInicial`, `Serie`, `StockTecnico` ni
auditoría.

**Errores**:

| Caso | Código | Mensaje |
|---|---|---|
| Sin archivo | `400` | "Debes seleccionar un archivo Excel" |
| Extensión no `.xlsx` | `400` | "El archivo debe ser un Excel .xlsx" |
| Columna faltante | `400` | "El archivo no tiene la columna obligatoria: {columna}" |
| Sin filas | `400` | "El archivo no contiene filas de datos" |
| Rol no autorizado | `403` | "No tienes permiso para cargar stock inicial" |
| Tenant suspendido | `403` | "El tenant está suspendido" |
| Método no permitido | `405` | — |

## 4. `POST /stock-inicial/cargar-excel/`

**Función**: cargar el stock inicial desde un Excel.

**Permisos**: `USUARIO_TENANT` activo; tenant activo.

**Petición**:

- `Content-Type: multipart/form-data`.
- Campo `archivo`: archivo `.xlsx` obligatorio.
- El archivo se revalida por completo; no se confía en una validación previa.

**Respuesta éxito `302`**: `Location: /stock-inicial/<id>/`.

**Respuesta `400`**: errores de validación. Se vuelve a renderizar el formulario con los errores por
fila y los valores conservados cuando sea posible. No se crea nada.

**Respuesta `409`**: el tenant ya cargó su stock inicial (flag o restricción única) o una serie fue
creada por otra sesión durante el guardado.

**Errores**:

| Caso | Código | Mensaje |
|---|---|---|
| Ya cargado | `409` | "El stock inicial ya fue cargado para este tenant" |
| Serie creada en paralelo | `409` | "La serie ya está registrada en el sistema" |
| Validación de fila | `400` | Mensaje de la tabla del §8 |
| Archivo inválido | `400` | Mensaje de `validar-excel` |
| Rol no autorizado | `403` | "No tienes permiso para cargar stock inicial" |
| Tenant suspendido | `403` | "El tenant está suspendido" |
| Método no permitido | `405` | — |

## 5. `GET /stock-inicial/formulario/`

**Función**: mostrar el formulario de carga con secciones por técnico.

**Permisos**: `USUARIO_TENANT` activo; tenant activo.

**Respuesta `200`**:

- una o más secciones; cada sección tiene:
  - selector de técnico (solo activos del tenant, con búsqueda HTMX);
  - selector de material (catálogo global, con búsqueda HTMX);
  - tipo de material de solo lectura;
  - lote de solo lectura (del catálogo);
  - campo `series` (solo seriados);
  - campo `cantidad` (solo no seriados);
  - botón "Agregar línea" y "Quitar línea";
- botón "Guardar stock inicial";
- aviso de carga única.

**Errores**: `403`, `405` y `302` sin sesión.

## 6. `POST /stock-inicial/formulario/`

**Función**: cargar el stock inicial desde el formulario.

**Permisos**: `USUARIO_TENANT` activo; tenant activo.

**Petición** (`application/x-www-form-urlencoded` o `multipart/form-data`):

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `secciones` | lista de secciones | Sí | Al menos una sección con al menos una línea. |
| `secciones[i].tecnico_id` | entero | Sí | Técnico del tenant. |
| `secciones[i].lineas[j].material_id` | entero | Sí | Material del catálogo. |
| `secciones[i].lineas[j].series` | texto | Condicional | Series separadas por saltos de línea, comas o espacios; solo seriados. |
| `secciones[i].lineas[j].cantidad` | entero | Condicional | Cantidad; solo no seriados. |

- No se aceptan `tenant_id`, `region_id`, `almacen_id`, `carga_id`, `lote`, `descripcion` ni
  `es_seriado`; el tipo y el lote salen del catálogo.
- El formulario se valida con la misma lógica que el Excel.

**Respuesta éxito `302`**: `Location: /stock-inicial/<id>/`.

**Respuesta `400`**: errores de validación; se vuelve a renderizar el formulario con los mensajes y
los valores conservados. No se crea nada.

**Respuesta `409`**: carga ya realizada o serie creada en paralelo.

**Errores**: los mismos mensajes del §8.

## 7. `GET /stock-inicial/<int:carga_id>/`

**Función**: mostrar el detalle de la carga.

**Permisos**: `USUARIO_TENANT` activo; tenant activo.

**Respuesta `200`**:

- fecha, método, región;
- nombre y hash del archivo (si es Excel);
- totales: técnicos, líneas, series y cantidad;
- líneas agrupadas por técnico: NIF, nombre, material, descripción, lote, serie o cantidad;
- enlace a edición.

**Errores**:

| Caso | Código | Mensaje |
|---|---|---|
| Carga inexistente | `404` | "El stock inicial no existe" |
| Carga de otro tenant | `404` | "El stock inicial no existe" |
| Rol no autorizado | `403` | "No tienes permiso para cargar stock inicial" |
| Tenant suspendido | `403` | "El tenant está suspendido" |
| Método no permitido | `405` | — |

## 8. `GET/POST /stock-inicial/<int:carga_id>/editar/`

**Función**: editar el stock inicial en un lote transaccional.

**Permisos**: `USUARIO_TENANT` activo; tenant activo.

**`GET` respuesta `200`**:

- líneas agrupadas por técnico;
- para cada línea existente: `linea_id`, material, lote, serie o cantidad actual, campo
  `cantidad` editable solo para no seriados y casilla `eliminar`;
- formulario para agregar líneas nuevas por técnico;
- botón "Guardar cambios".

**`POST` petición**:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `lineas_existentes[i].linea_id` | entero | Sí | Línea de la carga. |
| `lineas_existentes[i].eliminar` | booleano | No | Marca la línea para eliminar. |
| `lineas_existentes[i].cantidad` | entero | Condicional | Nueva cantidad; solo no seriadas. |
| `lineas_nuevas[j].tecnico_id` | entero | Sí | Técnico del tenant. |
| `lineas_nuevas[j].material_id` | entero | Sí | Material del catálogo. |
| `lineas_nuevas[j].series` | texto | Condicional | Series nuevas; solo seriados. |
| `lineas_nuevas[j].cantidad` | entero | Condicional | Cantidad nueva; solo no seriados. |

- El servidor construye una lista de operaciones `AGREGAR`, `ELIMINAR` y `MODIFICAR` y llama a
  `aplicar_edicion_stock_inicial`.
- No se aceptan cambios de `tecnico`, `material`, `lote` ni `serie` en una línea existente.
- El lote de operaciones se aplica completo o no se aplica.

**Respuesta éxito `302`**: `Location: /stock-inicial/<id>/`.

**Respuesta `400`**: errores de validación del lote; no se aplica ninguna operación.

**Respuesta `409`**:

- el stock inicial no está cargado: "El stock inicial aún no ha sido cargado";
- una serie fue creada en paralelo: "La serie ya está registrada en el sistema".

**Errores**:

| Caso | Código | Mensaje |
|---|---|---|
| Sin carga | `409` | "El stock inicial aún no ha sido cargado" |
| Línea de otra carga | `404` | "La línea no pertenece al stock inicial" |
| Carga de otro tenant | `404` | "El stock inicial no existe" |
| Línea seriada en modificar cantidad | `400` | "La línea no es de un material no seriado" |
| Serie ya no asignada | `400` | "La serie ya no pertenece al stock inicial del técnico" |
| Stock insuficiente | `400` | "El técnico no tiene suficiente stock" |
| Serie nueva duplicada | `400` | "La serie está duplicada en la carga" |
| Serie nueva existente | `409` | "La serie ya está registrada en el sistema" |
| Lote vacío | `400` | "No se enviaron cambios" |
| Rol no autorizado | `403` | "No tienes permiso para editar el stock inicial" |
| Tenant suspendido | `403` | "El tenant está suspendido" |
| Método no permitido | `405` | — |

## 9. Tabla de mensajes exactos

| Mensaje | Uso |
|---|---|
| "El stock inicial ya fue cargado para este tenant" | Segunda carga (`409`). |
| "El stock inicial aún no ha sido cargado" | Edición sin carga (`409`). |
| "No tienes permiso para cargar stock inicial" | Rol no autorizado en carga/consulta (`403`). |
| "No tienes permiso para editar el stock inicial" | Rol no autorizado en edición (`403`). |
| "El tenant está suspendido" | Tenant suspendido (`403`). |
| "El stock inicial no existe" | Carga inexistente o de otro tenant (`404`). |
| "La línea no pertenece al stock inicial" | Línea de otra carga (`404`). |
| "El técnico no existe en este tenant" | NIF no encontrado en el tenant (`400`). |
| "El NIF debe tener el formato LAXXXX" | NIF con formato inválido (`400`). |
| "El material no existe en el catálogo" | Código no encontrado (`400`). |
| "El material es seriado y requiere número de serie" | Seriado sin serie (`400`). |
| "El material no es seriado y no admite número de serie" | No seriado con serie (`400`). |
| "La serie debe tener 12 caracteres alfanuméricos" | Formato inválido (`400`). |
| "La serie está duplicada en la carga" | Duplicado interno (`400`). |
| "La serie ya está registrada en el sistema" | Serie existente (`400`/`409`). |
| "La cantidad debe ser mayor a 0" | Cantidad cero/negativa (`400`). |
| "La cantidad de la fila {n} no es un número válido" | Texto o decimal en Excel (`400`). |
| "La cantidad no es un número válido" | Texto o decimal en formulario (`400`). |
| "El archivo debe ser un Excel .xlsx" | Extensión no permitida (`400`). |
| "El archivo no se pudo leer como Excel" | Archivo corrupto o ilegible (`400`). |
| "El archivo no tiene la columna obligatoria: {columna}" | Cabecera faltante (`400`). |
| "El archivo no contiene filas de datos" | Excel vacío (`400`). |
| "Debes seleccionar un archivo Excel" | Sin archivo (`400`). |
| "No se enviaron cambios" | Lote de edición vacío (`400`). |
| "La línea no es de un material no seriado" | Modificar cantidad de seriada (`400`). |
| "La serie ya no pertenece al stock inicial del técnico" | Serie que salió del técnico (`400`). |
| "El técnico no tiene suficiente stock" | Stock insuficiente al eliminar/modificar (`400`). |
| "El stock inicial ya fue modificado; no se puede reiniciar" | Comando de reinicio bloqueado. |
| "No hay stock inicial cargado para reiniciar" | Comando sin carga. |
| "El reinicio del stock inicial está deshabilitado" | Comando con la configuración apagada. |
| "No tienes permiso para reiniciar el stock inicial" | Comando con actor no Admin. |

## 10. Matriz de permisos

| Ruta | `USUARIO_TENANT` | `ADMIN_PLATAFORMA` | `RESPONSABLE_ALMACEN` | Tenant suspendido | Otro tenant |
|---|---|---|---|---|---|
| `GET /stock-inicial/` | `200` | `403` | `403` | `403` | No aplica |
| `POST /stock-inicial/validar-excel/` | `200`/`400` | `403` | `403` | `403` | No aplica |
| `POST /stock-inicial/cargar-excel/` | `302`/`400`/`409` | `403` | `403` | `403` | No aplica |
| `GET /stock-inicial/formulario/` | `200` | `403` | `403` | `403` | No aplica |
| `POST /stock-inicial/formulario/` | `302`/`400`/`409` | `403` | `403` | `403` | No aplica |
| `GET /stock-inicial/<id>/` | `200` | `403` | `403` | `403` | `404` |
| `GET /stock-inicial/<id>/editar/` | `200` | `403` | `403` | `403` | `404` |
| `POST /stock-inicial/<id>/editar/` | `302`/`400`/`409` | `403` | `403` | `403` | `404` |

## 11. Notas de implementación

- La vista valida rol y tenant antes de tocar el servicio; el servicio vuelve a validar. Una llamada
  interna no puede evadir el control.
- La vista no acepta `tenant_id` ni `region_id`; si llegan, se ignoran y no se pasan al servicio.
- `validar-excel` es idempotente y no escribe; `cargar-excel` revalida siempre.
- Los mensajes de error no incluyen `tenant_id`, `region_id`, stock, creador ni datos de otro
  tenant.
- El detalle y la edición usan `select_related`/`prefetch_related` para evitar N+1.
- El enlace de navegación a Stock inicial se muestra solo a `USUARIO_TENANT` con tenant activo.
