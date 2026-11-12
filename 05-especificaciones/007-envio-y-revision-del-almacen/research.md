# Investigación y decisiones: 007 Envío y Revisión del Almacén

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/007-envio-y-revision-del-almacen/spec.md`

Este documento resuelve las incógnitas técnicas del plan y fija las decisiones que no deben
quedar a criterio de la implementación. No hay `NEEDS CLARIFICATION` pendientes: cada punto se
cierra con una decisión, su justificación y las alternativas descartadas.

## Contexto de dependencias

| Dependencia | Estado esperado | Uso en 007 |
|---|---|---|
| 001 — acceso, regiones, auditoría | Implementada | Roles, middleware, `request.region`, `Region.almacen.buzon`, `RegistroCambio` |
| 004 — series | Implementada | `Serie.estado`, unicidad global |
| 006 — solicitudes de asignación | Implementada | `SolicitudAsignacion`, `LineaAsignacion`, `excel_ruta`, `excel_hash`, `enviada_en` |
| 008 — stock y confirmación | Parte fundacional + `actualizar_stock_confirmacion_asignacion` | Movimiento de stock y `RESERVADA→ASIGNADA` al confirmar |
| Celery + Redis | Infraestructura del proyecto | Envío asíncrono, reintentos y pub/sub de notificaciones |
| PostgreSQL 16+ | Infraestructura del proyecto | Transacciones, bloqueos y RLS |

## Decisiones

### D-01. Registro de envíos: una fila por intento

- **Decisión**: `asignaciones.EnvioCorreo` guarda una fila por intento, con
  `unique(solicitud, numero_intento)`, `tenant`, `region`, `destinatario`, `archivo`,
  `hash_sha256`, `estado`, `error_mensaje`, `creado_en` y `enviado_en`.
- **Justificación**: CA-03 exige destinatario, fecha, archivo y hash del envío exacto. Un contador
  mutable en una sola fila pierde la trazabilidad de qué archivo y hash se enviaron en cada
  intento. La restricción única hace el reintento idempotente.
- **Alternativas descartadas**: una sola fila con `reintentos` (pierde el historial y permite
  dobles envíos); una tabla de eventos genérica (mezcla auditoría con estado operativo).

### D-02. Intentos y cadencia de reintento

- **Decisión**: intento inicial + 3 reintentos = 4 intentos como máximo, con intervalo **fijo** de
  300 segundos (5 minutos). `ENVIOS_MAX_INTENTOS=4` y
  `ENVIOS_INTERVALO_REINTENTO_SEGUNDOS=300`.
- **Justificación**: CA-02 dice literalmente «reintenta hasta 3 veces con intervalo de 5 minutos».
  El intento inicial no cuenta como reintento. Un intervalo fijo es determinista y verificable.
- **Alternativas descartadas**: backoff exponencial 5/10/20 (contradice CA-02 y la redacción previa
  del plan); reintentos ilimitados (riesgo de bucles y correo duplicado).

### D-03. Disparo del correo después del commit

- **Decisión**: 006 invoca `asignaciones.correo.programar_envio_solicitud(solicitud_id)` mediante
  `transaction.on_commit` al finalizar `enviar_solicitud`. 007 no envía dentro de la transacción.
- **Justificación**: si el envío se dispara antes del commit y la transacción revierte, se envía un
  Excel de una solicitud inexistente. `on_commit` garantiza que solo se notifica lo persistido.
- **Alternativas descartadas**: enviar dentro de `enviar_solicitud` (acopla 006 a SMTP y bloquea la
  respuesta); señal `post_save` genérica (difícil de acotar y de probar).

### D-04. Notificaciones en tiempo real: SSE + Redis pub/sub

- **Decisión**: `GET /almacen/notificaciones/sse/` devuelve `StreamingHttpResponse`
  `text/event-stream`, suscrito al canal `almacen:region:<region_id>`; la publicación se hace
  después del commit. Se ofrece `GET /almacen/notificaciones/pendientes/` como respaldo de polling
  cada 30 s.
- **Justificación**: la spec admite «WebSocket o SSE». SSE funciona con Django WSGI, usa el cliente
  `redis` que ya está en el stack de Celery y no requiere ASGI, Channels ni Daphne. El aislamiento
  por región se resuelve con el nombre del canal y la validación de `request.region`.
- **Alternativas descartadas**: Django Channels + WebSocket (dependencias y servidor ASGI no
  previstos en la constitución); polling puro (no cumple «tiempo real» ni la notificación sonora
  inmediata de CA-05).

### D-05. Aislamiento por región del almacén

- **Decisión**: el alcance sale de `request.usuario.region`; los servicios filtran por
  `solicitud.region` y `EnvioCorreo.region`. Una solicitud de otra región responde `404`.
  El Administrador de plataforma tiene alcance global solo para consulta y descarga.
- **Justificación**: principio I y regla 4 de la spec. `region_id` nunca se acepta de la URL ni del
  formulario. El `404` evita revelar la existencia de solicitudes ajenas.
- **Alternativas descartadas**: filtrar por `tenant__region` en cada consulta (más joins y riesgo de
  divergencia); confiar solo en RLS (la aplicación debe filtrar igualmente).

### D-06. Propiedad del stock y de las series al confirmar

- **Decisión**: 007 cambia `estado` a `CONFIRMADA` y fija `confirmada_en`; llama a
  `stock.services.actualizar_stock_confirmacion_asignacion(solicitud, actor)` dentro de la misma
  transacción. 008 es dueño de `RESERVADA→ASIGNADA`, de `StockGeneral`/`StockTecnico` y de su
  auditoría.
- **Justificación**: evita dos escritores del mismo dato y cumple la separación de la spec 008. La
  misma transacción garantiza todo o nada.
- **Alternativas descartadas**: que 007 escriba stock y series (duplica lógica y auditoría); que 008
  cambie el estado de la solicitud (rompe la propiedad de 006/007).

### D-07. Liberación de series y cantidades al rechazar

- **Decisión**: 007 cambia `SolicitudAsignacion.estado` a `RECHAZADA` y las series de las líneas
  seriadas `RESERVADA→DISPONIBLE`. Las cantidades no seriadas se liberan implícitamente porque el
  reservado de 006 solo suma líneas de solicitudes `ENVIADA`.
- **Justificación**: RF-31 y `03-reglas-de-dominio/series.md`. No existe tabla de reservas, por lo
  que no hay nada que borrar para los no seriados.
- **Alternativas descartadas**: crear una tabla de reservas solo para el rechazo (duplica el cálculo
  de 006); dejar las series `RESERVADA` (las bloquea para siempre).

### D-08. Notificación al tenant

- **Decisión**: el rechazo y el fallo definitivo de correo se muestran en el detalle de la solicitud
  de 006 (`motivo_rechazo`, `rechazada_en` y `envio_definitivo_fallido`). Además se envía un correo
  best-effort al buzón del tenant si está configurado. El tenant no usa SSE ni accede a `/almacen/`.
- **Justificación**: la spec pide «notificar al remitente» sin exigir tiempo real. El detalle es la
  fuente persistente y el correo es un refuerzo. Evita abrir un canal SSE por tenant.
- **Alternativas descartadas**: SSE para tenants (más canales y superficie de permisos); solo correo
  (si falla, el tenant no se entera).

### D-09. Fuente de la búsqueda histórica

- **Decisión**: la búsqueda opera sobre `SolicitudAsignacion` con `excel_ruta != ""`, no sobre
  `EnvioCorreo`. Cada fila muestra el hash canónico y el estado del último intento de envío.
- **Justificación**: un Excel histórico es uno por solicitud; los reintentos no crean Excels
  distintos. Buscar en `EnvioCorreo` duplicaría filas y confundiría al usuario.
- **Alternativas descartadas**: buscar por intento (duplicados); listar archivos del disco (sin
  metadatos ni control de acceso).

### D-10. Verificación de hash en la descarga

- **Decisión**: se calcula SHA-256 del archivo leído y se compara con `solicitud.excel_hash` usando
  `hmac.compare_digest`. Si no coincide, se responde `409` con
  "El archivo fue modificado, descarga bloqueada" y no se entrega el archivo. La misma verificación
  se aplica antes de adjuntar el Excel al correo.
- **Justificación**: CA-07 y CA-12; el hash canónico lo generó 006 y es la referencia. La
  comparación en tiempo constante evita filtraciones por temporización.
- **Alternativas descartadas**: confiar en el hash del último `EnvioCorreo` (podría ser de otro
  archivo); regenerar el Excel para comparar (cambiaría el archivo y violaría la inmutabilidad).

### D-11. Alcance del Administrador de plataforma

- **Decisión**: puede buscar y descargar Excels históricos de todas las regiones; no puede ver la
  bandeja, ni confirmar, ni rechazar, ni abrir el detalle operativo del almacén.
- **Justificación**: la spec le asigna solo HU-27 y la constitución prohíbe que el Administrador
  opere inventario.
- **Alternativas descartadas**: darle acceso completo al almacén (viola la separación de funciones);
  limitarlo a su región (no tiene región).

### D-12. Uso de roles explícitos, no permisos Django

- **Decisión**: las vistas y servicios comparan `actor.rol` con `Rol.RESPONSABLE_ALMACEN` o
  `Rol.ADMIN_PLATAFORMA`. No se crean grupos, permisos ni cadenas como
  `asignaciones.confirmar_solicitudasignacion`.
- **Justificación**: 001, 004, 005 y 006 usan comprobaciones explícitas de rol y alcance; los
  permisos Django no modelan la región ni el tenant.
- **Alternativas descartadas**: `@permission_required` (no conoce región); grupos por región
  (mantenimiento duplicado).

### D-13. RLS como respaldo

- **Decisión**: `EnvioCorreo` lleva `tenant` y `region` y se le aplica RLS por `tenant_id` y
  `region_id` si la infraestructura de 001 está disponible. Si no existe, se registra la deuda y se
  mantiene el filtrado en el ORM.
- **Justificación**: principio I y patrón de 001/006. No se inventa una infraestructura RLS
  paralela.
- **Alternativas descartadas**: omitir RLS (pierde el respaldo); crear políticas ad hoc sin el
  middleware de 001 (inoperantes).

### D-14. Idempotencia y reintentos seguros

- **Decisión**: la tarea `enviar_excel_solicitud(solicitud_id, numero_intento)` solo procesa un
  intento en estado `REINTENTANDO`; si ya está `EXITOSO` o `FALLIDO`, termina sin reenviar. La
  restricción única impide crear dos veces el mismo intento.
- **Justificación**: Celery puede reentregar una tarea; el registro por intento evita correos
  duplicados y mantiene la trazabilidad.
- **Alternativas descartadas**: confiar en la semántica exactly-once de la cola (no existe);
  bloquear con un lock en Redis (más complejo y no persistente).

### D-15. Formato y tamaño del mensaje SSE

- **Decisión**: cada evento usa `event: notificacion` y `data: <json>` con `solicitud_id`, `tenant`,
  `tecnico`, `total_series`, `total_cantidad`, `enviada_en`, `estado_anterior`, `estado_nuevo` y
  `pendientes` según el tipo. Heartbeat cada 25 s como comentario SSE (`: keep-alive`).
- **Justificación**: SSE estándar, fácil de consumir con `EventSource`, sin dependencias.
- **Alternativas descartadas**: enviar HTML completo por SSE (acopla el canal a la plantilla);
  mensajes binarios (innecesarios).

## Correcciones documentales derivadas de esta investigación

1. `spec.md` §11: **aplicado**. Se reemplazó «backoff exponencial» por intervalo fijo de 5 minutos,
   se aclaró que son 3 reintentos además del intento inicial y se precisó SSE sobre Redis.
2. `04-contratos/excel-asignacion.md` §2 y §8: el Excel se genera al enviar en 006 y 007 solo lo
   envía, descarga y verifica; no se regenera.
3. `008/plan.md`: eliminar `cantidad=-1`; validar stock suficiente y no permitir cantidades
   negativas; 008 es dueño de `RESERVADA→ASIGNADA` y del stock.
4. `006/plan.md` y `006/tasks.md`: agregar `transaction.on_commit` hacia
   `programar_envio_solicitud`, mostrar el fallo definitivo de correo en el detalle y dejar
   `confirmada_en` a cargo de 007.
5. `docs/02-arquitectura-software/funcionamiento-arquitectura.md`: aclarar que la implementación
   aprobada es SSE sobre Redis.

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| Infraestructura RLS de 001 no disponible | Registrar en este documento y mantener filtrado en ORM; no crear RLS paralela |
| `006/tasks.md` sin tarea de `on_commit` | Se corrige antes de implementar 007 (corrección 4) |
| Correo o worker caídos | Cada intento queda `FALLIDO`; el tenant ve el fallo definitivo; la solicitud sigue `ENVIADA` y visible en la bandeja |
| SSE interrumpido | Contador de pendientes y polling de respaldo cada 30 s |
| Archivo ausente o alterado | Se bloquea el envío y la descarga con `409`; se registra el error |
| Volumen de históricos | Índices por `region`, `tenant`, `fecha` y `estado`; paginación a 50 |

## Conclusión

No quedan incógnitas bloqueantes. El diseño respeta la constitución, no agrega dependencias y
cierra el ciclo `ENVIADA→CONFIRMADA`/`ENVIADA→RECHAZADA` sin duplicar stock, series ni generación
de Excel.
