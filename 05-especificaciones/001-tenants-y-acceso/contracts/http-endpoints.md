# Contrato HTTP: tenants, regiones y acceso

**Fase**: 1 | **Fecha**: 2026-11-11 | **Spec**: `05-especificaciones/001-tenants-y-acceso/spec.md`

La aplicación es server-rendered con HTMX. Todas las rutas comparten cookie de sesión, CSRF,
autenticación y middleware de contexto. Las respuestas de error de negocio se devuelven como
HTML parcial (HTMX) o página completa, con el mensaje exacto indicado. Los permisos se validan
en el servidor; ocultar un botón no es una autorización.

## Convenciones

- **Autenticación**: cookie de sesión de Django. Sesión en estado `pendiente_2fa` solo puede
  acceder a `/login/2fa/`, `/logout/` y recursos estáticos.
- **Roles**: `ADMIN` = Administrador de plataforma; `TENANT` = cuenta del tenant;
  `ALMACEN` = Responsable de almacén.
- **CSRF**: obligatorio en todo `POST`.
- **Idempotencia**: los `POST` de suspensión, desactivación, reactivación y cambio de rol son
  idempotentes respecto del estado final; repetir la acción no duplica auditoría de valores
  sin cambio.
- **Formato de error**: `{"mensaje": "<texto>"}` cuando la petición es HTMX/JSON; HTML con el
  mismo texto en navegación normal.
- **Códigos**: `200` éxito de lectura, `201` alta, `204`/`200` acción sin cuerpo, `302`
  redirección tras `POST` exitoso, `400` validación, `401` sin sesión, `403` rol o alcance
  insuficiente, `404` recurso inexistente **o ajeno** (no se revela su existencia), `409`
  conflicto de unicidad, `410` invitación vencida/usada/revocada.

## Rutas de autenticación e invitación

### `GET/POST /login/`

Inicio de sesión con correo y contraseña.

| Aspecto | Contrato |
|---|---|
| Acceso | Público |
| Petición | `email`, `password`, `csrfmiddlewaretoken` |
| Éxito sin 2FA | `302` a la pantalla inicial del rol; sesión autenticada |
| Éxito con 2FA | `302` a `/login/2fa/`; sesión `pendiente_2fa`, sin acceso al resto |
| Error | `400` `"Correo o contraseña incorrectos"` (mismo mensaje para cuenta inexistente o clave errónea) |
| Cuenta inactiva | `403` `"La cuenta está desactivada"` |
| Tenant suspendido | `403` `"El tenant está suspendido"` |

### `GET/POST /login/2fa/`

Verificación del segundo factor.

| Aspecto | Contrato |
|---|---|
| Acceso | Sesión `pendiente_2fa` |
| Petición | `codigo` (6 dígitos TOTP) |
| Éxito | `302` a la pantalla inicial del rol; sesión autenticada |
| Error | `400` `"Debes completar el segundo factor"` |
| Sin sesión pendiente | `403` `"Debes iniciar sesión"` |
| Reintentos | Límite configurable por usuario; al excederse se cierra la sesión pendiente |

### `POST /logout/`

Cierre de sesión.

| Aspecto | Contrato |
|---|---|
| Acceso | Autenticado o `pendiente_2fa` |
| Éxito | `302` a `/login/`; sesión cerrada |
| CSRF ausente | `403` |

### `GET/POST /invitacion/<token>/`

Definir contraseña desde la invitación.

| Aspecto | Contrato |
|---|---|
| Acceso | Público con token válido |
| Petición | `password`, `password_confirmacion` |
| Éxito | `302` a `/login/` con mensaje `"Contraseña definida"`; cuenta activa e invitación usada |
| Token inválido/vencido/usado/revocado | `410` `"La invitación venció o ya fue usada"` |
| Contraseña débil | `400` con el mensaje del validador correspondiente |
| Cuenta ya activa | `410` con el mismo mensaje uniforme |

> El token original solo viaja en el enlace del correo. La base guarda su hash y nunca lo
> devuelve.

## Rutas del Administrador de plataforma

Todas requieren `rol = ADMIN`, sesión autenticada con segundo factor completado. Un rol
distinto recibe `403` `"No tienes permiso para administrar esta cuenta"`.

### `GET /plataforma/regiones/`

Listado paginado de regiones (50 por página) con código, nombre, estado y número de tenants.
`200`.

### `GET/POST /plataforma/regiones/nueva/`

Alta de región y su almacén en una sola transacción y con auditoría.

| Aspecto | Contrato |
|---|---|
| Petición (`POST`) | `codigo`, `nombre`, `centro`, `almacen`, `buzon` |
| Éxito | `302` al listado; región y almacén creados; auditoría de alta |
| Código duplicado | `409` `"El código de región ya existe"` |
| Buzón inválido | `400` `"El buzón no es válido"` |
| Centro/Almacén vacíos | `400` `"Centro y Almacén son obligatorios"` |
| Nombre vacío | `400` `"El nombre es obligatorio"` |

### `GET/POST /plataforma/regiones/<id>/editar/`

Edición de región y almacén. Audita cada campo modificado con valor anterior y nuevo.

| Aspecto | Contrato |
|---|---|
| Petición (`POST`) | `nombre`, `centro`, `almacen`, `buzon`, `activa` |
| Éxito | `302` al listado; cambios y auditoría en la misma transacción |
| Región ajena/inexistente | `404` |
| Buzón inválido | `400` `"El buzón no es válido"` |

El `codigo` no es editable después del alta.

### `GET /plataforma/tenants/`

Listado paginado de tenants con código, nombre, región y estado. `200`.

### `GET/POST /plataforma/tenants/nuevo/`

Alta de tenant.

| Aspecto | Contrato |
|---|---|
| Petición (`POST`) | `codigo`, `nombre`, `region` (id de una región activa) |
| Éxito | `302` al detalle; tenant `ACTIVO`; auditoría de alta |
| Sin región | `400` `"El tenant debe pertenecer a una región"` |
| Región inactiva/inexistente | `400` `"La región seleccionada no está disponible"` |
| Código duplicado | `409` `"El código de tenant ya existe"` |

### `GET /plataforma/tenants/<id>/`

Detalle del tenant y de su cuenta única (correo, rol y estado de activación). `404` si no
existe. `200`.

### `GET/POST /plataforma/tenants/<id>/cuenta/nueva/`

Crear la cuenta única del tenant y enviar la invitación.

| Aspecto | Contrato |
|---|---|
| Petición (`POST`) | `email` |
| Éxito | `302` al detalle; cuenta `is_active=False`, rol `USUARIO_TENANT`, invitación creada; correo encolado tras el commit; auditoría de alta |
| Tenant ya tiene cuenta | `409` `"El tenant ya tiene una cuenta"` |
| Correo ya registrado | `409` `"El correo ya está registrado"` |
| Correo inválido | `400` `"El correo no es válido"` |
| Fallo de correo | El alta se mantiene; se registra `ultimo_error` y se puede reenviar |

### `POST /plataforma/tenants/<id>/suspender/`

Suspender el tenant.

| Aspecto | Contrato |
|---|---|
| Éxito | `302` al detalle; `estado=SUSPENDIDO`; sesiones del tenant invalidadas (`version_sesion`); auditoría |
| Tenant ya suspendido | `200` sin cambios ni auditoría nueva |
| Tenant inexistente | `404` |

La suspensión no modifica datos ni stock.

### `GET /plataforma/cuentas/`

Listado paginado de cuentas con correo, rol, alcance (tenant o región) y estado. `200`.

### `POST /plataforma/cuentas/<id>/desactivar/`

| Aspecto | Contrato |
|---|---|
| Éxito | `302`; `is_active=False`; `version_sesion++`; auditoría con valor anterior y nuevo |
| Cuenta ya inactiva | `200` sin cambios |
| Cuenta inexistente/ajena | `404` |
| Intento de eliminar (`DELETE`) | `405`; no existe ruta de borrado |

### `POST /plataforma/cuentas/<id>/reactivar/`

| Aspecto | Contrato |
|---|---|
| Éxito | `302`; `is_active=True`; `version_sesion++`; auditoría |
| Cuenta inexistente | `404` |
| Cuenta de tenant con tenant suspendido | `409` `"El tenant está suspendido"` |

### `POST /plataforma/cuentas/<id>/rol/`

Cambiar rol de una cuenta administrativa.

| Aspecto | Contrato |
|---|---|
| Petición | `rol` destino (`ADMIN_PLATAFORMA` o `RESPONSABLE_ALMACEN`) |
| Éxito | `302`; nuevo rol aplicado; `version_sesion++`; auditoría con rol anterior y nuevo |
| Cuenta de tenant | `409` `"La cuenta del tenant no cambia de rol"` |
| Rol no permitido | `400` `"No puedes asignar ese rol"` |
| Alcance incompatible (p. ej. almacén sin región) | `400` `"El alcance de la cuenta no es válido"` |

## Rutas de consulta de auditoría

### `GET /auditoria/acceso/`

Consulta paginada de altas, cambios de rol, desactivaciones y suspensiones de acceso.

| Aspecto | Contrato |
|---|---|
| `ADMIN` | Ve toda la auditoría administrativa |
| `TENANT` | Ve solo la auditoría de su tenant y sus cuentas; nunca la de otro tenant |
| `ALMACEN` | Ve la auditoría de su región cuando corresponda; nunca la de tenants |
| Filtros | `entidad`, `entidad_id`, `desde`, `hasta`, `usuario` |
| Respuesta | `200` con entidad, entidad_id, campo, valor anterior, valor nuevo, usuario y fecha |
| Recurso ajeno | Se omite del resultado; una consulta directa a un id ajeno devuelve `404` |

## Matriz de permisos

| Ruta | ADMIN | TENANT | ALMACEN |
|---|---|---|---|
| `/login/`, `/login/2fa/`, `/logout/`, `/invitacion/<token>/` | Público | Público | Público |
| `/plataforma/regiones/**` | Sí | No | No |
| `/plataforma/tenants/**` | Sí | No | No |
| `/plataforma/cuentas/**` | Sí | No | No |
| `/auditoria/acceso/` | Global | Solo su tenant | Solo su región |

## Reglas transversales verificadas en el servidor

1. El tenant y la región salen de la sesión; cualquier `tenant_id` o `region_id` enviado por
   el cliente se ignora o se rechaza.
2. Un recurso de otro tenant o región se responde como `404`, sin revelar su existencia.
3. El Administrador de plataforma no puede usar estas rutas para operar inventario, recojos,
   asignaciones, traspasos ni conciliaciones.
4. La cuenta del tenant no puede crear cuentas ni subcuentas: no existe ruta y el servicio
   rechaza la operación aunque se fuerce.
5. Toda alta, cambio de rol, desactivación y suspensión deja un registro de auditoría en la
   misma transacción.
