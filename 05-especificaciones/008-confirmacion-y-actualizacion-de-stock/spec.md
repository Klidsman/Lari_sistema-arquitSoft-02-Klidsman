# Spec 008 - Confirmación y Actualización de Stock

Especificación técnica para la actualización de stock al confirmar una solicitud de asignación.

## 1. Propósito

Definir la lógica de actualización de stock cuando el Responsable de almacén confirma una solicitud de asignación. Esta actualización incluye el cambio de estado de series, el incremento del stock del técnico y el decremento del stock general del tenant.

## 2. Alcance

- Actualización de stock al confirmar una solicitud de asignación
- Cambio de estado de series de Reservada a Asignada
- Incremento del stock del técnico
- Decremento del stock general del tenant
- Inicio del conteo de días en mano para seriados
- Registro de auditoría de los cambios de stock

## 3. Actores

- **Responsable de almacén (ACT-03)**: Confirma la solicitud de asignación
- **Tenant (ACT-01)**: Recibe notificación de confirmación

## 4. Trazabilidad

### Historias de Usuario
- **HU-16** (RF-29, RF-32): Como Almacén, quiero confirmar la asignación

### Requisitos Funcionales
- **RF-32**: Al confirmar, las series pasan a Asignada al técnico, el stock del técnico sube y el stock general baja

### Atributos de Calidad
- RF-32: Consistencia (actualización transaccional)
- RF-32: Integridad (auditoría de cambios)

## 5. Requisitos Funcionales

### 5.1 Cambio de Estado de Series (RF-32)
- Al confirmar una solicitud, las series pasan de estado Reservada a Asignada
- Solo las series de la solicitud confirmada cambian de estado
- Las series quedan asociadas al técnico de la solicitud
- El cambio de estado es irreversible (para liberar, se requiere devolución o traspaso)

### 5.2 Incremento del Stock del Técnico (RF-32)
- Al confirmar, el stock del técnico se incrementa
- Para materiales seriados: cada serie confirma agrega 1 al stock del técnico
- Para materiales no seriados: la cantidad reservada se suma al stock del técnico
- El stock del técnico se actualiza inmediatamente

### 5.3 Decremento del Stock General (RF-32)
- Al confirmar, el stock general del tenant se decrementa
- Para materiales seriados: cada serie confirma resta 1 del stock general
- Para materiales no seriados: la cantidad reservada se resta del stock general
- El stock general se actualiza inmediatamente

### 5.4 Cálculo de Días en Mano (RF-61)
- Al confirmar, inicia el conteo de días en mano para los seriados
- Los días en mano se calculan desde la fecha de confirmación
- Este dato es informativo para el control de custodia
- Se muestra en el detalle del técnico y en reportes

### 5.5 Transaccionalidad
- La actualización de stock es transaccional
- Si falla alguna parte (cambio de estado, actualización de técnico, actualización de general), toda la operación se revierte
- No se pueden tener actualizaciones parciales de stock

### 5.6 Auditoría de Cambios
- Todo cambio de stock registra auditoría
- Para cada cambio se registra: usuario, fecha, valor anterior, valor nuevo
- Se registra el cambio de estado de cada serie
- Se registra el cambio de stock del técnico
- Se registra el cambio de stock general

## 6. Requisitos No Funcionales

### 6.1 Consistencia
- La actualización de stock debe ser atómica
- No se pueden tener inconsistencias entre stock del técnico y stock general

### 6.2 Rendimiento
- La actualización de stock debe ser rápida (< 2 segundos)
- La actualización de múltiples series debe ser eficiente

### 6.3 Integridad
- La auditoría debe ser completa y trazable
- No se pueden perder registros de cambios

## 7. Criterios de Aceptación

### CA-01: Series Pasan a Asignada
Dado una solicitud confirmada
Cuando se consulta el estado de las series
Entonces las series están en estado Asignada

### CA-02: Stock del Técnico Sube
Dado un técnico con stock inicial de 10
Cuando se confirma una asignación de 5 series
Entonces el stock del técnico es 15

### CA-03: Stock General Baja
Dado un tenant con stock general de 100
Cuando se confirma una asignación de 5 series
Entonces el stock general es 95

### CA-04: Actualización Transaccional
Dado una confirmación que falla en la actualización del técnico
Cuando se consulta el stock
Entonces no hubo cambios (general ni técnico)

### CA-05: Días en Mano Inician
Dado una asignación confirmada hoy
Cuando se consulta los días en mano mañana
Entonces muestra 1 día

### CA-06: Auditoría Completa
Dado una confirmación de asignación
Cuando se consulta la auditoría
Entonces registra cambio de estado de series, stock técnico y stock general

### CA-07: No Seriados Actualizan Cantidad
Dado una asignación de 50 unidades de material no seriado
Cuando se confirma
Entonces el stock del técnico suma 50 y el stock general resta 50

## 8. Datos de Salida

### Actualización de Stock

| Campo | Descripción |
|---|---|
| ID de solicitud | Solicitud confirmada |
| Fecha confirmación | Fecha y hora de confirmación |
| Series actualizadas | Lista de series que cambiaron a Asignada |
| Stock técnico anterior | Stock del técnico antes de la confirmación |
| Stock técnico nuevo | Stock del técnico después de la confirmación |
| Stock general anterior | Stock general antes de la confirmación |
| Stock general nuevo | Stock general después de la confirmación |

## 9. Reglas de Negocio

1. Al confirmar, las series pasan de Reservada a Asignada
2. El stock del técnico se incrementa con las series/cantidades confirmadas
3. El stock general se decrementa con las series/cantidades confirmadas
4. La actualización es transaccional (todo o nada)
5. Se inicia el conteo de días en mano para seriados
6. Todo cambio se audita completamente

## 10. Consideraciones de Implementación

- La actualización de stock se integra con la confirmación de solicitud (spec 007)
- El modelo de stock debe tener campos para stock general y stock por técnico
- El cambio de estado de series se hace en el módulo de series
- La auditoría usa el modelo compartido `RegistroCambio`
- El cálculo de días en mano se puede hacer a demanda o en background
- La transacción debe abarcar: cambio de estado de series + actualización de stock técnico + actualización de stock general + auditoría
