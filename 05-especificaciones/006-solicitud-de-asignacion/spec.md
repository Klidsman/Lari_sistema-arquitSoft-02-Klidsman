# Spec 006 - Solicitud de Asignación

Especificación técnica para la creación de solicitudes de asignación de materiales a técnicos.

## 1. Propósito

Permitir que los tenants creen solicitudes de asignación de materiales a sus técnicos. Las solicitudes incluyen materiales seriados (series específicas) y no seriados (cantidades), se validan contra el stock disponible, generan un Excel estandarizado y pasan las series a estado Reservado hasta la confirmación del almacén.

## 2. Alcance

- Creación de solicitudes de asignación por técnico
- Selección de series disponibles del inventario general
- Ingreso de cantidades para materiales no seriados
- Validación de disponibilidad (descontando lo reservado)
- Generación automática de Excel de asignación (ver `04-contratos/excel-asignacion.md`)
- Cambio de estado de series a Reservada
- Envío del Excel al almacén central
- Cálculo de días en mano para seriados (al confirmar)
- Alerta de cupo máximo de equipos

## 3. Actores

- **Tenant (ACT-01)**: Crea solicitudes de asignación a sus técnicos
- **Almacén (ACT-03)**: Recibe y confirma las solicitudes (spec 007)

## 4. Trazabilidad

### Historias de Usuario
- **HU-08** (RF-21, RF-22, RF-23): Como tenant, quiero armar una asignación con equipos serializados específicos y material fungible, validando existencia en stock
- **HU-09** (RF-63): Como tenant, quiero ser alertado si un técnico supera su cupo máximo de equipos sin liquidar
- **HU-10** (RF-25): Como tenant, quiero que el sistema genere automáticamente el Excel estandarizado de despacho
- **HU-11** (RF-21): Como tenant, quiero asignar materiales a mis técnicos
- **HU-12** (RF-28): Como tenant, quiero que el Excel se guarde de forma inmutable con firma SHA-256
- **HU-13** (RF-61): Como tenant, quiero ver los días en mano que tiene un equipo seriado

### Requisitos Funcionales
- **RF-21**: Crear una solicitud de asignación por técnico, con líneas de material
- **RF-22**: En seriados, el tenant elige series Disponibles de su inventario. Cada serie es una fila con cantidad 1
- **RF-23**: En no seriados, la cantidad es un entero mayor que 0 y no supera el disponible, descontando lo reservado
- **RF-24**: Al enviar la solicitud, sus series y cantidades pasan a Reservada
- **RF-25**: El sistema genera el Excel de asignación con Movimiento Z31, Centro PR05 y Almacén BE03 autocompletados
- **RF-26**: El NIF se completa desde el técnico elegido y no es editable
- **RF-61**: Una vez aceptado la asignación, inicia a contar los días de seriados en mano de cada técnico
- **RF-63**: Para equipos seriados que tengan 20 días en mano de un técnico, el sistema debe emitir una alerta

### Atributos de Calidad
- RF-23: Usabilidad (validación de disponibilidad en tiempo real)
- RF-25: Compatibilidad (Excel estandarizado)
- RF-28: Integridad (firma SHA-256)

## 5. Requisitos Funcionales

### 5.1 Creación por Técnico (RF-21)
- Cada solicitud de asignación pertenece a un solo técnico
- El usuario selecciona el técnico de la lista del tenant
- La solicitud puede tener múltiples líneas de material
- Cada línea puede ser seriada o no seriada

### 5.2 Selección de Series (RF-22)
- Para materiales seriados, el tenant elige series del inventario general del tenant
- Solo se muestran series en estado Disponible
- Cada serie seleccionada es una fila con cantidad 1
- No se escriben las series manualmente; se seleccionan del inventario disponible
- El selector permite búsqueda por serie o material

### 5.3 Ingreso de Cantidades (RF-23)
- Para materiales no seriados, el tenant ingresa la cantidad
- La cantidad debe ser un entero mayor que 0
- La cantidad no puede superar el disponible en stock general
- La disponibilidad se calcula descontando lo reservado en asignaciones pendientes
- Fórmula: `Disponible = Stock General - Reservado`

### 5.4 Reserva al Enviar (RF-24)
- Al enviar la solicitud, las series seleccionadas pasan a estado Reservada
- Las cantidades de no seriados se reservan del stock general
- Mientras está Reservada, la serie no puede ser seleccionada en otra asignación
- Si el almacén rechaza la asignación, las series vuelven a Disponible

### 5.5 Generación de Excel (RF-25)
- El sistema genera automáticamente el Excel de asignación al crear la solicitud
- El Excel tiene el formato definido en `04-contratos/excel-asignacion.md`
- Metadatos autocompletados: Movimiento Z31, Centro PR05, Almacén BE03
- El Excel se guarda con firma SHA-256 para garantizar integridad
- El Excel se envía por correo al buzón del almacén de la región

### 5.6 NIF Autocompletado (RF-26)
- El NIF del técnico se completa desde el técnico elegido
- El NIF no es editable en el formulario
- El NIF se copia al Excel de asignación

### 5.7 Cálculo de Días en Mano (RF-61)
- Una vez aceptada la asignación (por el almacén), inicia el conteo de días en mano
- Los días en mano se calculan desde la fecha de aceptación hasta la fecha actual o de devolución
- Este dato es informativo para el control de custodia
- Se muestra en el detalle del técnico y en reportes

### 5.8 Alerta de Cupo Máximo (RF-63)
- Para equipos seriados, el sistema emite una alerta si un técnico supera 20 días en mano
- La alerta se muestra al tenant cuando intenta crear una nueva asignación
- La alerta no bloquea la asignación, solo informa
- El propósito es cumplir la política de custodia de equipos

## 6. Requisitos No Funcionales

### 6.1 Rendimiento
- La validación de disponibilidad debe ser rápida (< 1 segundo)
- La generación del Excel debe ser eficiente
- El selector de series debe cargar y filtrar rápidamente

### 6.2 Usabilidad
- El selector de series debe permitir búsqueda y filtrado
- Los errores de validación deben ser claros y específicos
- La alerta de cupo máximo debe ser visible pero no intrusiva

### 6.3 Integridad
- La generación del Excel debe incluir firma SHA-256
- La reserva de series debe ser transaccional
- No se pueden asignar series que no están disponibles

## 7. Criterios de Aceptación

### CA-01: Creación de Solicitud Válida
Dado un técnico y materiales disponibles
Cuando el tenant crea una solicitud de asignación
Entonces la solicitud se crea, las series pasan a Reservada y se genera el Excel

### CA-02: Selección de Series Disponibles
Dado el inventario general del tenant
Cuando el tenant selecciona series para asignación
Entonces solo se muestran series en estado Disponible

### CA-03: Validación de Cantidad No Supera Disponible
Dado un material no seriado con stock disponible de 50
Cuando el tenant intenta asignar 60 unidades
Entonces el sistema rechaza la asignación y muestra el error

### CA-04: Cantidad Descontando Reservado
Dado un material con stock general de 50 y 20 reservados
Cuando el tenant intenta asignar
Entonces el disponible es 30 y no se puede asignar más de 30

### CA-05: Series Pasan a Reservada
Dado una solicitud de asignación creada
Cuando se consulta el estado de las series
Entonces las series están en estado Reservada

### CA-06: Generación de Excel Correcto
Dado una solicitud de asignación creada
Cuando se consulta el Excel generado
Entonces tiene los metadatos Z31, PR05, BE03 y el NIF correcto

### CA-07: NIF Autocompletado No Editable
Dado un técnico seleccionado en el formulario
Cuando el usuario intenta editar el NIF
Entonces el campo es de solo lectura

### CA-08: Días en Mano Inician al Aceptar
Dado una asignación aceptada por el almacén
Cuando se consulta los días en mano de las series
Entonces se cuentan desde la fecha de aceptación

### CA-09: Alerta de Cupo Máximo
Dado un técnico con 25 días en mano de equipos seriados
Cuando el tenant intenta crear una nueva asignación
Entonces el sistema muestra una alerta de cupo máximo

### CA-10: Serie No Disponible No Se Puede Asignar
Dado una serie en estado Asignada
Cuando el tenant intenta seleccionarla para asignación
Entonces la serie no aparece en el selector

### CA-11: Serie Reservada No Se Puede Asignar
Dado una serie en estado Reservada en otra asignación
Cuando el tenant intenta seleccionarla para asignación
Entonces la serie no aparece en el selector

## 8. Datos de Entrada

### Formulario de Solicitud de Asignación

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Técnico | Select | Sí | Técnico del tenant (solo activos) |
| Fecha | Date | Sí | Fecha de la solicitud (por defecto: hoy) |
| Material | Select | Condicional | Material del catálogo (por línea) |
| Tipo de material | Read-only | Condicional | Seriado o no seriado (del catálogo) |
| Lote | Read-only | Condicional | Lote del material (del catálogo) |
| Series | Multi-select | Condicional | Series disponibles (solo para seriados) |
| Cantidad | Number | Condicional | Cantidad (solo para no seriados) |

## 9. Datos de Salida

### Solicitud de Asignación

| Campo | Descripción |
|---|---|
| ID de solicitud | Identificador único de la solicitud |
| Estado | Borrador, Enviada, Confirmada, Rechazada, Cancelada |
| Técnico | Técnico destinatario |
| NIF | NIF del técnico |
| Fecha | Fecha de creación |
| Líneas | Lista de materiales, series o cantidades |
| Excel | Ruta del archivo Excel generado |
| Hash SHA-256 | Firma del Excel |

## 10. Reglas de Negocio

1. Una solicitud de asignación pertenece a un solo técnico
2. Solo se pueden seleccionar series en estado Disponible
3. La cantidad no puede superar el disponible (descontando lo reservado)
4. Al enviar, las series pasan a Reservada
5. El Excel se genera automáticamente con metadatos fijos
6. El NIF se autocompleta y no es editable
7. Los días en mano inician al aceptar la asignación
8. Se alerta si el técnico supera 20 días en mano de seriados

## 11. Consideraciones de Implementación

- La validación de disponibilidad debe ser eficiente (consultar índices de stock y series)
- La generación del Excel debe usar openpyxl y calcular el hash SHA-256
- La reserva de series debe ser transaccional
- El selector de series debe soportar búsqueda y paginación para grandes volúmenes
- El cálculo de días en mano se hace al confirmar la asignación (spec 007)
- La alerta de cupo máximo se calcula sumando días en mano de todos los seriados del técnico
- El envío del Excel por correo se implementa en spec 007
