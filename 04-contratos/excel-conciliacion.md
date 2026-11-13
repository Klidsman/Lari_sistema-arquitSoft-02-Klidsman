# Excel de Conciliación (Reporte de Lari)

Formato y estructura del archivo de reporte de Lari para conciliación de stock.

## 1. Propósito

El reporte de Lari es el documento que la contrata principal envía diariamente para conciliar el stock de materiales de una región. El reporte contiene datos de todos los tenants de la región. Cuando un tenant carga este reporte en el sistema, este filtra solo los técnicos registrados en ese tenant para comparar el stock registrado con lo que Lari reporta, detectar diferencias y, tras aprobación, ajustar el stock según el reporte.

## 2. Formato del Archivo

### 2.1 Nombre del Archivo
- Formato: `STOCK CONTRASTAS [REGIÓN] [FECHA].xlsx`; solo se acepta `.xlsx`
- Ejemplo: `STOCK CONTRASTAS AYACUCHO 20-10-2026.xlsx`

### 2.2 Estructura del Excel
- El Excel contiene múltiples hojas
- El sistema **solo lee la hoja llamada "GENERAL"**
- Las otras hojas tienen nombres de tenants y se ignoran

## 3. Columnas de la Hoja GENERAL

La hoja GENERAL contiene las siguientes columnas:

| Columna | Descripción | ¿Se lee? |
|---|---|---|
| Cliente | Cliente | No |
| Material | Código del material | **Sí** |
| Centro | Centro | No |
| Lote | Lote del material | **Sí** |
| Libre utilización | Stock de material (cantidad) | **Sí** |
| Almacén | Almacén | No |
| Número de serie | Serie del material (si aplica) | **Sí** |
| Nº ident.fis.1 | Identificador del técnico (LAXXXX) | **Sí** |
| Unidad medida base | Unidad de medida | No |
| Texto breve material | Descripción del material | **Sí** |
| Nombre | Nombre | No |
| Denominación-almacén | Denominación del almacén | No |
| Cantitad Regularizada | Cantidad regularizada | No |
| CONTRATA | Contrata | No |

## 4. Columnas Leídas por el Sistema

El sistema solo lee las siguientes columnas para la conciliación:

| Columna del Excel | Campo en el sistema | Descripción |
|---|---|---|
| Material | Código de material | Código que identifica el material en el catálogo |
| Lote | Lote | Lote del material |
| Libre utilización | Cantidad | Stock de material (para no seriados) |
| Número de serie | Serie | Serie individual (para seriados) |
| Nº ident.fis.1 | NIF del técnico | Identificador del técnico (formato LAXXXX) |
| Texto breve material | Descripción | Descripción del material |

## 5. Interpretación de los Datos

### 5.1 Materiales Seriados
- Se identifican porque tienen valor en la columna "Número de serie"
- Cada fila con serie representa una unidad individual
- La columna "Libre utilización" se ignora para seriados
- El sistema valida que la serie tenga el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)

### 5.2 Materiales No Seriados
- Se identifican porque no tienen valor en la columna "Número de serie"
- La columna "Libre utilización" indica la cantidad de stock según el reporte de Lari
- **El sistema toma directamente la cantidad del reporte Excel (columna "Libre utilización")**
- **No se calcula consumo ni se realizan operaciones matemáticas**
- **Al aprobar la conciliación, el stock del técnico se actualiza exactamente a la cantidad que aparece en "Libre utilización"**

### 5.3 Identificación del Técnico
- La columna "Nº ident.fis.1" contiene el identificador del técnico (formato LAXXXX)
- Este valor se usa para asociar cada fila con el técnico correspondiente
- **El reporte de Lari contiene técnicos de todos los tenants de la región**
- **El sistema solo procesa las filas donde el técnico (Nº ident.fis.1) está registrado en el tenant que carga el reporte**
- **Las filas con técnicos de otros tenants se ignoran silenciosamente** (no causan error)
- Si el técnico es desconocido o pertenece a otra región, se rechaza el archivo completo

## 6. Validaciones del Reporte

El sistema valida que:
- El archivo sea un Excel válido `.xlsx` (no `.xls`)
- Exista la hoja llamada "GENERAL"
- La hoja GENERAL tenga las columnas requeridas (Material, Lote, Libre utilización, Número de serie, Nº ident.fis.1, Texto breve material)
- Los códigos de material existan en el catálogo
- Las series (cuando están presentes) tengan el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- Los NIF tengan el formato correcto (LAXXXX)
- Las cantidades en "Libre utilización" sean números válidos

**Nota sobre técnicos:**
- El reporte de Lari contiene técnicos de todos los tenants de la región
- El sistema filtra y solo procesa las filas donde el técnico está registrado en el tenant que carga el reporte
- Las filas con técnicos de otros tenants de la misma región se ignoran silenciosamente (no causan
  error ni rechazo del archivo)
- Las filas con técnicos desconocidos o de otra región rechazan el archivo completo

## 7. Proceso de Carga

1. El tenant carga el archivo Excel `.xlsx`
2. El sistema lee únicamente la hoja llamada "GENERAL"
3. El sistema extrae las columnas: Material, Lote, Libre utilización, Número de serie, Nº ident.fis.1, Texto breve material
4. El sistema crea una conciliación en estado "En revisión"
5. El sistema compara el stock del tenant con el reporte de Lari
6. El sistema muestra las diferencias en dos grupos:
   - "En reporte, no en sistema": series/materiales que el reporte indica pero el sistema no tiene
   - "En sistema, no en reporte": series/materiales que el sistema tiene pero el reporte no indica
7. Solo puede haber una conciliación en revisión por tenant a la vez
8. Cargar el reporte **no modifica el stock** automáticamente

## 8. Comparación y Diferencias

### 8.1 Para Materiales Seriados
- El sistema compara cada serie individual por técnico
- Lista cada serie que está en el reporte (columna "Número de serie") pero no en el sistema
- Lista cada serie que está en el sistema pero no en el reporte
- Agrupa por técnico (columna "Nº ident.fis.1")

### 8.2 Para Materiales No Seriados
- El sistema compara las cantidades por técnico y material
- Compara el stock del sistema con la columna "Libre utilización" del reporte
- **Al aprobar la conciliación, el stock del técnico se actualiza exactamente al valor de "Libre utilización" del reporte**

## 9. Aprobación de la Conciliación

### 9.1 Regla de Prevalencia
- En una conciliación aprobada, el reporte de Lari prevalece sobre el stock del sistema
- El stock del sistema se ajusta para coincidir con el reporte

### 9.2 Ajustes al Aprobar
- Para seriados: las series del reporte (columna "Número de serie") que no existen en el sistema se crean en el técnico; las que el sistema tiene y el reporte no traen se retiran o se marcan como instaladas
- Para no seriados: el stock del técnico se actualiza a la cantidad reportada en la columna "Libre utilización"
- Cada ajuste registra valor anterior y valor nuevo

### 9.3 Liquidación de Seriados
- Las series ya no reportadas se actualizan a estado instalado automáticamente
- Esto refleja la liquidación del equipo

### 9.4 Regla de Todo o Nada
- El tenant aprueba o rechaza la conciliación completa
- No se pueden aprobar parcialmente algunos ajustes
- Si hay materiales del reporte que no existen en el catálogo, la aprobación se bloquea

### 9.5 Recálculo si Hubo Cambios
- Si el stock de un técnico cambió entre la carga y la aprobación, el sistema recalcula las diferencias
- El tenant debe revisar de nuevo antes de aprobar

## 10. Rechazo de la Conciliación

- El tenant puede rechazar la conciliación completa
- Al rechazar, no se modifica ningún stock
- El tenant puede cargar un nuevo reporte para iniciar una nueva conciliación

## 11. Auditoría

- El sistema registra quién cargó el reporte, cuándo y qué archivo exacto
- El sistema registra el nombre del archivo original (ej: "STOCK CONTRASTAS AYACUCHO 20-10-2026.xlsx")
- Todo ajuste derivado de la conciliación registra usuario, fecha, valor anterior y valor nuevo
