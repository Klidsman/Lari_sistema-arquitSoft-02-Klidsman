# Spec 009 - Traspaso entre Técnicos

Especificación técnica para el traspaso de materiales entre técnicos del mismo tenant.

## 1. Propósito

Permitir que los tiles traspasen materiales entre técnicos del mismo tenant. Los traspasos mueven materiales (series o cantidades) de un técnico origen a un técnico destino, generan un Excel de dos hojas (Desasignación Z32 y Asignación Z31), requieren confirmación del almacén y no modifican el stock general del tenant.

## 2. Alcance

- Creación de solicitudes de traspaso entre técnicos del mismo tenant
- Selección de series/cantidades del técnico origen
- Validación de disponibilidad en el técnico origen
- Generación automática de Excel de dos hojas (ver `04-contratos/excel-traspaso.md`)
- Cambio de técnico de las series al confirmar
- No modificación del stock general del tenant
- Inicio del conteo de días en mano para seriados (al confirmar)

## 3. Actores

- **Tenant (ACT-01)**: Crea solicitudes de traspaso entre sus técnicos
- **Responsable de almacén (ACT-03)**: Confirma o rechaza los traspasos

## 4. Trazabilidad

### Requisitos Funcionales
- **RF-33**: Un traspaso mueve materiales entre técnicos del mismo tenant, con un Excel de dos hojas: Desasignación (Z32) y Asignación (Z31)
- **RF-34**: El técnico origen y el destino no pueden ser el mismo
- **RF-35**: El origen solo puede ceder materiales y series que tiene asignados, descontando lo reservado
- **RF-36**: Lo que sale debe cuadrar con lo que entra, por material y por serie. Si no cuadra, se rechaza todo
- **RF-37**: El Responsable de almacén acepta o rechaza el traspaso. Al aceptar, las series cambian de técnico. Al rechazar, no cambia nada
- **RF-38**: Un traspaso no modifica el stock general del tenant

### Atributos de Calidad
- RF-35: Consistencia (validación de disponibilidad)
- RF-36: Integridad (cuadre de lo que sale y entra)
- RF-38: Consistencia (stock general invariable)

## 5. Requisitos Funcionales

### 5.1 Traspaso entre Técnicos del Mismo Tenant (RF-33)
- Un traspaso mueve materiales entre técnicos del mismo tenant
- No existen traspasos entre tenants
- El sistema genera un Excel de dos hojas:
  - Hoja 1: Desasignación (Z32) para el técnico origen
  - Hoja 2: Asignación (Z31) para el técnico destino

### 5.2 Origen y Destino Distintos (RF-34)
- El técnico origen y el técnico destino no pueden ser el mismo
- El sistema valida que origen != destino
- Si son iguales, rechaza la solicitud

### 5.3 Disponibilidad en el Origen (RF-35)
- El técnico origen solo puede ceder materiales y series que tiene asignados
- La disponibilidad se calcula descontando lo reservado en traspasos pendientes
- Solo se pueden traspasar series en estado Asignada al técnico origen
- Fórmula: `Disponible = Stock Técnico - Reservado en Traspasos Pendientes`

### 5.4 Cuadre de Lo que Sale y Entra (RF-36)
- Lo que sale del técnico origen debe cuadrar con lo que entra al técnico destino
- El cuadre se hace por material y por serie
- Si no cuadra, se rechaza todo el traspaso
- Ejemplo de cuadre:
  - Por serie: la serie ABC123 sale del origen y entra al destino
  - Por material: 50 unidades de cable salen del origen y 50 entran al destino

### 5.5 Confirmación del Almacén (RF-37)
- El Responsable de almacén acepta o rechaza el traspaso
- Al aceptar:
  - Las series cambian de técnico (origen → destino)
  - El stock del origen baja
  - El stock del destino sube
  - Se inicia el conteo de días en mano para seriados (RF-62)
- Al rechazar:
  - No cambia nada
  - Las series siguen en el técnico origen
  - Se requiere un comentario del motivo

### 5.6 Stock General Invariable (RF-38)
- Un traspaso no modifica el stock general del tenant
- Solo se mueve material entre técnicos
- El total del tenant no cambia con traspasos

## 6. Requisitos No Funcionales

### 6.1 Consistencia
- La validación de cuadre debe ser precisa
- El stock general no debe modificarse nunca

### 6.2 Rendimiento
- La validación de disponibilidad debe ser rápida
- La generación del Excel de dos hojas debe ser eficiente

### 6.3 Integridad
- El traspaso debe ser transaccional
- No se pueden tener traspasos parciales

## 7. Criterios de Aceptación

### CA-01: Traspaso entre Técnicos del Mismo Tenant
Dado un tenant con dos técnicos
Cuando el tenant crea un traspaso entre ellos
Entonces el sistema genera el Excel de dos hojas

### CA-02: Origen y Destino Distintos
Dado que el usuario selecciona el mismo técnico como origen y destino
Cuando el sistema valida
Entonces rechaza la solicitud

### CA-03: Solo Cede lo que Tiene Asignado
Dado un técnico origen con stock de 10
Cuando intenta traspasar 15
Entonces el sistema rechaza por insuficiente

### CA-04: Cuadre de Series
Dado un traspaso con serie ABC123 que sale pero no entra
Cuando el sistema valida
Entonces rechaza el traspaso

### CA-05: Cuadre de Cantidades
Dado un traspaso con 50 unidades que salen pero 40 entran
Cuando el sistema valida
Entonces rechaza el traspaso

### CA-06: Confirmación Cambia de Técnico
Dado un traspaso confirmado
Cuando se consulta el técnico de las series
Entonces las series están en el técnico destino

### CA-07: Rechazo No Cambia Nada
Dado un traspaso rechazado
Cuando se consulta el técnico de las series
Entonces las series siguen en el técnico origen

### CA-08: Stock General Invariable
Dado un traspaso confirmado
Cuando se consulta el stock general del tenant
Entonces no cambió

### CA-09: Días en Mano Reinician al Traspasar
Dado una serie con 10 días en mano en el técnico origen
Cuando se confirma el traspaso
Entonces reinicia el conteo en el técnico destino (RF-62)

## 8. Datos de Entrada

### Formulario de Traspaso

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Técnico origen | Select | Sí | Técnico que cede los materiales |
| Técnico destino | Select | Sí | Técnico que recibe los materiales |
| Fecha | Date | Sí | Fecha del traspaso (por defecto: hoy) |
| Material | Select | Condicional | Material del catálogo (por línea) |
| Tipo de material | Read-only | Condicional | Seriado o no seriado (del catálogo) |
| Lote | Read-only | Condicional | Lote del material (del catálogo) |
| Series | Multi-select | Condicional | Series del técnico origen (solo para seriados) |
| Cantidad | Number | Condicional | Cantidad (solo para no seriados) |

## 9. Datos de Salida

### Solicitud de Traspaso

| Campo | Descripción |
|---|---|
| ID de solicitud | Identificador único de la solicitud |
| Estado | Borrador, Enviada, Confirmada, Rechazada, Cancelada |
| Técnico origen | Técnico que cede |
| Técnico destino | Técnico que recibe |
| Fecha | Fecha de creación |
| Líneas | Lista de materiales, series o cantidades |
| Excel | Ruta del archivo Excel generado |
| Hash SHA-256 | Firma del Excel |

## 10. Reglas de Negocio

1. Un traspaso es entre técnicos del mismo tenant
2. El técnico origen y destino no pueden ser el mismo
3. El origen solo puede ceder lo que tiene asignado
4. Lo que sale debe cuadrar con lo que entra
5. Al confirmar, las series cambian de técnico
6. Al rechazar, no cambia nada
7. El stock general del tenant no cambia
8. Los días en mano reinician al traspasar (RF-62)

## 11. Consideraciones de Implementación

- La validación de disponibilidad consulta el stock del técnico origen
- El cuadre se valida al crear la solicitud (no solo al confirmar)
- La generación del Excel de dos hojas usa openpyxl
- El cambio de técnico de series requiere actualizar la FK de técnico en el modelo de series
- El stock general no se toca en ningún momento
- La actualización de stock técnico se hace con las funciones de spec 008
