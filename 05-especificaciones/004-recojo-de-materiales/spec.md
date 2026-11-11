# Spec 004 - Recojo de Materiales

Especificación técnica para el registro de recojos de materiales del almacén central.

## 1. Propósito

Permitir que los tenants registren los materiales que retiran del almacén central de su región. Cada recojo incrementa el stock general del tenant con las series y cantidades recibidas.

## 2. Alcance

- Registro de recojos por formulario (no por Excel)
- Soporte para materiales seriados y no seriados
- Validación de series en tiempo real
- Incremento del stock general del tenant

## 3. Actores

- **Tenant (ACT-01)**: Registra el recojo de materiales
- **Almacén central**: Entrega los materiales (no es actor del sistema)

## 4. Trazabilidad

### Historias de Usuario
- No hay HU específica para recojo (considerado parte del flujo de trabajo general)

### Requisitos Funcionales
- **RF-14**: Un tenant recoge solo en el almacén de su región
- **RF-15**: Una serie pertenece a un tenant y no cambia de región
- **RF-16**: El recojo se registra por formulario con varias líneas. Cada línea suma al stock general del tenant
- **RF-17**: Las series se ingresan pegando texto o escaneando una por una, con vista previa por fila y su estado
- **RF-18**: Cada serie se normaliza (mayúsculas, sin espacios) y debe tener 12 caracteres alfanuméricos
- **RF-19**: Si alguna serie es inválida, duplicada o ya existe, no se guarda ningún recojo

### Atributos de Calidad
- RF-14: Integridad de datos (aislamiento por región)
- RF-19: Consistencia (todo o nada)

## 5. Requisitos Funcionales

### 5.1 Restricción de Región (RF-14)
- Un tenant solo puede registrar recojos del almacén central de su región
- El sistema valida que el tenant pertenezca a la región del almacén
- No se permite registrar recojos de almacenes de otras regiones

### 5.2 Propiedad de Series (RF-15)
- Una serie pertenece a un tenant desde el momento del recojo
- Una serie no cambia de región durante toda su vida
- El sistema asigna la región del tenant a cada serie registrada

### 5.3 Registro por Formulario (RF-16)
- El recojo se registra mediante un formulario web
- El formulario permite múltiples líneas (una por material o serie)
- Cada línea suma al stock general del tenant
- No se usa Excel para el registro de recojos

### 5.4 Ingreso de Series (RF-17)
- Las series se ingresan de dos formas:
  - Pegando texto (una serie por línea)
  - Escaneando una por una con lector de código de barras
- El sistema muestra vista previa por fila con:
  - La serie ingresada
  - Su estado (válida, inválida, duplicada, ya existe)
- La vista previa se actualiza en tiempo real

### 5.5 Normalización de Series (RF-18)
- Cada serie se normaliza automáticamente:
  - Convertir a mayúsculas
  - Eliminar espacios
- La serie debe tener exactamente 12 caracteres alfanuméricos (A-Z, 0-9)
- Las series que no cumplen el formato se marcan como inválidas

### 5.6 Validación y Regla Todo o Nada (RF-19)
- El sistema valida cada serie antes de guardar:
  - Formato correcto (12 caracteres alfanuméricos)
  - No duplicada dentro del mismo recojo
  - No existe ya en el sistema (en ningún tenant)
- Si alguna serie es inválida, duplicada o ya existe:
  - No se guarda ningún recojo
  - Se muestra el error al usuario
  - El usuario debe corregir y reintentar
- Solo se guarda el recojo si todas las series son válidas

## 6. Requisitos No Funcionales

### 6.1 Rendimiento
- La validación de series debe ser rápida (< 1 segundo por serie)
- La vista previa debe actualizarse en tiempo real

### 6.2 Usabilidad
- El formulario debe permitir pegar múltiples series de una vez
- Debe soportar entrada con lector de código de barras
- Los errores deben ser claros y específicos

### 6.3 Integridad
- La operación de guardar un recojo debe ser transaccional
- No se pueden guardar recojos parciales

## 7. Criterios de Aceptación

### CA-01: Restricción de Región
Dado un tenant de la región "Ayacucho"
Cuando intenta registrar un recojo
Entonces el sistema solo permite recojos del almacén de Ayacucho

### CA-02: Registro de Materiales Seriados
Dado un formulario de recojo
Cuando el tenant ingresa series válidas (formato correcto, no duplicadas, no existentes)
Entonces el sistema guarda el recojo y las series se agregan al stock general del tenant

### CA-03: Normalización de Series
Dado que el usuario ingresa la serie "abc123456789"
Cuando el sistema procesa la serie
Entonces la serie se normaliza a "ABC123456789"

### CA-04: Validación de Formato
Dado que el usuario ingresa la serie "ABC123"
Cuando el sistema valida la serie
Entonces la serie se marca como inválida (no tiene 12 caracteres)

### CA-05: Detección de Duplicados
Dado que el usuario ingresa la serie "ABC123456789" dos veces en el mismo recojo
Cuando el sistema valida las series
Entonces la segunda ocurrencia se marca como duplicada

### CA-06: Detección de Series Existentes
Dado que la serie "ABC123456789" ya existe en el sistema
Cuando el usuario intenta registrarla en un nuevo recojo
Entonces la serie se marca como ya existente

### CA-07: Regla Todo o Nada
Dado que el usuario ingresa 10 series, pero 1 es inválida
Cuando el usuario intenta guardar el recojo
Entonces no se guarda ningún recojo y se muestra el error

### CA-08: Vista Previa en Tiempo Real
Dado que el usuario pega o escanea series
Cuando cada serie se ingresa
Entonces el sistema muestra vista previa con la serie y su estado inmediatamente

### CA-09: Registro de Materiales No Seriados
Dado un formulario de recojo
Cuando el tenant ingresa un material no seriado con cantidad
Entonces el sistema guarda el recojo y la cantidad se suma al stock general del tenant

## 8. Datos de Entrada

### Formulario de Recojo

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Fecha | Date | Sí | Fecha del recojo (por defecto: hoy) |
| Material | Select | Sí | Material del catálogo |
| Tipo de material | Read-only | Sí | Seriado o no seriado (del catálogo) |
| Lote | Read-only | Sí | Lote del material (del catálogo) |
| Series | Text area / Scanner | Condicional | Series (solo para seriados) |
| Cantidad | Number | Condicional | Cantidad (solo para no seriados) |

## 9. Datos de Salida

### Confirmación de Recojo

| Campo | Descripción |
|---|---|
| ID de recojo | Identificador único del recojo |
| Fecha | Fecha del recojo |
| Tenant | Tenant que registró el recojo |
| Región | Región del tenant |
| Total series | Número de series registradas |
| Total cantidad | Suma de cantidades (no seriados) |

## 10. Reglas de Negocio

1. Un tenant solo puede registrar recojos de su región
2. Una serie pertenece a un solo tenant y no cambia de región
3. El stock general solo sube con recojos registrados
4. El recojo se registra por formulario, no por Excel
5. Las series se normalizan (mayúsculas, sin espacios)
6. Si alguna serie es inválida, duplicada o ya existe, no se guarda ningún recojo (todo o nada)

## 11. Consideraciones de Implementación

- La validación de existencia de series debe ser eficiente (consultar índice de series)
- La normalización debe aplicarse antes de cualquier validación
- La transacción debe abarcar: validación de todas las series + inserción en stock general + asignación de tenant y región
- El frontend debe mostrar la vista previa antes de guardar
