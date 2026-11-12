# Contrato de validación previa de Excel: 005 Stock Inicial de Técnicos

**Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/005-stock-inicial-de-tecnicos/spec.md`

Este contrato define la respuesta de `POST /stock-inicial/validar-excel/`. La validación previa es
un fragmento HTML/HTMX, no escribe en la base y no es autoridad: la carga revalida todo.

## 1. Principios

- **Sin escrituras**: no crea `CargaStockInicial`, `LineaStockInicial`, `Serie`, `StockTecnico` ni
  `RegistroCambio`.
- **Sin estado en servidor**: no guarda el archivo ni el resultado en sesión. La carga recibe de
  nuevo el archivo.
- **HTML/HTMX**: no JSON, no JavaScript obligatorio.
- **Aislamiento**: el fragmento no incluye `tenant_id`, `region_id`, stock, creador ni datos de otro
  tenant.
- **Tolerante**: muestra todos los errores encontrados para que el usuario corrija el archivo de una
  vez.

## 2. Petición

```http
POST /stock-inicial/validar-excel/
Content-Type: multipart/form-data

archivo=<archivo.xlsx>
```

- `archivo` es obligatorio.
- No se aceptan `tenant_id`, `region_id`, `carga_id` ni `material_id`.
- CSRF obligatorio.

## 3. Respuesta `200` (archivo procesado)

El cuerpo es un fragmento HTML con esta estructura lógica:

```html
<section
  data-valido="true|false"
  data-filas-validas="3"
  data-filas-error="1"
  data-total-tecnicos="2"
  data-total-series="4"
  data-total-cantidad="25"
>
  <p class="resumen">...</p>

  <table class="errores">
    <tbody>
      <tr data-fila="4" data-campo="tecnico" data-mensaje="El técnico no existe en este tenant">
        <td>4</td>
        <td>Técnico</td>
        <td>El técnico no existe en este tenant</td>
      </tr>
    </tbody>
  </table>

  <table class="lineas-validas">
    <tbody>
      <tr data-tecnico="LA0001" data-material="12345678901">
        <td>LA0001</td>
        <td>12345678901</td>
        <td>Descripción del catálogo</td>
        <td>Lote del catálogo</td>
        <td>ABC123456789</td>
        <td>1</td>
      </tr>
    </tbody>
  </table>
</section>
```

### Atributos del contenedor

| Atributo | Tipo | Significado |
|---|---|---|
| `data-valido` | `"true"`/`"false"` | `true` solo si no hay errores. |
| `data-filas-validas` | entero | Filas del Excel que produjeron una línea válida (antes de agrupar). |
| `data-filas-error` | entero | Filas con al menos un error. |
| `data-total-tecnicos` | entero | Técnicos distintos en las líneas válidas. |
| `data-total-series` | entero | Series válidas. |
| `data-total-cantidad` | entero | Suma de cantidades no seriadas. |

### Filas de error

Cada fila de error tiene:

| Atributo | Significado |
|---|---|
| `data-fila` | Número de fila del Excel (2 o mayor; la 1 es la cabecera). |
| `data-campo` | `tecnico`, `material`, `serie`, `cantidad`, `tipo` o `archivo`. |
| `data-mensaje` | Mensaje exacto de la tabla del §5. |

- Una fila puede generar más de un error; se muestran todos.
- Los errores de archivo (extensión, columna, sin filas) usan `data-fila="0"` y `data-campo="archivo"`.
- El texto visible es el mismo `data-mensaje`, sin HTML ni datos internos.

### Líneas válidas

Cada fila de línea válida muestra:

- NIF del técnico;
- código del material;
- descripción del catálogo (no la del Excel);
- lote del catálogo (no el del Excel);
- serie (si aplica) o cantidad (si no aplica);
- no muestra stock, tenant, región ni creador.

Las líneas no seriadas ya agrupadas se muestran una sola vez con la cantidad sumada. Para
trazabilidad de la vista previa, la fila puede incluir `data-filas-origen="2,3"`, pero no es
obligatorio.

### Resumen

El resumen muestra, como mínimo:

- “El archivo es válido y se puede cargar” o “El archivo tiene N errores; corrige y vuelve a
  intentar”;
- número de técnicos, líneas, series y cantidad;
- recordatorio de que la carga es única y definitiva hasta una edición.

## 4. Respuesta `400` (archivo no procesable)

Se devuelve un fragmento con `data-valido="false"` y un error de archivo cuando:

| Caso | Mensaje |
|---|---|
| No se envió archivo | "Debes seleccionar un archivo Excel" |
| Extensión distinta de `.xlsx` | "El archivo debe ser un Excel .xlsx" |
| Falta una columna obligatoria | "El archivo no tiene la columna obligatoria: {columna}" |
| No hay filas de datos | "El archivo no contiene filas de datos" |
| Archivo corrupto o ilegible | "El archivo no se pudo leer como Excel" |

No se devuelve una traza ni el detalle interno de `openpyxl`.

## 5. Mensajes por fila

| Campo | Mensaje |
|---|---|
| `tecnico` | "El NIF debe tener el formato LAXXXX" |
| `tecnico` | "El técnico no existe en este tenant" |
| `material` | "El material no existe en el catálogo" |
| `tipo` | "El material es seriado y requiere número de serie" |
| `tipo` | "El material no es seriado y no admite número de serie" |
| `serie` | "La serie debe tener 12 caracteres alfanuméricos" |
| `serie` | "La serie está duplicada en la carga" |
| `serie` | "La serie ya está registrada en el sistema" |
| `cantidad` | "La cantidad de la fila {n} no es un número válido" |
| `cantidad` | "La cantidad debe ser mayor a 0" |

## 6. Comportamiento HTMX

Ejemplo de uso en la plantilla:

```html
<form
  hx-post="/stock-inicial/validar-excel/"
  hx-target="#resultado-validacion"
  hx-swap="innerHTML"
  hx-encoding="multipart/form-data"
  hx-indicator="#indicador-validacion"
  hx-disabled-elt="find button[type='submit']"
>
  {% csrf_token %}
  <input type="file" name="archivo" accept=".xlsx" required>
  <button type="submit">Validar Excel</button>
</form>

<div id="resultado-validacion"></div>
<div id="indicador-validacion" class="htmx-indicator">Validando…</div>
```

- El botón "Cargar" del formulario de carga solo se habilita cuando `data-valido="true"`.
- Si el usuario modifica el archivo, debe volver a validar.
- La validación previa no bloquea la carga: el servidor revalida y puede rechazarla si el estado
  cambió.

## 7. Seguridad

- El fragmento no refleja el nombre del archivo sin escapar; se usa el escape de plantillas.
- No se muestran rutas del servidor, trazas, `tenant_id`, `region_id`, stock ni creador.
- Los valores de celda se escapan; no se interpretan como HTML.
- El archivo se procesa en memoria y no se guarda en disco.
- El hash se calcula, pero la vista previa no lo muestra necesariamente; la carga lo guarda en
  `CargaStockInicial.archivo_hash`.

## 8. Pruebas de contrato

- `200` con `data-valido="true"` para un archivo válido.
- `200` con `data-valido="false"` y una fila de error por cada problema.
- `data-fila` correcto (2 para la primera fila de datos).
- `data-campo` correcto.
- `data-mensaje` exacto.
- `400` para archivo ausente, `.xls`, columna faltante, sin filas y corrupto.
- `403` para Admin, Almacén y tenant suspendido.
- `405` para `GET`, `PUT`, `DELETE`.
- Sin escrituras: los conteos de las tablas no cambian.
- El fragmento no contiene `tenant_id`, `region_id`, stock, creador ni datos de otro tenant.
