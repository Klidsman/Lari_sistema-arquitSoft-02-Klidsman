# Contrato: envío de correo y registro de intentos

Define el correo del Excel de asignación al almacén de la región, las tareas Celery y el registro
`EnvioCorreo`. El envío es asíncrono y nunca bloquea ni revierte la transacción de 006.

## Disparo

- 006 finaliza `enviar_solicitud` y registra `transaction.on_commit(programar_envio_solicitud,
  solicitud.id)`.
- `programar_envio_solicitud` solo actúa si la solicitud está `ENVIADA` y tiene `excel_ruta` y
  `excel_hash`.
- Si faltan el archivo o el hash, registra el intento 1 como `FALLIDO` con
  "El archivo del Excel no está disponible o fue modificado" y notifica al tenant.
- Si el broker de Celery no está disponible, cierra el intento como `FALLIDO` y notifica al
  tenant; no lanza la excepción hacia la transacción ya confirmada.

## Registro `EnvioCorreo`

| Campo | Obligatorio | Regla |
|---|---|---|
| `solicitud` | Sí | FK `PROTECT` a `SolicitudAsignacion` |
| `tenant` | Sí | Copiado de `solicitud.tenant` |
| `region` | Sí | Copiado de `solicitud.region` |
| `numero_intento` | Sí | Entero ≥ 1; único por solicitud |
| `destinatario` | Sí | `solicitud.region.almacen.buzon` |
| `archivo` | Sí | Ruta relativa del Excel de 006 |
| `hash_sha256` | Sí | 64 hex; igual a `solicitud.excel_hash` |
| `estado` | Sí | `REINTENTANDO`, `EXITOSO` o `FALLIDO` |
| `error_mensaje` | No | Vacío en éxito; truncado a 500 caracteres en fallo |
| `creado_en` | Sí | Automático al programar el intento |
| `enviado_en` | No | Se fija al cerrar el intento |

- Una fila por intento; nunca se reutiliza `numero_intento`.
- Los campos de identidad son inmutables.
- `estado` se cierra una sola vez: `REINTENTANDO→EXITOSO` o `REINTENTANDO→FALLIDO`.
- `error_mensaje` no incluye trazas, credenciales SMTP ni el cuerpo del correo.
- No se guarda el binario del Excel ni el mensaje completo.

## Mensaje de correo

| Elemento | Valor |
|---|---|
| Remitente | `settings.ENVIOS_REMITENTE` |
| Destinatario | `EnvioCorreo.destinatario` (buzón del almacén de la región) |
| Asunto | `settings.ALMACEN_ALERTA_ASUNTO` con ID de solicitud y tenant |
| Cuerpo | Texto plano con ID, fecha, tenant, técnico, totales y aviso de revisión |
| Adjunto | Excel archivado por 006, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, nombre `asignacion-<id>.xlsx` |
| Copias | Ninguna; no se copia al tenant |

- Antes de adjuntar se verifica que el archivo exista, que esté dentro de `MEDIA_ROOT` y que su
  SHA-256 coincida con `solicitud.excel_hash`.
- El correo no incluye enlaces con tokens ni secretos.

## Reintentos

| Parámetro | Valor por defecto | Configuración |
|---|---|---|
| Intentos máximos | 4 (1 inicial + 3 reintentos) | `ENVIOS_MAX_INTENTOS` |
| Intervalo | 300 s fijos | `ENVIOS_INTERVALO_REINTENTO_SEGUNDOS` |
| Programación | `apply_async(countdown=300)` | Celery |
| Backoff | No se usa | — |

Flujo:

1. Intento 1 `REINTENTANDO`; si falla, `FALLIDO`.
2. Si `numero_intento < ENVIOS_MAX_INTENTOS`, crea el intento siguiente y lo encola con `countdown`.
3. Repite hasta el intento 4.
4. Si el intento 4 falla, no se reprograma y se marca el fallo definitivo.

- Un intento ya cerrado no se reenvía aunque la tarea se reentregue.
- La restricción `unique(solicitud, numero_intento)` impide duplicados.
- El fallo de correo no cambia `SolicitudAsignacion.estado`; la solicitud sigue `ENVIADA` y visible
  en la bandeja.

## Fallo definitivo

- `envio_definitivo_fallido(solicitud)` es verdadero si el intento 4 está `FALLIDO` y no existe
  ningún intento `EXITOSO`.
- El detalle de la solicitud de 006 muestra el aviso "No se pudo enviar el correo al almacén" y la
  bandeja del almacén sigue mostrando la solicitud.
- Se envía un correo best-effort al buzón del tenant; si también falla, no se revierte nada y queda
  el aviso persistente en el detalle.

## Tareas Celery

| Tarea | Firma | Responsabilidad |
|---|---|---|
| `programar_envio_solicitud` | `(solicitud_id)` | Crear el intento 1 y encolar |
| `enviar_excel_solicitud` | `(solicitud_id, numero_intento)` | Enviar, cerrar el intento y reprogramar o notificar |

- Ambas son idempotentes y verifican el estado antes de actuar.
- No acceden a `tenant_id`/`region_id` del cliente; usan la solicitud persistida.
- Auditan el cierre del intento con `EnvioCorreo/estado`.
- No auditan credenciales, cuerpo del correo ni contenido binario.

## Errores registrados

| Situación | `estado` | `error_mensaje` |
|---|---|---|
| Buzón del almacén no configurado | `FALLIDO` | "El buzón del almacén no está configurado" |
| Almacén inactivo o región sin almacén | `FALLIDO` | "El almacén de la región no está activo" |
| Excel ausente, fuera de `MEDIA_ROOT` o hash alterado | `FALLIDO` | "El archivo del Excel no está disponible o fue modificado" |
| Error SMTP transitorio | `FALLIDO` | Mensaje truncado de la excepción, sin credenciales |
| Broker no disponible al programar | `FALLIDO` | "No se pudo programar el envío del correo" |

## Pruebas de contrato

- `programar_envio_solicitud` crea el intento 1 con el buzón, archivo y hash correctos.
- `enviar_excel_solicitud` usa `locmem` y deja el intento `EXITOSO` con un adjunto `.xlsx`.
- Un fallo simulado deja `FALLIDO` y programa el intento 2 con `countdown=300`.
- Los intentos 1..4 existen con `numero_intento` único y el intento 4 `FALLIDO` marca el fallo
  definitivo.
- Reejecutar una tarea cerrada no envía otro correo ni crea otra fila.
- El hash alterado bloquea el envío y registra el mensaje exacto.
- La solicitud sigue `ENVIADA` después de cualquier fallo de correo.
