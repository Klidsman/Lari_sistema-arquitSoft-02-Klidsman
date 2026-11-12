# Contrato: auditoría de 007

Toda operación que cambia estado en 007 se audita con `auditoria.services.registrar_cambio` en la
misma transacción. La auditoría es inmutable y compartida con el resto del sistema.

## Eventos obligatorios

### Confirmación

| Campo | Valor |
|---|---|
| Entidad | `SolicitudAsignacion` |
| ID entidad | `solicitud.id` |
| Campo | `estado` |
| Valor anterior | `ENVIADA` |
| Valor nuevo | `CONFIRMADA` |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |
| Momento | Dentro de la transacción de confirmación |
| Extra | `confirmada_en` |

La auditoría de series y stock de la confirmación la escribe 008 en la misma transacción. 007 no la
duplica.

### Rechazo

| Campo | Valor |
|---|---|
| Entidad | `SolicitudAsignacion` |
| ID entidad | `solicitud.id` |
| Campo | `estado` |
| Valor anterior | `ENVIADA` |
| Valor nuevo | `RECHAZADA` |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |
| Momento | Dentro de la transacción de rechazo |
| Extra | `motivo_rechazo`, `rechazada_en` |

Además, por cada serie liberada:

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `estado` |
| Valor anterior | `RESERVADA` |
| Valor nuevo | `DISPONIBLE` |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |

El motivo se audita como valor nuevo de `motivo_rechazo`; no se repite en cada serie.

### Intento de envío

| Campo | Valor |
|---|---|
| Entidad | `EnvioCorreo` |
| ID entidad | `envio.id` |
| Campo | `estado` |
| Valor anterior | `REINTENTANDO` |
| Valor nuevo | `EXITOSO` o `FALLIDO` |
| Actor | Usuario del sistema o `None` para la tarea |
| Momento | Al cerrar el intento |
| Extra | `numero_intento`, destinatario, archivo, hash, `error_mensaje` truncado |

- No se audita cada reintento programado por separado; el cierre del intento es el evento.
- Si un intento se cierra dos veces, la segunda no debe producir un registro nuevo.

## Reglas

- La auditoría de confirmación y rechazo es **síncrona y transaccional**: si falla, se revierte la
  operación completa.
- La auditoría del envío ocurre en la tarea, después de cerrar el intento; un fallo de auditoría no
  reenvía el correo.
- Nunca se auditan:
  - contraseñas, tokens, secretos TOTP ni credenciales SMTP;
  - el cuerpo del correo;
  - el contenido binario del Excel;
  - rutas físicas absolutas (solo la ruta relativa);
  - datos de otra región o tenant.
- El actor de la tarea de correo es el sistema; no se inventa un usuario humano.
- Los registros son inmutables: no se editan ni se eliminan desde 007.
- La auditoría no se usa como almacenamiento del motivo de rechazo; el motivo vive en
  `SolicitudAsignacion.motivo_rechazo`.

## Consulta

- La auditoría se consulta con las vistas de 001 según el alcance del rol.
- 007 no crea una pantalla de auditoría propia.
- El Administrador de plataforma puede consultar la auditoría global según 001; el almacén, la de
  su región.

## Pruebas de contrato

- Confirmar produce un registro `SolicitudAsignacion/estado` `ENVIADA→CONFIRMADA` con
  `confirmada_en` y el actor correcto.
- Rechazar produce un registro `ENVIADA→RECHAZADA` con el motivo y un registro `Serie/estado` por
  cada serie liberada.
- Un rechazo sin series seriadas produce el registro de la solicitud y ninguno de serie.
- Cada intento cerrado produce un registro `EnvioCorreo/estado` con `numero_intento`.
- Ningún registro contiene contraseñas, tokens, secretos, cuerpo del correo, binario ni ruta física
  absoluta.
- Si la auditoría falla dentro de la transacción, la confirmación o el rechazo se revierten.
- La auditoría de stock y series de la confirmación aparece una sola vez, escrita por 008.
