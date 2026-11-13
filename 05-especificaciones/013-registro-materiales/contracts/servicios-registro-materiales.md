# Contrato: servicios de registro de materiales

Los servicios viven en `registro_materiales/services.py`, `carga.py`, `dashboard.py`, `cierre.py` y
`exportacion.py`. Las vistas solo orquestan.

## Tipos

| Tipo | Definición |
|---|---|
| `tenant` | `tenants.Tenant` de la sesión |
| `tecnico` | `tecnicos.Tecnico` del tenant |
| `periodo` | `YYYY-MM` |
| `texto` | Texto pegado de órdenes |
| `cantidades` | `material_id -> cantidad` |
| `actor` | `acceso.Usuario` de la sesión |

```python
@dataclass(frozen=True)
class ListaNormalizada:
    ordenes: list[str]
    rechazadas: list[str]

@dataclass(frozen=True)
class ResumenCarga:
    leidas: int
    nuevas: int
    omitidas: int
    tambien_otro_tecnico: int

@dataclass(frozen=True)
class ArchivoReporte:
    nombre: str
    contenido: bytes
    content_type: str
```

## Excepciones

| Excepción | Mensaje |
|---|---|
| `PermisoDenegado` | “No tienes permiso para registrar materiales” |
| `TecnicoNoExiste` | “El técnico no pertenece a tu tenant” |
| `MaterialNoHabilitado` | “El material no está habilitado para tu tenant” |
| `MaterialInactivo` | “El material está deshabilitado” |
| `CantidadInvalida` | “La cantidad debe ser un número entero mayor o igual a 0” |
| `NumeroOrdenInvalido` | “El número de orden es obligatorio y debe tener entre 1 y 30 caracteres alfanuméricos” |
| `PeriodoInvalido` | “El periodo debe tener el formato AAAA-MM” |
| `SaldoInsuficiente` | “El uso supera el disponible del mes” |
| `PeriodoCerrado` | “El mes está cerrado; solicita reapertura” |
| `CargaNoDeshacible` | “No se puede deshacer: hay órdenes con materiales registrados” |
| `CierreBloqueado` | “El cierre tiene pendientes sin resolver o justificar” |
| `BackupRequerido` | “Debes registrar la referencia del respaldo antes de cerrar” |
| `NoEncontrado` | “El registro no existe” |

## Normalización y carga masiva

### `procesar_lista(texto) -> ListaNormalizada`

- Quita espacios al inicio y al final.
- Descarta líneas vacías.
- Rechaza líneas con espacios internos, tabs, comas, punto y coma o más de un token.
- Deduplica sin distinguir mayúsculas/minúsculas.
- Conserva el original y devuelve el normalizado para comparar.

### `previsualizar_carga(tenant, tecnico, periodo, texto) -> ResumenCarga`

- Compara con las órdenes del técnico y periodo.
- Cuenta nuevas, omitidas y cuántas también existen para otro técnico.
- No escribe en base.

### `confirmar_carga(tenant, tecnico, periodo, texto, actor) -> CargaOrdenes`

- Vuelve a normalizar y calcular el resumen.
- En `transaction.atomic`: crea `CargaOrdenes` y solo las órdenes nuevas.
- Las órdenes existentes no cambian de técnico ni de estado.
- No modifica materiales ni saldos.

### `deshacer_carga(carga, actor, motivo="") -> CargaOrdenes`

- Solo si las órdenes creadas por el lote no tienen usos con cantidad > 0.
- Elimina las órdenes del lote y audita `CargaOrdenes/deshecha`.
- Si alguna tiene materiales, `CargaNoDeshacible` con la lista.

## Órdenes y materiales

### `buscar_orden(tenant, tecnico, periodo, numero) -> OrdenLiquidacion | None`

- Compara `numero_normalizado` en mayúsculas.
- Filtra por tenant, técnico y periodo.
- Búsqueda exacta, sin distinguir mayúsculas/minúsculas.

### `guardar_uso(orden, fecha_instalacion, cantidades, actor) -> OrdenLiquidacion`

1. Exige mes abierto (`CierreMensual.estado != CERRADO`).
2. Valida fecha, técnico, materiales habilitados/activos y cantidades.
3. Calcula el periodo de la fecha; si cambia, revalida `(tenant, tecnico, periodo, numero)`.
4. Calcula por material:
   - `disponible = saldo_inicial + despachos`.
   - `uso_total` del periodo, excluyendo el uso actual de la orden.
   - `uso_nuevo = uso_total + cantidad_nueva`.
5. Si `uso_nuevo > disponible`, lanza `SaldoInsuficiente` con disponible, usado y faltante.
6. Si `cantidad > factor * promedio_mensual_ultimos_3_cierres`, crea `AdvertenciaUso`
   (`CANTIDAD_ATIPICA`). El promedio usa el total mensual usado por material, no el promedio por
   orden. Sin historial no advierte.
7. Crea/actualiza `UsoMaterialOrden`; las líneas existentes que pasan a 0 se conservan.
8. Actualiza `fecha_instalacion` y `periodo` de la orden; audita.
9. No toca stock.

### `resolver_advertencia(advertencia, justificacion, actor) -> AdvertenciaUso`

- Exige `justificacion` no vacía.
- Marca `resuelta=True`, `justificacion`, `resuelta_por`, `resuelta_en`.
- Audita `AdvertenciaUso/resuelta`.
- No modifica el uso ni el saldo.

### `historial_orden(tenant, orden_id) -> QuerySet[RegistroCambio]`

- Filtra por tenant, entidad/ID de orden y usos.
- Ordena por fecha descendente.

## Saldos

### `registrar_saldo_inicial(tenant, material, periodo, cantidad, actor)`

- Exige mes abierto.
- Valida material habilitado/activo, periodo y cantidad.
- Crea/actualiza; audita.
- No permite un saldo que deje el mes en negativo si ya hay uso.

### `saldo_inicial_efectivo(tenant, material, periodo) -> int`

- Manual si existe.
- Si no, el `SaldoMensualMaterial` del cierre anterior.
- Si no hay cierre, el saldo final calculado del mes anterior.
- Si no hay datos, 0.

### `saldo_final(tenant, material, periodo) -> int`

- `inicial + despachos - usado`.
- Puede ser negativo en el dashboard; el guardado de uso impide generarlo.

### `despachos_del_periodo(tenant, periodo) -> dict[material_id, int]`

- Agrega `DespachoAlmacen` por material y mes.
- Solo lectura.
- No crea, edita ni borra despachos.
- `validar_periodo_abierto(tenant, periodo)` se invoca también desde el servicio existente de alta/edición de `DespachoAlmacen`; si el mes está cerrado, `PeriodoCerrado`.

## Dashboard

### `dashboard_mensual(tenant, periodo, tecnico=None, material=None, desde=None, hasta=None)`

- Materiales habilitados activos más los que tengan datos.
- Por material: inicial, despachos, usado, final y alerta.
- Detalle por técnico.
- Totales de órdenes y técnicos con uso.
- Sin N+1.

## Pendientes

### `ordenes_pendientes(tenant, periodo=None, dias=None)`

- Órdenes sin usos con cantidad > 0.
- Filtro por antigüedad y técnico.
- Ordenadas por antigüedad.

## Cierre

### `lista_chequeo(tenant, periodo) -> list[PendienteCierre]`

- Órdenes sin materiales.
- Materiales con saldo negativo.
- Advertencias sin resolver.

### `justificar_pendiente(cierre, tipo, referencia, motivo, actor)`

- Crea `JustificacionCierre`.
- No modifica el dato original.
- Si el tipo es `ADVERTENCIA`, marca la advertencia como resuelta con la misma justificación.

### `validar_backup_ref(backup_ref) -> None`

- No vacío.
- Formato `backups/<archivo>` o referencia emitida por `respaldar_bd`.
- Si no es válido, lanza `BackupRequerido`.

### `cerrar_mes(tenant, periodo, backup_ref, actor) -> CierreMensual`

- Exige checklist resuelto/justificado.
- Exige `backup_ref` y ejecuta `validar_backup_ref`.
- En `transaction.atomic`: `CERRADO`, snapshot por material, auditoría.
- No permite cerrar si falta backup.
- Al reabrir y recerrar, reemplaza el snapshot con auditoría de valores anteriores; conserva la versión anterior en el historial de auditoría.

### `reabrir_mes(cierre, motivo, actor) -> CierreMensual`

- Exige motivo.
- `ABIERTO`, versión +1, actor/fecha, auditoría.
- Un mes cerrado rechaza usos, saldos y despachos con `PeriodoCerrado`.

## Exportación

### `exportar_reporte_mensual(tenant, periodo, formato) -> ArchivoReporte`

- `formato` `xlsx` o `csv`.
- Incluye inicial, despachos, usado, final y detalle por técnico.
- Solo datos del tenant.

### `exportar_detalle_ordenes(tenant, periodo, formato) -> ArchivoReporte`

- Técnico, orden, fecha, materiales y cantidades.
- Solo datos del tenant.

## Reglas transversales

- Toda escritura ocurre en una transacción y audita en la misma transacción.
- Nunca se acepta `tenant` del cliente.
- 013 no lee ni escribe stock, series, asignaciones, traspasos ni conciliaciones.
- `DespachoAlmacen` es de solo lectura.
- No se borran datos, salvo deshacer una carga sin materiales.
- No se usan permisos Django por cadena.

## Pruebas de contrato

- Normalización, deduplicación y resumen.
- Carga idempotente y deshacer sin materiales.
- Uso 0 no suma; uso que supera disponible se bloquea.
- Advertencia atípica no bloquea; `resolver_advertencia` la marca resuelta.
- Saldo final, herencia y bloqueo de saldo inicial negativo.
- Dashboard y pendientes.
- Cierre bloqueado, cierre con backup válido y reapertura.
- Un despacho no se edita en un mes cerrado.
- Exportación Excel/CSV solo del tenant.
