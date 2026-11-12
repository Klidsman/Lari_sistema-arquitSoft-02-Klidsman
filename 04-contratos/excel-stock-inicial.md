# Excel de Stock Inicial de Técnicos

Formato y estructura del archivo para la carga del stock inicial de técnicos.

## 1. Propósito

El stock inicial de técnicos se carga una sola vez el día de implementación del sistema. Este Excel contiene el stock que cada técnico tenía antes de empezar a usar el sistema, para que puedan continuar trabajando con sus materiales existentes.

## 2. Formato del Archivo

- **Formato:** Excel (.xlsx). El formato binario `.xls` no se acepta: debe abrirse y guardarse como `.xlsx` antes de cargarlo.
- **Uso:** Solo se puede cargar una vez por tenant
- **Momento:** Día de implementación del sistema

## 3. Estructura del Excel

El Excel debe tener las siguientes columnas:

| Columna | Descripción | ¿Se lee? |
|---|---|---|
| Material | Código del material | **Sí** |
| Lote | Lote del material | **Informativo**; prevalece el lote del catálogo |
| Libre utilización | Stock de material (cantidad) | **Sí** |
| Número de serie | Serie del material (si aplica) | **Sí** |
| Nº ident.fis.1 | Identificador del técnico (LAXXXX) | **Sí** |
| Texto breve material | Descripción del material | **Informativo**; prevalece la descripción del catálogo |

**Nota:** El formato es idéntico al reporte de Lari para facilitar la migración.

## 4. Columnas Leídas por el Sistema

| Columna del Excel | Campo en el sistema | Descripción |
|---|---|---|
| Material | Código de material | Código que identifica el material en el catálogo |
| Lote | Lote (catálogo) | Se lee del archivo, pero el valor guardado es `material.lote` |
| Libre utilización | Cantidad | Stock de material (para no seriados) |
| Número de serie | Serie | Serie individual (para seriados) |
| Nº ident.fis.1 | NIF del técnico | Identificador del técnico (formato LAXXXX) |
| Texto breve material | Descripción (catálogo) | Se lee del archivo, pero prevalece `material.descripcion` |

**Nota:** el lote y la descripción del catálogo son la fuente de verdad. Los valores del Excel son
informativos y no generan error si difieren; el lote no separa stock.

## 5. Interpretación de los Datos

### 5.1 Materiales Seriados
- Se identifican porque tienen valor en la columna "Número de serie"
- Cada fila con serie representa una unidad individual
- La columna "Libre utilización" se ignora para seriados
- El sistema valida que la serie tenga el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- La serie se asigna al técnico indicado en "Nº ident.fis.1"
- El lote guardado es el del catálogo, no el de la columna "Lote"

### 5.2 Materiales No Seriados
- Se identifican porque no tienen valor en la columna "Número de serie"
- La columna "Libre utilización" indica la cantidad de stock
- El sistema asigna esa cantidad al técnico indicado en "Nº ident.fis.1"
- Varias filas del mismo técnico y material se suman en una sola línea

### 5.3 Identificación del Técnico
- La columna "Nº ident.fis.1" contiene el identificador del técnico (formato LAXXXX)
- Este valor se usa para asociar cada fila con el técnico correspondiente
- El técnico debe existir previamente en el tenant
- Si el técnico no existe, se registra como error

## 6. Validaciones del Excel

El sistema valida que:
- El archivo sea un Excel válido (`.xlsx`; los `.xls` deben guardarse como `.xlsx`)
- El archivo tenga las columnas requeridas (Material, Lote, Libre utilización, Número de serie, Nº ident.fis.1, Texto breve material)
- Los códigos de material existan en el catálogo
- Las series (cuando están presentes) tengan el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- Los NIF tengan el formato correcto (LAXXXX)
- Las cantidades en "Libre utilización" sean números válidos
- Todos los técnicos del Excel existan en el tenant
- Las series no estén duplicadas en el Excel
- Las series no existan ya en el sistema

## 7. Proceso de Carga

1. El tenant carga el archivo Excel (`.xlsx`; si está en `.xls`, lo guarda como `.xlsx`)
2. El sistema valida el formato y las columnas
3. El sistema valida cada fila (técnico, material, serie, cantidad)
4. Si hay errores, se muestran al usuario y no se carga nada
5. Si todo es válido, el sistema carga el stock inicial:
   - Para seriados: crea la serie y la asigna al técnico
   - Para no seriados: asigna la cantidad al técnico
6. La carga es transaccional: si falla una fila, falla todo
7. Una vez cargado, no se puede volver a cargar stock inicial para ese tenant

## 8. Regla de Carga y Edición

- El stock inicial se carga **una sola vez** por tenant
- Después de la carga exitosa, el sistema marca el tenant como "stock inicial cargado"
- No se permite cargar stock inicial nuevamente (se usa edición para ajustes)
- Cualquier ajuste posterior debe hacerse a través de **editar el stock inicial**, recojos, asignaciones o traspasos
- La edición del stock inicial permite corregir errores en la carga original
- La edición registra auditoría completa de los cambios

## 9. Alternativa: Formulario

Además del Excel, el sistema permite cargar el stock inicial por formulario:
- El formulario tiene secciones por técnico: el usuario selecciona el técnico de la lista y agrega sus materiales, series o cantidades
- Varias secciones se guardan como una sola carga, para respetar la carga única por tenant
- Similar al formulario de recojo, pero asigna directamente al técnico
- Ambas opciones (Excel y formulario) cargan el mismo tipo de datos

## 10. Auditoría

- El sistema registra quién cargó el stock inicial, cuándo y qué archivo exacto
- Se registra el nombre del archivo original
- Cada serie y cantidad creada registra usuario, fecha y valor anterior (ninguno) y nuevo
