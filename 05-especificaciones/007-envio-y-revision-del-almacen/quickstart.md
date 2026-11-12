# Quickstart y validación: 007 Envío y Revisión del Almacén

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/007-envio-y-revision-del-almacen/spec.md`

Guía para validar de extremo a extremo el envío del Excel al almacén, el registro de intentos, la
bandeja con notificaciones, la confirmación/rechazo y la búsqueda de históricos con hash. Los
detalles de datos están en `data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Specs 001, 004 y 006 implementadas, y la parte fundacional y de confirmación de 008.
- Python 3.12+, PostgreSQL 16+ (rol de aplicación sin `SUPERUSER` ni `BYPASSRLS`) y Redis 7+.
- Worker de Celery operativo y `MEDIA_ROOT` compartido entre web y worker.
- Al menos una región con almacén (`centro`, `codigo_almacen`, `buzon`, `activo`), un tenant
  activo con cuenta, un técnico activo y materiales seriados y no seriados.
- Una solicitud `ENVIADA` con Excel archivado y hash (generada por 006).

## Configuración

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python manage.py migrate
```

Variables relevantes en `.env` (nunca versionado):

```text
DJANGO_SETTINGS_MODULE=config.settings.dev
DATABASE_URL=postgresql://lari_app:cambiar-en-local@localhost:5432/lari
REDIS_URL=redis://localhost:6379/0
REDIS_NOTIFICACIONES_URL=redis://localhost:6379/0
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=no-reply@lari.local
ENVIOS_REMITENTE=no-reply@lari.local
ENVIOS_MAX_INTENTOS=4
ENVIOS_INTERVALO_REINTENTO_SEGUNDOS=300
ALMACEN_SSE_PREFIJO_CANAL=almacen:region:
ALMACEN_SSE_HEARTBEAT_SEGUNDOS=25
```

Para ver los correos en desarrollo se puede usar `EMAIL_BACKEND` de consola (salida del worker) o
un buzón local tipo MailHog apuntando `EMAIL_HOST`/`EMAIL_PORT`. En pruebas se usa
`locmem`, nunca un servidor real.

## Puesta en marcha

En tres terminales:

```powershell
python manage.py runserver
celery -A config worker -l info
celery -A config beat -l info   # solo si se programan tareas periódicas
```

No se requiere un servidor ASGI ni Django Channels: SSE se sirve con el `runserver`/WSGI normal.

## Pruebas automatizadas

```powershell
# Suite completa sobre PostgreSQL
pytest

# Solo 007
pytest tests/unit tests/integration tests/contract -k "envio or almacen or almacén or historico or sse"

# Cobertura del módulo
pytest --cov=asignaciones --cov-report=term-missing
```

Las pruebas usan `django.core.mail.backends.locmem.EmailBackend`, Celery en modo eager y PostgreSQL
real. No se acepta SQLite.

## Escenarios de validación

### 1. CA-01 — Envío exitoso y registro

1. Crear y enviar una solicitud como `USUARIO_TENANT` (006).
2. **Esperado**: la solicitud queda `ENVIADA`; el worker envía el correo al buzón del almacén; se
   crea `EnvioCorreo` con `numero_intento=1`, `estado=EXITOSO`, destinatario, `archivo`,
   `hash_sha256` y `enviado_en`.
3. Abrir el correo en la consola/MailHog.
4. **Esperado**: el adjunto es el Excel archivado y su hash coincide con `solicitud.excel_hash`.

### 2. CA-02 — Reintentos fijos

1. Configurar temporalmente `ENVIOS_INTERVALO_REINTENTO_SEGUNDOS=5` y simular fallo SMTP.
2. Enviar una solicitud.
3. **Esperado**: intentos 1..4, cada uno `FALLIDO`/`REINTENTANDO` según avance, separados por 5 s;
   ningún backoff exponencial.
4. **Esperado**: el intento 4 queda `FALLIDO` y no se reprograma; la solicitud sigue `ENVIADA`.

### 3. CA-03 — Registro completo e inmutable

1. Consultar `EnvioCorreo` en el admin o por shell.
2. **Esperado**: destinatario, `creado_en`/`enviado_en`, archivo relativo y hash de 64 hex.
3. Intentar modificar `destinatario`, `archivo`, `hash_sha256` o `numero_intento`.
4. **Esperado**: no se permite; solo se cierran `estado`, `error_mensaje` y `enviado_en`.

### 4. CA-04 — Bandeja por región

1. Iniciar sesión como `RESPONSABLE_ALMACEN` de Ayacucho y abrir `/almacen/bandeja/`.
2. **Esperado**: solo solicitudes de tenants de Ayacucho; no aparecen `BORRADOR` ni `CANCELADA`.
3. Probar con una solicitud de otra región.
4. **Esperado**: `404` al abrirla; no se lista.

### 5. CA-05 — Notificación en tiempo real

1. Mantener la bandeja abierta en el navegador.
2. Enviar una nueva solicitud desde el tenant de la misma región.
3. **Esperado**: llega un evento SSE, suena el aviso, aparece el toast, se actualiza el badge y la
   tabla en menos de 1 segundo.
4. Repetir con el almacén de otra región conectado.
5. **Esperado**: no recibe el evento.
6. Desconectar SSE o bloquearlo.
7. **Esperado**: el polling a `/almacen/notificaciones/pendientes/` actualiza el contador en 30 s.

### 6. CA-06 — Previsualización y descarga

1. Abrir `/almacen/solicitudes/<id>/` y `/almacen/solicitudes/<id>/previsualizar/`.
2. **Esperado**: cabecera, líneas agrupadas, totales, hash y enlace de descarga.
3. Descargar el Excel.
4. **Esperado**: `200` con el `.xlsx` original y nombre `asignacion-<id>.xlsx`.

### 7. CA-07 — Verificación de hash en la descarga

1. Descargar un Excel histórico.
2. **Esperado**: el sistema calcula SHA-256 y lo compara con `solicitud.excel_hash`; la descarga se
   entrega solo si coincide.

### 8. CA-08 — Confirmación y stock

1. Como almacén, abrir una solicitud `ENVIADA` y pulsar "Confirmar".
2. **Esperado**: `302` al detalle, estado `CONFIRMADA`, `confirmada_en` fijado.
3. **Esperado**: las series pasan a `ASIGNADA`; `StockTecnico` sube y `StockGeneral` baja; la
   auditoría de 008 registra los cambios.
4. Intentar confirmar dos veces o desde otro almacén.
5. **Esperado**: `409` "Solo se pueden confirmar solicitudes enviadas"; sin doble descuento.
6. Forzar stock insuficiente antes de confirmar.
7. **Esperado**: la transacción se revierte y la solicitud sigue `ENVIADA`.

### 9. CA-09 — Rechazo con motivo

1. Como almacén, rechazar una solicitud `ENVIADA` con motivo "Serie no coincide".
2. **Esperado**: `302`, estado `RECHAZADA`, `motivo_rechazo`, `rechazada_en`; series
   `RESERVADA→DISPONIBLE`.
3. **Esperado**: el tenant ve el motivo en el detalle de 006 y recibe correo best-effort.
4. **Esperado**: las cantidades no seriadas vuelven a contar como disponibles.

### 10. CA-10 — Comentario obligatorio

1. Intentar rechazar con el motivo vacío o solo espacios.
2. **Esperado**: `400` "Debe indicar el motivo del rechazo"; sin cambios de estado.
3. Enviar más de 1000 caracteres.
4. **Esperado**: `400` "El motivo del rechazo no puede superar los 1000 caracteres".

### 11. CA-11 — Búsqueda de históricos

1. Como Administrador, abrir `/almacen/excels-historicos/` y filtrar por fecha, tenant, técnico y
   estado.
2. **Esperado**: solo solicitudes con Excel, una fila por solicitud, con hash y estado del último
   envío; paginación de 50.
3. Repetir como almacén.
4. **Esperado**: solo los históricos de su región.
5. Entrar como `USUARIO_TENANT`.
6. **Esperado**: `403`.

### 12. CA-12 — Hash alterado bloquea la descarga

1. Modificar manualmente el archivo Excel en `MEDIA_ROOT` (un byte distinto).
2. Intentar descargarlo desde el detalle y desde históricos.
3. **Esperado**: `409` "El archivo fue modificado, descarga bloqueada"; no se entrega ningún byte.
4. Restaurar el archivo.
5. **Esperado**: la descarga vuelve a funcionar.

### 13. Permisos y aislamiento

1. Probar las 10 rutas con `ADMIN_PLATAFORMA`, `RESPONSABLE_ALMACEN`, `USUARIO_TENANT`, tenant
   suspendido, cuenta inactiva y anónimo.
2. **Esperado**: se cumple la matriz de `contracts/http-endpoints.md` (`403`, `404`, `302`, `405`).
3. Forzar `tenant_id`, `region_id`, `estado`, `destinatario` o `hash` en el `POST`.
4. **Esperado**: se ignoran; la región y el tenant salen de la sesión.

### 14. Concurrencia

1. Lanzar dos confirmaciones simultáneas de la misma solicitud.
2. **Esperado**: una pasa y la otra recibe `409`; el stock se mueve una sola vez.
3. Lanzar dos rechazos simultáneos.
4. **Esperado**: uno libera las series y el otro recibe `409`; no quedan series `RESERVADA`.

### 15. Auditoría

1. Revisar `RegistroCambio` tras confirmar y rechazar.
2. **Esperado**: `SolicitudAsignacion/estado` con `confirmada_en` o con motivo y `rechazada_en`;
   `Serie/estado` por cada serie liberada; `EnvioCorreo/estado` por cada intento cerrado.
3. **Esperado**: sin contraseñas, tokens, secretos, cuerpo del correo, binario ni rutas absolutas.

## Criterios de salida

- [ ] Los 12 criterios CA-01…CA-12 tienen al menos una prueba automatizada en verde.
- [ ] Las 10 rutas cumplen `contracts/http-endpoints.md` (métodos, permisos, códigos y mensajes).
- [ ] El correo se envía solo después del commit y nunca revierte una solicitud.
- [ ] Los reintentos son 4 intentos con intervalo fijo de 300 s.
- [ ] `EnvioCorreo` es único por `(solicitud, numero_intento)` y conserva archivo y hash exactos.
- [ ] La bandeja solo muestra la región del almacén; el Admin solo consulta históricos.
- [ ] SSE entrega eventos solo a la región y el polling recupera el contador si falla.
- [ ] La confirmación delega stock y series en 008 y fija `confirmada_en` una sola vez.
- [ ] El rechazo exige motivo, libera series y notifica al tenant.
- [ ] La descarga verifica SHA-256 y bloquea con `409` si no coincide.
- [ ] La auditoría está completa, es inmutable y no contiene secretos.
- [ ] `pytest`, `makemigrations --check --dry-run` y `migrate --plan` sin pendientes.
- [ ] No se modificaron tablas de stock, series, recojos, traspasos ni conciliaciones fuera de lo
      previsto.
