# Contrato: servicios de traspaso

Los servicios viven en `traspasos/services.py`; las vistas solo orquestan. No hay lógica de negocio
en modelos, formularios ni plantillas.

## Tipos

| Tipo | Definición |
|---|---|
| `tenant` | `tenants.Tenant` de la sesión |
| `region` | `tenants.Region` de `tenant.region` |
| `actor` | `acceso.Usuario` de la sesión |
| `lineas` | Lista de `LineaEntrada` (material, serie o cantidad) |
| `solicitud` | `traspasos.SolicitudTraspaso` |

```python
@dataclass(frozen=True)
class LineaEntrada:
    material: Material
    serie: Serie | None
    cantidad: int
```

## Excepciones

| Excepción | Mensaje |
|---|---|
| `PermisoDenegado` | “No tienes permiso para crear traspasos” / “No tienes permiso para gestionar traspasos” |
| `TecnicosDistintoTenant` | “Los técnicos deben ser del mismo tenant” |
| `OrigenDestinoIguales` | “El técnico origen y destino no pueden ser el mismo” |
| `TecnicoNoExiste` | “El técnico no existe” / “El técnico destino no está activo” |
| `MaterialNoExiste` | “El material no existe” |
| `SerieNoEnTecnico` | “La serie no está asignada al técnico origen” |
| `SerieReservada` | “La serie está reservada en otro traspaso” |
| `StockTecnicoInsuficiente` | “La cantidad supera el stock del técnico” |
| `CuadreIncorrecto` | “Lo que sale debe cuadrar con lo que entra” |
| `EstadoTraspasoInvalido` | Mensaje según la acción (enviar, cancelar, confirmar o rechazar) |
| `MotivoRechazoRequerido` | “El motivo de rechazo es obligatorio” |
| `NoEncontrado` | “El traspaso no existe” |
| `ArchivoNoDisponible` | “El archivo no está disponible” |
| `HashNoCoincide` | “El archivo fue modificado, descarga bloqueada” |

## Datos de cuadre

```python
@dataclass(frozen=True)
class MovimientoTraspaso:
    material_id: int
    lote: str
    serie_id: int | None
    cantidad: int

@dataclass(frozen=True)
class CuadreTraspaso:
    salida: list[MovimientoTraspaso]
    entrada: list[MovimientoTraspaso]
```

- `construir_movimientos(lineas) -> CuadreTraspaso`: proyecta la lista canónica a salida y entrada.
- `validar_cuadre_traspaso(cuadre) -> None`: lanza `CuadreIncorrecto` si las proyecciones no
  coinciden en series, materiales, lotes o cantidades.
- `resumen_cuadre(lineas) -> dict`: totales por material para la vista previa.

## Validación de alcance

### `validar_cuenta_tenant(actor, tenant) -> None`

- Exige `actor.rol == "USUARIO_TENANT"`, cuenta activa y `actor.tenant_id == tenant.id`.
- Si no, `PermisoDenegado`.

### `validar_cuenta_almacen(actor, region) -> None`

- Reutiliza `asignaciones.services.validar_cuenta_almacen` de 007.
- Exige `RESPONSABLE_ALMACEN`, región activa y almacén activo.
- Si no, `PermisoDenegado`.

### `validar_tecnicos(origen, destino, tenant) -> None`

- Ambos existen y pertenecen al tenant; si no, `TecnicosDistintoTenant`.
- `origen.id != destino.id`; si no, `OrigenDestinoIguales`.
- El destino está activo; si no, `TecnicoNoExiste`.
- El origen puede estar inactivo si aún tiene stock.

## Disponibilidad

### `calcular_reservado_tecnico(tecnico, material) -> int`

- Suma líneas no seriadas de solicitudes `ENVIADA` del técnico y material.
- Cuenta 1 por cada línea seriada de solicitudes `ENVIADA`.
- No escribe ni bloquea.

### `calcular_disponible_tecnico(tecnico, material) -> int`

- `max(0, StockTecnico.cantidad - calcular_reservado_tecnico(...))`.
- Material sin stock devuelve `0`.

### `series_disponibles_para_traspaso(tecnico, material, q="") -> QuerySet[Serie]`

- `estado=ASIGNADA`, `tecnico=tecnico`, mismo tenant y material.
- Excluye series con línea en solicitud `ENVIADA`.
- Filtra por número si `q` no está vacío; ordena por número.

### `validar_disponibilidad_lineas(origen, lineas) -> None`

- Seriados: cada serie `ASIGNADA` al origen, mismo tenant/material y no reservada.
- No seriados: suma por material y compara con `calcular_disponible_tecnico`.
- No crea reservas.

## Operaciones

### `crear_solicitud_traspaso(tenant, origen, destino, fecha, lineas, actor) -> SolicitudTraspaso`

1. `validar_cuenta_tenant`, `validar_tecnicos`, materiales y disponibilidad.
2. `validar_cuadre_traspaso(construir_movimientos(lineas))`.
3. `transaction.atomic`: crear solicitud `BORRADOR` con `region=tenant.region` y líneas con
   `tenant`/`lote`; auditar alta de solicitud y líneas.
4. No reservar series ni cantidades; no generar Excel.
5. Devolver la solicitud.

### `actualizar_lineas_borrador(solicitud, lineas, actor) -> SolicitudTraspaso`

1. Exigir `BORRADOR` y tenant del actor; si no, `EstadoTraspasoInvalido` o `NoEncontrado`.
2. Revalidar disponibilidad y cuadre.
3. `transaction.atomic`: reemplazar líneas, auditar bajas y altas.
4. No tocar stock, series ni Excel.

### `enviar_solicitud_traspaso(solicitud, actor) -> SolicitudTraspaso`

1. `validar_cuenta_tenant` y exigir `BORRADOR`.
2. `transaction.atomic`:
   - Bloquear solicitud, `Tenant`, `StockTecnico` por `(material_id, tecnico_id)` y series por `id`.
   - Revalidar técnicos, disponibilidad, reservas y cuadre.
   - Cambiar a `ENVIADA`, `enviada_en=ahora`, `actualizado_por=actor`.
   - Generar Excel, guardar `excel_ruta`/`excel_hash`.
   - Auditar `SolicitudTraspaso/estado` y `SolicitudTraspaso/excel`.
3. Si falla la generación, revertir y eliminar el archivo parcial.
4. No enviar correo ni encolar tareas.

### `confirmar_traspaso(solicitud, actor) -> ResultadoTraspaso`

1. `validar_cuenta_almacen(actor, solicitud.region)` y exigir `ENVIADA`.
2. `transaction.atomic`:
   - Bloquear solicitud, `Tenant`, `StockTecnico` de ambos técnicos por `(material_id, tecnico_id)`
     y series por `id`.
   - Revalidar que cada serie siga `ASIGNADA` al origen y que el stock alcance.
   - Revalidar cuadre.
   - Por serie: `tecnico=destino`, `asignada_en=ahora`; estado `ASIGNADA`.
   - Por material: `decrementar_stock_tecnico(origen, material, total, actor)` e
     `incrementar_stock_tecnico(destino, material, total, actor)`.
   - Cambiar a `CONFIRMADA`, `confirmada_en=ahora`, `actualizado_por=actor`.
   - Auditar estado, `Serie/tecnico` y `Serie/asignada_en`.
3. No leer ni escribir `StockGeneral`.
4. Devolver `ResultadoTraspaso` con series movidas, totales y fechas.

### `rechazar_traspaso(solicitud, comentario, actor) -> SolicitudTraspaso`

1. `validar_cuenta_almacen(actor, solicitud.region)` y exigir `ENVIADA`.
2. Exigir comentario no vacío, no solo espacios, máximo 1000.
3. `transaction.atomic`: `RECHAZADA`, `rechazada_en`, `motivo_rechazo`, `actualizado_por`; auditar
   estado y motivo.
4. No cambiar series, stock ni Excel. La reserva se libera al dejar de estar `ENVIADA`.

### `cancelar_traspaso(solicitud, actor) -> SolicitudTraspaso`

1. `validar_cuenta_tenant` y exigir `BORRADOR`.
2. `transaction.atomic`: `CANCELADA`, `cancelada_en`, `actualizado_por`; auditar.
3. No hay reservas que liberar.

### `revalidar_traspaso(solicitud) -> None`

- Verifica líneas completas, series `ASIGNADA` al origen, no reservadas por otra solicitud y stock
  suficiente.
- Lanza `SerieNoEnTecnico`, `SerieReservada`, `StockTecnicoInsuficiente` o `CuadreIncorrecto`.

## Excel

### `generar_excel_traspaso(solicitud) -> tuple[str, str]`

- Devuelve `(ruta_relativa, hash_sha256)`.
- Dos hojas: `Desasignación` (Z32) y `Asignación` (Z31).
- Metadatos: movimiento, Centro, Almacén, NIF, fecha, tenant, región e ID.
- Tabla de seriales y tabla de material menor.
- Nombre seguro `traspasos/<tenant_id>/traspaso-<id>-<hash>.xlsx`.
- No envía correo.

### `verificar_hash_excel(solicitud, contenido: bytes) -> None`

- Recalcula SHA-256 y compara con `hmac.compare_digest`.
- Si no coincide, `HashNoCoincide`.

## Resultado

```python
@dataclass(frozen=True)
class ResultadoTraspaso:
    solicitud_id: int
    series_movidas: list[int]
    cambios_por_material: list[CambioMaterialTraspaso]
    confirmada_en: datetime | None
    total_series: int
    total_no_seriados: int
```

`CambioMaterialTraspaso`: `material_id`, `stock_origen_anterior`, `stock_origen_nuevo`,
`stock_destino_anterior`, `stock_destino_nuevo`.

## Consultas

- `listar_traspasos(tenant, estado=None, q="")`
- `obtener_traspaso(tenant, traspaso_id)`
- `obtener_traspaso_almacen(region, traspaso_id)`
- `detalle_traspaso(solicitud)`
- `resumen_cuadre(solicitud)`

## Reglas transversales

- Toda operación de escritura ocurre en una transacción y audita en la misma transacción.
- Nunca se acepta `tenant_id`/`region_id` del cliente.
- 009 no toca `StockGeneral`, no crea series, no cambia el estado de las series y no reabre
  solicitudes.
- No se usan permisos Django por cadena.
- No se usa `F()` ciego para stock; se usan los servicios de 008.

## Pruebas de contrato

- Cada servicio tiene la firma, retorno y excepción indicados.
- Crear no reserva ni genera Excel; enviar reserva y genera; confirmar mueve custodia/stock; rechazar y
  cancelar no mueven nada.
- El stock general queda idéntico en todo el ciclo.
- `Serie.asignada_en` se reinicia solo al confirmar el traspaso.
- Un fallo de auditoría o de Excel revierte la transacción.
- Ningún servicio expone datos de otro tenant.
