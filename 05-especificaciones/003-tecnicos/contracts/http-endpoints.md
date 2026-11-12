# Contrato HTTP: técnicos

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/003-tecnicos/spec.md`

Aplicación server-rendered con HTMX. Todas las rutas comparten cookie de sesión, CSRF, el
middleware de contexto y la autenticación de la spec 001. Los errores de negocio se devuelven como
HTML parcial (HTMX) o página completa, con el mensaje exacto indicado. Los permisos se validan en
el servidor; ocultar un control no es una autorización.

## Convenciones

- **Autenticación**: cookie de sesión de Django. Una sesión `pendiente_2fa` no accede a estas
  rutas (se redirige a `/login/2fa/`).
- **Roles**: `ADMIN` = Administrador de plataforma; `TENANT` = cuenta del tenant; `ALMACEN` =
  Responsable de almacén.
- **CSRF**: obligatorio en todo `POST`.
- **Tenant**: se obtiene de la sesión (`request.tenant`/`actor.tenant`). Ninguna ruta acepta ni usa
  `tenant_id`/`region_id` del cliente.
- **Formato de error**: HTML con el texto indicado; en peticiones HTMX, un fragmento con el mismo
  texto y el código de estado correspondiente.
- **Códigos**: `200` lectura; `302` redirección tras `POST` exitoso; `400` validación o intento de
  cambiar NIF/tenant; `401` sin sesión; `403` rol no autorizado o tenant suspendido; `404`
  técnico inexistente o de otro tenant; `405` método no permitido (incluye `DELETE`); `409` NIF
  duplicado.

## Matriz de permisos

| Ruta | ADMIN | TENANT | ALMACEN |
|---|---|---|---|
| `GET /tecnicos/` | No (`403`) | Sí | No (`403`) |
| `GET /tecnicos/buscar/` | No (`403`) | Sí | No (`403`) |
| `GET/POST /tecnicos/nuevo/` | No (`403`) | Sí | No (`403`) |
| `GET /tecnicos/<id>/` | No (`403`) | Sí | No (`403`) |
| `GET/POST /tecnicos/<id>/editar/` | No (`403`) | Sí | No (`403`) |
| `POST /tecnicos/<id>/desactivar/` | No (`403`) | Sí | No (`403`) |
| `POST /tecnicos/<id>/reactivar/` | No (`403`) | Sí | No (`403`) |

- El Administrador de plataforma no gestiona técnicos.
- El Responsable de almacén no gestiona técnicos ni ve su listado completo.
- La autorización se revalida en el servicio; forzar la URL o el `POST` no cambia el resultado.
- Si el tenant está suspendido, la cuenta del tenant recibe `403` "El tenant está suspendido".

## Rutas

### `GET /tecnicos/`

Listado paginado de los técnicos del tenant de la sesión.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Parámetros | `q` (opcional), `estado` (opcional: `todos`, `activos`, `desactivados`), `page` (opcional) |
| Comportamiento | Sin `q` devuelve los técnicos del tenant; con `q` filtra por NIF **o** nombre (`icontains`) |
| Filtro de estado | `todos` por defecto; `activos` filtra `activo=True`; `desactivados` filtra `activo=False`; valores no reconocidos se tratan como `todos` |
| Orden | `nombre` ascendente, `nif` como desempate |
| Paginación | 50 filas por página |
| Respuesta | `200` con NIF, nombre, estado y acciones; no incluye stock ni datos de otros tenants |
| Sesión ausente | `401` o redirección a `/login/` |
| Rol incorrecto | `403` "No tienes permiso para gestionar técnicos" |
| Tenant suspendido | `403` "El tenant está suspendido" |

### `GET /tecnicos/buscar/?q=&limit=`

Fragmento HTMX de autocompletado consumido por las specs 005, 006, 009 y 013. La spec 010 usa los
servicios de resolución por NIF, no el fragmento de operaciones nuevas. Solo devuelve técnicos
**activos** del tenant de la sesión. El detalle de la respuesta está en
`contracts/busqueda-tecnicos.md`.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Parámetros | `q` (opcional), `limit` (opcional, por defecto 20, máximo 50) |
| Filtro | Siempre `tenant=sesión` y `activo=True` |
| Respuesta | `200` con fragmento HTML de filas `data-*` |
| Sin coincidencias | `200` con el estado vacío explícito |
| Sesión ausente | `401` o redirección a `/login/` |
| Rol incorrecto | `403` |
| Método distinto de `GET` | `405` |

### `GET/POST /tecnicos/nuevo/`

Alta de técnico del tenant de la sesión.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición (`POST`) | `nif`, `nombre`, `csrfmiddlewaretoken` |
| Campos no aceptados | `tenant`, `tenant_id`, `region`, `region_id`, `activo`; se ignoran o se rechazan |
| Éxito | `302` al listado o al detalle; técnico creado activo; auditoría `alta` |
| NIF inválido (`LA123`, `LA12345`, `A1234`, `LA12A4`, `LA 1234`, `LA-1234`) | `400` "El NIF debe tener el formato LAXXXX" |
| NIF duplicado activo (mismo u otro tenant) | `409` "El NIF ya está registrado" |
| NIF de un desactivado del mismo tenant | `409` "El NIF ya está registrado; reactiva el técnico existente" |
| NIF de un desactivado de otro tenant | `409` "El NIF ya está registrado" (no revela el tenant) |
| Nombre vacío o solo espacios | `400` "El nombre es obligatorio" |
| Nombre > 100 caracteres | `400` "El nombre no puede superar los 100 caracteres" |
| Doble envío | La segunda petición responde `409`; no crea duplicado |
| Rol incorrecto | `403` "No tienes permiso para gestionar técnicos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| `DELETE` u otro método | `405` |

- El NIF se normaliza (`strip` + mayúsculas) antes de validar y de comprobar la unicidad.
- El nombre se normaliza (`strip` + colapso de espacios) antes de validar.
- El alta siempre crea el técnico como activo; `activo` no se acepta desde el formulario.

### `GET /tecnicos/<id>/`

Detalle de un técnico del tenant de la sesión.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Respuesta | `200` con NIF, nombre, estado, creador/fecha y última actualización |
| Técnico de otro tenant | `404` "El técnico no existe" |
| Técnico inexistente | `404` "El técnico no existe" |
| Rol incorrecto | `403` "No tienes permiso para gestionar técnicos" |
| Otros métodos | `405` |

- No se muestran datos de stock, asignaciones ni otros tenants; esos detalles pertenecen a sus
  módulos.
- El historial visible se limita a los datos del técnico; los documentos históricos se consultan
  en los módulos que los generan.

### `GET/POST /tecnicos/<id>/editar/`

Edición del nombre. El NIF y el tenant son inmutables.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición (`POST`) | `nombre`, `csrfmiddlewaretoken` |
| Éxito | `302` al detalle o al listado; cambio y auditoría por campo en la misma transacción |
| Técnico inexistente o de otro tenant | `404` "El técnico no existe" |
| Intento de enviar `nif` | `400` "El NIF no se puede cambiar" |
| Intento de enviar `tenant` o `tenant_id` | `400` "El tenant del técnico no se puede cambiar" |
| Nombre vacío o solo espacios | `400` "El nombre es obligatorio" |
| Nombre > 100 caracteres | `400` "El nombre no puede superar los 100 caracteres" |
| Nombre sin cambios | `302` sin auditoría nueva |
| Técnico desactivado | Se permite editar el nombre; no se reactiva ni se habilita para operaciones |
| Rol incorrecto | `403` "No tienes permiso para gestionar técnicos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| `DELETE` u otro método | `405`; no existe ruta de borrado |

- El formulario muestra NIF y tenant como solo lectura.
- Si se envían `nif` y `tenant` a la vez, se rechaza primero el NIF; el mensaje del tenant aparece
  al corregirlo. La validación nunca aplica un cambio parcial.

### `POST /tecnicos/<id>/desactivar/`

Desactiva un técnico sin eliminarlo.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | `csrfmiddlewaretoken`; sin cuerpo adicional |
| Éxito | `302` al detalle o al listado; `activo=False`; auditoría `activo` |
| Ya desactivado | `302` sin cambio ni auditoría nueva (idempotente) |
| Técnico inexistente o de otro tenant | `404` "El técnico no existe" |
| Rol incorrecto | `403` "No tienes permiso para gestionar técnicos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| `GET` u otro método | `405`; la acción solo acepta `POST` |

- No borra stock, series, asignaciones, traspasos, órdenes ni conciliaciones.
- El técnico deja de aparecer en `/tecnicos/buscar/` y en `tecnicos_para_operacion`.
- Su historial sigue visible en el detalle y en los módulos consumidores.

### `POST /tecnicos/<id>/reactivar/`

Reactiva un técnico desactivado.

| Aspecto | Contrato |
|---|---|
| Acceso | `TENANT` autenticado y activo; tenant activo |
| Petición | `csrfmiddlewaretoken`; sin cuerpo adicional |
| Éxito | `302` al detalle o al listado; `activo=True`; auditoría `activo` |
| Ya activo | `302` sin cambio ni auditoría nueva (idempotente) |
| Técnico inexistente o de otro tenant | `404` "El técnico no existe" |
| Rol incorrecto | `403` "No tienes permiso para gestionar técnicos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| `GET` u otro método | `405`; la acción solo acepta `POST` |

- La reactivación vuelve a habilitar al técnico para operaciones nuevas.
- No crea un técnico nuevo ni cambia su NIF, su tenant ni su historial.

## Reglas transversales verificadas en el servidor

1. Ninguna ruta acepta `tenant_id` ni `region_id`; el tenant sale de la sesión.
2. Un técnico de otro tenant se trata como inexistente (`404`), sin revelar su existencia ni su
   propietario.
3. El NIF y el tenant no se pueden cambiar por ninguna vía; el formulario de edición no los
   incluye y el servicio rechaza las claves si se fuerzan.
4. El mensaje de duplicado es uniforme. La variante "reactiva el técnico existente" solo aparece
   para un desactivado del mismo tenant.
5. Toda alta, cambio de nombre, desactivación y reactivación deja auditoría en la misma
   transacción.
6. Un técnico no se elimina por ninguna ruta; `DELETE` responde `405`.
7. La verificación de rol y tenant se repite en el servicio, no solo en la vista.
8. El fragmento de búsqueda solo devuelve técnicos activos del tenant de la sesión y nunca datos de
   stock, región o creador.
9. Las acciones de estado son idempotentes y no duplican auditoría.
10. El listado y el detalle no exponen información de otros tenants.

## Pruebas de contrato asociadas

- Alta válida: `302`, técnico activo y auditoría `alta`.
- NIF `LA123`, `LA12345`, `A1234`, `LA12A4`, `LA 1234` y `LA-1234`: `400` con el mensaje exacto.
- NIF `la1234` o con espacios externos: se normaliza y se guarda como `LA1234`.
- NIF duplicado en el mismo tenant y en otro tenant: `409` con "El NIF ya está registrado".
- NIF de un desactivado del mismo tenant: `409` con la variante de reactivación.
- NIF de un desactivado de otro tenant: `409` con el mensaje uniforme.
- Nombre vacío, solo espacios o > 100: `400` con el mensaje correspondiente.
- Edición de nombre: `302` y auditoría con valor anterior y nuevo.
- `nif` o `tenant` forzados: `400` con el mensaje exacto.
- Técnico de otro tenant: `404` en detalle, edición, desactivación y reactivación.
- `ADMIN` y `ALMACEN`: `403` en todas las rutas.
- Tenant suspendido: `403` "El tenant está suspendido".
- Desactivar/reactivar dos veces: `302` sin auditoría duplicada.
- `DELETE` y `GET` en acciones de estado: `405`.
- Listado: 50 filas por página, filtro por estado y búsqueda por NIF o nombre.
