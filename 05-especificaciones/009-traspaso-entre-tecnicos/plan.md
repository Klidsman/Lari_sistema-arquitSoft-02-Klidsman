# Plan técnico: 009 Traspaso entre Técnicos

## Referencias
- Spec: `05-especificaciones/009-traspaso-entre-tecnicos/spec.md`
- Contrato: `04-contratos/excel-traspaso.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación), ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, Celery, Redis, HTMX, openpyxl y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `traspasos`: modelo `SolicitudTraspaso`, `LineaTraspaso`, servicios, formularios y vistas.
- App `stock`: actualización de stock de técnicos (origen baja, destino sube), usando funciones de spec 008.
- App `series`: cambio de técnico de series.
- App `materiales`: consulta del catálogo de materiales.
- App `tecnicos`: selector de técnicos activos.
- App `auditoria`: modelo `RegistroCambio`, compartido.
- Middleware de contexto de tenant de la spec 001.
- No se modifican recojos, asignaciones ni conciliaciones.

## Modelo de datos

```python
class SolicitudTraspaso(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="solicitudes_traspaso",
    )
    tecnico_origen = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="traspasos_origen",
    )
    tecnico_destino = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="traspasos_destino",
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
        related_name="solicitudes_traspaso_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(tecnico_origen=models.F("tecnico_destino")),
                name="solicitud_traspaso_origen_destino_distintos",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "estado"], name="solicitud_traspaso_tenant_estado"),
            models.Index(fields=["tecnico_origen", "fecha"], name="solicitud_traspaso_origen_fecha"),
            models.Index(fields=["tecnico_destino", "fecha"], name="solicitud_traspaso_destino_fecha"),
        ]

    def __str__(self):
        return f"Traspaso {self.id} - {self.tecnico_origen.nif} → {self.tecnico_destino.nif} - {self.estado}"


class LineaTraspaso(models.Model):
    solicitud = models.ForeignKey(
        "SolicitudTraspaso",
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_traspaso",
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
                name="linea_traspaso_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=~Q(serie__isnull=False) | Q(cantidad=1),
                name="linea_traspaso_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(serie__regex=r"^[A-Z0-9]{12}$") | Q(serie__isnull=True),
                name="linea_traspaso_serie_formato",
            ),
        ]
        indexes = [
            models.Index(fields=["solicitud", "material"], name="linea_traspaso_solicitud_material"),
            models.Index(fields=["serie"], name="linea_traspaso_serie"),
        ]

    def __str__(self):
        if self.serie:
            return f"{self.material.codigo} - {self.serie}"
        return f"{self.material.codigo} - {self.cantidad}"
```

- `SolicitudTraspaso` representa un traspaso entre dos técnicos del mismo tenant.
- La restricción `solicitud_traspaso_origen_destino_distintos` asegura que origen != destino.
- `estado` sigue el ciclo: Borrador → Enviada → Confirmada/Rechazada/Cancelada.
- `LineaTraspaso` representa cada línea del traspaso (material, serie o cantidad).
- Para materiales seriados: `serie` tiene valor, `cantidad=1`.
- Para materiales no seriados: `serie` es NULL, `cantidad>0`.
- Las restricciones son idénticas a las de las otras specs para mantener consistencia.
- El índice en `serie` acelera la validación de disponibilidad y cuadre.

## Migraciones
- `traspasos/migrations/0001_initial.py`: modelos `SolicitudTraspaso` y `LineaTraspaso` con restricciones e índices.
- No se crean traspasos por migración.
- No se modifican tablas de stock, series, asignaciones ni conciliaciones.

## Servicios (lógica de negocio)
Viven en `traspasos/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_tenant(actor, tenant)`:
  - Verifica que `actor.rol == "USUARIO_TENANT"`.
  - Verifica que `actor.tenant_id == tenant.id`.
  - Verifica que la cuenta esté activa y que el tenant esté activo.
  - Si no cumple, lanza `PermisoDenegado`.
- `validar_tecnicos_mismo_tenant(tecnico_origen, tecnico_destino)`:
  - Verifica que `tecnico_origen.tenant == tecnico_destino.tenant`.
  - Si no, lanza `TecnicosDistintoTenant`.
- `validar_origen_destino_distintos(tecnico_origen, tecnico_destino)`:
  - Verifica que `tecnico_origen.id != tecnico_destino.id`.
  - Si son iguales, lanza `OrigenDestinoIguales`.

### Validación de disponibilidad en origen
- `calcular_disponible_tecnico(tecnico, material)`:
  - Obtiene el stock del técnico para el material.
  - Obtiene la cantidad reservada en traspasos pendientes (estado ENVIADA).
  - Devuelve: `Disponible = Stock Técnico - Reservado`.
- `validar_serie_en_tecnico(serie, tecnico)`:
  - Consulta si la serie está asignada al técnico.
  - Si no, lanza `SerieNoEnTecnico`.
- `validar_serie_no_reservada(serie)`:
  - Consulta si la serie está reservada en un traspaso pendiente.
  - Si está reservada, lanza `SerieReservada`.

### Validación de cuadre
- `validar_cuadre_traspaso(lineas)`:
  - Para seriados: verifica que cada serie aparece exactamente una vez (sale y entra).
  - Para no seriados: verifica que la cantidad total de salida == cantidad total de entrada por material.
  - Si no cuadra, lanza `CuadreIncorrecto`.

### Creación de traspaso
- `crear_solicitud_traspaso(tenant, tecnico_origen, tecnico_destino, lineas, actor)`:
  - `validar_cuenta_tenant(actor, tenant)`.
  - `validar_tecnicos_mismo_tenant(tecnico_origen, tecnico_destino)`.
  - `validar_origen_destino_distintos(tecnico_origen, tecnico_destino)`.
  - Para cada línea:
    - Valida que el material exista en el catálogo.
    - Si es seriado:
      - Valida que la serie esté asignada al técnico origen.
      - Valida que la serie no esté reservada en otro traspaso.
    - Si es no seriado:
      - Valida la cantidad contra el disponible del técnico origen.
  - `validar_cuadre_traspaso(lineas)`.
  - En `transaction.atomic`:
    - Crea la `SolicitudTraspaso` en estado BORRADOR.
    - Crea cada `LineaTraspaso` con sus datos.
    - No reserva series ni cantidades aún (se reserva al enviar).
    - Registra auditoría de la creación.
  - Devuelve la `SolicitudTraspaso` creada.

### Envío de traspaso
- `enviar_solicitud_traspaso(solicitud, actor)`:
  - `validar_cuenta_tenant(actor, solicitud.tenant)`.
  - Verifica que `solicitud.estado == "BORRADOR"`.
  - Para cada línea seriada:
    - Valida que la serie siga asignada al técnico origen.
    - Valida que la serie no esté reservada en otro traspaso.
  - En `transaction.atomic`:
    - Cambia estado a "ENVIADA".
    - Para seriados: marca la serie como reservada en este traspaso (puede ser un campo en `Serie` o una tabla de reservas).
    - Para no seriados: reserva la cantidad del stock del técnico origen.
    - Genera el Excel de traspaso (ver `generar_excel_traspaso`).
    - Guarda ruta y hash del Excel.
    - Envía el Excel por correo al almacén (similar a spec 007).
    - Registra auditoría del envío.
  - Devuelve la `SolicitudTraspaso` actualizada.

### Generación de Excel
- `generar_excel_traspaso(solicitud)`:
  - Usa `openpyxl` para crear el Excel con dos hojas.
  - Hoja 1 "Desasignación":
    - Metadatos: Movimiento Z32, Centro PR05, Almacén BE03, NIF del técnico origen.
    - Tabla de seriales y material menor del técnico origen.
  - Hoja 2 "Asignación":
    - Metadatos: Movimiento Z31, Centro PR05, Almacén BE03, NIF del técnico destino.
    - Tabla de seriales y material menor (idéntica a hoja 1).
  - Guarda el archivo en disco con nombre único.
  - Calcula el hash SHA-256 del archivo.
  - Devuelve ruta y hash.

### Confirmación de traspaso
- `confirmar_traspaso(solicitud, actor)`:
  - `validar_cuenta_almacen(actor, solicitud.tenant.region)` (usando validación de spec 007).
  - Verifica que `solicitud.estado == "ENVIADA"`.
  - En `transaction.atomic`:
    - Cambia estado a "CONFIRMADA".
    - Para seriados:
      - Cambia el técnico de la serie (origen → destino).
      - Libera la reserva.
      - Decrementa stock del técnico origen (usando `decrementar_stock_tecnico` de spec 008).
      - Incrementa stock del técnico destino (usando `incrementar_stock_tecnico` de spec 008).
      - Reinicia el conteo de días en mano (RF-62).
    - Para no seriados:
      - Confirma la reserva (stock del origen baja, stock del destino sube).
      - Libera la reserva.
    - Registra auditoría de la confirmación.
    - Notifica al tenant que el traspaso fue confirmado.
  - Devuelve la `SolicitudTraspaso` actualizada.

### Rechazo de traspaso
- `rechazar_traspaso(solicitud, comentario, actor)`:
  - `validar_cuenta_almacen(actor, solicitud.tenant.region)`.
  - Verifica que `solicitud.estado == "ENVIADA"`.
  - Verifica que `comentario` no esté vacío.
  - En `transaction.atomic`:
    - Cambia estado a "RECHAZADA".
    - Para seriados: libera la reserva (la serie vuelve a estar disponible para traspaso).
    - Para no seriados: libera la reserva (la cantidad vuelve a estar disponible en el técnico origen).
    - Registra auditoría del rechazo (con comentario).
    - Notifica al tenant del rechazo con el motivo.
  - Devuelve la `SolicitudTraspaso` actualizada.

### Cancelación de traspaso
- `cancelar_traspaso(solicitud, actor)`:
  - `validar_cuenta_tenant(actor, solicitud.tenant)`.
  - Verifica que `solicitud.estado == "BORRADOR"`.
  - En `transaction.atomic`:
    - Cambia estado a "CANCELADA".
    - No hay series reservadas aún (solo en ENVIADA), así que no se liberan.
    - Registra auditoría de la cancelación.
  - Devuelve la `SolicitudTraspaso` actualizada.

### Consultas
- `listar_traspasos(tenant, estado=None)`:
  - Filtra siempre por `tenant`.
  - Opcionalmente filtra por estado.
  - Ordena por `fecha` descendente.
  - Devuelve un queryset paginado.
- `obtener_traspaso(tenant, traspaso_id)`:
  - Busca el traspaso filtrando por `tenant`.
  - Si no existe o pertenece a otro tenant, lanza `NoEncontrado`.
- `series_tecnico_para_traspaso(tecnico, material, q="")`:
  - Filtra series por técnico y material.
  - Solo estado `ASIGNADA` al técnico.
  - No reservadas en otros traspasos.
  - Busca por serie si se proporciona `q`.
  - Ordena por serie.
  - Devuelve un queryset paginado para el selector.

## Permisos
- Crear: `traspasos.add_solicitudtraspaso`.
- Ver: `traspasos.view_solicitudtraspaso`.
- Enviar: `traspasos.enviar_solicitudtraspaso`.
- Cancelar: `traspasos.cancelar_solicitudtraspaso`.
- Todos se asignan al rol `USUARIO_TENANT`.
- El Responsable de almacén confirma/rechaza a través de spec 007 (su bandeja incluye traspasos).
- Los servicios vuelven a validar rol, tenant y estado; nunca se confía solo en la vista.
- No se acepta `tenant_id` o técnicos desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/traspasos/` | GET | Listado paginado con filtro por estado |
| `/traspasos/nuevo/` | GET / POST | Creación de solicitud de traspaso |
| `/traspasos/<id>/` | GET | Detalle del traspaso |
| `/traspasos/<id>/enviar/` | POST | Enviar traspaso al almacén |
| `/traspasos/<id>/cancelar/` | POST | Cancelar traspaso (solo borrador) |
| `/traspasos/series-tecnico/` | GET | Fragmento HTMX con series del técnico para selector |
| `/traspasos/validar-disponibilidad/` | POST | Validación en tiempo real de disponibilidad |

### Pantallas
- **Listado:** Fecha, técnico origen, técnico destino, estado, total series, total cantidad. Filtro por estado.
- **Creación:**
  - Selector de técnico origen (solo activos del tenant).
  - Selector de técnico destino (solo activos del tenant, != origen).
  - Fecha (precompletada con hoy, editable).
  - Lista de líneas (agregar/editar/eliminar).
  - Para cada línea:
    - Selector de material.
    - Tipo de material (solo lectura).
    - Lote (solo lectura).
    - Para seriados: selector de series del técnico origen (multi-select con búsqueda).
    - Para no seriados: campo numérico para cantidad.
    - Validación en tiempo real de disponibilidad.
  - Vista previa de cuadre (lo que sale vs lo que entra).
  - Botón "Guardar borrador" y "Enviar".
- **Detalle:**
  - Datos del traspaso (técnicos, fecha, estado).
  - Lista de líneas.
  - Descarga del Excel (si generado).
  - Acciones según estado (enviar, cancelar).
- **Selector de series:**
  - HTMX fragmento con búsqueda y paginación.
  - Muestra solo series Asignadas al técnico origen.
  - Permite selección múltiple.

### Validación en tiempo real
- Similar a spec 006, pero validando disponibilidad del técnico origen.
- El endpoint `/traspasos/validar-disponibilidad/` valida:
  - Material.
  - Cantidad (para no seriados).
  - Lista de series (para seriados).
- Devuelve JSON con estado, disponible y alertas.
- El endpoint `/traspasos/series-tecnico/` devuelve series del técnico origen.

## Integraciones
- **Stock (spec 008):** usa `incrementar_stock_tecnico` y `decrementar_stock_tecnico` para actualizar stock de origen y destino.
- **Series (transversal):** las series cambian de técnico (origen → destino).
- **Catálogo de materiales (spec 002):** el selector de materiales consulta el catálogo compartido.
- **Técnicos (spec 003):** el selector de técnicos usa `tecnicos_para_operacion`.
- **Envío de Excel (spec 007):** el envío por correo al almacén es similar a las asignaciones.
- **Auditoría (transversal):** toda operación registra usuario, fecha y cambios.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Tenant de la sesión | Servicio y decorador | "No tienes permiso para crear traspasos" |
| Técnicos mismo tenant | Servicio | "Los técnicos deben ser del mismo tenant" |
| Origen y destino distintos | Servicio y `CheckConstraint` | "El técnico origen y destino no pueden ser el mismo" |
| Serie asignada a origen | Servicio | "La serie no está asignada al técnico origen" |
| Serie no reservada | Servicio | "La serie está reservada en otro traspaso" |
| Cantidad no supera disponible | Servicio | "La cantidad supera el stock del técnico" |
| Cuadre correcto | Servicio | "Lo que sale debe cuadrar con lo que entra" |
| Estado Borrador para enviar | Servicio | "Solo se pueden enviar traspasos en borrador" |
| Estado Borrador para cancelar | Servicio | "Solo se pueden cancelar traspasos en borrador" |

## Transacciones y concurrencia
- La creación del traspaso y sus líneas se ejecutan en una sola transacción.
- El envío del traspaso, la reserva de series, la generación del Excel y el envío de correo se ejecutan en una sola transacción.
- La confirmación del traspaso, el cambio de técnico de series, la actualización de stock y la liberación de reservas se ejecutan en una sola transacción.
- La validación de disponibilidad se ejecuta antes de la transacción para fallar rápido.
- Si dos sesiones intentan reservar la misma serie simultáneamente:
  - La primera en validar pasa.
  - La segunda detecta que la serie ya está reservada y falla.
- No se usan bloqueos de aplicación; el estado de reserva es la fuente de verdad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_traspaso_mismo_tenant_genera_excel_dos_hojas`
- `test_origen_destino_iguales_se_rechaza`
- `test_solo_cede_lo_que_tiene_asignado`
- `test_cuadre_series_incorrecto_rechaza`
- `test_cuadre_cantidades_incorrecto_rechaza`
- `test_confirmar_cambia_tecnico_de_series`
- `test_rechazar_no_cambia_nada`
- `test_stock_general_invariable`
- `test_dias_en_mano_reinician_al_traspasar`
- `test_validar_cuadre_traspaso`
- `test_series_tecnico_para_traspaso_muestra_asignadas`
- `test_cancelar_traspaso_borrador`

Además, pruebas de base de datos:
- Insertar un traspaso con origen = destino debe fallar.
- Insertar una serie con formato inválido directamente debe fallar.
- Insertar dos líneas del mismo traspaso con la misma serie debe fallar.

## Decisiones y riesgos
- **Excel de dos hojas:** representa los dos movimientos (Z32 desasignación, Z31 asignación). Esto requiere generar dos hojas en el mismo archivo Excel.
- **Reserva al enviar:** similar a asignaciones, la reserva se hace al enviar, no al crear. Permite ediciones en borrador.
- **Cuadre por material y serie:** asegura integridad del traspaso. Si no cuadra, se rechaza todo. Esto puede ser estricto pero previene errores.
- **Cambio de técnico de series:** requiere actualizar la FK de técnico en el modelo de `Serie`. Alternativa: tener una tabla de asignación, pero eso añade complejidad.
- **Stock general invariable:** es una regla de negocio clave. Se debe asegurar que ninguna función de este módulo toque el stock general.
- **Selector de series del técnico origen:** muestra solo series Asignadas al técnico, no reservadas en otros traspasos.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Riesgo de cuadre estricto:** si el cuadre es muy estricto, puede rechazar traspasos válidos por errores menores. Se puede añadir tolerancia si el negocio lo requiere.
- **Riesgo de concurrencia en series:** si una serie se traspasa mientras está reservada en otro traspaso, falla. La validación de disponibilidad al enviar mitiga esto.
