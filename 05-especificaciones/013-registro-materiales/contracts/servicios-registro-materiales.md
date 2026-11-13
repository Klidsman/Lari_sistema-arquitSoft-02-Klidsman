# Contrato: servicios de registro de materiales

Los servicios viven en `registro_materiales/services.py`; las vistas solo orquestan.

## Tipos

| Tipo | Definición |
|---|---|
| `tenant` | `tenants.Tenant` de la sesión |
| `tecnico` | `tecnicos.Tecnico` del tenant |
| `periodo` | `YYYY-MM` |
| `cantidades` | Diccionario `material_id -> cantidad` |
| `actor` | `acceso.Usuario` de la sesión |

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
| `RecojoNoExiste` | “El recojo no pertenece a tu tenant” |
| `LineaRecojoNoExiste` | “La línea de recojo no pertenece al recojo” |
| `MaterialNoCoincide` | “El material no coincide con la línea de recojo” |
| `DespachoExcedeRecojo` | “La cantidad despachada supera la cantidad del recojo” |
| `TecnicoNoCoincide` | “El técnico de la línea no coincide con el técnico de la orden” |
| `NoEncontrado` | “El registro no existe” |

## Periodos y cantidades

### `periodo_de_fecha(fecha) -> str`

- Devuelve `YYYY-MM` según la zona configurada.

### `validar_periodo(periodo) -> None`

- Exige `^[0-9]{4}-(0[1-9]|1[0-2])$`; si no, `PeriodoInvalido`.

### `normalizar_numero_orden(valor) -> str`

- `strip`, mayúsculas y sin espacios internos.
- Exige 1–30 alfanuméricos (`^[A-Z0-9]{1,30}$`); si no, `NumeroOrdenInvalido`.

### `validar_cantidad(valor, permitir_vacio=False) -> int`

- Normaliza espacios.
- Vacío → 0 si `permitir_vacio`; si no, `CantidadInvalida`.
- Rechaza negativos, decimales y texto; devuelve entero `>=0`.

## Catálogo

### `materiales_habilitados(tenant, incluir_inactivos=False) -> QuerySet`

- Filtra por tenant; por defecto solo activos.
- Ordena por `orden`, `material.codigo`.

### `habilitar_material(tenant, material, actor) -> MaterialHabilitado`

- Crea o reactiva; audita `MaterialHabilitado/alta` o `/activo`.

### `deshabilitar_material(tenant, material, actor) -> MaterialHabilitado`

- Marca inactivo; audita `MaterialHabilitado/activo`; conserva historial.

## Órdenes

### `obtener_orden(tenant, tecnico, numero_orden, fecha) -> OrdenLiquidacion`

- Normaliza número y periodo.
- Busca por `(tenant, tecnico, periodo, numero_orden)`.
- Devuelve la existente o una instancia sin guardar con el catálogo habilitado.

### `guardar_orden(tenant, tecnico, numero_orden, fecha, cantidades, actor) -> OrdenLiquidacion`

1. Valida cuenta, técnico, número, fecha y cantidades.
2. Exige materiales habilitados/activos para líneas nuevas; permite editar líneas históricas de un
   material que se deshabilitó después.
3. `transaction.atomic`:
   - Bloquear `Tenant` y la orden existente con `select_for_update`.
   - Calcular periodo y crear/actualizar la orden; revalidar unicidad de la nueva clave.
   - Crear/actualizar `UsoMaterialOrden`; las líneas que pasan a 0 se conservan con 0; no se borran.
   - Auditar orden y cada cambio de uso.
4. Si la clave ya existe por concurrencia, recargar la orden y actualizarla sin duplicar.
5. Devolver la orden.

### `historial_orden(tenant, orden_id) -> QuerySet[RegistroCambio]`

- Filtra por tenant, entidad `OrdenLiquidacion`/`UsoMaterialOrden` y sus IDs.
- Ordena por fecha descendente.

## Saldos

### `registrar_saldo_inicial(tenant, material, periodo, cantidad, actor) -> SaldoInicialPeriodo`

- Valida material habilitado/activo, periodo y cantidad.
- Crea o actualiza el saldo manual; audita alta y cambio.

### `saldo_inicial_efectivo(tenant, material, periodo) -> int`

- Manual si existe.
- Si no, saldo final del periodo anterior; si no hay datos anteriores, 0.
- Itera desde el periodo más antiguo con datos; cachea por request.

### `saldo_final(tenant, material, periodo) -> int`

- `inicial + despachos - usado`.
- Puede ser negativo; no lanza excepción.

## Despachos

### `registrar_despacho(tenant, recojo, recojo_linea, material, fecha, cantidad, actor) -> DespachoAlmacen`

- Valida cuenta, tenant del recojo/línea, material de la línea, fecha y cantidad.
- `transaction.atomic`: bloquea `Tenant` y `LineaRecojo`, suma despachos existentes (excluyendo el
  editado) y verifica que no superen `recojo_linea.cantidad`.
- Crea el despacho; audita `DespachoAlmacen/alta`.

### `actualizar_despacho(despacho, fecha, cantidad, actor) -> DespachoAlmacen`

- Valida pertenencia, fecha y cantidad.
- Recalcula la suma de la línea excluyendo el despacho; actualiza fecha/cantidad y audita.

### `despachos_del_periodo(tenant, periodo)` y `recojos_del_tenant(tenant, q="")`

- Consultas de solo lectura para entradas y selectores.

## Reporte

### `reporte_mensual(tenant, periodo) -> ReporteMensual`

- Materiales: habilitados activos más los que tengan saldo, despacho o uso en el periodo.
- Por material: `saldo_inicial`, `despachos`, `usado`, `saldo_final`.
- Detalle por técnico: NIF y cantidad usada por material.
- `saldo_final < 0` marca `alerta=True`.
- Agregaciones y `select_related`; sin N+1.

```python
@dataclass(frozen=True)
class FilaMaterial:
    material_id: int
    codigo: str
    descripcion: str
    saldo_inicial: int
    despachos: int
    usado: int
    saldo_final: int
    alerta: bool

@dataclass(frozen=True)
class ReporteMensual:
    periodo: str
    filas: list[FilaMaterial]
    detalle_tecnicos: list[DetalleTecnico]
```

## Reglas transversales

- Toda escritura ocurre en una transacción y audita en la misma transacción.
- Nunca se acepta `tenant` del cliente.
- 013 no lee ni escribe stock, series ni conciliaciones.
- No se borran órdenes, usos, saldos ni despachos.
- No se usan permisos Django por cadena.

## Pruebas de contrato

- Cada firma, retorno y excepción coincide con este documento.
- Una orden existente se devuelve para editar; no se duplica.
- Un uso con 0 se conserva y no suma.
- Un despacho no supera la línea de recojo.
- El saldo final es la fórmula documentada y la herencia funciona.
- Ningún servicio modifica stock ni expone datos de otro tenant.
