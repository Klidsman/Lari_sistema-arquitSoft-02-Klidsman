# Contrato: servicios de stock de 008

Los servicios viven en `stock/services.py` y son internos. No hay endpoints, vistas, rutas,
plantillas ni tareas Celery en 008. Cada consumidor valida rol y alcance antes de llamarlos y los
invoca dentro de su propia transacción.

## Tipos de entrada

| Tipo | Definición |
|---|---|
| `tenant` | Instancia de `tenants.Tenant`. Nunca un `tenant_id` recibido del cliente. |
| `material` | Instancia de `materiales.Material`. |
| `tecnico` | Instancia de `tecnicos.Tecnico`; su tenant debe coincidir con el del consumidor. |
| `cantidad` | Entero estrictamente mayor que `0`. |
| `actor` | `acceso.Usuario` de la sesión; nunca `None` en operaciones humanas. |
| `solicitud` | `asignaciones.SolicitudAsignacion` en estado `ENVIADA`. |

## Excepciones

| Excepción | Cuándo | Código que propaga el consumidor |
|---|---|---|
| `CantidadInvalida` | `cantidad` no es entero, es cero o negativa | `400` |
| `StockInsuficiente` | El stock general o técnico no alcanza | `409` |
| `StockNoExiste` | Material o fila de stock requerida no existe | `400`/`404` según el consumidor |
| `TecnicoNoExiste` | Técnico inexistente o de otro tenant | `400` |
| `TenantNoCoincide` | Técnico o material fuera del tenant de la solicitud | `403` |
| `SerieNoReservada` | Serie no está `RESERVADA`, no pertenece al tenant/material o ya fue asignada | `409` |
| `ConfirmacionStockInvalida` | Solicitud no `ENVIADA`, sin líneas o incompleta | `409` |

Mensajes exactos:

- “La cantidad debe ser mayor a 0”
- “El tenant no tiene suficiente stock general”
- “El técnico no tiene suficiente stock”
- “La serie no está reservada para esta asignación”
- “No se puede confirmar el stock de la asignación”

Los mensajes no revelan la existencia de datos de otro tenant.

## Consultas (solo lectura)

### `obtener_stock_general(tenant, material) -> int`

- Devuelve `StockGeneral.cantidad` o `0` si no existe.
- No crea filas, no bloquea, no audita.

### `obtener_stock_tecnico(tecnico, material) -> int`

- Devuelve `StockTecnico.cantidad` o `0` si no existe.
- No crea filas, no bloquea, no audita.

### `calcular_reservado(tenant, material) -> int`

- Suma solo las líneas no seriadas (`serie__isnull=True`) de `LineaAsignacion` cuya
  `SolicitudAsignacion` está `ENVIADA` y pertenece al mismo tenant y material.
- No cuenta líneas seriadas: su reserva vive en `Serie.estado = RESERVADA`.
- No crea filas ni bloquea.

### `calcular_disponible(tenant, material) -> int`

- `max(0, obtener_stock_general(tenant, material) - calcular_reservado(tenant, material))`.
- Material sin `StockGeneral` devuelve `0`.
- No escribe.

## Escrituras fundacionales

### `incrementar_stock_general(tenant, material, cantidad, actor) -> int`

- Valida entero `> 0`; si no, `CantidadInvalida`.
- Dentro de `transaction.atomic`: bloquea el `Tenant`, bloquea la fila de `StockGeneral` con
  `select_for_update` o la crea si no existe, suma `cantidad` y audita
  `StockGeneral/cantidad` con valor anterior y nuevo.
- Devuelve la cantidad resultante.
- Un fallo revierte suma y auditoría.

### `decrementar_stock_general(tenant, material, cantidad, actor) -> int`

- Valida entero `> 0`; si no, `CantidadInvalida`.
- Dentro de `transaction.atomic`: bloquea el `Tenant`, bloquea la fila con `select_for_update`; si
  no existe o `cantidad_actual < cantidad`, lanza `StockInsuficiente` **sin escribir**.
- Si alcanza, resta, audita y devuelve la cantidad resultante.
- Prohibido crear una fila con `cantidad` negativa o usar `cantidad=-1` como señal.
- Prohibido decrementar con `F()` ciego: se lee bajo bloqueo, se valida y luego se escribe.

### `incrementar_stock_tecnico(tecnico, material, cantidad, actor) -> int`

- Valida entero `> 0`; si no, `CantidadInvalida`.
- Valida que el técnico exista; si no, `TecnicoNoExiste`.
- Copia `tenant` desde `tecnico.tenant`; si la fila existente tiene otro tenant, `TenantNoCoincide`.
- Dentro de `transaction.atomic`: bloquea la fila de `StockTecnico` por `(tenant, tecnico, material)`
  con `select_for_update` o la crea si no existe, suma, audita `StockTecnico/cantidad` y devuelve el
  resultado.

### `decrementar_stock_tecnico(tecnico, material, cantidad, actor) -> int`

- Valida entero `> 0`; si no, `CantidadInvalida`.
- Valida que el técnico exista y que el `tenant` de la fila coincida con `tecnico.tenant`.
- Bloquea la fila con `select_for_update`; si no existe o no alcanza, `StockInsuficiente` sin
  escribir.
- Si alcanza, resta, audita y devuelve el resultado.
- Nunca deja `cantidad` negativa.

## Confirmación

### `actualizar_stock_confirmacion_asignacion(solicitud, actor) -> ResultadoConfirmacionStock`

Debe invocarse dentro de la transacción abierta por 007. Si se invoca fuera, abre su propio
`transaction.atomic` y exige que la solicitud siga `ENVIADA`; nunca hace commit propio.

**Validaciones previas**

1. `solicitud.estado == "ENVIADA"` y al menos una línea; si no, `ConfirmacionStockInvalida`.
2. El técnico de la solicitud pertenece a `solicitud.tenant`; si no, `TenantNoCoincide`.
3. Cada línea seriada referencia una `Serie` con `estado == RESERVADA`, del mismo tenant y del
   material de la línea; si no, `SerieNoReservada`.
4. Cada línea no seriada tiene `cantidad > 0`; si no, `CantidadInvalida`.
5. Agregado por material: el `StockGeneral` alcanza `series + cantidad_no_seriada`; si no,
   `StockInsuficiente`.

**Bloqueos, en orden estable ascendente**

`SolicitudAsignacion` (ya bloqueada por 007) → `Tenant` → `StockGeneral` por `material_id` →
`StockTecnico` por `material_id` → `Serie` por `id`.

**Escrituras**

- Cada serie: `estado = ASIGNADA`.
- `StockTecnico`: `cantidad += series + cantidad_no_seriada` por material; crea la fila si no
  existe con `tenant = solicitud.tenant`.
- `StockGeneral`: `cantidad -= series + cantidad_no_seriada` por material; nunca negativa.
- Auditoría: `Serie/estado` por serie y `StockTecnico/cantidad`/`StockGeneral/cantidad` por material.
- **No** modifica `SolicitudAsignacion.estado` ni `SolicitudAsignacion.confirmada_en`: son de 007.
- **No** libera series ni participa en el rechazo: eso es de 007.

**Resultado** (`dataclass` inmutable)

| Campo | Tipo | Contenido |
|---|---|---|
| `solicitud_id` | `int` | Solicitud confirmada |
| `series_actualizadas` | `list[int]` | IDs de series `RESERVADA→ASIGNADA` |
| `cambios_por_material` | `list[CambioStockMaterial]` | Detalle agregado |
| `confirmada_en` | `datetime` | Solo lectura; lo fija 007 |
| `total_series` | `int` | Series actualizadas |
| `total_cantidad` | `int` | Suma de no seriados |

`CambioStockMaterial`: `material_id`, `stock_general_anterior`, `stock_general_nuevo`,
`stock_tecnico_anterior`, `stock_tecnico_nuevo`.

## Reglas transversales

- Toda escritura ocurre en una transacción; un fallo revierte stock, series y auditoría.
- Ningún servicio acepta `tenant_id`/`region_id` del cliente; el alcance sale de la sesión y de la
  solicitud.
- Ningún servicio elimina filas de stock; se ajustan con movimiento auditado.
- Los servicios fundacionales son idempotentes respecto de su propia transacción: repetir una
  llamada con la misma cantidad vuelve a mover stock, por lo que el consumidor debe evitar
  reintentos ciegos.
- `calcular_reservado` y `calcular_disponible` son de solo lectura y no bloquean.

## Pruebas de contrato

- Cada firma existe con el nombre, orden y tipos indicados.
- `cantidad=0` y `cantidad=-1` producen `CantidadInvalida` y no escriben.
- `decrementar_stock_general`/`decrementar_stock_tecnico` con stock insuficiente lanzan
  `StockInsuficiente` y dejan la fila intacta.
- Una fila de `StockTecnico` con `tenant` distinto al de `tecnico.tenant` produce `TenantNoCoincide`
  y no se modifica.
- `actualizar_stock_confirmacion_asignacion` fuera de una transacción abre la suya y no confirma
  por separado.
- La confirmación no cambia `estado` ni `confirmada_en` de la solicitud.
- El resultado contiene los IDs de series y los valores anterior/nuevo por material.
- Ningún servicio expone datos de otro tenant.
