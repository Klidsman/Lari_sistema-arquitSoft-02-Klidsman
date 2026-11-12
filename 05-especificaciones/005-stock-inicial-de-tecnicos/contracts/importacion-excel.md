# Contrato de importación Excel: 005 Stock Inicial de Técnicos

**Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/005-stock-inicial-de-tecnicos/spec.md`

Este contrato define el archivo Excel aceptado por la carga de stock inicial. Corrige y concreta
`04-contratos/excel-stock-inicial.md`: solo se acepta `.xlsx`, y lote y descripción se toman del
catálogo de materiales.

## 1. Formato del archivo

| Aspecto | Regla |
|---|---|
| Extensión | `.xlsx` únicamente. `.xls`, `.xlsm`, `.csv` y otros se rechazan con "El archivo debe ser un Excel .xlsx". |
| Contenido | Un libro Excel con al menos una hoja. Se lee la primera hoja. |
| Cabecera | Primera fila; debe contener las seis columnas obligatorias. |
| Filas | Una o más filas de datos; las filas completamente vacías se ignoran. |
| Tamaño | No se impone un límite distinto del que permita el servidor; si se agrega, se documenta aquí y en la spec. |
| Codificación | La del propio `.xlsx`; `openpyxl` la resuelve. |
| Fórmulas | Se leen con `data_only=True`; se usa el valor calculado si existe. |

**Nota para el usuario**: un archivo `.xls` debe abrirse en Excel/LibreOffice y guardarse como
`.xlsx` antes de cargarlo. El sistema no convierte formatos.

## 2. Columnas obligatorias

| Columna | Descripción | Se usa para |
|---|---|---|
| `Material` | Código del material | Buscar `materiales.Material.codigo`. |
| `Lote` | Lote del material | Solo se lee; **no prevalece**. El lote guardado es `material.lote`. |
| `Libre utilización` | Cantidad para materiales no seriados | Cantidad; se ignora si hay serie. |
| `Número de serie` | Serie individual | Identifica una unidad seriada. |
| `Nº ident.fis.1` | NIF del técnico (LAXXXX) | Buscar el técnico en el tenant. |
| `Texto breve material` | Descripción del material | Solo se lee; **no prevalece**. La descripción es `material.descripcion`. |

- La comparación de cabeceras ignora espacios al inicio/final y mayúsculas/minúsculas, pero el
  archivo debe traer los nombres anteriores. Si falta una, el error es
  "El archivo no tiene la columna obligatoria: {columna}".
- Las columnas adicionales se ignoran.
- No se aceptan columnas de `tenant`, `region`, `almacen`, `creado_por`, `id` ni similares.

## 3. Interpretación de filas

### 3.1 Material seriado

- Se reconoce por `material.es_seriado=True`.
- Debe tener `Número de serie` no vacío; si no,
  "El material es seriado y requiere número de serie".
- Cada fila con serie genera una línea con `cantidad=1`.
- `Libre utilización` se ignora, aunque traiga un valor.
- La serie se normaliza (sin espacios, mayúsculas) y se valida con el patrón configurable
  (`^[A-Z0-9]{12}$` por defecto).
- La serie se crea en `series.Serie` con estado `ASIGNADA`, tenant y región de la sesión, material y
  lote del catálogo.

### 3.2 Material no seriado

- Se reconoce por `material.es_seriado=False`.
- No debe tener `Número de serie`; si lo tiene,
  "El material no es seriado y no admite número de serie".
- `Libre utilización` debe ser un entero mayor a 0; si no, "La cantidad debe ser mayor a 0" o
  "La cantidad de la fila {n} no es un número válido".
- Varias filas del mismo técnico y material se suman en una sola línea.
- La línea se crea con `serie=NULL`, `cantidad` sumada y `lote=material.lote`.

### 3.3 Técnico

- `Nº ident.fis.1` se normaliza (sin espacios, mayúsculas) y se valida con `^LA[0-9]{4}$`; si no,
  "El NIF debe tener el formato LAXXXX".
- Debe existir en el tenant de la sesión; si no, "El técnico no existe en este tenant".
- Se aceptan técnicos activos o desactivados que existan en el tenant, para no perder stock
  histórico. El formulario, en cambio, solo ofrece activos.
- No se busca en otros tenants.

### 3.4 Material

- `Material` se normaliza con `strip()`.
- Debe existir en el catálogo global; si no, "El material no existe en el catálogo".
- El tipo (`es_seriado`) y el lote se toman del catálogo.
- El `Lote` y `Texto breve material` del Excel son informativos; si difieren del catálogo, no
  generan error y no cambian el dato guardado.

## 4. Series

- Formato: 12 caracteres alfanuméricos A-Z y 0-9; la longitud y el patrón salen de
  `settings.SERIE_LONGITUD` y `settings.SERIE_PATRON` (004), con el valor vigente como respaldo.
- Normalización: eliminar espacios en blanco y pasar a mayúsculas.
- Duplicado dentro del archivo: la segunda y posteriores se marcan con
  "La serie está duplicada en la carga".
- Serie ya existente en el sistema: "La serie ya está registrada en el sistema", sin revelar el
  tenant, la región, el recojo ni el técnico de origen.
- La validación de existencia se hace en una sola consulta con `series_existentes`.
- La carga revalida y la base impone `unique(numero)`; si la carrera la gana otra sesión, el mensaje
  es el mismo.

## 5. Agregación de filas

| Caso | Resultado |
|---|---|
| Varias filas no seriadas del mismo `(técnico, material)` | Una línea con la suma de `Libre utilización`. |
| Varias filas seriadas del mismo material y técnico, con series distintas | Una línea por serie, `cantidad=1`. |
| Dos filas con la misma serie | Error de duplicado; no se carga nada. |
| Fila vacía | Se ignora. |
| Fila con material/técnico inválido | Error; no se carga nada. |

Ejemplo:

```text
Fila 2: Material=12345678901, Libre utilización=10, Nº ident.fis.1=LA0001, Número de serie=(vacío)
Fila 3: Material=12345678901, Libre utilización=5,  Nº ident.fis.1=LA0001, Número de serie=(vacío)
```

Resultado: una línea `(LA0001, 12345678901, cantidad=15, serie=NULL)`.

## 6. Validaciones y mensajes

| Validación | Mensaje | Se detiene |
|---|---|---|
| Extensión no `.xlsx` | "El archivo debe ser un Excel .xlsx" | Sí |
| Archivo corrupto o ilegible | "El archivo no se pudo leer como Excel" | Sí |
| Columna faltante | "El archivo no tiene la columna obligatoria: {columna}" | Sí |
| Sin filas de datos | "El archivo no contiene filas de datos" | Sí |
| NIF inválido | "El NIF debe tener el formato LAXXXX" | Sí |
| Técnico inexistente | "El técnico no existe en este tenant" | Sí |
| Material inexistente | "El material no existe en el catálogo" | Sí |
| Seriado sin serie | "El material es seriado y requiere número de serie" | Sí |
| No seriado con serie | "El material no es seriado y no admite número de serie" | Sí |
| Serie con formato inválido | "La serie debe tener 12 caracteres alfanuméricos" | Sí |
| Serie duplicada en el archivo | "La serie está duplicada en la carga" | Sí |
| Serie existente | "La serie ya está registrada en el sistema" | Sí |
| Cantidad no numérica | "La cantidad de la fila {n} no es un número válido" | Sí |
| Cantidad `<= 0` | "La cantidad debe ser mayor a 0" | Sí |

- "Se detiene" significa que no se aplica la carga completa; la vista previa muestra todos los
  errores encontrados para que el usuario corrija el archivo y reintente.
- Los errores de fila incluyen el número de fila del Excel (empezando en 2, porque la fila 1 es la
  cabecera) y el campo.
- El mensaje nunca incluye datos del tenant de una serie ajena.

## 7. Flujo de carga

1. El usuario entra a `/stock-inicial/` o `/stock-inicial/formulario/`.
2. Si el tenant ya cargó, el sistema muestra el resumen y bloquea una nueva carga (`409`).
3. En Excel, el usuario sube el archivo a `/stock-inicial/validar-excel/`; el sistema devuelve un
   fragmento con errores y resumen, sin escribir.
4. Si el archivo es válido, el usuario envía el mismo archivo a `/stock-inicial/cargar-excel/`.
5. El sistema revalida, abre una transacción, crea la carga, las líneas, las series y el stock, marca
   el tenant y audita.
6. Si cualquier fila falla, se revierte todo y se muestra el error.
7. Si todo es válido, redirige al detalle.

## 8. Datos que se guardan

| Dato | Origen |
|---|---|
| `CargaStockInicial.metodo` | `EXCEL`. |
| `CargaStockInicial.archivo_nombre` | Nombre base del archivo. |
| `CargaStockInicial.archivo_hash` | SHA-256 de los bytes originales. |
| `CargaStockInicial.region` | `tenant.region` de la sesión. |
| `LineaStockInicial.tecnico` | Técnico resuelto por NIF en el tenant. |
| `LineaStockInicial.material` | Material resuelto por código en el catálogo. |
| `LineaStockInicial.lote` | `material.lote`, no el del Excel. |
| `LineaStockInicial.serie` | `series.Serie` creada en `ASIGNADA` o `NULL`. |
| `LineaStockInicial.cantidad` | Suma de no seriados o `1` para seriados. |
| `StockTecnico.cantidad` | Incremento por los servicios de 008. |
| `Tenant.stock_inicial_cargado` | `True`. |
| `Tenant.fecha_stock_inicial` | `timezone.now()`. |

## 9. Lo que el archivo no puede hacer

- No puede crear tenants, regiones, técnicos, materiales ni usuarios.
- No puede cambiar el tipo de un material ni su lote.
- No puede cargar stock para otro tenant.
- No puede saltarse la validación de series ni la carga única.
- No puede modificar `StockGeneral`.
- No puede dejar una carga parcial.
- No puede eliminar ni reemplazar una carga existente; la corrección es por edición.

## 10. Relación con otros contratos

- `04-contratos/excel-stock-inicial.md`: fuente original del formato. Debe corregirse para reflejar
  `.xlsx` únicamente y el lote/descripción del catálogo.
- `contracts/validacion-excel.md`: fragmento HTML/HTMX de la vista previa.
- `contracts/http-endpoints.md`: rutas, permisos y estados.
- `contracts/auditoria-stock-inicial.md`: eventos y valores auditados.
