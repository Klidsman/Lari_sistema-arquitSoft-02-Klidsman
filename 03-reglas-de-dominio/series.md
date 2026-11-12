# Series

Reglas de dominio para la gestión de series en el sistema.

## 1. Definición

Una **serie** es un identificador único que distingue unidades individuales de materiales seriados. Cada serie representa una unidad física específica que puede ser rastreada a través del sistema.

## 2. Formato

- **Longitud:** 12 caracteres alfanuméricos
- **Caracteres permitidos:** A-Z (mayúsculas) y 0-9
- **Formato:** No tiene separadores ni caracteres especiales
- **Ejemplo:** ABC123456789

## 3. Estados de una Serie

Una serie puede estar en uno de los siguientes estados:

| Estado | Descripción | Transiciones permitidas |
|---|---|---|
| **Disponible** | La serie está en el stock general del tenant y puede ser asignada | → Reservada (al seleccionarse en una asignación) |
| **Reservada** | La serie está reservada en una asignación pendiente de confirmación por el almacén | → Disponible (si el almacén rechaza la asignación) → Asignada (si el almacén confirma la asignación) |
| **Asignada** | La serie está en posesión de un técnico específico | → Disponible (cuando el técnico la devuelve/desasigna) |

## 4. Reglas de Unicidad y Existencia

### 4.1 Unicidad Global
- Cada serie existe **una sola vez** en todo el sistema
- No puede haber duplicados de la misma serie en ningún lugar del sistema
- Una serie pertenece a un solo tenant y, por ende, a una sola región durante toda su vida

### 4.2 Ubicación Única
- Una serie está en un solo lugar a la vez:
  - Stock general del tenant (estado Disponible)
  - Reservada en una asignación pendiente (estado Reservada)
  - Stock de un técnico específico (estado Asignada)

### 4.3 Materiales Seriados vs No Seriados
- **Material seriado:** Cada unidad se identifica por su serie individual. Genera una fila por serie en el inventario, con Cantidad = 1.
- **Material no seriado:** Las unidades no tienen serie individual. Genera una fila con la cantidad que digita el tenant.

## 5. Ciclo de Vida de una Serie

### 5.1 Ingreso al Sistema
- Las series ingresan al sistema mediante un **recojo** registrado por el tenant
- El recojo registra qué series fueron retiradas del almacén central de la región
- Al registrarse, las series quedan en estado **Disponible** en el stock general del tenant
- Excepción de implementación: el **stock inicial de técnicos** también crea series, pero nacen en estado **Asignada** y se asignan directamente al técnico sin pasar por el stock general
- El stock inicial se carga una sola vez por tenant; después solo se corrige por edición o por los flujos normales

### 5.2 Selección para Asignación
- El tenant selecciona series del inventario general (solo estado Disponible)
- Las series seleccionadas pasan a estado **Reservada**
- No se escriben las series manualmente en el formulario; se eligen del inventario disponible

### 5.3 Confirmación de Asignación
- El almacén central revisa la solicitud de asignación
- Si confirma: las series pasan a estado **Asignada** y se mueven al stock del técnico
- Si rechaza: las series vuelven a estado **Disponible** en el stock general

### 5.4 Traspaso entre Técnicos
- Un traspaso mueve series de un técnico a otro del mismo tenant
- Las series siguen en estado **Asignada**, solo cambia el técnico propietario
- El total de series del tenant no cambia con traspasos
- No existen traspasos entre tenants

### 5.5 Devolución/Desasignación
- Cuando un técnico devuelve materiales, las series vuelven a estado **Disponible**
- Esto libera la custodia del técnico sobre esas series
- Las series regresan al stock general del tenant

### 5.6 Baja/Recuperación
- Las series pueden darse de baja por avería, migración u otras causas
- Esto registra el fin de vida útil de la serie en el sistema
- La serie no vuelve al stock disponible

## 6. Validaciones

### 6.1 Validación de Formato
- Toda serie debe cumplir el formato de 12 caracteres alfanuméricos (A-Z, 0-9)
- El sistema rechaza series con formato inválido

### 6.2 Validación de Unicidad
- No se puede registrar una serie que ya existe en el sistema
- No se puede asignar una serie que no está disponible

### 6.3 Validación de Estado
- Solo se pueden seleccionar series en estado Disponible para asignación
- No se puede asignar una serie ya asignada a otro técnico
- No se puede traspasar una serie que no está asignada

## 7. Conciliación y Series

### 7.1 Comparación con Reporte de Lari
- En la conciliación, el sistema compara las series asignadas vs las series reportadas por Lari
- Las series ya no reportadas se actualizan a estado instalado automáticamente (liquidación)

### 7.2 Alertas de Discrepancias
- Las diferencias de series se alertan listando cada serie afectada
- Si un técnico está ausente del reporte, se ignora
- Si un material está ausente de un técnico presente en el reporte, se asume en 0

### 7.3 Regla de Prevalencia
- En una conciliación aprobada, el reporte de Lari prevalece sobre el stock del sistema
- Los ajustes requieren aprobación humana; cargar un reporte no modifica stock automáticamente

## 8. Auditoría de Series

- Todo movimiento de serie registra: usuario, fecha, valor anterior y valor nuevo
- No se borran movimientos de series; se corrigen con uno nuevo
- Las series son trazables a través de toda su vida en el sistema

## 9. Seguridad y Aislamiento

- Un tenant nunca ve ni modifica series de otro tenant
- La única excepción es el catálogo de materiales, que es compartido
- El filtrado por tenant se aplica en el backend (y en la base de datos si es posible)
