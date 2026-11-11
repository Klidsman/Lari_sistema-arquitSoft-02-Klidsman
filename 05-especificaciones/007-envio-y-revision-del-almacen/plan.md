# Plan técnico: 007 Envío y Revisión del Almacén

## Referencias
- Spec: `05-especificaciones/007-envio-y-revision-del-almacen/spec.md`
- Contrato: `04-contratos/excel-asignacion.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación), ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, Celery, Redis, HTMX, WebSocket/SSE, openpyxl y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django `asignaciones` (de spec 006): agregar modelo `EnvioCorreo` y servicios de envío.
- App `stock`: actualización de stock al confirmar (integración con spec 008).
- App `series`: cambio de estado de series (Reservada → Asignada, Rechazada → Disponible).
- App `notificaciones`: sistema de notificaciones en tiempo real (WebSocket/SSE).
- Worker Celery: para envío asíncrono de correos.
- Redis: para cola de tareas de Celery y caché de notificaciones.
- Middleware de contexto de tenant de la spec 001.
- No se modifican recojos, traspasos ni conciliaciones.

## Modelo de datos

```python
# Agregado a asignaciones.models
class EnvioCorreo(models.Model):
    solicitud = models.ForeignKey(
        "SolicitudAsignacion",
        on_delete=models.CASCADE,
        related_name="envios_correo",
    )
    destinatario = models.EmailField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    archivo = models.CharField(max_length=255)
    hash_sha256 = models.CharField(max_length=64)
    estado = models.CharField(
        max_length=20,
        choices=[
            ("EXITOSO", "Exitoso"),
            ("FALLIDO", "Fallido"),
            ("REINTENTANDO", "Reintentando"),
        ],
        default="REINTENTANDO",
    )
    reintentos = models.IntegerField(default=0)
    error_mensaje = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["solicitud", "fecha_envio"], name="envio_correo_solicitud_fecha"),
            models.Index(fields=["estado"], name="envio_correo_estado"),
        ]

    def __str__(self):
        return f"Envio {self.id} - {self.destinatario} - {self.estado}"
```

- `EnvioCorreo` registra cada intento de envío de correo.
- `destinatario` es el buzón del almacén (parámetro de la región).
- `archivo` es la ruta del Excel enviado.
- `hash_sha256` es la firma del archivo para verificación posterior.
- `estado` rastrea si el envío fue exitoso, fallido o está reintentando.
- `reintentos` cuenta el número de intentos.
- `error_mensaje` guarda el detalle del error si falló.

## Migraciones
- `asignaciones/migrations/XXXX_add_envio_correo.py`: agregar modelo `EnvioCorreo`.
- No se crean envíos por migración.
- No se modifican tablas de stock, series, traspasos ni conciliaciones.

## Servicios (lógica de negocio)
Viven en `asignaciones/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_almacen(actor, region)`:
  - Verifica que `actor.rol == "RESPONSABLE_ALMACEN"`.
  - Verifica que `actor.region == region`.
  - Verifica que la cuenta esté activa.
  - Si no cumple, lanza `PermisoDenegado`.
- `validar_solicitud_pertenece_region(solicitud, region)`:
  - Verifica que `solicitud.tenant.region == region`.
  - Si no, lanza `NoEncontrado` (sin revelar que existe en otra región).

### Envío de correo (Celery task)
- `enviar_excel_por_correo(solicitud_id)`:
  - Task de Celery ejecutada asíncronamente.
  - Obtiene la `SolicitudAsignacion`.
  - Obtiene el buzón del almacén de la región (`solicitud.tenant.region.buzon_almacen`).
  - Lee el archivo Excel desde disco.
  - Envía el correo con el Excel adjunto.
  - Si exitoso:
    - Crea `EnvioCorreo` con estado EXITOSO.
    - Notifica al tenant que el envío fue exitoso.
  - Si falla:
    - Crea `EnvioCorreo` con estado FALLIDO y error_mensaje.
    - Si `reintentos < 3`, programa un reintento con backoff exponencial.
    - Si `reintentos >= 3`, notifica al tenant que el envío falló definitivamente.
  - Devuelve el estado del envío.

### Gestión de reintentos
- `programar_reintento(envio_id)`:
  - Task de Celery que programa un nuevo intento de envío.
  - Incrementa `reintentos` del `EnvioCorreo`.
  - Cambia estado a REINTENTANDO.
  - Llama `enviar_excel_por_correo` con el `solicitud_id`.
  - Usa `eta` de Celery para programar el envío en el futuro (5 minutos, 10 minutos, 20 minutos).

### Confirmación de solicitud
- `confirmar_solicitud(solicitud, actor)`:
  - `validar_cuenta_almacen(actor, solicitud.tenant.region)`.
  - Verifica que `solicitud.estado == "ENVIADA"`.
  - En `transaction.atomic`:
    - Cambia estado a "CONFIRMADA".
    - Para seriados: cambia estado de serie a ASIGNADA.
    - Para no seriados: confirma la reserva (stock del técnico sube, stock general baja).
    - Inicia el conteo de días en mano para seriados (RF-61).
    - Registra auditoría de la confirmación.
    - Notifica al tenant que la solicitud fue confirmada.
  - Devuelve la `SolicitudAsignacion` actualizada.

### Rechazo de solicitud
- `rechazar_solicitud(solicitud, comentario, actor)`:
  - `validar_cuenta_almacen(actor, solicitud.tenant.region)`.
  - Verifica que `solicitud.estado == "ENVIADA"`.
  - Verifica que `comentario` no esté vacío.
  - En `transaction.atomic`:
    - Cambia estado a "RECHAZADA".
    - Para seriados: cambia estado de serie a DISPONIBLE.
    - Para no seriados: libera la reserva (stock general vuelve a estar disponible).
    - Registra auditoría del rechazo (con comentario).
    - Notifica al tenant del rechazo con el motivo.
  - Devuelve la `SolicitudAsignacion` actualizada.

### Consultas para almacén
- `listar_solicitudes_almacen(region, estado=None)`:
  - Filtra solicitudes por `tenant.region == region`.
  - Opcionalmente filtra por estado.
  - Solo muestra solicitudes ENVIADA, CONFIRMADA, RECHAZADA (no BORRADOR).
  - Ordena por `fecha` descendente.
  - Devuelve un queryset paginado.
- `obtener_solicitud_almacen(region, solicitud_id)`:
  - Busca la solicitud filtrando por `tenant.region == region`.
  - Si no existe o pertenece a otra región, lanza `NoEncontrado`.

### Búsqueda de Excels históricos
- `buscar_excels_historicos(region, filtros)`:
  - Filtra `EnvioCorreo` por región (a través de solicitud.tenant.region).
  - Aplica filtros: fecha, tenant, técnico, estado.
  - Devuelve un queryset paginado.
- `verificar_hash_excel(envio, ruta_archivo)`:
  - Lee el archivo desde disco.
  - Calcula el hash SHA-256 del archivo actual.
  - Compara con `envio.hash_sha256`.
  - Si coinciden, devuelve True.
  - Si no coinciden, devuelve False y lanza advertencia.

### Notificaciones en tiempo real
- `notificar_nueva_solicitud(region, solicitud)`:
  - Publica un mensaje en el canal de WebSocket/SSE de la región.
  - El mensaje contiene: ID de solicitud, tenant, técnico, total series.
  - Los clientes conectados de esa región reciben la notificación.
- `notificar_cambio_estado(solicitud, estado_anterior, estado_nuevo)`:
  - Publica un mensaje cuando cambia el estado de una solicitud.
  - El tenant y el almacén reciben la notificación.

## Permisos
- Ver bandeja: `asignaciones.view_bandejadespachos`.
- Confirmar: `asignaciones.confirmar_solicitudasignacion`.
- Rechazar: `asignaciones.rechazar_solicitudasignacion`.
- Buscar Excels: `asignaciones.buscar_excels_historicos`.
- Ver y Confirmar/Rechazar se asignan al rol `RESPONSABLE_ALMACEN`.
- Buscar Excels se asigna a `RESPONSABLE_ALMACEN` y `ADMIN_PLATAFORMA`.
- El Tenant no tiene permisos en este módulo (solo recibe notificaciones).
- Los servicios vuelven a validar rol y región; nunca se confía solo en la vista.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por región.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/almacen/bandeja/` | GET | Bandeja de despachos del almacén |
| `/almacen/bandeja/ws/` | WebSocket | Conexión WebSocket para notificaciones en tiempo real |
| `/almacen/solicitudes/<id>/` | GET | Detalle de solicitud (almacén) |
| `/almacen/solicitudes/<id>/confirmar/` | POST | Confirmar solicitud |
| `/almacen/solicitudes/<id>/rechazar/` | POST | Rechazar solicitud |
| `/almacen/solicitudes/<id>/previsualizar/` | GET | Previsualizar solicitud |
| `/almacen/solicitudes/<id>/descargar-excel/` | GET | Descargar Excel con verificación de hash |
| `/almacen/excels-historicos/` | GET | Búsqueda de Excels históricos |
| `/almacen/excels-historicos/<id>/descargar/` | GET | Descargar Excel histórico con verificación |

### Pantallas
- **Bandeja de despachos:**
  - Lista de solicitudes de la región del almacén.
  - Filtro por estado (Enviada, Confirmada, Rechazada).
  - Ordenamiento por fecha.
  - Notificación sonora y visual cuando llega una nueva solicitud.
  - Badge con contador de solicitudes pendientes (Enviada).
  - Acciones: Ver detalle, Confirmar, Rechazar.
- **Detalle de solicitud (almacén):**
  - Datos de la solicitud (tenant, técnico, fecha).
  - Lista de líneas (series o cantidades).
  - Descarga del Excel original.
  - Botón "Confirmar" y "Rechazar".
  - Estado actual y comentarios de rechazo (si aplica).
- **Formulario de rechazo:**
  - Comentario obligatorio (textarea).
  - Botón "Enviar rechazo".
- **Búsqueda de Excels históricos:**
  - Filtros: fecha, tenant, técnico, estado.
  - Lista de envíos con hash SHA-256.
  - Acción: Descargar.
  - Al descargar, se verifica el hash.

### Notificaciones en tiempo real
- **WebSocket endpoint:** `/almacen/bandeja/ws/`
- El almacén se conecta al WebSocket con su región.
- El servidor publica mensajes cuando:
  - Llega una nueva solicitud.
  - Cambia el estado de una solicitud.
- El cliente recibe el mensaje y:
  - Reproduce sonido de notificación.
  - Muestra alerta visual (toast o badge).
  - Actualiza la bandeja si está visible.

## Integraciones
- **Solicitudes de asignación (spec 006):** esta spec completa el ciclo de vida de las solicitudes (envío, confirmación, rechazo).
- **Stock (spec 008):** la confirmación actualiza el stock (técnico sube, general baja).
- **Series (transversal):** las series cambian de estado (Reservada → Asignada o Disponible).
- **Regiones (spec 001):** el buzón del almacén es un parámetro de la región.
- **Celery + Redis:** procesamiento asíncrono de envío de correos.
- **WebSocket/SSE:** notificaciones en tiempo real para el almacén.
- **Auditoría (transversal):** toda operación registra usuario, fecha y cambios.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cuenta de almacén | Servicio y decorador | "No tienes permiso para gestionar despachos" |
| Región del almacén | Servicio | "Solo puedes ver solicitudes de tu región" |
| Estado ENVIADA para confirmar/rechazar | Servicio | "Solo se pueden confirmar/rechazar solicitudes enviadas" |
| Comentario obligatorio al rechazar | Servicio | "Debe indicar el motivo del rechazo" |
| Hash SHA-256 coincide | Servicio al descargar | "El archivo fue modificado, descarga bloqueada" |
| Buzón de almacén configurado | Task de Celery | "El buzón del almacén no está configurado" |

## Transacciones y concurrencia
- La confirmación de solicitud, el cambio de estado de series y la actualización de stock se ejecutan en una sola transacción.
- El rechazo de solicitud, el cambio de estado de series y la liberación de stock se ejecutan en una sola transacción.
- El envío de correo es asíncrono (Celery), no bloquea la transacción de envío de solicitud.
- Si dos almacenes intentan confirmar la misma solicitud simultáneamente:
  - La primera en validar pasa.
  - La segunda detecta que el estado ya no es ENVIADA y falla.
- No se usan bloqueos de aplicación; el estado de solicitud es la fuente de verdad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_envio_correo_exitoso_registra_envio`
- `test_reintento_correo_fallido_3_veces`
- `test_registro_envio_completo`
- `test_bandeja_despachos_solo_muestra_region_almacen`
- `test_notificacion_tiempo_real_llega_solicitud`
- `test_previsualizar_solicitud_muestra_detalle`
- `test_verificar_hash_excel_descarga`
- `test_confirmar_solicitud_actualiza_stock`
- `test_rechazar_solicitud_con_comentario_libera_series`
- `test_comentario_obligatorio_al_rechazar`
- `test_buscar_excels_historicos_filtrado`
- `test_hash_no_coincide_bloquea_descarga`
- `test_almacen_otra_region_no_ve_solicitudes`
- `test_confirmar_solicitud_no_enviada_falla`

Además, pruebas de Celery:
- Task de envío de correo se ejecuta correctamente.
- Task de reintento se programa con el backoff correcto.
- Task fallida después de 3 reintentos notifica error.

## Decisiones y riesgos
- **Envío asíncrono con Celery:** permite que el envío de correos no bloquee la respuesta HTTP. Requiere Redis y configuración de workers.
- **Reintentos con backoff exponencial:** aumenta la probabilidad de éxito ante fallos transitorios. El límite de 3 reintentos es configurable.
- **WebSocket para notificaciones:** requiere mantener conexiones abiertas. Si no es viable, se puede usar polling o SSE.
- **Verificación de hash al descargar:** protege contra alteraciones de archivos. Si el hash no coincide, se debe investigar manualmente.
- **Notificaciones solo a almacén de la región:** el filtrado por región es crítico para seguridad. El WebSocket debe validar la región del cliente.
- **Estado ENVIADA necesario para confirmar/rechazar:** impide confirmar solicitudes en borrador o ya procesadas.
- **Comentario obligatorio al rechazar:** mejora la comunicación entre almacén y tenant. Se puede hacer opcional si el negocio lo requiere.
- **Búsqueda de Excels históricos:** puede volverse lento con muchos registros. Se recomienda particionamiento por fecha.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Riesgo de buzón no configurado:** si el buzón del almacén no está configurado, el envío falla. Se debe validar al crear la región.
- **Riesgo de notificaciones perdidas:** si el WebSocket se desconecta, el almacén puede perder notificaciones. Se recomienda mostrar contador de solicitudes pendientes al reconectar.
