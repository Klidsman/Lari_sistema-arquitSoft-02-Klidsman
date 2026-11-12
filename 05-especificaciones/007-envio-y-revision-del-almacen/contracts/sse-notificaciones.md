# Contrato SSE: notificaciones del almacén

Canal de notificaciones en tiempo real para el Responsable de almacén. Usa Server-Sent Events
sobre `StreamingHttpResponse` y pub/sub de Redis. No usa WebSocket ni Django Channels.

## Endpoint

| Ruta | Método | Rol | Respuesta |
|---|---|---|---|
| `/almacen/notificaciones/sse/` | GET | `RESPONSABLE_ALMACEN` | `200` `text/event-stream` |
| `/almacen/notificaciones/pendientes/` | GET | `RESPONSABLE_ALMACEN` | `200` fragmento HTML |

## Autenticación y alcance

- Requiere sesión y `@login_required`.
- Solo `RESPONSABLE_ALMACEN` con cuenta activa y región activa.
- La región se toma de `request.usuario.region`; no se acepta `region_id` por query string.
- `ADMIN_PLATAFORMA` y `USUARIO_TENANT` reciben `403`; sin sesión, `302` al login.
- Cada conexión se suscribe únicamente al canal de su región.

## Cabeceras de la respuesta

```http
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
X-Accel-Buffering: no
Connection: keep-alive
```

## Formato del evento

```text
event: notificacion
data: {"tipo":"nueva_solicitud","solicitud_id":42,"tenant":"ACME","tecnico":"Luis Pérez","total_series":3,"total_cantidad":10,"enviada_en":"2026-11-12T10:15:00Z","pendientes":5}

```

- Una línea `event:` y una línea `data:` con JSON compacto, terminadas en una línea vacía.
- Los valores se escapan correctamente; no se inyecta HTML.
- El cliente usa `EventSource` y actualiza el badge, la tabla y el aviso sonoro/visual.

## Tipos de evento

### `nueva_solicitud`

Se publica después del commit de `enviar_solicitud` (006) y de crear el primer intento de correo.

| Campo | Tipo | Descripción |
|---|---|---|
| `tipo` | string | `"nueva_solicitud"` |
| `solicitud_id` | int | ID de la solicitud |
| `tenant` | string | Código o nombre del tenant |
| `tecnico` | string | Nombre del técnico |
| `total_series` | int | Líneas seriadas |
| `total_cantidad` | int | Suma de cantidades no seriadas |
| `enviada_en` | ISO 8601 | Instante de envío |
| `pendientes` | int | Solicitudes `ENVIADA` de la región tras el evento |

### `cambio_estado`

Se publica después del commit de la confirmación o del rechazo.

| Campo | Tipo | Descripción |
|---|---|---|
| `tipo` | string | `"cambio_estado"` |
| `solicitud_id` | int | ID de la solicitud |
| `estado_anterior` | string | `"ENVIADA"` |
| `estado_nuevo` | string | `"CONFIRMADA"` o `"RECHAZADA"` |
| `pendientes` | int | Solicitudes `ENVIADA` restantes |

### Heartbeat

Cada `ALMACEN_SSE_HEARTBEAT_SEGUNDOS` (25 por defecto) el servidor envía un comentario SSE:

```text
: keep-alive

```

Mantiene viva la conexión a través de proxies y permite detectar desconexiones.

## Canal de Redis

- Nombre: `f"{settings.ALMACEN_SSE_PREFIJO_CANAL}{region.id}"`, por defecto
  `almacen:region:<id>`.
- Publicación: `redis.Redis.from_url(settings.REDIS_NOTIFICACIONES_URL).publish(canal, json)`.
- Suscripción: `pubsub.subscribe(canal)` dentro del generador del flujo.
- La publicación ocurre **después del commit** de la operación de negocio.
- Si Redis falla al publicar, se registra el error y no se revierte la operación.
- No se publican datos personales innecesarios ni el contenido del Excel.

## Degradación y recuperación

- Si `EventSource` falla o el navegador no lo soporta, el cliente consulta
  `/almacen/notificaciones/pendientes/` cada 30 segundos.
- El fragmento devuelve `data-pendientes` y `data-ultima-solicitud-id`; si cambian, recarga la tabla.
- Al reconectar, el badge y el polling recuperan el estado; no se depende de eventos perdidos.
- El servidor cierra el flujo cuando el cliente se desconecta y libera la suscripción.

## Pruebas de contrato

- `200` con `Content-Type: text/event-stream; charset=utf-8` para almacén de la región.
- `403` para Admin, Tenant, cuenta inactiva y región inactiva; `302` sin sesión; `405` para `POST`.
- Un evento publicado en la región A no llega al flujo de la región B.
- El evento contiene `event: notificacion` y JSON parseable con los campos del tipo.
- El heartbeat aparece dentro del intervalo configurado.
- `pendientes` coincide con el número de solicitudes `ENVIADA` de la región.
- El fragmento de polling es HTML y expone `data-pendientes` y `data-ultima-solicitud-id`.
