---
description: "Lista de tareas para la implementación de 007 Envío y Revisión del Almacén"
---

# Tareas: 007 Envío y Revisión del Almacén

**Entrada**: Documentos de diseño en `05-especificaciones/007-envio-y-revision-del-almacen/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`, `tenants.Region`,
`tenants.Almacen`, `ContextoUsuarioMiddleware`, roles y `auditoria.RegistroCambio`),
**spec 004 implementada** (`series.Serie` y `EstadoSerie`), **spec 006 implementada**
(`asignaciones.SolicitudAsignacion`, `LineaAsignacion`, `excel_ruta`, `excel_hash`, `enviada_en` y
`enviar_solicitud`) y **parte de confirmación de 008 implementada**
(`stock.StockGeneral`, `stock.StockTecnico` y
`stock.services.actualizar_stock_confirmacion_asignacion`). También se requieren worker de Celery,
Redis, `MEDIA_ROOT` compartido y backend de correo configurado. La creación de solicitudes y la
generación del Excel pertenecen a 006 y no se repiten aquí.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-12. Cada historia escribe primero sus
pruebas, las ve fallar y luego implementa.

**Organización**: `spec.md` define las historias HU-14…HU-17 y HU-27 sin etiqueta de prioridad
explícita; se agrupan en seis historias derivadas para permitir entregas incrementales e
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario asociada (`US1`…`US6`)
- Todas las rutas de archivo son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Enviar el Excel al almacén y registrar cada intento | P1 | HU-14; RF-27, RF-28; CA-01, CA-02, CA-03; §5.1, §5.2 |
| US2 — Bandeja de despachos y notificaciones en tiempo real | P2 | HU-14; RF-29, RF-30; CA-04, CA-05; §5.3, §5.4 |
| US3 — Previsualizar, descargar y verificar el hash | P3 | HU-15, HU-27; RF-28; CA-06, CA-07, CA-12; §5.5, §5.9 |
| US4 — Confirmar la solicitud y actualizar stock | P4 | HU-16; RF-29; CA-08; §5.6 |
| US5 — Rechazar con motivo y liberar series | P5 | HU-17; RF-29, RF-31; CA-09, CA-10; §5.7 |
| US6 — Buscar Excels históricos | P6 | HU-27; RF-28; CA-11; §5.9 |

## Convenciones de rutas

Proyecto Django único en la raíz: se reutiliza la app `asignaciones/` de 006; las plantillas viven
en `templates/almacen/`; las pruebas en `tests/{unit,integration,contract}/`. Las apps `acceso`,
`tenants`, `auditoria` (001), `materiales` (002), `tecnicos` (003), `series` (004), `asignaciones`
(006) y `stock` (008) son propiedad de sus specs y no se duplican. 007 **no** crea una tabla de
series, **no** crea tablas de stock, **no** regenera el Excel de 006 y **no** implementa la creación
de solicitudes.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: aplicar las correcciones documentales, configurar correo, Celery, Redis, rutas y
fixtures, y dejar el entorno listo para las historias.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `series/models.py`, `asignaciones/models.py`, `asignaciones/services.py` y `stock/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware`, roles `ADMIN_PLATAFORMA`/`USUARIO_TENANT`/`RESPONSABLE_ALMACEN`, `Region.almacen` con `buzon`/`centro`/`codigo_almacen`/`activo`, `Serie.estado` con `DISPONIBLE`/`RESERVADA`/`ASIGNADA` y campos `tecnico`/`asignada_en`, `SolicitudAsignacion.excel_ruta`/`excel_hash`/`enviada_en`/`confirmada_en` y `stock.services.actualizar_stock_confirmacion_asignacion`; detenerse y reportar si falta alguno
- [ ] T002 [P] Verificar en `05-especificaciones/007-envio-y-revision-del-almacen/spec.md` §11 que los reintentos son 3 además del intento inicial (4 en total) con intervalo fijo de 5 minutos, sin backoff exponencial, y que la notificación en tiempo real es SSE sobre Redis; corregir cualquier contradicción restante antes de implementar
- [ ] T003 [P] Corregir `04-contratos/excel-asignacion.md` §2 y §8 para precisar que el Excel se genera al enviar (`BORRADOR`→`ENVIADA`) en 006 y que 007 solo lo envía, descarga y verifica; 007 nunca lo regenera
- [ ] T004 [P] Corregir `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/plan.md` para eliminar `cantidad=-1`, validar stock suficiente antes de decrementar, no permitir cantidades negativas y dejar claro que 008 es dueño de `RESERVADA→ASIGNADA`, del stock y de su auditoría, mientras 007 solo fija `confirmada_en` y el estado de la solicitud
- [ ] T005 [P] Corregir `05-especificaciones/006-solicitud-de-asignacion/plan.md` y `05-especificaciones/006-solicitud-de-asignacion/tasks.md` para agregar el gancho `transaction.on_commit` hacia `programar_envio_solicitud`, mostrar el fallo definitivo de correo en el detalle del tenant y confirmar que `confirmada_en` lo escribe 007
- [ ] T006 [P] Corregir `docs/02-arquitectura-software/funcionamiento-arquitectura.md` para aclarar que la implementación aprobada de notificaciones en tiempo real es SSE sobre Redis, aunque el texto mencione WebSocket/SSE
- [ ] T007 [P] Agregar en `config/settings/base.py` `ENVIOS_MAX_INTENTOS=4`, `ENVIOS_INTERVALO_REINTENTO_SEGUNDOS=300`, `ENVIOS_REMITENTE`, `ALMACEN_ALERTA_ASUNTO`, `ALMACEN_SSE_PREFIJO_CANAL="almacen:region:"`, `ALMACEN_SSE_HEARTBEAT_SEGUNDOS=25` y `REDIS_NOTIFICACIONES_URL` (por defecto el broker de Celery), con lectura desde variables de entorno y esos valores por defecto
- [ ] T008 [P] Incluir `asignaciones.urls` desde `config/urls.py` bajo el prefijo `/almacen/` (las rutas se completan en T062, T077, T088, T104 y T117)
- [ ] T009 [P] Agregar en `templates/base.html` el enlace a Bandeja de despachos visible solo para `RESPONSABLE_ALMACEN` con región activa, sin exponerlo a `USUARIO_TENANT` ni a `ADMIN_PLATAFORMA`
- [ ] T010 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region_almacen`, `almacen_activo`, `almacen_inactivo`, `region_sin_almacen`, `usuario_almacen`, `usuario_almacen_otra_region`, `usuario_admin`, `usuario_tenant`, `solicitud_enviada`, `solicitud_confirmada`, `solicitud_rechazada`, `envio_exitoso`, `envio_fallido`, `envio_reintentando` y `registro_cambios_almacen`
- [ ] T011 [P] Configurar en `config/settings/test.py` `EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"`, Celery en modo eager y `REDIS_NOTIFICACIONES_URL` de prueba, para que las pruebas de correo y SSE no dependan de servicios externos

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelo `EnvioCorreo`, migraciones, excepciones, permisos, utilidades de hash y ruta,
auditoría, contadores y contratos base que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

- [ ] T012 [P] Escribir las pruebas de restricciones y campos de `EnvioCorreo` en `tests/integration/test_envio_registro.py`: `unique(solicitud, numero_intento)`, `numero_intento >= 1`, `estado IN ("REINTENTANDO","EXITOSO","FALLIDO")`, `PROTECT` en `solicitud`/`tenant`/`region`, `error_mensaje` vacío por defecto, `enviado_en` nulo al programar y campos de identidad inmutables
- [ ] T013 [P] Escribir las pruebas de permisos y alcance del almacén en `tests/unit/test_almacen_servicios.py`: `validar_cuenta_almacen` con los tres roles, cuenta inactiva, región inactiva, región sin almacén y almacén inactivo; `validar_cuenta_consulta` con Almacén, Admin y Tenant; y `obtener_solicitud_almacen` con solicitud propia, ajena, inexistente, `BORRADOR` y `CANCELADA`
- [ ] T014 [P] Escribir las pruebas unitarias de hash y ruta segura en `tests/unit/test_almacen_hash.py`: SHA-256 de contenido conocido, comparación con `hmac.compare_digest`, archivo alterado, archivo ausente, ruta con `..`, ruta absoluta y ruta fuera de `MEDIA_ROOT`
- [ ] T015 [P] Escribir las pruebas de publicación y aislamiento del canal SSE en `tests/integration/test_almacen_notificaciones.py`: `canal_region` usa `almacen:region:<id>`, un evento de la región A no llega a la región B, la publicación no revierte la operación si Redis falla y el contador de pendientes coincide con las solicitudes `ENVIADA`
- [ ] T016 Implementar `EnvioCorreo` en `asignaciones/models.py`: `solicitud` FK `SolicitudAsignacion` `on_delete=PROTECT` `related_name="envios_correo"`, `tenant` FK `"tenants.Tenant"` `PROTECT` `related_name="envios_correo"`, `region` FK `"tenants.Region"` `PROTECT` `related_name="envios_correo"`, `numero_intento = PositiveIntegerField()`, `destinatario = EmailField()`, `archivo = CharField(max_length=255)`, `hash_sha256 = CharField(max_length=64)`, `estado = CharField(max_length=20, choices=[("REINTENTANDO","Reintentando"),("EXITOSO","Exitoso"),("FALLIDO","Fallido")], default="REINTENTANDO")`, `error_mensaje = TextField(blank=True, default="")`, `creado_en = DateTimeField(auto_now_add=True)`, `enviado_en = DateTimeField(null=True, blank=True)`; `Meta.ordering=["solicitud","numero_intento"]`, `UniqueConstraint(fields=["solicitud","numero_intento"], name="envio_correo_intento_unico")`, `CheckConstraint(numero_intento__gte=1, name="envio_correo_numero_intento_positivo")`, `CheckConstraint(estado__in=[...], name="envio_correo_estado_valido")` e índices `envio_correo_region_estado`, `envio_correo_tenant_fecha` y `envio_correo_solicitud_intento`
- [ ] T017 Agregar a `SolicitudAsignacion` en `asignaciones/models.py` los campos `motivo_rechazo = TextField(blank=True, default="")` y `rechazada_en = DateTimeField(null=True, blank=True)`, sin duplicar `confirmada_en`, y documentar que `CONFIRMADA`/`RECHAZADA` son terminales
- [ ] T018 Crear `asignaciones/migrations/0003_envio_correo.py` con T016 y T017, revisar que no cree envíos, solicitudes ni series por migración y aplicar con `migrate`
- [ ] T019 Crear `asignaciones/migrations/0004_envio_correo_rls.py` con políticas RLS por `tenant_id` y `region_id` para `asignaciones_enviocorreo`; si la infraestructura RLS de 001 no está disponible, registrar la deuda en `05-especificaciones/007-envio-y-revision-del-almacen/research.md` y no inventar una infraestructura paralela
- [ ] T020 Implementar en `asignaciones/services.py` las excepciones `PermisoDenegado`, `SolicitudNoExiste`, `EstadoSolicitudInvalido`, `MotivoRechazoRequerido`, `MotivoRechazoInvalido`, `BuzonAlmacenNoConfigurado`, `ArchivoExcelNoDisponible`, `HashNoCoincide` y `EnvioNoExiste`, con los mensajes exactos de `contracts/http-endpoints.md`
- [ ] T021 Implementar en `asignaciones/services.py` `validar_cuenta_almacen(actor)` y `validar_cuenta_consulta(actor)`: el primero exige `RESPONSABLE_ALMACEN`, cuenta activa, región activa y almacén activo con buzón y parámetros, y lanza “No tienes permiso para gestionar despachos”; el segundo devuelve `("REGION", region)` para Almacén y `("GLOBAL", None)` para Admin, y rechaza a `USUARIO_TENANT`
- [ ] T022 Implementar en `asignaciones/services.py` `obtener_solicitud_almacen(region, solicitud_id)`, `validar_solicitud_confirmable(solicitud)` y `validar_solicitud_rechazable(solicitud)`: filtrar por `region`, excluir `BORRADOR` y `CANCELADA`, responder “La solicitud no existe” y exigir `ENVIADA` con “Solo se pueden confirmar solicitudes enviadas” o “Solo se pueden rechazar solicitudes enviadas”
- [ ] T023 Implementar en `asignaciones/services.py` `totales_solicitud(solicitud)`, `obtener_detalle_almacen(region, solicitud_id)` y las consultas base con `select_related` de tenant/técnico/región y `prefetch_related` de `lineas__material`/`lineas__serie`, sin N+1 y sin revelar datos de otra región
- [ ] T024 Implementar en `asignaciones/services.py` `verificar_hash_excel(solicitud, contenido)` y el helper de ruta segura: resolver `Path(settings.MEDIA_ROOT) / solicitud.excel_ruta`, rechazar `..`, rutas absolutas y salidas de `MEDIA_ROOT`, calcular SHA-256 y comparar con `solicitud.excel_hash` usando `hmac.compare_digest`; lanzar `HashNoCoincide` con “El archivo fue modificado, descarga bloqueada”
- [ ] T025 Implementar en `asignaciones/notificaciones.py` `canal_region(region)`, `publicar_evento_region(region, evento)` y `contar_solicitudes_pendientes(region)`: publicar JSON en `almacen:region:<region_id>` con `redis.Redis.from_url(settings.REDIS_NOTIFICACIONES_URL)`, registrar el fallo sin revertir y contar solo solicitudes `ENVIADA` de la región
- [ ] T026 Implementar en `asignaciones/services.py` los helpers de auditoría para `SolicitudAsignacion/estado`, `Serie/estado` y `EnvioCorreo/estado` con `auditoria.services.registrar_cambio`, en la misma transacción cuando corresponda, sin secretos, sin contenido binario y sin `tenant_id` separado
- [ ] T027 Implementar en `asignaciones/forms.py` `RechazoForm` con `motivo = CharField(widget=Textarea, required=True, max_length=1000)` y `FiltrosHistoricosForm` con `fecha_desde`, `fecha_hasta`, `tenant`, `tecnico` y `estado`; validar el motivo no vacío, solo espacios y máximo 1000 caracteres
- [ ] T028 Crear `templates/almacen/_notificacion.html` con el contenedor `data-sse-url`, `data-poll-url`, `data-pendientes` y el toast reutilizable, sin datos de otra región
- [ ] T029 Implementar en `asignaciones/services.py` la guarda de transición común `ENVIADA→CONFIRMADA`/`ENVIADA→RECHAZADA` dentro de `transaction.atomic` con `select_for_update` sobre la solicitud y orden de bloqueo estable: solicitud, series por `id`, stock dentro de 008
- [ ] T030 Verificar en `config/celery.py` que las tareas de `asignaciones.tasks` se autodescubren y que el worker usa el mismo `MEDIA_ROOT`, `DATABASE_URL` y `REDIS_NOTIFICACIONES_URL` que la web; documentar la comprobación en `05-especificaciones/007-envio-y-revision-del-almacen/quickstart.md`

**Checkpoint**: modelo, migraciones, permisos, hash, auditoría, canal SSE, formularios y bloqueos listos; las historias pueden comenzar.

---

## Fase 3: US1 — Enviar el Excel y registrar cada intento (P1) 🎯 MVP

**Objetivo**: al confirmarse el envío de 006, programar y ejecutar el correo al buzón del almacén,
registrar una fila por intento con destinatario, archivo y hash, reintentar 3 veces con intervalo
fijo de 5 minutos y avisar al tenant si se agotan los intentos.

**Prueba independiente**: con una solicitud `ENVIADA` y su Excel archivado, disparar
`programar_envio_solicitud`; verificar un correo en `locmem` con adjunto, una fila `EXITOSO` con
destinatario/archivo/hash y, al simular fallo SMTP, 4 intentos separados por 300 s y el aviso de
fallo definitivo, sin cambiar el estado de la solicitud.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T031 [P] [US1] Pruebas unitarias de construcción del correo en `tests/unit/test_envio_correo.py`: asunto con ID y tenant, destinatario del intento, cuerpo con totales, adjunto `.xlsx`, nombre `asignacion-<id>.xlsx`, sin copias ni secretos y sin adjuntar si el hash no coincide
- [ ] T032 [US1] Pruebas unitarias de reintentos en `tests/unit/test_envio_correo.py`: 4 intentos máximos (1 inicial + 3 reintentos), `countdown=300` fijo, sin backoff, intento 4 `FALLIDO` sin reprogramación y tarea ya cerrada que no reenvía
- [ ] T033 [P] [US1] Pruebas de integración de **CA-01** en `tests/integration/test_envio_registro.py`: `test_envio_exitoso_registra_destinatario_fecha_archivo_y_hash`; el correo llega a `locmem`, el adjunto es el Excel de 006 y el intento queda `EXITOSO` con `enviado_en`
- [ ] T034 [US1] Pruebas de integración de **CA-02** en `tests/integration/test_envio_registro.py`: `test_reintento_fijo_cada_cinco_minutos_hasta_tres_veces`; fallo SMTP simulado, intentos 1..4 con `numero_intento` único, `countdown=300` y sin solapamiento
- [ ] T035 [US1] Pruebas de integración de **CA-03** en `tests/integration/test_envio_registro.py`: `test_registro_envio_completo_es_inmutable`; destinatario, `creado_en`/`enviado_en`, archivo relativo y hash de 64 hex; identidad inmutable y `error_mensaje` truncado
- [ ] T036 [US1] Pruebas de integración del fallo definitivo en `tests/integration/test_envio_registro.py`: intento 4 `FALLIDO` sin intento `EXITOSO`, `envio_definitivo_fallido` verdadero, aviso visible para el tenant y solicitud que sigue `ENVIADA`
- [ ] T037 [US1] Pruebas de integración del disparo con `transaction.on_commit` en `tests/integration/test_envio_registro.py`: una transacción revertida no encola correo; una confirmada lo encola una sola vez; el fallo del broker no revierte la solicitud
- [ ] T038 [US1] Pruebas de integración de idempotencia en `tests/integration/test_envio_registro.py`: reejecutar `enviar_excel_solicitud` sobre un intento cerrado no envía otro correo ni crea otra fila; dos programaciones simultáneas no duplican `numero_intento=1`

### Implementación de US1

- [ ] T039 [US1] Implementar `programar_envio_solicitud(solicitud_id)` en `asignaciones/correo.py`: releer la solicitud, exigir `ENVIADA`, `excel_ruta` y `excel_hash`, crear el intento 1 con `destinatario=solicitud.region.almacen.buzon`, `archivo=solicitud.excel_ruta`, `hash_sha256=solicitud.excel_hash`, `estado="REINTENTANDO"` y encolar la tarea
- [ ] T040 [US1] Implementar `enviar_excel_solicitud(solicitud_id, numero_intento)` en `asignaciones/tasks.py`: releer solicitud e intento, validar `ENVIADA` y `REINTENTANDO`, verificar archivo y hash, construir y enviar el correo con `django.core.mail.EmailMessage` y cerrar el intento como `EXITOSO` o `FALLIDO`
- [ ] T041 [US1] Implementar en `asignaciones/tasks.py` la reprogramación: si `numero_intento < settings.ENVIOS_MAX_INTENTOS`, crear el siguiente intento `REINTENTANDO` y encolar con `countdown=settings.ENVIOS_INTERVALO_REINTENTO_SEGUNDOS`; si se agotaron, no reprogramar
- [ ] T042 [US1] Implementar en `asignaciones/correo.py` y `asignaciones/tasks.py` el manejo de fallos: buzón no configurado, almacén inactivo, Excel ausente o alterado, error SMTP y broker no disponible; guardar `error_mensaje` truncado y no exponer trazas ni credenciales
- [ ] T043 [US1] Implementar `envio_definitivo_fallido(solicitud)` en `asignaciones/correo.py`: verdadero si el intento `ENVIOS_MAX_INTENTOS` está `FALLIDO` y no existe ningún `EXITOSO`; usarlo en el detalle de 006 para mostrar “No se pudo enviar el correo al almacén”
- [ ] T044 [US1] Implementar en `asignaciones/services.py` el gancho de 006: al finalizar `enviar_solicitud`, registrar `transaction.on_commit(lambda: programar_envio_solicitud(solicitud.id))`; no enviar antes del commit y no dejar el correo dentro de la transacción
- [ ] T045 [US1] Implementar en `asignaciones/correo.py` la notificación best-effort al tenant del fallo definitivo y la verificación de que el fallo de correo no cambia `SolicitudAsignacion.estado`
- [ ] T046 [US1] Auditar en `asignaciones/services.py`/`asignaciones/tasks.py` cada cierre de `EnvioCorreo` con `EnvioCorreo/estado` `REINTENTANDO→EXITOSO` o `→FALLIDO`, incluyendo `numero_intento`, destinatario, archivo, hash y `error_mensaje`, sin cuerpo del correo ni credenciales

**Checkpoint**: US1 funcional e independiente; el Excel se envía, se registra cada intento y el fallo no bloquea la solicitud.

---

## Fase 4: US2 — Bandeja de despachos y notificaciones en tiempo real (P2)

**Objetivo**: el Responsable de almacén ve solo las solicitudes de su región, filtra por estado,
recibe un evento SSE con sonido y aviso visual al llegar una nueva solicitud y cuenta con polling de
respaldo si SSE falla.

**Prueba independiente**: como almacén de Ayacucho, abrir `/almacen/bandeja/`; ver solo solicitudes
de esa región, sin `BORRADOR` ni `CANCELADA`; enviar una solicitud desde un tenant de Ayacucho y
recibir el evento SSE con el contador actualizado; con el almacén de otra región conectado, no
recibir el evento; bloquear SSE y comprobar el polling cada 30 s.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T047 [P] [US2] Pruebas de contrato de `GET /almacen/bandeja/` en `tests/contract/test_almacen_bandeja_http.py`: **CA-04** `200` con solicitudes solo de la región, columnas fecha/tenant/técnico/totales/estado, `data-pendientes`, filtro `estado`, paginación de 50, exclusión de `BORRADOR`/`CANCELADA`, `403` para Admin/Tenant y `302` sin sesión
- [ ] T048 [P] [US2] Pruebas de contrato de **CA-05** en `tests/contract/test_almacen_sse_http.py`: `200` `text/event-stream; charset=utf-8`, `Cache-Control: no-cache`, `event: notificacion`, JSON parseable con `solicitud_id`/`tenant`/`tecnico`/totales/`pendientes`, heartbeat y `403`/`302`/`405` según contrato
- [ ] T049 [US2] Pruebas de contrato del polling en `tests/contract/test_almacen_sse_http.py`: `GET /almacen/notificaciones/pendientes/` devuelve `200` HTML con `data-pendientes` y `data-ultima-solicitud-id`, sin datos de otra región, y `403` para Admin/Tenant
- [ ] T050 [P] [US2] Pruebas de integración de **CA-04** en `tests/integration/test_almacen_bandeja.py`: dos regiones con solicitudes `ENVIADA`/`CONFIRMADA`/`RECHAZADA`; la bandeja de Ayacucho solo lista las suyas; una solicitud de otra región responde `404`; los totales de series/cantidad son correctos
- [ ] T051 [P] [US2] Pruebas de integración de **CA-05** en `tests/integration/test_almacen_notificaciones.py`: publicar `nueva_solicitud` y `cambio_estado` después del commit; el canal de la región A no entrega a la región B; un fallo de Redis no revierte la operación; el contador coincide con las solicitudes `ENVIADA`
- [ ] T052 [US2] Pruebas de integración del polling de respaldo en `tests/integration/test_almacen_notificaciones.py`: el fragmento refleja el número de pendientes y la última solicitud después de enviar, confirmar y rechazar

### Implementación de US2

- [ ] T053 [US2] Implementar `listar_solicitudes_almacen(region, estado=None)` en `asignaciones/services.py`: filtro por `region`, estados `ENVIADA`/`CONFIRMADA`/`RECHAZADA`, orden por `enviada_en` e `id` descendente, paginación de 50 y anotaciones `total_series`/`total_cantidad` sin N+1
- [ ] T054 [US2] Implementar `contar_solicitudes_pendientes(region)` en `asignaciones/notificaciones.py` y reutilizarlo en la bandeja, el SSE y el polling
- [ ] T055 [US2] Implementar en `asignaciones/views.py` `bandeja_almacen` (GET): `@login_required`, `validar_cuenta_almacen`, filtro `estado`, paginación, badge de pendientes y `403`/`405`
- [ ] T056 [US2] Implementar en `asignaciones/views.py` `notificaciones_sse` (GET): `@login_required`, `validar_cuenta_almacen`, `StreamingHttpResponse` `text/event-stream` con `X-Accel-Buffering: no`, suscripción al canal de la región y cierre al desconectar
- [ ] T057 [US2] Implementar en `asignaciones/notificaciones.py` `flujo_eventos_region(region, ultimo_id=None)`: generador SSE con eventos `nueva_solicitud`/`cambio_estado`, JSON compacto, heartbeat cada `ALMACEN_SSE_HEARTBEAT_SEGUNDOS` y sin filtrar eventos de otra región
- [ ] T058 [US2] Implementar en `asignaciones/views.py` `notificaciones_pendientes` (GET): fragmento HTML con `data-pendientes` y `data-ultima-solicitud-id`, alcance de la región, `403`/`405`
- [ ] T059 [US2] Publicar en `asignaciones/notificaciones.py` los eventos `nueva_solicitud` al enviar (006/007) y `cambio_estado` al confirmar o rechazar, siempre con `transaction.on_commit`, incluyendo `pendientes` recalculado
- [ ] T060 [US2] Crear `templates/almacen/bandeja.html` con tabla, filtro por estado, badge, paginación, enlaces de detalle y contenedor `data-sse-url`/`data-poll-url`; sin datos de otra región ni de stock del técnico
- [ ] T061 [US2] Implementar en `templates/almacen/bandeja.html` el cliente `EventSource`: sonido corto, toast visual, actualización del badge y recarga de la tabla al recibir eventos; si falla, polling cada 30 s a `/almacen/notificaciones/pendientes/` y sin bloquear la interfaz
- [ ] T062 [US2] Agregar a `asignaciones/urls.py` `GET /almacen/bandeja/`, `GET /almacen/notificaciones/sse/` y `GET /almacen/notificaciones/pendientes/`, sin rutas de escritura adicionales
- [ ] T063 [US2] Verificar con `django_assert_num_queries` en `tests/integration/test_almacen_bandeja.py` que la bandeja y el contador no tienen N+1 y que la bandeja responde en menos de 1 segundo en el escenario de prueba

**Checkpoint**: US2 funcional; el almacén ve su región, recibe notificaciones y tiene respaldo por polling.

---

## Fase 5: US3 — Previsualizar, descargar y verificar el hash (P3)

**Objetivo**: el almacén previsualiza la solicitud, descarga el Excel original y el sistema verifica
SHA-256 antes de entregarlo; si el archivo fue alterado, bloquea la descarga y alerta.

**Prueba independiente**: abrir el detalle y la previsualización de una solicitud `ENVIADA`;
descargar el Excel y comprobar bytes y hash originales; modificar un byte del archivo y verificar
`409` con “El archivo fue modificado, descarga bloqueada”; probar una ruta con `..` y comprobar que
no sale de `MEDIA_ROOT`.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T064 [P] [US3] Pruebas de contrato de `GET /almacen/solicitudes/<id>/` en `tests/contract/test_almacen_acciones_http.py`: **CA-06** `200` con cabecera, líneas agrupadas, totales, hash, último envío, motivo de rechazo si aplica y botones solo en `ENVIADA`; `404` por solicitud ajena/`BORRADOR`/`CANCELADA`; `403`/`405`
- [ ] T065 [US3] Pruebas de contrato de `GET /almacen/solicitudes/<id>/previsualizar/` en `tests/contract/test_almacen_acciones_http.py`: `200` fragmento HTML sin `<html>`, con `data-solicitud-id`, líneas, totales y hash; `404`/`403`/`405`
- [ ] T066 [P] [US3] Pruebas de contrato de descarga exitosa en `tests/contract/test_almacen_descarga_http.py`: **CA-07** `200` con `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename="asignacion-<id>.xlsx"`, bytes idénticos al archivo y `Cache-Control: private, no-store`
- [ ] T067 [US3] Pruebas de contrato de **CA-12** en `tests/contract/test_almacen_descarga_http.py`: archivo alterado → `409` “El archivo fue modificado, descarga bloqueada”, sin bytes del archivo; archivo ausente → `409`; solicitud sin Excel → `404`; Admin en detalle → `403`
- [ ] T068 [P] [US3] Pruebas de integración de hash en `tests/integration/test_almacen_historicos.py`: descarga del Excel del detalle y de históricos con hash correcto; un byte modificado bloquea ambas rutas; restaurar el archivo vuelve a permitir la descarga
- [ ] T069 [P] [US3] Pruebas unitarias de ruta segura y nombre de descarga en `tests/unit/test_almacen_hash.py`: rechazo de `..`, ruta absoluta, enlace fuera de `MEDIA_ROOT`; nombre `asignacion-<id>.xlsx` sin NIF ni correo; comparación en tiempo constante

### Implementación de US3

- [ ] T070 [US3] Implementar en `asignaciones/services.py` `obtener_detalle_almacen(region, solicitud_id)` con cabecera, líneas agrupadas, totales, hash, último envío, motivo de rechazo y `select_related`/`prefetch_related` sin N+1
- [ ] T071 [US3] Implementar en `asignaciones/views.py` `detalle_almacen` (GET): `@login_required`, `validar_cuenta_almacen`, `obtener_solicitud_almacen`, contexto del detalle y `404`/`403`/`405`
- [ ] T072 [US3] Implementar en `asignaciones/views.py` `previsualizar_solicitud` (GET): mismo alcance y datos que el detalle, respuesta de fragmento HTML para modal HTMX, `404`/`403`/`405`
- [ ] T073 [US3] Implementar en `asignaciones/services.py` `verificar_hash_excel(solicitud, contenido)` con `hashlib.sha256` y `hmac.compare_digest`; lanzar `HashNoCoincide` con el mensaje exacto y no devolver contenido si no coincide
- [ ] T074 [US3] Implementar en `asignaciones/services.py` `preparar_descarga_excel(solicitud)`: resolver la ruta dentro de `MEDIA_ROOT`, leer el archivo, verificar el hash, devolver `(contenido, nombre_seguro, content_type)` y lanzar `ArchivoExcelNoDisponible`/`HashNoCoincide`
- [ ] T075 [US3] Implementar en `asignaciones/views.py` `descargar_excel_solicitud` (GET): `@login_required`, alcance del almacén, `preparar_descarga_excel`, `FileResponse`/`HttpResponse` con cabeceras seguras y `404`/`409`/`403`/`405`
- [ ] T076 [US3] Crear `templates/almacen/detalle.html` y `templates/almacen/_previsualizacion.html` con cabecera, líneas agrupadas, totales, hash, último envío, motivo de rechazo y enlaces de descarga; sin edición ni cancelación del tenant
- [ ] T077 [US3] Agregar a `asignaciones/urls.py` `GET /almacen/solicitudes/<int:solicitud_id>/`, `GET /almacen/solicitudes/<int:solicitud_id>/previsualizar/` y `GET /almacen/solicitudes/<int:solicitud_id>/descargar-excel/`
- [ ] T078 [US3] Asegurar en `asignaciones/services.py` que la descarga no modifica la solicitud, no reescribe el Excel, no actualiza `excel_hash` y no expone la ruta física ni el hash en cabeceras

**Checkpoint**: US3 funcional; previsualización, descarga y bloqueo por hash operan de forma independiente.

---

## Fase 6: US4 — Confirmar la solicitud y actualizar stock (P4)

**Objetivo**: el Responsable de almacén confirma una solicitud `ENVIADA`; la solicitud pasa a
`CONFIRMADA`, se fija `confirmada_en` y 008 mueve series y stock en la misma transacción, sin doble
descuento ni cantidades negativas.

**Prueba independiente**: confirmar una solicitud `ENVIADA` con series y no seriados; verificar
`CONFIRMADA`, `confirmada_en`, series `ASIGNADA`, `StockTecnico` arriba y `StockGeneral` abajo;
repetir la confirmación y recibir `409`; forzar stock insuficiente y comprobar la reversión completa.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T079 [P] [US4] Pruebas de contrato de `POST /almacen/solicitudes/<id>/confirmar/` en `tests/contract/test_almacen_acciones_http.py`: **CA-08** `302` desde `ENVIADA`; `409` “Solo se pueden confirmar solicitudes enviadas” desde otros estados; `404` por solicitud ajena; `403` para Admin/Tenant/región ajena; `405` para `GET`/`PUT`/`DELETE`
- [ ] T080 [P] [US4] Pruebas de integración de **CA-08** en `tests/integration/test_almacen_confirmacion.py`: `confirmar_solicitud` fija `CONFIRMADA` y `confirmada_en`, llama a `stock.services.actualizar_stock_confirmacion_asignacion` y deja series `ASIGNADA` con `tecnico`/`asignada_en`, stock técnico incrementado y stock general decrementado
- [ ] T081 [US4] Pruebas de integración de reversión en `tests/integration/test_almacen_confirmacion.py`: stock general insuficiente o fallo de auditoría revierten solicitud, series, stock y auditoría; la solicitud sigue `ENVIADA` y 008 no crea cantidades negativas
- [ ] T082 [US4] Pruebas de integración de concurrencia en `tests/integration/test_almacen_confirmacion.py`: dos confirmaciones simultáneas de la misma solicitud dejan una sola `CONFIRMADA`, un `409` en la segunda y un solo movimiento de stock
- [ ] T083 [P] [US4] Pruebas de auditoría de la confirmación en `tests/integration/test_almacen_auditoria.py`: un registro `SolicitudAsignacion/estado` `ENVIADA→CONFIRMADA` con `confirmada_en` y actor; los registros de serie y stock aparecen una sola vez, escritos por 008; sin secretos

### Implementación de US4

- [ ] T084 [US4] Implementar `confirmar_solicitud(solicitud, actor)` en `asignaciones/services.py`: validar cuenta, exigir `ENVIADA`, abrir `transaction.atomic`, bloquear la solicitud con `select_for_update`, releer y confirmar el estado dentro del bloqueo
- [ ] T085 [US4] Implementar en `confirmar_solicitud` la llamada a `stock.services.actualizar_stock_confirmacion_asignacion(solicitud, actor)` dentro de la misma transacción; 007 no escribe `StockGeneral`/`StockTecnico` ni cambia series directamente
- [ ] T086 [US4] Implementar en `confirmar_solicitud` el cambio a `CONFIRMADA`, `confirmada_en=timezone.now()`, `actualizado_por=actor` y la auditoría `SolicitudAsignacion/estado` con el actor de la sesión
- [ ] T087 [US4] Implementar en `asignaciones/views.py` `confirmar_solicitud_almacen` (POST): `@login_required`, `validar_cuenta_almacen`, CSRF, `obtener_solicitud_almacen`, llamada al servicio, `302` al detalle y `409`/`404`/`403`/`405`
- [ ] T088 [US4] Agregar a `asignaciones/urls.py` `POST /almacen/solicitudes/<int:solicitud_id>/confirmar/` sin ruta `GET`
- [ ] T089 [US4] Agregar en `templates/almacen/detalle.html` el botón “Confirmar” solo para `ENVIADA`, con `hx-post`, `hx-disabled-elt` y confirmación visual; sin acción para Admin ni para estados terminales
- [ ] T090 [US4] Publicar después del commit el evento `cambio_estado` `ENVIADA→CONFIRMADA` y actualizar el contador de pendientes, sin publicar dentro de la transacción
- [ ] T091 [US4] Mapear en `asignaciones/views.py` los errores de 008 y de estado a `409` con mensaje seguro, sin exponer trazas ni detalles de stock de otro tenant

**Checkpoint**: US4 funcional; la confirmación cierra el ciclo y el stock se mueve una sola vez.

---

## Fase 7: US5 — Rechazar con motivo y liberar series (P5)

**Objetivo**: el Responsable de almacén rechaza una solicitud `ENVIADA` con un motivo obligatorio;
la solicitud pasa a `RECHAZADA`, las series vuelven a `DISPONIBLE`, las cantidades no seriadas se
liberan y el tenant recibe el motivo.

**Prueba independiente**: rechazar una solicitud `ENVIADA` con motivo; verificar `RECHAZADA`,
`motivo_rechazo`, `rechazada_en`, series `DISPONIBLE`, cantidades disponibles de nuevo y aviso al
tenant; intentar rechazar sin motivo y recibir `400`; repetir el rechazo y recibir `409`.

### Pruebas de US5 (escribir primero, deben fallar)

- [ ] T092 [P] [US5] Pruebas de contrato de `POST /almacen/solicitudes/<id>/rechazar/` en `tests/contract/test_almacen_acciones_http.py`: **CA-09** `302` con motivo; `409` “Solo se pueden rechazar solicitudes enviadas” desde otros estados; `404` por solicitud ajena; `403` para Admin/Tenant/región ajena; `405`
- [ ] T093 [US5] Pruebas de contrato de **CA-10** en `tests/contract/test_almacen_acciones_http.py`: motivo vacío o solo espacios → `400` “Debe indicar el motivo del rechazo” y sin cambios de estado
- [ ] T094 [US5] Pruebas de contrato del límite de motivo en `tests/contract/test_almacen_acciones_http.py`: más de 1000 caracteres → `400` “El motivo del rechazo no puede superar los 1000 caracteres”
- [ ] T095 [P] [US5] Pruebas de integración de **CA-09** en `tests/integration/test_almacen_rechazo.py`: `rechazar_solicitud` deja `RECHAZADA`, guarda motivo y `rechazada_en`, cambia cada serie `RESERVADA→DISPONIBLE` y audita `Serie/estado` por serie
- [ ] T096 [US5] Pruebas de integración de liberación de no seriados en `tests/integration/test_almacen_rechazo.py`: tras el rechazo, el disponible de 006 vuelve a contar la cantidad; no se escribe stock ni se crea tabla de reservas
- [ ] T097 [P] [US5] Pruebas de integración de notificación al tenant en `tests/integration/test_almacen_notificaciones.py`: el detalle de 006 muestra `motivo_rechazo` y `rechazada_en`; el correo best-effort usa el buzón del tenant; un fallo de correo no revierte el rechazo
- [ ] T098 [US5] Pruebas de integración de concurrencia en `tests/integration/test_almacen_rechazo.py`: dos rechazos simultáneos dejan una sola `RECHAZADA`, un `409` en el segundo y ninguna serie `RESERVADA`
- [ ] T099 [P] [US5] Pruebas de auditoría del rechazo en `tests/integration/test_almacen_auditoria.py`: `SolicitudAsignacion/estado` `ENVIADA→RECHAZADA` con motivo y `rechazada_en`; `Serie/estado` por cada serie; sin secretos ni `tenant_id` separado

### Implementación de US5

- [ ] T100 [US5] Implementar `rechazar_solicitud(solicitud, motivo, actor)` en `asignaciones/services.py`: validar cuenta y `ENVIADA`, normalizar el motivo con `strip()`, exigir no vacío y máximo 1000 caracteres, y abrir `transaction.atomic` con bloqueo de la solicitud
- [ ] T101 [US5] Implementar en `rechazar_solicitud` el cambio a `RECHAZADA`, `motivo_rechazo`, `rechazada_en`, `actualizado_por`, la liberación de series `RESERVADA→DISPONIBLE` y la auditoría de solicitud y series; no escribir stock
- [ ] T102 [US5] Implementar en `asignaciones/views.py` `rechazar_solicitud_almacen` (POST): `@login_required`, `validar_cuenta_almacen`, CSRF, `obtener_solicitud_almacen`, `RechazoForm`, llamada al servicio, `302` al detalle y `400`/`409`/`404`/`403`/`405`
- [ ] T103 [US5] Completar en `asignaciones/forms.py` `RechazoForm` con el mensaje exacto “Debe indicar el motivo del rechazo”, límite de 1000 caracteres y widget `Textarea`; el formulario no acepta `estado`, `tenant` ni `region`
- [ ] T104 [US5] Agregar a `asignaciones/urls.py` `POST /almacen/solicitudes/<int:solicitud_id>/rechazar/` sin ruta `GET`
- [ ] T105 [US5] Crear `templates/almacen/_formulario_rechazo.html` con textarea obligatoria, error en línea, botón “Enviar rechazo”, `hx-post`, `hx-disabled-elt` y sin campos ocultos de tenant/región/estado
- [ ] T106 [US5] Implementar en `asignaciones/correo.py` la notificación best-effort al tenant del rechazo, con el motivo y sin secretos; el aviso persistente vive en `SolicitudAsignacion.motivo_rechazo` y se muestra en el detalle de 006
- [ ] T107 [US5] Publicar después del commit el evento `cambio_estado` `ENVIADA→RECHAZADA` y actualizar el contador de pendientes, sin publicar dentro de la transacción

**Checkpoint**: US5 funcional; el rechazo exige motivo, libera series y cantidades y notifica al tenant.

---

## Fase 8: US6 — Buscar Excels históricos (P6)

**Objetivo**: el Administrador de plataforma busca Excels de todas las regiones y el almacén solo de
la suya, filtrando por fecha, tenant, técnico y estado, con hash visible y descarga verificada.

**Prueba independiente**: crear solicitudes con Excel en dos regiones; como Admin, filtrar por fecha
y ver ambas; como almacén, ver solo su región; comprobar una fila por solicitud y no por intento de
correo; descargar un histórico con hash correcto y recibir `409` si se altera; el tenant recibe
`403`.

### Pruebas de US6 (escribir primero, deben fallar)

- [ ] T108 [P] [US6] Pruebas de contrato de `GET /almacen/excels-historicos/` en `tests/contract/test_almacen_historicos_http.py`: **CA-11** `200` con ID, fecha, tenant, técnico, estado, hash de 64 hex y estado del último envío; filtros por fecha/tenant/técnico/estado; paginación de 50; Admin global y Almacén por región; `403` para Tenant y `302` sin sesión
- [ ] T109 [US6] Pruebas de contrato de `GET /almacen/excels-historicos/<id>/descargar/` en `tests/contract/test_almacen_historicos_http.py`: `200` con el `.xlsx` verificado para Admin y Almacén; `404` fuera de alcance o sin Excel; `409` por hash alterado; `403` para Tenant; `405`
- [ ] T110 [P] [US6] Pruebas de integración de **CA-11** en `tests/integration/test_almacen_historicos.py`: búsqueda por rango de fechas devuelve los Excels de esa fecha con sus hashes; filtros combinados de tenant, técnico y estado; sin N+1
- [ ] T111 [US6] Pruebas de integración de unicidad de fila en `tests/integration/test_almacen_historicos.py`: una solicitud con varios intentos de correo aparece una sola vez; una solicitud sin Excel no aparece; el estado mostrado es el del último intento
- [ ] T112 [P] [US6] Pruebas de aislamiento en `tests/integration/test_almacen_aislamiento.py`: el Administrador ve todas las regiones; el almacén solo la suya; una solicitud de otra región responde `404`; `tenant_id`/`region_id` forzados se ignoran; RLS si está disponible

### Implementación de US6

- [ ] T113 [US6] Implementar `buscar_excels_historicos(alcance, region, filtros)` en `asignaciones/services.py`: fuente `SolicitudAsignacion` con `excel_ruta != ""`, alcance `REGION`/`GLOBAL`, filtros de fecha/tenant/técnico/estado, orden por `fecha`/`id` descendente, paginación de 50 y `Subquery` del último intento
- [ ] T114 [US6] Implementar `obtener_excel_historico(alcance, region, solicitud_id)` en `asignaciones/services.py`: aplica el mismo alcance, exige `excel_ruta` y lanza `EnvioNoExiste` (`404`) si no corresponde
- [ ] T115 [US6] Implementar en `asignaciones/views.py` `excels_historicos` (GET): `@login_required`, `validar_cuenta_consulta`, `FiltrosHistoricosForm`, contexto paginado y `403`/`405`
- [ ] T116 [US6] Implementar en `asignaciones/views.py` `descargar_excel_historico` (GET): alcance de consulta, `preparar_descarga_excel`, verificación de hash y `200`/`404`/`409`/`403`/`405`
- [ ] T117 [US6] Agregar a `asignaciones/urls.py` `GET /almacen/excels-historicos/` y `GET /almacen/excels-historicos/<int:solicitud_id>/descargar/`
- [ ] T118 [US6] Crear `templates/almacen/excels_historicos.html` y `templates/almacen/_fila_historico.html` con filtros, tabla, hash, estado del último envío, paginación y enlace de descarga; sin datos de otra región para el almacén
- [ ] T119 [US6] Verificar con `django_assert_num_queries` en `tests/integration/test_almacen_historicos.py` que la búsqueda paginada no tiene N+1 y que la descarga no relee la solicitud por cada fila

**Checkpoint**: US6 funcional; Admin y Almacén buscan y descargan históricos con el alcance correcto.

---

## Fase 9: Polish y preocupaciones transversales

**Propósito**: verificación final, cobertura de criterios, permisos, rendimiento, auditoría,
documentación y limpieza.

- [ ] T120 [P] Verificar en `05-especificaciones/007-envio-y-revision-del-almacen/quickstart.md` que cada CA-01…CA-12 tiene al menos una prueba en `tests/unit/`, `tests/integration/` o `tests/contract/`; agregar la prueba faltante si alguna no está cubierta
- [ ] T121 [P] Ejecutar `pytest` completo desde `tests/` sobre PostgreSQL y corregir cualquier fallo; no se avanza con pruebas en rojo
- [ ] T122 [P] Ejecutar `python manage.py makemigrations --check --dry-run` sobre `asignaciones/migrations/` y `python manage.py migrate --plan`; no deben quedar migraciones pendientes
- [ ] T123 [P] Ejecutar `pytest --cov=asignaciones --cov-report=term-missing` sobre `tests/` y cubrir los caminos de error de permisos, correo, SSE, hash, confirmación y rechazo
- [ ] T124 [P] Revisar `asignaciones/services.py`, `asignaciones/correo.py`, `asignaciones/tasks.py` y `asignaciones/notificaciones.py`: sin lógica de negocio en vistas, formularios ni plantillas; sin `tenant_id`/`region_id` del cliente; sin escrituras a `StockGeneral`/`StockTecnico`; sin permisos Django por cadena; sin WebSocket/Channels
- [ ] T125 [P] Revisar rendimiento con `django_assert_num_queries` en `tests/integration/test_almacen_bandeja.py`, `tests/integration/test_almacen_confirmacion.py` y `tests/integration/test_almacen_historicos.py`; bandeja, detalle, búsqueda y descarga sin N+1 y respuesta menor a 1 segundo en el escenario de prueba
- [ ] T126 [P] Revisar la auditoría en `tests/integration/test_almacen_auditoria.py`: sin contraseñas, tokens, secretos TOTP, credenciales SMTP, cuerpo del correo, contenido binario ni rutas absolutas; una sola auditoría de stock/series por confirmación
- [ ] T127 [P] Actualizar `05-especificaciones/007-envio-y-revision-del-almacen/research.md` y `plan.md` si la implementación difiere del diseño; registrar deudas (RLS no disponible, correo no configurado, limpieza de archivos) sin inventar comportamiento no especificado
- [ ] T128 [P] Ejecutar la matriz de permisos de `contracts/http-endpoints.md` para las 10 rutas y los perfiles `ADMIN_PLATAFORMA`, `RESPONSABLE_ALMACEN`, `USUARIO_TENANT`, tenant suspendido, cuenta inactiva y anónimo; corregir cualquier desviación de `403`/`404`/`302`/`405`
- [ ] T129 [P] Verificar el aislamiento por región en `tests/integration/test_almacen_aislamiento.py`: bandeja, detalle, SSE, polling, históricos y descargas no revelan datos de otra región; `tenant_id`/`region_id` forzados se ignoran
- [ ] T130 Ejecutar los escenarios de `05-especificaciones/007-envio-y-revision-del-almacen/quickstart.md`, marcar los criterios de salida y reportar el resultado antes de cerrar la feature

---

## Dependencias y orden de ejecución

### Dependencias de fase

- **Setup (Fase 1)**: sin dependencias; las correcciones T002–T006 deben completarse antes de implementar.
- **Fundacional (Fase 2)**: depende de Setup y **bloquea** las seis historias.
- **US1 (Fase 3)**: depende de Fundacional; no depende de otras historias.
- **US2 (Fase 4)**: depende de Fundacional; puede probarse con una solicitud `ENVIADA` creada por fixture y no requiere que US1 haya enviado correo.
- **US3 (Fase 5)**: depende de Fundacional; usa el Excel y el hash de 006.
- **US4 (Fase 6)**: depende de Fundacional y de la parte de confirmación de 008; no depende de US1/US2.
- **US5 (Fase 7)**: depende de Fundacional; no depende de US4.
- **US6 (Fase 8)**: depende de Fundacional y de US3 para la descarga verificada.
- **Polish (Fase 9)**: depende de las historias que se quieran entregar.

### Dependencias entre historias

- **US1 (P1)**: envía y registra; es la base de la entrega por correo.
- **US2 (P2)**: bandeja y SSE; usa solicitudes `ENVIADA` de 006 y no requiere US1.
- **US3 (P3)**: previsualiza, descarga y verifica; usa el Excel de 006.
- **US4 (P4)**: confirma y delega stock en 008; requiere la parte de confirmación de 008.
- **US5 (P5)**: rechaza, libera series y notifica; puede avanzar en paralelo con US4.
- **US6 (P6)**: busca históricos; reutiliza la descarga verificada de US3.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Servicios antes que vistas; vistas antes que plantillas.
- La lógica de negocio permanece en `services.py`, `correo.py`, `tasks.py` y `notificaciones.py`.
- Una historia se completa y se valida antes de pasar a la siguiente prioridad.

## Oportunidades de paralelización

- T002, T003, T004, T005, T006, T007, T008, T009, T010 y T011 pueden ejecutarse en paralelo si no comparten archivos.
- T012, T013, T014 y T015 (pruebas fundacionales) pueden escribirse en paralelo.
- T016 y T017 comparten `asignaciones/models.py`: no ejecutar en paralelo entre sí.
- T020–T026 comparten `asignaciones/services.py`: secuenciar o dividir por archivos; T025 usa `asignaciones/notificaciones.py`.
- Las pruebas de US1 T031, T033, T034, T035, T036, T037 y T038 pueden escribirse en paralelo entre archivos; T031 y T032 comparten `tests/unit/test_envio_correo.py` y deben secuenciarse.
- Las pruebas de US2 T047, T048, T050 y T051 pueden escribirse en paralelo; T048 y T049 comparten `tests/contract/test_almacen_sse_http.py`.
- Las pruebas de US3 T064, T066, T068 y T069 pueden escribirse en paralelo; T064/T065 y T066/T067 comparten archivo.
- Las pruebas de US4 T079, T080 y T083 pueden escribirse en paralelo; T081/T082 comparten `tests/integration/test_almacen_confirmacion.py`.
- Las pruebas de US5 T092, T095, T097 y T099 pueden escribirse en paralelo; T093/T094 comparten contrato y T096/T098 comparten integración.
- Las pruebas de US6 T108, T110 y T112 pueden escribirse en paralelo; T108/T109 comparten contrato y T110/T111 comparten integración.
- T120–T129 del polish pueden ejecutarse en paralelo; T121 y T130 requieren que las historias estén completas.

## Ejemplo de paralelización: US1

```text
# Pruebas de US1 en archivos distintos:
Task: "Unitarias de correo en tests/unit/test_envio_correo.py"
Task: "Integración CA-01/CA-02/CA-03 en tests/integration/test_envio_registro.py"
Task: "Integración de on_commit en tests/integration/test_envio_registro.py"
```

## Ejemplo de paralelización: US2

```text
# Pruebas de US2 en archivos distintos:
Task: "Contrato de bandeja en tests/contract/test_almacen_bandeja_http.py"
Task: "Contrato SSE en tests/contract/test_almacen_sse_http.py"
Task: "Integración de región en tests/integration/test_almacen_bandeja.py"
Task: "Integración de notificaciones en tests/integration/test_almacen_notificaciones.py"
```

## Estrategia de implementación

### MVP primero

1. Completar Setup y Fundacional.
2. Completar US1: enviar el Excel, registrar intentos y reintentar.
3. Completar US2: bandeja y notificaciones.
4. **DETENERSE y VALIDAR**: el correo llega, el almacén ve la solicitud en su bandeja y recibe el
   aviso en tiempo real. Este es el MVP operativo de 007; US1 sola solo envía correo.
5. Completar US3, US4, US5 y US6 para previsualización, confirmación, rechazo e históricos.

### Entrega incremental

1. Setup + Fundacional → base lista.
2. US1 → correo y trazabilidad de intentos.
3. US2 → bandeja y tiempo real; MVP operativo.
4. US3 → previsualización, descarga y verificación de hash.
5. US4 → confirmación y stock; cierre del despacho.
6. US5 → rechazo y liberación; cierre alternativo.
7. US6 → históricos y consulta del Administrador.

### Estrategia de equipo

- Una persona completa Setup + Fundacional.
- Después, una persona puede tomar US1, otra US2 y otra US3 con fixtures; US4 y US5 pueden avanzar
  en paralelo si la parte de confirmación de 008 está lista; US6 espera a US3 para reutilizar la
  descarga.
- Evitar que dos personas editen `asignaciones/services.py` a la vez; dividir por archivos o
  secuenciar. `asignaciones/notificaciones.py` y `asignaciones/tasks.py` permiten paralelismo.

## Cobertura de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US1 | T033 envío exitoso y registro |
| CA-02 | US1 | T034 reintentos fijos cada 5 minutos |
| CA-03 | US1 | T035 registro completo e inmutable |
| CA-04 | US2 | T047, T050 bandeja solo de la región |
| CA-05 | US2 | T048, T051 notificación SSE |
| CA-06 | US3 | T064, T065 previsualización y detalle |
| CA-07 | US3 | T066, T068 verificación de hash al descargar |
| CA-08 | US4 | T079, T080 confirmación y stock |
| CA-09 | US5 | T092, T095 rechazo, liberación y aviso |
| CA-10 | US5 | T093 comentario obligatorio |
| CA-11 | US6 | T108, T110 búsqueda de históricos |
| CA-12 | US3 | T067, T068 hash alterado bloquea la descarga |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id`, `region_id`, `destinatario`, `hash` ni `estado` del cliente.
- 007 no crea tablas de series ni de stock, no regenera el Excel y no implementa la creación de
  solicitudes.
- Las correcciones documentales T002–T006 son obligatorias antes de implementar (principio VIII).
- Evitar tareas vagas y conflictos de archivo; `asignaciones/services.py` es el archivo de mayor
  contención y debe secuenciarse.
