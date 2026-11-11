# Plan técnico: 006 Solicitud de Asignación

## Referencias
- Spec: `05-especificaciones/006-solicitud-de-asignacion/spec.md`
- Contrato: `04-contratos/excel-asignacion.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación), ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, HTMX, openpyxl, y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `asignaciones`: modelo `SolicitudAsignacion`, `LineaAsignacion`, servicios, formularios y vistas.
- App `stock`: validación de disponibilidad y reserva de stock.
- App `series`: cambio de estado de series (Disponible → Reservada → Asignada).
- App `materiales`: consulta del catálogo de materiales.
- App `tecnicos`: selector de técnicos activos.
- App `regiones`: parámetros de región (Centro, Almacén).
- App `auditoria`: modelo `RegistroCambio`, compartido.
- Middleware de contexto de tenant de la spec 001.
- No se modifican recojos, traspasos ni conciliaciones.

## Modelo de datos

```python
class SolicitudAsignacion(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion",
    )
    fecha = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=[
            ("BORRADOR", "Borrador"),
            ("ENVIADA", "Enviada"),
            ("CONFIRMADA", "Confirmada"),
            ("RECHAZADA", "Rechazada"),
            ("CANCELADA", "Cancelada"),
        ],
        default="BORRADOR",
    )
    excel_ruta = models.CharField(max_length=255, null=True, blank=True)
    excel_hash = models.CharField(max_length=64, null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitudes_asignacion_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "estado"], name="solicitud_asign_tenant_estado"),
            models.Index(fields=["tecnico", "fecha"], name="solicitud_asign_tecnico_fecha"),
        ]

    def __str__(self):
        return f"Solicitud {self.id} - {self.tecnico.nif} - {self.estado}"


class LineaAsignacion(models.Model):
    solicitud = models.ForeignKey(
        "SolicitudAsignacion",
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_asignacion",
    )
    lote = models.CharField(max_length=50)
    serie = models.CharField(
        max_length=12,
        null=True,
        blank=True,
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_asign_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=~Q(serie__isnull=False) | Q(cantidad=1),
                name="linea_asign_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(serie__regex=r"^[A-Z0-9]{12}$") | Q(serie__isnull=True),
                name="linea_asign_serie_formato",
            ),
        ]
        indexes = [
            models.Index(fields=["solicitud", "material"], name="linea_asign_solicitud_material"),
            models.Index(fields=["serie"], name="linea_asign_serie"),
        ]

    def __str__(self):
        if self.serie:
            return f"{self.material.codigo} - {self.serie}"
        return f"{self.material.codigo} - {self.cantidad}"
```

- `SolicitudAsignacion` representa una solicitud de asignación con su estado, técnico y Excel.
- `estado` sigue el ciclo: Borrador → Enviada → Confirmada/Rechazada/Cancelada.
- `excel_ruta` y `excel_hash` almacenan la ubicación y firma del Excel generado.
- `LineaAsignacion` representa cada línea de la solicitud (material, serie o cantidad).
- Para materiales seriados: `serie` tiene valor, `cantidad=1`.
- Para materiales no seriados: `serie` es NULL, `cantidad>0`.
- Las restricciones son idénticas a las de `LineaRecojo` y `LineaStockInicial` para mantener consistencia.
- El índice en `serie` acelera la validación de disponibilidad y estado.

## Migraciones
- `asignaciones/migrations/0001_initial.py`: modelos `SolicitudAsignacion` y `LineaAsignacion` con restricciones e índices.
- No se crean solicitudes por migración.
- No se modifican tablas de stock, series, traspasos ni conciliaciones.

## Servicios (lógica de negocio)
Viven en `asignaciones/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_tenant(actor, tenant)`:
  - Verifica que `actor.rol == "USUARIO_TENANT"`.
  - Verifica que `actor.tenant_id == tenant.id`.
  - Verifica que la cuenta esté activa y que el tenant esté activo.
  - Si no cumple, lanza `PermisoDenegado`.
- `validar_tecnico_para_asignacion(tenant, tecnico_id)`:
  - Usa `validar_tecnico_para_operacion` del módulo de técnicos.
  - Devuelve el técnico o lanza `TecnicoNoDisponible`.

### Validación de disponibilidad
- `calcular_disponible(tenant, material)`:
  - Obtiene el stock general del tenant para el material.
  - Obtiene la cantidad reservada en asignaciones pendientes (estado ENVIADA).
  - Devuelve: `Disponible = Stock General - Reservado`.
- `validar_cantidad_disponible(tenant, material, cantidad)`:
  - Llama `calcular_disponible`.
  - Si `cantidad > disponible`, lanza `CantidadExcedeDisponible`.
- `validar_serie_disponible(serie)`:
  - Consulta el estado de la serie.
  - Si no es `DISPONIBLE`, lanza `SerieNoDisponible`.

### Validación de cupo máximo
- `calcular_dias_en_mano_tecnico(tecnico)`:
  - Suma los días en mano de todos los seriados asignados al técnico.
  - Los días en mano se calculan desde la fecha de asignación hasta hoy.
  - Devuelve el total de días.
- `validar_cupo_maximo(tecnico)`:
  - Llama `calcular_dias_en_mano_tecnico`.
  - Si el total > 20, devuelve una advertencia (no excepción, solo alerta).

### Creación de solicitud
- `crear_solicitud_asignacion(tenant, tecnico, lineas, actor)`:
  - `validar_cuenta_tenant(actor, tenant)`.
  - `validar_tecnico_para_asignacion(tenant, tecnico.id)`.
  - Para cada línea:
    - Valida que el material exista en el catálogo.
    - Si es seriado: valida que la serie esté Disponible.
    - Si es no seriado: valida la cantidad contra el disponible.
  - Verifica cupo máximo del técnico (alerta si supera 20 días).
  - En `transaction.atomic`:
    - Crea la `SolicitudAsignacion` en estado BORRADOR.
    - Crea cada `LineaAsignacion` con sus datos.
    - No reserva series ni cantidades aún (se reserva al enviar).
    - Registra auditoría de la creación.
  - Devuelve la `SolicitudAsignacion` creada.

### Envío de solicitud
- `enviar_solicitud(solicitud, actor)`:
  - `validar_cuenta_tenant(actor, solicitud.tenant)`.
  - Verifica que `solicitud.estado == "BORRADOR"`.
  - Para cada línea seriada:
    - Valida que la serie siga Disponible.
  - En `transaction.atomic`:
    - Cambia estado a "ENVIADA".
    - Para seriados: cambia estado de serie a RESERVADA.
    - Para no seriados: reserva la cantidad del stock general.
    - Genera el Excel de asignación (ver `generar_excel_asignacion`).
    - Guarda ruta y hash del Excel.
    - Registra auditoría del envío.
  - Devuelve la `SolicitudAsignacion` actualizada.

### Generación de Excel
- `generar_excel_asignacion(solicitud)`:
  - Usa `openpyxl` para crear el Excel.
  - Escribe metadatos: Movimiento Z31, Centro PR05, Almacén BE03 (de la región), NIF del técnico, fecha.
  - Escribe tabla de seriales (líneas seriadas).
  - Escribe tabla de material menor (líneas no seriadas).
  - Guarda el archivo en disco con nombre único.
  - Calcula el hash SHA-256 del archivo.
  - Devuelve ruta y hash.

### Cancelación de solicitud
- `cancelar_solicitud(solicitud, actor)`:
  - `validar_cuenta_tenant(actor, solicitud.tenant)`.
  - Verifica que `solicitud.estado == "BORRADOR"`.
  - En `transaction.atomic`:
    - Cambia estado a "CANCELADA".
    - No hay series reservadas aún (solo en ENVIADA), así que no se liberan.
    - Registra auditoría de la cancelación.
  - Devuelve la `SolicitudAsignacion` actualizada.

### Consultas
- `listar_solicitudes(tenant, estado=None)`:
  - Filtra siempre por `tenant`.
  - Opcionalmente filtra por estado.
  - Ordena por `fecha` descendente.
  - Devuelve un queryset paginado.
- `obtener_solicitud(tenant, solicitud_id)`:
  - Busca la solicitud filtrando por `tenant`.
  - Si no existe o pertenece a otro tenant, lanza `NoEncontrado`.
- `series_disponibles_para_asignacion(tenant, material, q="")`:
  - Filtra series por tenant y material.
  - Solo estado `DISPONIBLE`.
  - Busca por serie si se proporciona `q`.
  - Ordena por serie.
  - Devuelve un queryset paginado para el selector.

## Permisos
- Crear: `asignaciones.add_solicitudasignacion`.
- Ver: `asignaciones.view_solicitudasignacion`.
- Enviar: `asignaciones.enviar_solicitudasignacion`.
- Cancelar: `asignaciones.cancelar_solicitudasignacion`.
- Todos se asignan al rol `USUARIO_TENANT`.
- El Administrador de plataforma y el Responsable de almacén no reciben estos permisos por defecto.
- Los servicios vuelven a validar rol, tenant y estado; nunca se confía solo en la vista.
- No se acepta `tenant_id` o `tecnico_id` desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/asignaciones/` | GET | Listado paginado con filtro por estado |
| `/asignaciones/nueva/` | GET / POST | Creación de solicitud de asignación |
| `/asignaciones/<id>/` | GET | Detalle de la solicitud |
| `/asignaciones/<id>/enviar/` | POST | Enviar solicitud al almacén |
| `/asignaciones/<id>/cancelar/` | POST | Cancelar solicitud (solo borrador) |
| `/asignaciones/series-disponibles/` | GET | Fragmento HTMX con series disponibles para selector |
| `/asignaciones/validar-disponibilidad/` | POST | Validación en tiempo real de disponibilidad |

### Pantallas
- **Listado:** Fecha, técnico, estado, total series, total cantidad. Filtro por estado.
- **Creación:**
  - Selector de técnico (solo activos).
  - Fecha (precompletada con hoy, editable).
  - Lista de líneas (agregar/editar/eliminar).
  - Para cada línea:
    - Selector de material.
    - Tipo de material (solo lectura).
    - Lote (solo lectura).
    - Para seriados: selector de series disponibles (multi-select con búsqueda).
    - Para no seriados: campo numérico para cantidad.
    - Validación en tiempo real de disponibilidad.
  - Vista previa de alerta de cupo máximo (si aplica).
  - Botón "Guardar borrador" y "Enviar".
- **Detalle:**
  - Datos de la solicitud (técnico, fecha, estado).
  - Lista de líneas.
  - Descarga del Excel (si generado).
  - Acciones según estado (enviar, cancelar).
- **Selector de series:**
  - HTMX fragmento con búsqueda y paginación.
  - Muestra solo series Disponibles del material seleccionado.
  - Permite selección múltiple.

### Validación en tiempo real
- El endpoint `/asignaciones/validar-disponibilidad/` recibe:
  - Material.
  - Cantidad (para no seriados).
  - Lista de series (para seriados).
- Devuelve JSON con:
  - Estado: `valido` o `invalido`.
  - Disponible calculado.
  - Alerta de cupo máximo si aplica.
- El endpoint `/asignaciones/series-disponibles/` recibe:
  - Material.
  - Query de búsqueda (opcional).
- Devuelve HTML con HTMX:
  - Lista de series disponibles paginada.
  - Checkboxes para selección múltiple.

## Integraciones
- **Stock (transversal):** la validación de disponibilidad consulta el stock general y lo reservado. La reserva se hace al enviar la solicitud.
- **Series (transversal):** las series cambian de estado (Disponible → Reservada → Asignada). La confirmación final se hace en spec 007.
- **Catálogo de materiales (spec 002):** el selector de materiales consulta el catálogo compartido.
- **Técnicos (spec 003):** el selector de técnicos usa `tecnicos_para_operacion`.
- **Regiones (spec 001):** los parámetros Centro y Almacén se obtienen de la región del tenant.
- **Envío de Excel (spec 007):** el envío por correo al almacén se implementa en la spec 007.
- **Auditoría (transversal):** toda operación registra usuario, fecha y cambios.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Tenant de la sesión | Servicio y decorador | "No tienes permiso para crear asignaciones" |
| Técnico activo | Servicio (reutiliza técnicos) | "El técnico está desactivado" |
| Serie Disponible | Servicio y estado de serie | "La serie no está disponible" |
| Cantidad no supera disponible | Servicio | "La cantidad supera el stock disponible" |
| Disponible = Stock - Reservado | Servicio | Cálculo interno |
| Cantidad > 0 | Formulario y servicio | "La cantidad debe ser mayor a 0" |
| Serie o cantidad obligatoria | Formulario y `CheckConstraint` | "Debe indicar serie o cantidad" |
| Estado Borrador para enviar | Servicio | "Solo se pueden enviar solicitudes en borrador" |
| Estado Borrador para cancelar | Servicio | "Solo se pueden cancelar solicitudes en borrador" |
| Cupo máximo alerta | Servicio (no bloquea) | "El técnico supera los 20 días en mano" |

## Transacciones y concurrencia
- La creación de la solicitud y sus líneas se ejecutan en una sola transacción.
- El envío de la solicitud, el cambio de estado de series, la reserva de stock y la generación del Excel se ejecutan en una sola transacción.
- La validación de disponibilidad se ejecuta antes de la transacción para fallar rápido.
- Si dos sesiones intentan reservar la misma serie simultáneamente:
  - La primera en validar pasa.
  - La segunda detecta que la serie ya no está Disponible (porque la primera la reservó) y falla.
- No se usan bloqueos de aplicación; el estado de serie es la fuente de verdad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_crear_solicitud_asignacion_valida`
- `test_seleccionar_series_disponibles_muestra_solo_disponibles`
- `test_cantidad_excede_disponible_se_rechaza`
- `test_cantidad_descontando_reservado_correcta`
- `test_series_pasan_a_reservada_al_enviar`
- `test_generacion_excel_correcta_con_metadatos`
- `test_nif_autocompletado_no_editable`
- `test_dias_en_mano_inician_al_aceptar` (se probará en spec 007)
- `test_alerta_cupo_maximo_se_muestra`
- `test_serie_no_disponible_no_aparece_en_selector`
- `test_serie_reservada_no_aparece_en_selector`
- `test_cancelar_solicitud_borrador`
- `test_no_se_puede_enviar_solicitud_no_borrador`
- `test_validacion_disponibilidad_tiempo_real_htmx`
- `test_selector_series_htmx_con_busqueda`

Además, pruebas de base de datos:
- Insertar una serie con formato inválido directamente debe fallar.
- Insertar dos líneas de la misma solicitud con la misma serie debe fallar.
- Insertar una línea con serie y cantidad != 1 debe fallar.
- Insertar una línea sin serie ni cantidad debe fallar.

## Decisiones y riesgos
- **Reserva al enviar, no al crear:** la solicitud se crea en borrador sin reservar. La reserva se hace al enviar para permitir ediciones previas. Esto requiere validar disponibilidad al enviar nuevamente.
- **Estado Borrador:** permite que el usuario revise y modifique la solicitud antes de enviar. Si se decide que no es necesario, se puede simplificar creando directamente en ENVIADA.
- **Alerta de cupo máximo no bloquea:** es informativa, no preventiva. Si se requiere bloqueo, se puede cambiar a excepción.
- **Cálculo de días en mano:** se inicia al confirmar la asignación (spec 007), no al crear la solicitud. La spec actual menciona "una vez aceptada".
- **Selector de series con HTMX:** permite cargar fragmentos dinámicos sin recargar la página. Es crítico para rendimiento con grandes volúmenes de series.
- **Índice en serie:** es crítico para rendimiento al validar disponibilidad y estado.
- **Concurrencia en series:** el estado de serie resuelve el caso de dos usuarios intentando reservar la misma serie simultáneamente.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Integración con stock:** la validación de disponibilidad consulta el stock general y lo reservado. La reserva se hace al enviar.
- **Riesgo de validación al enviar:** si una serie deja de estar Disponible entre el borrador y el envío, el envío falla. Esto es correcto pero puede ser frustrante para el usuario. Se mitigará con validación en tiempo real al enviar.
