# Contrato de auditoría: 005 Stock Inicial de Técnicos

**Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/005-stock-inicial-de-tecnicos/spec.md`

Este contrato define qué se audita en la carga, la edición y el reinicio del stock inicial, con qué
valores y en qué transacción. Se reutiliza `auditoria.RegistroCambio` de la spec 001, de solo
inserción.

## 1. Reglas generales

- Todo cambio se audita en la **misma transacción** que el cambio. Si la operación falla, no se
  escribe ninguna auditoría.
- `RegistroCambio` es de solo inserción: no se actualiza ni se borra.
- Se registran `entidad`, `entidad_id`, `campo`, `valor_anterior`, `valor_nuevo`, `usuario` y
  `fecha`.
- Nunca se auditan contraseñas, tokens, `token_hash`, secretos TOTP ni datos sensibles.
- No se guarda `tenant_id` como campo separado; el tenant se deduce del usuario y de la entidad.
- Los valores se serializan como texto legible; los importes y cantidades se guardan como enteros.
- La auditoría no revela datos de otros tenants. Un mensaje o valor de auditoría de una serie
  existente no incluye el tenant propietario.
- La auditoría sobrevive a la desactivación de la cuenta, la suspensión del tenant y el borrado
  físico de una serie o línea.
- La auditoría de stock (`StockTecnico/cantidad`) la escribe la spec 008; 005 no la duplica.

## 2. Carga inicial

### 2.1 Resumen de la carga

| Campo | Valor |
|---|---|
| `entidad` | `CargaStockInicial` |
| `entidad_id` | `carga.id` |
| `campo` | `alta` |
| `valor_anterior` | vacío |
| `valor_nuevo` | texto con `metodo`, `archivo_nombre`, `archivo_hash`, `region`, `total_tecnicos`, `total_lineas`, `total_series`, `total_cantidad` |

Ejemplo de `valor_nuevo`:

```text
metodo=EXCEL; archivo=stock_inicial_2026_11.xlsx; hash=9f2c...; region=REG-01;
tecnicos=3; lineas=42; series=17; cantidad=250
```

- Para el formulario, `archivo` y `hash` quedan vacíos.
- El hash es SHA-256 hexadecimal de 64 caracteres.

### 2.2 Alta de línea

| Campo | Valor |
|---|---|
| `entidad` | `LineaStockInicial` |
| `entidad_id` | `linea.id` |
| `campo` | `alta` |
| `valor_anterior` | vacío |
| `valor_nuevo` | `tecnico=<NIF>; material=<codigo>; lote=<lote>; serie=<numero>` o `cantidad=<n>` |

- Para seriados: `serie=<numero>; cantidad=1`.
- Para no seriados: `serie=; cantidad=<n>`.
- El lote es el del catálogo.

### 2.3 Alta de serie

| Campo | Valor |
|---|---|
| `entidad` | `Serie` |
| `entidad_id` | `serie.id` |
| `campo` | `alta` |
| `valor_anterior` | vacío |
| `valor_nuevo` | `numero=<numero>; tenant=<tenant.codigo>; region=<region.codigo>; material=<codigo>; estado=ASIGNADA` |

- Se escribe una por cada serie creada.
- La serie tiene además `creado_por` y `creado_en` en `series.Serie`.

### 2.4 Cambios en el tenant

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Marca de carga | `Tenant` | `stock_inicial_cargado` | `False` | `True` |
| Fecha de carga | `Tenant` | `fecha_stock_inicial` | vacío | fecha ISO 8601 |

- Se actualizan `actualizado_por` y `actualizado_en` del tenant.
- La fecha se registra en UTC y se muestra en la zona local cuando corresponda.

### 2.5 Stock

- El incremento de `StockTecnico` lo audita 008 con `entidad="StockTecnico"`, `campo="cantidad"`,
  valor anterior y nuevo.
- 005 agrupa por `(tecnico, material)` y llama una sola vez por grupo; por eso hay un registro de
  stock por técnico y material, no por serie.
- La serie tiene su propio `Serie/alta`; el stock agregado no oculta la trazabilidad individual.

## 3. Edición

### 3.1 Agregar línea

| Tipo | Evento |
|---|---|
| Seriada | `Serie/alta` + `LineaStockInicial/alta` + `StockTecnico/cantidad` (008) |
| No seriada nueva | `LineaStockInicial/alta` + `StockTecnico/cantidad` (008) |
| No seriada sobre línea existente | `LineaStockInicial/cantidad` (anterior y nueva) + `StockTecnico/cantidad` (008) |

### 3.2 Eliminar línea

| Tipo | Evento |
|---|---|
| Seriada | `LineaStockInicial/baja` + `Serie/baja` + `StockTecnico/cantidad` (008) |
| No seriada | `LineaStockInicial/baja` + `StockTecnico/cantidad` (008) |

- `LineaStockInicial/baja` guarda en `valor_anterior` el técnico, material, lote y serie o cantidad;
  `valor_nuevo` queda vacío.
- `Serie/baja` guarda en `valor_anterior` el número, estado, técnico y material; `valor_nuevo` queda
  vacío.
- Se elimina primero la línea y después la serie, por la FK `PROTECT`.
- La auditoría conserva los valores aunque la fila desaparezca.

### 3.3 Modificar cantidad

| Campo | Valor |
|---|---|
| `entidad` | `LineaStockInicial` |
| `entidad_id` | `linea.id` |
| `campo` | `cantidad` |
| `valor_anterior` | cantidad anterior |
| `valor_nuevo` | cantidad nueva |

- Solo para líneas no seriadas.
- El ajuste de `StockTecnico` lo audita 008 con la diferencia.

### 3.4 Lote de edición

- Si el lote tiene varias operaciones, cada una genera sus registros.
- Si una operación falla, se revierte todo: no queda ningún registro de auditoría del lote.
- No se audita un “lote” como entidad separada; la trazabilidad se reconstruye por los registros de
  cada línea, serie y stock.

## 4. Reinicio

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Baja de cada línea | `LineaStockInicial` | `baja` | técnico, material, lote, serie o cantidad | vacío |
| Baja de cada serie | `Serie` | `baja` | número, estado, técnico, material | vacío |
| Baja de la carga | `CargaStockInicial` | `baja` | método, archivo, hash, totales | vacío |
| Reinicio del tenant | `Tenant` | `stock_inicial_cargado` | `True` | `False` |
| Limpieza de fecha | `Tenant` | `fecha_stock_inicial` | fecha anterior | vacío |
| Stock | `StockTecnico` | `cantidad` | anterior | nueva (008) |

- El reinicio exige que las series sigan `ASIGNADA` y que el stock alcance; si no, aborta sin
  auditar.
- La auditoría del reinicio permite reconstruir qué se borró y con qué valores.
- El comando exige `PERMITIR_REINICIO_STOCK_INICIAL=True`, un actor `ADMIN_PLATAFORMA` y
  `--confirmar`.

## 5. Orden y momento

1. Se valida todo (sin escribir).
2. Se abre la transacción.
3. Se aplican los cambios de entidades y stock.
4. Se escriben los `RegistroCambio`.
5. Se confirma la transacción.
6. Si algo falla, se revierte todo, incluida la auditoría.

No se escribe auditoría “previa” ni “de intento”. Un intento fallido no deja rastro de cambio, solo
el error mostrado al usuario.

## 6. Consulta de auditoría

- La auditoría se consulta por `entidad` y `entidad_id`, o por usuario y fecha, con las herramientas
  de 001. 005 no crea un visor propio.
- Para reconstruir una carga:
  1. buscar `CargaStockInicial/alta`;
  2. buscar `LineaStockInicial/alta` del mismo período y usuario;
  3. buscar `Serie/alta` de las series creadas;
  4. buscar `StockTecnico/cantidad` del mismo período.
- Para reconstruir una edición:
  1. buscar `LineaStockInicial/alta`, `baja` o `cantidad`;
  2. buscar `Serie/alta` o `baja` correspondiente;
  3. buscar `StockTecnico/cantidad`.
- La auditoría no se borra al eliminar una serie o una línea.

## 7. Prohibiciones

- No se auditan contraseñas, tokens, `token_hash`, secretos TOTP ni claves.
- No se guarda el contenido completo del Excel; solo nombre y hash.
- No se guarda el archivo en disco desde la vista de validación.
- No se escribe un registro por fila del Excel; se escribe por línea agregada y por serie.
- No se duplica la auditoría de stock de 008.
- No se usa la auditoría para exponer datos de otro tenant.

## 8. Pruebas de contrato

- Carga exitosa: un `CargaStockInicial/alta`, un `LineaStockInicial/alta` por línea, un
  `Serie/alta` por serie, dos registros de `Tenant` y los registros de `StockTecnico`.
- Carga fallida: cero registros de carga, línea, serie, tenant y stock.
- Edición agregar: `Serie/alta`, `LineaStockInicial/alta`, `StockTecnico/cantidad`.
- Edición eliminar: `LineaStockInicial/baja`, `Serie/baja`, `StockTecnico/cantidad`; la auditoría
  sobrevive al borrado.
- Edición modificar: `LineaStockInicial/cantidad` con anterior y nuevo.
- Reinicio: bajas de línea, serie y carga; cambios de tenant; stock.
- Ningún registro contiene contraseñas, tokens ni secretos.
- La auditoría se conserva al desactivar la cuenta o suspender el tenant.
- El `valor_nuevo` de la carga contiene el hash correcto y el nombre del archivo.
- El `valor_nuevo` de una serie no revela el tenant de una serie ajena.
