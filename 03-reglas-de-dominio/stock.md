# Stock

Reglas de dominio para la gestión de stock en el sistema.

## 1. Definición

El **stock** representa la cantidad de materiales disponibles en el sistema. Existen dos niveles de stock que funcionan de manera jerárquica.

## 2. Niveles de Stock

### 2.1 Stock General del Tenant
- Es el stock total del tenant, antes de asignar a técnicos
- Ubicación: almacén del tenant (no es el almacén central de Lari)
- Solo contiene materiales con estado **Disponible**
- Un material pasa al stock de un técnico solo mediante una asignación confirmada por el almacén central

### 2.2 Stock por Técnico
- Es el stock asignado a un técnico específico
- Ubicación: posesión del técnico (LAxxxx)
- Contiene materiales con estado **Asignada**
- Representa la custodia actual del técnico sobre los materiales

## 3. Reglas de Movimiento de Stock

### 3.1 Stock General - Incrementos
El stock general del tenant **solo sube** con:
- **Recojos registrados** de materiales del almacén central de la región
- Devoluciones de técnicos (desasignaciones confirmadas)

No existen otras formas de incrementar el stock general.

### 3.2 Stock General - Decrementos
El stock general del tenant **solo baja** con:
- **Asignaciones confirmadas** por el almacén central
- Cuando una asignación pasa de estado pendiente a confirmada, el material se mueve del stock general al stock del técnico

Los traspasos **no modifican** el stock general del tenant.

### 3.3 Stock por Técnico - Incrementos
El stock de un técnico sube con:
- **Asignaciones confirmadas** por el almacén central
- **Traspasos recibidos** de otros técnicos del mismo tenant

### 3.4 Stock por Técnico - Decrementos
El stock de un técnico baja con:
- **Devoluciones/desasignaciones** al stock general del tenant
- **Traspasos enviados** a otros técnicos del mismo tenant
- **Bajas/Recuperaciones** (avería, migración, etc.)

## 4. Reglas de Asignación

### 4.1 Disponibilidad
- **No se asigna más de lo disponible** en el stock general
- La disponibilidad se calcula descontando lo reservado en asignaciones pendientes
- Fórmula: `Disponible = Stock General - Reservado`

### 4.2 Confirmación del Almacén
- Una asignación no modifica el stock hasta que el almacén central la confirma
- Si el almacén rechaza la asignación, las series reservadas vuelven al stock general
- Solo las asignaciones confirmadas mueven material del stock general al stock del técnico

### 4.3 Traspasos
- **Traspaso = mover, no crear**
- Lo que sale de un técnico entra en otro del mismo tenant
- El total del tenant no cambia con traspasos
- No existen traspasos entre tenants

## 5. Stock de Materiales Seriados vs No Seriados

### 5.1 Materiales Seriados
- Cada unidad se identifica por su serie individual
- Genera una fila por serie en el inventario
- Cada fila tiene Cantidad = 1
- El stock se mide en número de series

### 5.2 Materiales No Seriados
- Las unidades no tienen serie individual
- Genera una fila con la cantidad que digita el tenant
- El stock se mide en cantidad numérica

## 6. Validaciones de Stock

### 6.1 Validación de Disponibilidad
- No se puede crear una asignación si el material no está disponible en stock general
- No se puede reservar más cantidad de la disponible (descontando lo ya reservado)

### 6.2 Validación de Asignación
- No se puede asignar a un técnico más material del que tiene disponible
- Un técnico no puede recibir series que ya están asignadas a otro técnico

### 6.3 Validación de Traspaso
- No se puede traspasar más material del que tiene el técnico origen
- El traspaso solo es válido entre técnicos del mismo tenant

## 7. Stock Inicial de Técnicos

- Los técnicos pueden comenzar con un stock inicial configurado
- Este stock inicial se registra mediante un proceso específico
- El stock inicial se asigna directamente al técnico sin pasar por el stock general

## 8. Cálculo de Días en Mano

- Para equipos seriados, el sistema calcula los días que han estado en posesión del técnico
- Se calcula desde la fecha de asignación hasta la fecha actual o de devolución
- Este dato es informativo para el control de custodia

## 9. Cupo Máximo de Equipos

- Un técnico puede tener un cupo máximo de equipos sin liquidar
- Si un técnico supera este cupo, el sistema alerta al tenant
- Esto cumple la política de custodia de equipos

## 10. Conciliación de Stock

### 10.1 Comparación con Reporte de Lari
- El sistema compara el stock del tenant con el reporte de Lari
- En una conciliación aprobada, el reporte de Lari prevalece sobre el stock del sistema

### 10.2 Actualización de Stock de Fungibles
- Para materiales no seriados, el sistema actualiza el stock del técnico a la cantidad que reporta Lari
- No se calcula consumo de fungibles
- El stock inicial (cantidad al inicio del día) es solo informativo

### 10.3 Liquidación de Seriados
- Las series ya no reportadas se actualizan a estado instalado automáticamente
- Esto refleja la liquidación del equipo

### 10.4 Aprobación Humana
- Cargar un reporte no modifica stock automáticamente
- La conciliación se aprueba o rechaza completa (todo o nada)
- Los ajustes requieren aprobación humana

## 11. Auditoría de Stock

- Todo movimiento de stock registra: usuario, fecha, valor anterior y valor nuevo
- No se borran movimientos de stock; se corrigen con uno nuevo
- Nada cambia el stock sin dejar rastro
- El stock es trazable a través de toda su vida en el sistema

## 12. Seguridad y Aislamiento

- Un tenant nunca ve ni modifica el stock de otro tenant
- El filtrado por tenant se aplica en el backend (y en la base de datos si es posible)
- Cada stock referencia a su tenant, y de ahí se obtiene su región
