# Spec 005 - Stock Inicial de Técnicos

Especificación técnica para la carga del stock inicial de técnicos.

## 1. Propósito

Permitir que los tenants carguen el stock inicial de sus técnicos el día de implementación del sistema. Este stock representa los materiales que cada técnico tenía antes de empezar a usar el sistema, para que puedan continuar trabajando sin interrupciones.

## 2. Alcance

- Carga de stock inicial por Excel (una sola vez por tenant)
- Carga de stock inicial por formulario (alternativa a Excel)
- Soporte para materiales seriados y no seriados
- Validación de técnicos, materiales y series
- Asignación directa al stock del técnico (no pasa por stock general)
- Marca de tenant como "stock inicial cargado"

## 3. Actores

- **Tenant (ACT-01)**: Carga el stock inicial de sus técnicos
- **Administrador de plataforma (ACT-02)**: Puede reiniciar el stock inicial en caso de error (solo en implementación)

## 4. Trazabilidad

### Historias de Usuario
- No hay HU específica (considerado parte de la implementación inicial)

### Requisitos Funcionales
- **RF-20**: Cargar una sola vez el stock inicial de cada técnico el día de implementación. La forma de carga (Excel o formulario) está pendiente

### Atributos de Calidad
- RF-20: Consistencia (carga única)
- RF-20: Integridad de datos (validaciones)

## 5. Requisitos Funcionales

### 5.1 Carga por Excel (RF-20)
- El sistema permite cargar el stock inicial mediante un archivo Excel
- El formato del Excel es idéntico al reporte de Lari (ver `04-contratos/excel-stock-inicial.md`)
- El Excel contiene las columnas: Material, Lote, Libre utilización, Número de serie, Nº ident.fis.1, Texto breve material
- El sistema lee solo estas columnas y las procesa

### 5.2 Carga por Formulario (RF-20)
- El sistema permite cargar el stock inicial mediante formulario
- El formulario es por técnico (uno por técnico)
- El usuario selecciona el técnico de la lista
- Ingresa materiales, series o cantidades
- Similar al formulario de recojo, pero asigna directamente al técnico
- Ambas opciones (Excel y formulario) cargan el mismo tipo de datos

### 5.3 Carga Única (RF-20)
- El stock inicial se carga una sola vez por tenant
- Después de la carga exitosa, el sistema marca el tenant como "stock inicial cargado"
- No se permite cargar stock inicial nuevamente
- Cualquier ajuste posterior debe hacerse a través de editar el stock inicial, recojos, asignaciones o traspasos

### 5.4 Edición del Stock Inicial
- El sistema permite editar el stock inicial después de la carga
- La edición se usa para corregir errores en la carga original
- Se pueden agregar series o cantidades faltantes
- Se pueden eliminar series o cantidades incorrectas
- Se pueden modificar cantidades de materiales no seriados
- La edición registra auditoría completa de los cambios
- La edición es transaccional: si falla una modificación, falla todo

### 5.5 Validación de Técnicos
- Todos los técnicos del Excel o formulario deben existir en el tenant
- Si un técnico no existe, se registra como error
- El NIF debe tener el formato correcto (LAXXXX)

### 5.6 Validación de Materiales
- Todos los materiales deben existir en el catálogo
- El código de material se valida contra el catálogo
- El lote se completa desde el catálogo

### 5.7 Validación de Series
- Las series deben tener el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- Las series no deben estar duplicadas en el Excel o formulario
- Las series no deben existir ya en el sistema

### 5.8 Validación de Cantidades
- Para materiales no seriados, la cantidad debe ser un número válido
- La cantidad debe ser mayor a 0

### 5.9 Transaccionalidad
- La carga es transaccional: si falla una fila, falla todo
- Si hay errores, no se carga nada
- El usuario debe corregir y reintentar

### 5.10 Asignación Directa al Técnico
- El stock inicial se asigna directamente al técnico
- No pasa por el stock general del tenant
- Esto es diferente al recojo, que sí pasa por el stock general

### 5.11 Auditoría
- El sistema registra quién cargó el stock inicial, cuándo y qué archivo exacto
- Cada serie y cantidad creada registra usuario, fecha y valor anterior (ninguno) y nuevo

## 6. Requisitos No Funcionales

### 6.1 Rendimiento
- La validación del Excel debe ser eficiente para grandes volúmenes
- La carga por formulario debe ser rápida

### 6.2 Usabilidad
- El formulario debe permitir ingresar múltiples materiales por técnico
- Los errores deben ser claros y específicos
- Debe mostrar progreso durante la carga del Excel

### 6.3 Integridad
- La operación de carga debe ser transaccional
- No se pueden cargar stock inicial parcial

## 7. Criterios de Aceptación

### CA-01: Carga por Excel Exitosa
Dado un Excel válido con stock inicial de técnicos
Cuando el tenant carga el archivo
Entonces el sistema carga el stock inicial y marca el tenant como "stock inicial cargado"

### CA-02: Carga por Formulario Exitosa
Dado un formulario con stock inicial de un técnico
Cuando el tenant guarda el formulario
Entonces el sistema carga el stock inicial para ese técnico

### CA-03: Técnico No Existe
Dado un Excel con un técnico que no existe en el tenant
Cuando el tenant intenta cargar el archivo
Entonces el sistema rechaza la carga y muestra el error

### CA-04: Material No Existe
Dado un Excel con un material que no existe en el catálogo
Cuando el tenant intenta cargar el archivo
Entonces el sistema rechaza la carga y muestra el error

### CA-05: Serie Duplicada en Excel
Dado un Excel con la misma serie dos veces
Cuando el tenant intenta cargar el archivo
Entonces el sistema rechaza la carga y muestra el error

### CA-06: Serie Ya Existe en Sistema
Dado un Excel con una serie que ya existe en el sistema
Cuando el tenant intenta cargar el archivo
Entonces el sistema rechaza la carga y muestra el error

### CA-07: Carga Única
Dado un tenant que ya cargó su stock inicial
Cuando el tenant intenta cargar stock inicial nuevamente
Entonces el sistema rechaza la carga y muestra el error

### CA-08: Asignación Directa al Técnico
Dado un stock inicial cargado para un técnico
Cuando se consulta el stock del técnico
Entonces el stock refleja lo cargado (no pasa por stock general)

### CA-09: Auditoría de Carga
Dado un stock inicial cargado
Cuando se consulta la auditoría
Entonces se registra quién cargó, cuándo y qué archivo

### CA-10: Transaccionalidad
Dado un Excel con 100 filas, pero 1 tiene error
Cuando el tenant intenta cargar el archivo
Entonces no se carga nada y se muestra el error

### CA-11: Edición de Stock Inicial - Agregar Serie
Dado un stock inicial cargado
Cuando el tenant agrega una serie faltante
Entonces la serie se agrega al técnico y se audita el cambio

### CA-12: Edición de Stock Inicial - Eliminar Serie
Dado un stock inicial cargado con una serie incorrecta
Cuando el tenant elimina esa serie
Entonces la serie se elimina del técnico y se audita el cambio

### CA-13: Edición de Stock Inicial - Modificar Cantidad
Dado un stock inicial cargado con cantidad incorrecta
Cuando el tenant modifica la cantidad
Entonces la cantidad se actualiza y se audita el cambio

## 8. Datos de Entrada

### Excel de Stock Inicial

Ver `04-contratos/excel-stock-inicial.md` para el formato completo.

### Formulario de Stock Inicial

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Técnico | Select | Sí | Técnico del tenant |
| Material | Select | Sí | Material del catálogo |
| Tipo de material | Read-only | Sí | Seriado o no seriado (del catálogo) |
| Lote | Read-only | Sí | Lote del material (del catálogo) |
| Series | Text area / Scanner | Condicional | Series (solo para seriados) |
| Cantidad | Number | Condicional | Cantidad (solo para no seriados) |

## 9. Datos de Salida

### Confirmación de Carga

| Campo | Descripción |
|---|---|
| ID de carga | Identificador único de la carga |
| Fecha | Fecha de la carga |
| Tenant | Tenant que cargó el stock inicial |
| Total técnicos | Número de técnicos con stock inicial |
| Total series | Número de series cargadas |
| Total cantidad | Suma de cantidades (no seriados) |

## 10. Reglas de Negocio

1. El stock inicial se carga una sola vez por tenant
2. El stock inicial se asigna directamente al técnico (no pasa por stock general)
3. El formato del Excel es idéntico al reporte de Lari
4. Se permiten dos formas de carga: Excel y formulario
5. La carga es transaccional (todo o nada)
6. Todos los técnicos deben existir en el tenant
7. Las series no deben estar duplicadas ni existir ya en el sistema
8. La carga se audita completamente

## 11. Consideraciones de Implementación

- La validación de existencia de series debe ser eficiente (consultar índice de series)
- La carga por Excel debe procesar filas en batch para rendimiento
- La transacción debe abarcar: validación de todas las filas + creación de series + asignación a técnicos + marca de tenant
- El modelo Tenant necesita un campo `stock_inicial_cargado` (booleano, default False)
- El Administrador de plataforma puede tener un comando para reiniciar este flag en caso de error durante implementación
- La carga por formulario reutiliza la lógica de validación del Excel
