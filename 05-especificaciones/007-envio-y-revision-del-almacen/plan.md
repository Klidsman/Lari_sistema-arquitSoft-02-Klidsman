# Plan técnico: 007 Envío y Revisión del Almacén

**Branch**: `007-envio-y-revision-del-almacen` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/007-envio-y-revision-del-almacen/spec.md`

**Input**: Spec en `05-especificaciones/007-envio-y-revision-del-almacen/spec.md`

## Summary

Implementar la entrega del Excel de asignación al buzón del almacén de la región, el registro
inmutable de cada intento de envío, la bandeja de despachos del Responsable de almacén con
notificaciones en tiempo real y el cierre del ciclo de vida iniciado en 006: `ENVIADA→CONFIRMADA`
y `ENVIADA→RECHAZADA`. La confirmación delega el movimiento de series y stock en los servicios de
008 y fija `confirmada_en`; el rechazo exige motivo, libera las series `RESERVADA→DISPONIBLE` y
notifica al tenant. También se implementan la previsualización, la descarga del Excel original y la
búsqueda de Excels históricos con verificación SHA-256.

007 **no** crea una segunda tabla de series, **no** duplica tablas de stock, **no** regenera el Excel
de 006, **no** implementa la creación de solicitudes y **no** modifica recojos, traspasos ni
conciliaciones. El archivo Excel, su ruta y su hash son los que 006 generó y archivó al enviar.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX + plantillas; sin SPA ni API REST |
| Correo | `django.core.mail` con `EMAIL_BACKEND` configurable; adjunto `.xlsx` desde `MEDIA_ROOT` |
| Cola | Celery + Redis; tareas de envío y reintento |
| Tiempo real | SSE con `StreamingHttpResponse` y pub/sub de Redis; sin Django Channels ni WebSocket |
| Excel | `openpyxl` en 006; 007 solo lee y verifica el archivo archivado |
| Hash | SHA-256 con `hashlib` y comparación `hmac.compare_digest` |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL; backend de correo `locmem` |
| Apps | `asignaciones` (modelo, servicios, tareas, vistas); consumidor de `acceso`, `tenants`, `auditoria`, `series` y `stock` |
| Rutas | `asignaciones/urls.py` bajo el prefijo `/almacen/` |
| Plantillas | `templates/almacen/` |
| Pruebas | `tests/{unit,integration,contract}/` |
| Dependencias nuevas | Ninguna; `redis` ya forma parte del stack de Celery |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware` con `request.usuario`,
  `request.rol`, `request.tenant` y `request.region`; roles `ADMIN_PLATAFORMA`,
  `USUARIO_TENANT` y `RESPONSABLE_ALMACEN`; `tenants.Region` con `almacen` 1:1 y
  `tenants.Almacen` con `centro`, `codigo_almacen`, `buzon` y `activo`; `auditoria.RegistroCambio` y
  `auditoria.services.registrar_cambio`.
- **004**: `series.Serie` con `estado` (`DISPONIBLE`, `RESERVADA`, `ASIGNADA`) y unicidad global.
  007 cambia `RESERVADA→DISPONIBLE` al rechazar; 008 cambia `RESERVADA→ASIGNADA` al confirmar.
- **006**: `asignaciones.SolicitudAsignacion`, `LineaAsignacion`, `excel_ruta`, `excel_hash`,
  `excel_generado_en`, `enviada_en`, `confirmada_en` y el servicio `enviar_solicitud`, que deja la
  solicitud en `ENVIADA` con el Excel archivado.
- **008 (parte de confirmación)**: `stock.StockGeneral`, `stock.StockTecnico` y
  `stock.services.actualizar_stock_confirmacion_asignacion(solicitud, actor)`. 007 no escribe stock
  ni cambia series al confirmar: lo hace 008 dentro de la misma transacción.
- **Infraestructura**: worker Celery y Redis operativos; `MEDIA_ROOT` accesible por la web y por el
  worker; backend de correo configurado.

Si falta cualquiera de estos prerrequisitos, la implementación se detiene y se reporta; no se
sustituye con una tabla, un servicio local ni un mecanismo de notificación paralelo.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | El almacén solo ve solicitudes de su `region`; el Administrador solo consulta Excels históricos globales y no opera. La región sale de `request.usuario.region`, nunca de la URL o del `POST`. Una solicitud de otra región responde `404`. `EnvioCorreo` lleva `tenant` y `region` denormalizados para RLS y consultas. |
| II. Jerarquía Región → Tenant → Técnico | PASA | La bandeja filtra por `solicitud.region` (instantánea de `tenant.region` al enviar). El destinatario es `solicitud.region.almacen.buzon`. No se acepta `region_id` del cliente. |
| III. Invariantes de stock | PASA | 007 no escribe `StockGeneral` ni `StockTecnico`. Al confirmar llama a 008, que valida stock suficiente, nunca deja cantidades negativas y aplica el movimiento en la misma transacción. Al rechazar, el reservado de no seriados se libera porque solo se calcula sobre solicitudes `ENVIADA`. |
| IV. Identidad y unicidad de series | PASA | Se usa `series.Serie`. La confirmación cambia `RESERVADA→ASIGNADA` mediante 008; el rechazo cambia `RESERVADA→DISPONIBLE` en 007. No se crea otra tabla ni se duplica el número de serie. |
| V. Integridad transaccional | PASA | Confirmación, rechazo, cambios de serie, stock y auditoría ocurren en una sola `transaction.atomic`. El correo se dispara con `transaction.on_commit` y nunca dentro de la transacción de envío. Un fallo de correo no revierte la solicitud. |
| VI. Auditoría inmutable y trazabilidad | PASA | Se auditan `SolicitudAsignacion/estado`, `Serie/estado`, motivo de rechazo y resultado de cada intento de envío. No se auditan contraseñas, tokens, secretos TOTP ni el contenido binario del Excel. |
| VII. Autoridad del reporte de Lari y aprobación humana | PASA | La confirmación o el rechazo son siempre una acción humana del Responsable de almacén; el sistema no confirma automáticamente. 007 no procesa el reporte de Lari. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA-01…CA-12 tiene al menos una prueba. La lógica vive en `asignaciones/services.py`, `asignaciones/correo.py` y `asignaciones/notificaciones.py`; las vistas solo orquestan. No se agregan dependencias: SSE usa Redis, ya presente para Celery. |

**Post-design re-check**: PASA. El diseño final no crea tablas de stock ni de series, no duplica la
generación de Excel, no usa permisos Django por cadena, no usa WebSocket/Channels, no acepta
`tenant_id`/`region_id` del cliente y no deja la descarga sin verificación de hash.

## Project Structure

```text
asignaciones/
├── correo.py                 # programación y envío del correo
├── tasks.py                  # tareas Celery de envío y reintento
├── notificaciones.py         # publicación SSE y contador de pendientes
├── services.py               # confirmación, rechazo, bandeja, búsqueda y hash
├── views.py                  # vistas /almacen/
├── urls.py                   # rutas /almacen/
├── models.py                 # EnvioCorreo y campos nuevos de SolicitudAsignacion
├── forms.py                  # formulario de rechazo y filtros de búsqueda
└── migrations/
    ├── 0003_envio_correo.py
    └── 0004_envio_correo_rls.py

templates/almacen/
├── bandeja.html
├── detalle.html
├── _previsualizacion.html
├── _formulario_rechazo.html
├── _notificacion.html
├── excels_historicos.html
└── _fila_historico.html

tests/
├── unit/
│   ├── test_envio_correo.py
│   ├── test_almacen_servicios.py
│   └── test_almacen_hash.py
├── integration/
│   ├── test_envio_registro.py
│   ├── test_almacen_bandeja.py
│   ├── test_almacen_confirmacion.py
│   ├── test_almacen_rechazo.py
│   ├── test_almacen_historicos.py
│   ├── test_almacen_notificaciones.py
│   ├── test_almacen_auditoria.py
│   └── test_almacen_aislamiento.py
└── contract/
    ├── test_almacen_bandeja_http.py
    ├── test_almacen_acciones_http.py
    ├── test_almacen_descarga_http.py
    ├── test_almacen_historicos_http.py
    ├── test_almacen_sse_http.py
    └── test_almacen_permisos_http.py
```

También se modifican:

- `config/settings/base.py`: `ENVIOS_MAX_INTENTOS = 4` (intento inicial + 3 reintentos),
  `ENVIOS_INTERVALO_REINTENTO_SEGUNDOS = 300`, `ENVIOS_REMITENTE`, `ALMACEN_ALERTA_ASUNTO`,
  `ALMACEN_SSE_PREFIJO_CANAL = "almacen:region:"`, `ALMACEN_SSE_HEARTBEAT_SEGUNDOS = 25` y
  `REDIS_NOTIFICACIONES_URL` (por defecto el broker de Celery), todos configurables por entorno.
- `config/urls.py`: incluir `asignaciones.urls` bajo el prefijo `/almacen/`.
- `templates/base.html`: enlace a Bandeja de despachos visible solo para `RESPONSABLE_ALMACEN`.
- `asignaciones/models.py`: `EnvioCorreo`, `motivo_rechazo` y `rechazada_en`.
- `asignaciones/services.py`: ganchos de confirmación/rechazo y consultas del almacén.
- `06-solicitud-de-asignacion`: `transaction.on_commit` para programar el envío y visibilidad del
  fallo definitivo de correo en el detalle.

## Modelo de datos

### `asignaciones.EnvioCorreo`

```python
class EnvioCorreo(models.Model):
    solicitud = models.ForeignKey(
        SolicitudAsignacion,
        on_delete=models.PROTECT,
        related_name="envios_correo",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="envios_correo",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="envios_correo",
    )
    numero_intento = models.PositiveIntegerField()
    destinatario = models.EmailField()
    archivo = models.CharField(max_length=255)
    hash_sha256 = models.CharField(max_length=64)
    estado = models.CharField(
        max_length=20,
        choices=[
            ("REINTENTANDO", "Reintentando"),
            ("EXITOSO", "Exitoso"),
            ("FALLIDO", "Fallido"),
        ],
        default="REINTENTANDO",
    )
    error_mensaje = models.TextField(blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    enviado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["solicitud", "numero_intento"]
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "numero_intento"],
                name="envio_correo_intento_unico",
            ),
            models.CheckConstraint(
                condition=Q(numero_intento__gte=1),
                name="envio_correo_numero_intento_positivo",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["REINTENTANDO", "EXITOSO", "FALLIDO"]),
                name="envio_correo_estado_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["region", "estado"], name="envio_correo_region_estado"),
            models.Index(fields=["tenant", "creado_en"], name="envio_correo_tenant_fecha"),
            models.Index(fields=["solicitud", "numero_intento"], name="envio_correo_solicitud_intento"),
        ]
```

- Una fila por **intento** de envío; nunca una fila por correo con un contador mutable.
- `tenant` y `region` se copian de `solicitud.tenant` y `solicitud.region`; no se aceptan del
  cliente y sirven para RLS y para la búsqueda histórica.
- `destinatario` es `solicitud.region.almacen.buzon` al momento del intento.
- `archivo` es la ruta relativa a `MEDIA_ROOT` del Excel archivado por 006; 007 nunca lo regenera.
- `hash_sha256` es el hash canónico `solicitud.excel_hash`; se usa para verificar la descarga.
- `numero_intento` va de 1 a `settings.ENVIOS_MAX_INTENTOS` (4 por defecto: inicial + 3 reintentos).
- `estado` empieza en `REINTENTANDO` al programar el intento y se cierra **una sola vez** en
  `EXITOSO` o `FALLIDO`. `error_mensaje` se guarda truncado y sin trazas ni credenciales.
- Los campos de identidad (`solicitud`, `tenant`, `region`, `numero_intento`, `destinatario`,
  `archivo`, `hash_sha256`, `creado_en`) son inmutables; solo cambian `estado`, `error_mensaje` y
  `enviado_en`.

### Campos nuevos en `asignaciones.SolicitudAsignacion` (de 006)

```python
motivo_rechazo = models.TextField(blank=True, default="")
rechazada_en = models.DateTimeField(null=True, blank=True)
```

- `motivo_rechazo` se exige no vacío al rechazar y se limpia solo si la solicitud cambiara de
  estado, cosa que no ocurre porque `RECHAZADA` es terminal.
- `rechazada_en` registra el instante del rechazo; `confirmada_en` (ya existente) lo escribe 007 al
  confirmar y 006 lo usa para los días en mano.
- No se agrega `rechazada_por` ni `confirmada_por`: el actor queda en `auditoria.RegistroCambio`.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 007 |
|---|---|---|
| `SolicitudAsignacion` / `LineaAsignacion` | 006 | Solicitud a despachar, líneas, Excel y hash. 007 solo cambia estado, motivo y marcas de tiempo. |
| `series.Serie` | 004 | `RESERVADA→DISPONIBLE` al rechazar. `RESERVADA→ASIGNADA` lo hace 008 al confirmar. |
| `stock.StockGeneral` / `StockTecnico` | 008 | 007 **no** los escribe; la confirmación delega en 008. |
| `tenants.Almacen` | 001 | `buzon`, `centro`, `codigo_almacen` y `activo` del almacén de la región. |
| `auditoria.RegistroCambio` | 001 | Auditoría compartida e inmutable. |

## Migraciones

- `asignaciones/migrations/0003_envio_correo.py`: crea `EnvioCorreo`, agrega `motivo_rechazo` y
  `rechazada_en` a `SolicitudAsignacion`, con restricciones e índices.
- `asignaciones/migrations/0004_envio_correo_rls.py`: política RLS por `tenant_id` y `region_id`
  sobre `asignaciones_enviocorreo`, si la infraestructura de 001 está disponible; si no, se registra
  la deuda en `research.md`.
- No se crean envíos, solicitudes ni series por migración.
- No se modifican tablas de stock, series, recojos, traspasos ni conciliaciones.

## Servicios (lógica de negocio)

Viven en `asignaciones/services.py`, `asignaciones/correo.py` y `asignaciones/notificaciones.py`.
Las vistas, formularios y plantillas no contienen lógica de negocio.

### Excepciones

- `PermisoDenegado`: rol, cuenta o región incorrectos; `403`.
- `SolicitudNoExiste`: solicitud inexistente, de otra región o en `BORRADOR`; `404`.
- `EstadoSolicitudInvalido`: la acción no aplica al estado actual; `409`.
- `MotivoRechazoRequerido`: motivo vacío o solo espacios; `400`.
- `MotivoRechazoInvalido`: motivo mayor a 1000 caracteres; `400`.
- `BuzonAlmacenNoConfigurado`: `region.almacen` ausente, inactivo o sin buzón válido; error de
  envío registrado, sin bloquear la solicitud.
- `ArchivoExcelNoDisponible`: el Excel no existe en disco al enviar; error de envío registrado.
- `HashNoCoincide`: el hash calculado difiere del canónico; `409` y descarga bloqueada.
- `EnvioNoExiste`: envío o Excel histórico fuera de alcance; `404`.

### Permisos y alcance

- `validar_cuenta_almacen(actor)`:
  - Exige `actor.rol == Rol.RESPONSABLE_ALMACEN`, `actor.is_active`, `actor.region` no nula y
    `actor.region.activa`.
  - Exige que la región tenga `almacen` activo con buzón y parámetros.
  - Cualquier otro rol lanza `PermisoDenegado` con "No tienes permiso para gestionar despachos".
  - Devuelve la región de la sesión; no acepta `region_id` externo.
- `validar_cuenta_consulta(actor)`:
  - Permite `RESPONSABLE_ALMACEN` (alcance de su región) y `ADMIN_PLATAFORMA` (alcance global).
  - Rechaza `USUARIO_TENANT` con `PermisoDenegado`; `/almacen/` no es para el tenant.
  - Devuelve `(alcance, region)` donde `alcance` es `"REGION"` o `"GLOBAL"`.
- `obtener_solicitud_almacen(region, solicitud_id)`:
  - Busca `SolicitudAsignacion` con `region=region` y `estado` distinto de `BORRADOR` y `CANCELADA`.
  - Si no existe, es de otra región o está fuera de los estados operativos, lanza `SolicitudNoExiste`
    (`404`, sin revelar existencia).
- `validar_solicitud_confirmable(solicitud)` y `validar_solicitud_rechazable(solicitud)`:
  - Exigen `estado == "ENVIADA"`; si no, `EstadoSolicitudInvalido` con
    "Solo se pueden confirmar solicitudes enviadas" o
    "Solo se pueden rechazar solicitudes enviadas" (`409`).
- El Administrador de plataforma **no** puede confirmar ni rechazar: recibe `403`.

### Envío de correo y programación

- `programar_envio_solicitud(solicitud_id)` en `asignaciones/correo.py`:
  - Se invoca desde 006 con `transaction.on_commit` después de que la solicitud quedó `ENVIADA`.
  - Relee la solicitud; si no está `ENVIADA`, no hace nada.
  - Exige `excel_ruta` y `excel_hash`; si faltan, registra un intento `FALLIDO` y notifica al tenant.
  - Crea `EnvioCorreo(numero_intento=1, estado="REINTENTANDO", destinatario=region.almacen.buzon,
    archivo=solicitud.excel_ruta, hash_sha256=solicitud.excel_hash)`.
  - Encola `enviar_excel_solicitud.apply_async(args=[solicitud_id, 1])`.
  - Si el broker falla, cierra el intento como `FALLIDO` y notifica al tenant; no lanza hacia la
    transacción de 006 ya confirmada.
- `enviar_excel_solicitud(solicitud_id, numero_intento)` en `asignaciones/tasks.py`:
  - Relee la solicitud y el intento; valida que sigan en `ENVIADA` y `REINTENTANDO`.
  - Verifica que el archivo exista y que su hash coincida con `solicitud.excel_hash`; si no,
    cierra el intento como `FALLIDO` con "El archivo del Excel no está disponible o fue modificado".
  - Envía con `EmailMessage` el asunto, el cuerpo y el Excel adjunto; el destinatario es el de la
    fila de intento, no uno recalculado.
  - Éxito: cierra el intento como `EXITOSO`, fija `enviado_en`, audita y termina.
  - Fallo: cierra el intento como `FALLIDO` con el mensaje truncado.
  - Si `numero_intento < settings.ENVIOS_MAX_INTENTOS`, crea el siguiente intento
    (`numero_intento + 1`) y encola con `countdown=settings.ENVIOS_INTERVALO_REINTENTO_SEGUNDOS`
    (300 s fijos).
  - Si se agotaron los intentos, no reprograma y notifica al tenant el fallo definitivo.
  - Es idempotente por `(solicitud, numero_intento)`: la restricción única impide duplicados.
- `envio_definitivo_fallido(solicitud)`:
  - Verdadero si existe el intento `numero_intento == settings.ENVIOS_MAX_INTENTOS` en `FALLIDO` y
    no hay ningún intento `EXITOSO`.
  - 006 lo usa para mostrar el aviso de fallo de correo en el detalle del tenant.

### Confirmación de solicitud

- `confirmar_solicitud(solicitud, actor)` en `asignaciones/services.py`:
  - `validar_cuenta_almacen(actor)` y `validar_solicitud_confirmable(solicitud)`.
  - En `transaction.atomic`:
    - Bloquea la solicitud con `select_for_update` y la relee.
    - Confirma el estado otra vez dentro del bloqueo.
    - Invoca `stock.services.actualizar_stock_confirmacion_asignacion(solicitud, actor)`, que
      cambia las series `RESERVADA→ASIGNADA`, mueve `StockGeneral`/`StockTecnico` y audita esos
      cambios. **007 no los escribe directamente.**
    - Cambia `estado` a `CONFIRMADA`, fija `confirmada_en=timezone.now()` y
      `actualizado_por=actor`.
    - Audita `SolicitudAsignacion/estado` `ENVIADA→CONFIRMADA` con `confirmada_en`.
  - Tras el commit, publica la actualización de bandeja y notifica al tenant.
  - Devuelve la solicitud actualizada. Si 008 falla por stock insuficiente, toda la transacción se
    revierte y la solicitud sigue `ENVIADA`.
- `confirmada_en` es la única fuente de los días en mano; 007 la escribe, 006 la lee y 009/011
  deberán actualizar la fuente de custodia cuando muevan o devuelvan series.

### Rechazo de solicitud

- `rechazar_solicitud(solicitud, motivo, actor)`:
  - `validar_cuenta_almacen(actor)` y `validar_solicitud_rechazable(solicitud)`.
  - Normaliza `motivo = (motivo or "").strip()`; si queda vacío, `MotivoRechazoRequerido` con
    "Debe indicar el motivo del rechazo" (`400`); si supera 1000 caracteres,
    `MotivoRechazoInvalido`.
  - En `transaction.atomic`:
    - Bloquea la solicitud y sus series `RESERVADA` con `select_for_update`.
    - Cambia cada serie de las líneas seriadas a `DISPONIBLE`.
    - Cambia `estado` a `RECHAZADA`, guarda `motivo_rechazo`, fija `rechazada_en` y
      `actualizado_por`.
    - Audita `SolicitudAsignacion/estado` `ENVIADA→RECHAZADA` con motivo y `rechazada_en`, y
      `Serie/estado` `RESERVADA→DISPONIBLE` por cada serie.
  - Las cantidades no seriadas no requieren escritura: el reservado se calcula solo con solicitudes
    `ENVIADA`, por lo que al pasar a `RECHAZADA` dejan de descontar.
  - Tras el commit, notifica al tenant en el detalle y por correo best-effort.

### Bandeja de despachos

- `listar_solicitudes_almacen(region, estado=None)`:
  - Filtra por `region=region` y excluye `BORRADOR` y `CANCELADA`.
  - Filtra por `estado` si se recibe uno de `ENVIADA`, `CONFIRMADA`, `RECHAZADA`.
  - Ordena por `enviada_en` descendente y luego por `id` descendente; pagina a 50.
  - Anota totales con `Count`/`Sum` sobre líneas seriadas y no seriadas, sin N+1.
  - Devuelve fecha, tenant, técnico, total series, total cantidad y estado.
- `contar_solicitudes_pendientes(region)`:
  - Cuenta solicitudes `ENVIADA` de la región; alimenta el badge y el SSE.
- `obtener_detalle_almacen(region, solicitud_id)`:
  - Usa `select_related` de tenant, región, técnico y almacén y `prefetch_related` de
    `lineas__material`/`lineas__serie`.
  - Devuelve líneas agrupadas, totales, hash, estado, motivo de rechazo y el último envío.

### Búsqueda y descarga de Excels históricos

- `buscar_excels_historicos(alcance, region, filtros)`:
  - Fuente: `SolicitudAsignacion` con `excel_ruta != ""`, **no** una fila por intento de correo.
  - `alcance="REGION"` filtra por `region=region`; `alcance="GLOBAL"` no filtra por región.
  - Filtros: `fecha_desde`, `fecha_hasta` (sobre `fecha`), `tenant` (por código o id validado),
    `tecnico` (por NIF o id validado) y `estado`.
  - Ordena por `fecha` y `id` descendente; pagina a 50.
  - Cada fila muestra ID, fecha, tenant, técnico, estado, hash SHA-256 y el estado del último envío.
  - No expone solicitudes sin Excel ni intentos fallidos como si fueran Excels distintos.
- `obtener_excel_historico(alcance, region, solicitud_id)`:
  - Aplica el mismo alcance y exige `excel_ruta`; si no, `EnvioNoExiste` (`404`).
- `verificar_hash_excel(solicitud, contenido)`:
  - Calcula SHA-256 del contenido leído y lo compara con `solicitud.excel_hash` usando
    `hmac.compare_digest`.
  - Si no coincide, lanza `HashNoCoincide` con "El archivo fue modificado, descarga bloqueada"
    (`409`); no entrega el archivo.
- `preparar_descarga_excel(solicitud)`:
  - Resuelve la ruta con `Path(settings.MEDIA_ROOT) / solicitud.excel_ruta` y valida que quede
    dentro de `MEDIA_ROOT` (sin `..` ni rutas absolutas).
  - Lee el archivo, verifica el hash y devuelve `(contenido, nombre_seguro, content_type)`.
  - El nombre de descarga no contiene datos personales: `asignacion-<id>.xlsx`.

### Notificaciones en tiempo real

- `publicar_evento_region(region, evento)`:
  - Publica JSON en el canal `almacen:region:<region_id>` con `redis.Redis.from_url(
    settings.REDIS_NOTIFICACIONES_URL)`.
  - Se invoca **después del commit**; un fallo de Redis se registra y no revierte la operación.
- `canal_region(region)` devuelve `f"{settings.ALMACEN_SSE_PREFIJO_CANAL}{region.id}"`.
- `notificar_nueva_solicitud(solicitud)`:
  - Evento `nueva_solicitud` con `solicitud_id`, `tenant`, `tecnico`, `total_series`,
    `total_cantidad`, `enviada_en` y `pendientes`.
- `notificar_cambio_estado(solicitud, estado_anterior, estado_nuevo)`:
  - Evento `cambio_estado` con `solicitud_id`, `estado_anterior`, `estado_nuevo` y `pendientes`.
- `flujo_eventos_region(region, ultimo_id=None)`:
  - Generador para `StreamingHttpResponse`; se suscribe al canal, emite `event: notificacion` con
    `data:` JSON, envía un comentario de heartbeat cada
    `settings.ALMACEN_SSE_HEARTBEAT_SEGUNDOS` y cierra al desconectarse el cliente.
  - Valida la región del usuario antes de abrir el flujo; no revela eventos de otra región.
- `fragmento_pendientes(region)`:
  - Alternativa de polling: HTML con `data-pendientes`, `data-ultima-solicitud-id` y el enlace a la
    bandeja; se consulta cada 30 s si SSE no está disponible.
- El tenant **no** usa SSE: sus avisos de rechazo y de fallo definitivo de correo se muestran en el
  detalle de la solicitud de 006 y, si hay correo, se envían al buzón del tenant.

## Permisos y alcance

| Perfil | Bandeja / detalle / acciones | Excels históricos | SSE |
|---|---|---|---|
| `RESPONSABLE_ALMACEN` | Solo su región; confirma, rechaza, descarga y busca | Solo su región | Solo su región |
| `ADMIN_PLATAFORMA` | `403`; no confirma ni rechaza | Global; busca y descarga | `403` |
| `USUARIO_TENANT` | `403` en `/almacen/` | `403` | `403` |
| Anónimo | `302` al login | `302` al login | `302` al login |
| Tenant suspendido / cuenta inactiva | `403` | `403` | `403` |

- No se usan grupos ni cadenas de permisos de Django (`asignaciones.confirmar_*`).
- Las vistas comprueban rol; los servicios vuelven a validar rol, región y estado.
- Ninguna ruta acepta `tenant_id`, `region_id`, `destinatario`, `hash` ni `estado` del cliente.

## Interfaz y endpoints

| Ruta | Método | Función | Éxito |
|---|---|---|---|
| `/almacen/bandeja/` | GET | Bandeja de despachos de la región; filtro `estado`; página 50 | `200` HTML |
| `/almacen/solicitudes/<id>/` | GET | Detalle de solicitud del almacén | `200` HTML |
| `/almacen/solicitudes/<id>/previsualizar/` | GET | Fragmento HTML para previsualizar sin salir de la bandeja | `200` HTML |
| `/almacen/solicitudes/<id>/confirmar/` | POST | Confirmar `ENVIADA→CONFIRMADA` y delegar stock en 008 | `302` al detalle |
| `/almacen/solicitudes/<id>/rechazar/` | POST | Rechazar con motivo obligatorio | `302` al detalle |
| `/almacen/solicitudes/<id>/descargar-excel/` | GET | Descargar el Excel original con verificación SHA-256 | `200` `.xlsx` |
| `/almacen/excels-historicos/` | GET | Buscar Excels históricos por fecha, tenant, técnico y estado | `200` HTML |
| `/almacen/excels-historicos/<id>/descargar/` | GET | Descargar Excel histórico verificado | `200` `.xlsx` |
| `/almacen/notificaciones/sse/` | GET | Flujo SSE de la región | `200` `text/event-stream` |
| `/almacen/notificaciones/pendientes/` | GET | Fragmento de polling con contador y última solicitud | `200` HTML |

- `confirmar` y `rechazar` exigen CSRF y método `POST`; otros métodos responden `405`.
- Estado incorrecto responde `409`; solicitud ajena o inexistente, `404`; rol o región incorrectos,
  `403`.
- `descargar-excel` y `excels-historicos/<id>/descargar/` responden `409` con el mensaje de archivo
  modificado; nunca entregan un archivo no verificado.
- La bandeja no muestra `BORRADOR` ni `CANCELADA`; el detalle y las acciones tampoco.

### Pantallas y comportamiento HTMX/SSE

- **Bandeja**: tabla con fecha, tenant, técnico, totales, estado y acciones; filtro por estado;
  badge de pendientes; `EventSource` a `/almacen/notificaciones/sse/` que reproduce un sonido
  corto, muestra un toast y recarga la tabla al recibir `nueva_solicitud`.
- **Detalle**: datos de la solicitud, líneas agrupadas, totales, hash, último envío y motivo de
  rechazo si aplica; botones "Confirmar" y "Rechazar" solo en `ENVIADA`.
- **Rechazo**: formulario HTMX con `textarea` obligatorio, error en línea y `hx-disabled-elt`
  mientras se envía; el servidor revalida el motivo.
- **Históricos**: filtros de fecha, tenant, técnico y estado; tabla con hash y acción de descarga.
- **Degradación**: si `EventSource` falla, el cliente consulta
  `/almacen/notificaciones/pendientes/` cada 30 s; el contador y la bandeja siguen funcionando.

## Integraciones

- **006**: 006 envía y genera el Excel; al confirmar la transacción, programa
  `programar_envio_solicitud` con `transaction.on_commit`. 007 completa `ENVIADA→CONFIRMADA` y
  `ENVIADA→RECHAZADA`, escribe `confirmada_en`, `motivo_rechazo` y `rechazada_en`. 006 muestra el
  motivo de rechazo y el fallo definitivo de correo en el detalle.
- **008**: la confirmación llama a
  `stock.services.actualizar_stock_confirmacion_asignacion(solicitud, actor)` dentro de la misma
  transacción. 008 es dueño de las series `RESERVADA→ASIGNADA`, del stock y de su auditoría; 007
  no los duplica.
- **004**: 007 cambia `RESERVADA→DISPONIBLE` al rechazar y audita cada serie.
- **001**: región, almacén, buzón, roles, middleware y auditoría compartida.
- **Celery + Redis**: envío, reintentos fijos y pub/sub de notificaciones. El envío de correo es
  asíncrono y no bloquea la solicitud; un fallo de correo no cambia el estado `ENVIADA`.
- **Auditoría**: toda confirmación, rechazo, cambio de serie y resultado de envío se registra en la
  misma transacción; el envío asíncrono audita su propio resultado.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cuenta y región del almacén | Servicio y vista | "No tienes permiso para gestionar despachos" |
| Solicitud de otra región | Servicio | "La solicitud no existe" (`404`) |
| Estado `ENVIADA` para confirmar | Servicio | "Solo se pueden confirmar solicitudes enviadas" (`409`) |
| Estado `ENVIADA` para rechazar | Servicio | "Solo se pueden rechazar solicitudes enviadas" (`409`) |
| Motivo obligatorio | Servicio y formulario | "Debe indicar el motivo del rechazo" (`400`) |
| Motivo máximo 1000 caracteres | Servicio y formulario | "El motivo del rechazo no puede superar los 1000 caracteres" (`400`) |
| Buzón del almacén configurado | Programación del envío | "El buzón del almacén no está configurado" (registro de envío `FALLIDO`) |
| Excel existente y con hash | Tarea de envío y descarga | "El archivo del Excel no está disponible o fue modificado" |
| Hash SHA-256 coincide | Descarga | "El archivo fue modificado, descarga bloqueada" (`409`) |
| Rol del Administrador en acciones | Servicio | "No tienes permiso para gestionar despachos" (`403`) |
| Tenant en `/almacen/` | Servicio y vista | "No tienes permiso para gestionar despachos" (`403`) |

## Transacciones y concurrencia

- **Confirmación**: una `transaction.atomic` con bloqueo de la solicitud y del tenant; dentro se
  llama a 008. Dos confirmaciones simultáneas: la primera cambia a `CONFIRMADA`; la segunda
  encuentra el estado distinto de `ENVIADA` y responde `409`. El bloqueo evita dobles descuentos de
  stock.
- **Rechazo**: una `transaction.atomic` con bloqueo de la solicitud y de las series afectadas. Dos
  rechazos simultáneos: solo el primero cambia el estado y libera series; el segundo recibe `409`.
- **Orden de bloqueo**: `SolicitudAsignacion` → `Serie` por `id` ascendente → `StockGeneral`/`StockTecnico`
  dentro de 008. El orden es estable para evitar interbloqueos.
- **Envío de correo**: fuera de la transacción de 006; se programa con `on_commit`. Cada intento es
  una fila con restricción única; un reintento no duplica ni reenvía un intento ya cerrado.
- **Notificaciones**: se publican después del commit; si Redis falla, la operación de negocio ya
  está confirmada y el fallo solo se registra.
- **Descarga**: la verificación de hash se hace antes de construir la respuesta; el archivo no se
  sirve si no coincide.

## Auditoría y RLS

- Eventos auditados con `auditoria.services.registrar_cambio` en la misma transacción:
  - `SolicitudAsignacion/estado`: `ENVIADA→CONFIRMADA` con `confirmada_en`.
  - `SolicitudAsignacion/estado`: `ENVIADA→RECHAZADA` con `motivo_rechazo` y `rechazada_en`.
  - `Serie/estado`: `RESERVADA→DISPONIBLE` por cada serie rechazada.
  - `EnvioCorreo/estado`: `REINTENTANDO→EXITOSO` o `REINTENTANDO→FALLIDO` con `numero_intento`,
    destinatario y archivo; sin contenido binario ni credenciales SMTP.
- 008 audita los cambios de stock y de serie al confirmar; 007 no los duplica.
- Nunca se auditan contraseñas, tokens, secretos TOTP ni el cuerpo completo del correo.
- RLS: `asignaciones_enviocorreo` con políticas por `tenant_id` y `region_id`; la bandeja y la
  búsqueda filtran además en el ORM. Si la infraestructura RLS de 001 no existe, se registra como
  deuda en `research.md` y no se inventa una paralela.

## Pruebas

Un caso por criterio de aceptación, más pruebas de integración y contrato. Nombres propuestos:

| CA | Prueba principal |
|---|---|
| CA-01 | `test_envio_exitoso_registra_destinatario_fecha_archivo_y_hash` |
| CA-02 | `test_reintento_fijo_cada_cinco_minutos_hasta_tres_veces` |
| CA-03 | `test_registro_envio_completo_es_inmutable` |
| CA-04 | `test_bandeja_solo_muestra_solicitudes_de_la_region` |
| CA-05 | `test_evento_sse_nueva_solicitud_solo_a_la_region` |
| CA-06 | `test_previsualizar_solicitud_muestra_detalle_y_permite_descarga` |
| CA-07 | `test_descarga_verifica_hash_sha256` |
| CA-08 | `test_confirmar_solicitud_delega_stock_en_008_y_fija_confirmada_en` |
| CA-09 | `test_rechazar_con_motivo_libera_series_y_notifica_al_tenant` |
| CA-10 | `test_rechazo_sin_motivo_falla_con_mensaje_exacto` |
| CA-11 | `test_buscar_excels_historicos_por_fecha_devuelve_hash` |
| CA-12 | `test_hash_no_coincide_bloquea_descarga` |

Además:

- **Contrato HTTP**: cada ruta de la tabla, métodos permitidos (`405`), CSRF, `302` sin sesión,
  `403` por rol/región, `404` por solicitud ajena, `409` por estado o hash y `200` con el
  `Content-Type` correcto.
- **Permisos**: matriz completa para `ADMIN_PLATAFORMA`, `RESPONSABLE_ALMACEN`, `USUARIO_TENANT`,
  tenant suspendido, cuenta inactiva y anónimo.
- **Aislamiento**: una solicitud, un envío y un Excel de otra región no se listan, no se abren y no
  se descargan; `tenant_id`/`region_id` forzados se ignoran; RLS si está disponible.
- **Auditoría**: confirmación, rechazo, series y cada intento; sin secretos ni contenido binario.
- **Correo**: backend `locmem`; adjunto correcto, destinatario del intento, fallo simulado con
  `smtplib.SMTPException` y agotamiento de intentos.
- **SSE**: `StreamingHttpResponse` con `text/event-stream`, evento con `data:` JSON, aislamiento por
  región, heartbeat y polling de respaldo.
- **Rendimiento**: bandeja, detalle, búsqueda y descarga sin N+1 con `django_assert_num_queries`;
  la bandeja responde en menos de 1 segundo en el escenario de prueba.

## Decisiones y riesgos

- **Una fila por intento (`EnvioCorreo`)**: permite trazabilidad exacta del archivo y hash enviados
  y evita un contador mutable. Alternativa descartada: una fila por correo con `reintentos`.
- **Reintentos fijos de 5 minutos, no backoff exponencial**: es lo que exige CA-02. Se corrigen
  `spec.md` §11 y la redacción anterior del plan (5/10/20 minutos).
- **Disparo con `transaction.on_commit`**: evita enviar un correo de una solicitud que luego se
  revierte. Alternativa descartada: enviar dentro de la transacción de 006.
- **SSE con Redis pub/sub en lugar de WebSocket/Channels**: cumple «WebSocket o SSE», no agrega
  dependencias (Redis ya está para Celery), funciona con Django WSGI y respeta la simplicidad de la
  constitución. Alternativa descartada: Django Channels + Daphne, que añade dependencias y un
  servidor ASGI no previsto.
- **Bandeja y búsqueda sobre `SolicitudAsignacion`, no sobre intentos**: un Excel histórico es uno
  por solicitud; los reintentos no crean Excels distintos. `EnvioCorreo` aporta el estado del último
  envío.
- **Hash canónico `solicitud.excel_hash`**: el mismo que generó 006; la descarga compara el archivo
  actual y bloquea si difiere. No se recalcula ni se regenera el Excel.
- **Confirmación delegada en 008**: evita dos dueños del stock y del cambio de serie. 007 solo
  orquesta la transacción y fija `confirmada_en`. Se corrige el plan de 008 para que valide stock
  suficiente y nunca cree cantidades negativas.
- **Administrador de solo lectura**: puede buscar y descargar Excels históricos globales, pero no
  confirmar ni rechazar. Coincide con la constitución: el Administrador no opera inventario.
- **Riesgo de correo no configurado o caído**: se registra cada intento y se notifica al tenant; la
  solicitud ya está `ENVIADA` y visible en la bandeja, por lo que el despacho no se detiene.
- **Riesgo de notificaciones perdidas**: SSE es best-effort; el contador de pendientes y el polling
  de respaldo garantizan que el almacén vea la solicitud al reconectar.
- **Riesgo de archivo ausente o alterado**: se bloquea el envío y la descarga; se registra el error
  y se alerta; no se sirve un archivo no verificado.

## Correcciones documentales obligatorias antes de implementar

1. `05-especificaciones/007-envio-y-revision-del-almacen/spec.md` §11: **aplicado en esta fase**.
   Se sustituyó «backoff exponencial» por «3 reintentos con intervalo fijo de 5 minutos» y se aclaró
   que el intento inicial más 3 reintentos son 4 intentos registrados; también se precisó que la
   notificación en tiempo real es SSE sobre Redis.
2. `04-contratos/excel-asignacion.md` §2 y §8: precisar que 006 genera el Excel al enviar
   (`BORRADOR→ENVIADA`) y que 007 solo lo envía, descarga y verifica; 007 nunca lo regenera.
3. `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/plan.md`: eliminar
   `cantidad=-1`; validar stock suficiente y usar `decrementar_stock_general`/`StockTecnico` sin
   cantidades negativas; dejar claro que 008 es dueño de `RESERVADA→ASIGNADA` y del stock, y que
   007 solo fija `confirmada_en` y el estado de la solicitud.
4. `05-especificaciones/006-solicitud-de-asignacion/plan.md` y `tasks.md`: agregar el gancho
   `transaction.on_commit` hacia `programar_envio_solicitud`, mostrar el fallo definitivo de correo
   en el detalle y confirmar que `confirmada_en` lo escribe 007.
5. `docs/02-arquitectura-software/funcionamiento-arquitectura.md`: si se mantiene la mención a
   WebSocket, aclarar que la implementación aprobada es SSE sobre Redis.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| SSE en lugar de WebSocket | La spec permite «WebSocket o SSE»; SSE usa `StreamingHttpResponse` y Redis ya presente, sin dependencias nuevas ni servidor ASGI. |
| Celery para correo | Ya forma parte del stack aprobado (ADR-015) y es necesario para reintentos y para no bloquear la transacción. |
| Campos `tenant`/`region` en `EnvioCorreo` | Son una denormalización de `solicitud` para RLS, filtrado por región e índices; no crean una fuente paralela de verdad. |
| `motivo_rechazo` en `SolicitudAsignacion` | La spec exige conservar el motivo y notificarlo; la auditoría no se usa como almacenamiento de negocio. |

## Criterios de salida

- `research.md`, `data-model.md`, `contracts/` y `quickstart.md` creados y coherentes con este plan.
- Las cinco correcciones documentales aplicadas antes de codificar (principio VIII).
- `tasks.md` derivado de este plan cubre CA-01…CA-12 con al menos una prueba por criterio.
- No se implementa código en esta fase.
