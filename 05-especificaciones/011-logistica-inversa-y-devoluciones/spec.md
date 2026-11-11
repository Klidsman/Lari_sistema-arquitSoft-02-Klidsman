# Spec 011 - Logística Inversa y Devoluciones

Especificación técnica para la devolución de equipos, recuperación de equipos y generación de actas de entrega.

## 1. Propósito

Permitir que los tiles registren la devolución de equipos por parte de técnicos, registren equipos recuperados o de baja (avería, migración), y generen actas de entrega de devoluciones a Lari (contrata principal).

## 2. Alcance

- Registro de devolución de equipos del técnico
- Liberación de custodia del técnico sobre las series devueltas
- Registro de equipos recuperados o de baja con causa (avería, migración)
- Salida de series del stock disponible
- Generación de acta de entrega de devoluciones a Lari

## 3. Actores

- **Tenant (ACT-01)**: Registra devoluciones, recuperaciones y bajas, genera actas

## 4. Trazabilidad

### Historias de Usuario
- **HU-23** (RF-65): Como tenant, quiero registrar equipos devueltos por el técnico y retirarlos del stock disponible, liberando su custodia
- **HU-24** (RF-66): Como tenant, quiero registrar equipos recuperados o de baja (serie y causa: avería, migración), para controlar el flujo de retorno
- **HU-25** (RF-67): Como tenant, quiero generar el acta de entrega de devoluciones a la contrata principal/Lari

### Requisitos Funcionales
- **RF-65**: Registrar la devolución de equipos del técnico: cada serie sale de su stock y vuelve a Disponible, liberando su custodia
- **RF-66**: Registrar equipos recuperados o de baja con su serie y causa (avería, migración); salen del stock disponible
- **RF-67**: Generar el acta de entrega de devoluciones a Lari (contrata principal)

### Atributos de Calidad
- RF-65: Consistencia (liberación de custodia)
- RF-66: Trazabilidad (causa de baja)
- RF-67: Compatibilidad (acta estandarizada)

## 5. Requisitos Funcionales

### 5.1 Devolución de Equipos (RF-65)
- El tenant registra la devolución de equipos por parte de un técnico
- Cada serie devuelta sale del stock del técnico
- Las series vuelven a estado Disponible
- La custodia del técnico sobre las series se libera
- Las series pueden ser reasignadas a otros técnicos

### 5.2 Recuperación y Baja de Equipos (RF-66)
- El tenant registra equipos recuperados o de baja
- Se registra la serie y la causa:
  - Avería: el equipo está dañado
  - Migración: el equipo se está migrando a otro sistema/proceso
- Las series salen del stock disponible
- Las series no pueden ser reasignadas
- Se registra la causa para trazabilidad

### 5.3 Generación de Acta de Entrega (RF-67)
- El tenant genera el acta de entrega de devoluciones a Lari
- El acta contiene:
  - Lista de series devueltas
  - Técnico que devolvió
  - Fecha de devolución
  - Causa (si aplica)
- El acta se genera en formato Excel
- El acta se puede descargar y enviar a Lari

## 6. Requisitos No Funcionales

### 6.1 Consistencia
- La devolución debe liberar la custodia correctamente
- La baja debe eliminar el stock disponible

### 6.2 Trazabilidad
- La causa de baja debe registrarse
- Las devoluciones deben auditar completamente

### 6.3 Compatibilidad
- El acta debe ser compatible con los sistemas de Lari

## 7. Criterios de Aceptación

### CA-01: Devolución Libera Custodia
Dado un técnico con series asignadas
Cuando se registra la devolución
Entonces las series salen de su stock y vuelven a Disponible

### CA-02: Series Devueltas Pueden Reasignarse
Dado una serie devuelta y vuelta a Disponible
Cuando se consulta la serie
Entonces puede ser asignada a otro técnico

### CA-03: Recuperación con Causa
Dado un equipo recuperado por avería
Cuando se registra la recuperación
Entonces la serie sale del stock disponible y se registra la causa

### CA-04: Baja por Migración
Dado un equipo dado de baja por migración
Cuando se registra la baja
Entonces la serie sale del stock disponible y se registra la causa

### CA-05: Generación de Acta
Dado una devolución registrada
Cuando se genera el acta
Entonces contiene todas las series devueltas, técnico y fecha

### CA-06: Auditoría de Devoluciones
Dado una devolución registrada
Cuando se consulta la auditoría
Entonces registra usuario, fecha, series y cambios de estado

## 8. Datos de Entrada

### Formulario de Devolución

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Técnico | Select | Sí | Técnico que devuelve |
| Fecha | Date | Sí | Fecha de devolución |
| Series | Multi-select | Sí | Series a devolver |
| Observaciones | Textarea | No | Observaciones de la devolución |

### Formulario de Recuperación/Baja

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Serie | Text | Sí | Serie del equipo |
| Causa | Select | Sí | Avería, Migración, Otro |
| Observaciones | Textarea | No | Observaciones |

## 9. Datos de Salida

### Devolución

| Campo | Descripción |
|---|---|
| ID de devolución | Identificador único |
| Técnico | Técnico que devolvió |
| Fecha | Fecha de devolución |
| Series | Lista de series devueltas |
| Acta | Ruta del acta generada |

### Recuperación/Baja

| Campo | Descripción |
|---|---|
| ID de baja | Identificador único |
| Serie | Serie del equipo |
| Causa | Avería, Migración, Otro |
| Fecha | Fecha de registro |
| Usuario | Usuario que registró |

## 10. Reglas de Negocio

1. La devolución libera la custodia del técnico
2. Las series devueltas vuelven a Disponible
3. La recuperación/baja saca las series del stock disponible
4. La causa de baja debe registrarse
5. El acta de entrega se genera a partir de las devoluciones

## 11. Consideraciones de Implementación

- La devolución usa funciones de stock de spec 008 (decrementar stock técnico, incrementar stock general)
- La recuperación/baja cambia el estado de la serie a un estado inactivo
- El acta se genera con openpyxl
- La auditoría registra todos los cambios
