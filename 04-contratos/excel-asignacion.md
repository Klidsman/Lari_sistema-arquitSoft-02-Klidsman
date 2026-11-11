# Excel de Asignación

Formato y estructura del archivo Excel de asignación generado por el sistema.

## 1. Propósito

El Excel de asignación es el documento estandarizado que el sistema genera automáticamente cuando un tenant crea una solicitud de asignación de materiales a un técnico. Este Excel se envía al almacén central de la región para su confirmación y contiene toda la información necesaria para el despacho físico de los materiales.

## 2. Generación

- El sistema genera el Excel automáticamente al crear una solicitud de asignación
- No se puede editar manualmente el Excel antes de generarlo
- El Excel se guarda de forma inmutable con firma SHA-256 para garantizar su integridad
- El Excel se envía por correo al buzón del almacén de la región, con reintentos si falla

## 3. Estructura del Archivo

El Excel de asignación contiene tres secciones principales:

### 3.1 Metadatos de Cuadrilla

Información general de la asignación y el técnico.

| Campo | Descripción | Valor |
|---|---|---|
| **Movimiento** | Tipo de movimiento SAP | Z31 (asignación - el técnico recibe) |
| **Centro** | Centro de costo | PR05 (parámetro de la región) |
| **Almacén** | Código de almacén | BE03 (parámetro de la región) |
| **NIF** | Identificador del técnico | LAxxxx (completado desde el técnico elegido) |
| **Fecha de solicitud** | Fecha de creación de la solicitud | Fecha actual |
| **Tenant** | Nombre/código del tenant | Completado automáticamente |
| **Región** | Región del tenant | Completado automáticamente |
| **ID de solicitud** | Identificador único de la solicitud | Generado por el sistema |

**Reglas:**
- Movimiento, Centro y Almacén son fijos y se autorrellenan
- El NIF se completa desde el técnico elegido y no es editable
- Centro y Almacén son parámetros de la región; hoy tienen el mismo valor en todas las regiones, pero no están fijados en el código

### 3.2 Tabla de Seriales

Para materiales seriados, cada serie individual se lista en una fila separada.

| Columna | Descripción | Ejemplo |
|---|---|---|
| **Código de material** | Código del material (11 dígitos) | 12345678901 |
| **Descripción** | Descripción del material | Router Huawei |
| **Lote** | Lote del material | LOT-2024-001 |
| **Serie** | Serie individual (12 caracteres) | ABC123456789 |
| **Cantidad** | Cantidad de unidades | 1 (siempre 1 para seriados) |

**Reglas:**
- Cada serie es una fila con Cantidad = 1
- Código, Descripción y Lote se completan desde el catálogo de materiales
- Las series se eligen del inventario general del tenant (solo estado Disponible)
- No se escriben las series manualmente; se seleccionan del inventario disponible

### 3.3 Tabla de Material Menor

Para materiales no seriados, se agrupan por material con la cantidad total.

| Columna | Descripción | Ejemplo |
|---|---|---|
| **Código de material** | Código del material (11 dígitos) | 98765432109 |
| **Descripción** | Descripción del material | Cable coaxial 10m |
| **Lote** | Lote del material | LOT-2024-002 |
| **Cantidad** | Cantidad total de unidades | 50 |

**Reglas:**
- La cantidad es un entero mayor que 0
- No supera el disponible, descontando lo reservado
- Código, Descripción y Lote se completan desde el catálogo de materiales
- La cantidad la digita el tenant

## 4. Campos No Editables

Los siguientes campos se completan automáticamente y **no son editables** por el usuario:
- NIF (se completa desde la lista de técnicos del tenant)
- Movimiento (Z31)
- Centro (PR05)
- Almacén (BE03)
- Código de material
- Descripción
- Lote

## 5. Validaciones del Excel

El sistema valida que:
- Cada serie tenga el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- Las series sean únicas (no haya duplicados)
- Las series estén disponibles en el inventario del tenant
- La cantidad de no seriados no supere el disponible (descontando lo reservado)
- Código, Descripción y Lote coincidan con el catálogo de materiales

## 6. Integridad del Archivo

- El Excel se guarda con una firma SHA-256 para garantizar que no fue alterado
- El hash se registra en el sistema junto con el envío
- El almacén puede verificar el hash del Excel recibido contra el registrado
- Se puede buscar y descargar Excels históricos verificando su hash SHA-256

## 7. Envío al Almacén

- El Excel se envía por correo electrónico al buzón del almacén de la región
- El sistema reintentar el envío si falla
- Cada envío se registra con: destinatario, fecha y archivo exacto enviado
- El almacén puede previsualizar detalles y descargar el Excel original antes de confirmar

## 8. Estados de la Solicitud

La solicitud de asignación (y su Excel asociado) puede estar en los siguientes estados:

| Estado | Descripción |
|---|---|
| **Borrador** | La solicitud está siendo creada, aún no enviada |
| **Enviada** | El Excel ha sido enviado al almacén, espera confirmación |
| **Confirmada** | El almacén confirmó la asignación, el stock se actualizó |
| **Rechazada** | El almacén rechazó la asignación, las series vuelven a Disponible |
| **Cancelada** | El tenant canceló la solicitud antes de confirmación |

## 9. Confirmación del Almacén

- El Responsable de almacén confirma o rechaza la solicitud dentro del sistema
- Puede añadir un comentario del error si se rechaza
- Al confirmar: las series pasan a Asignada al técnico, el stock del técnico sube y el stock general baja
- Al rechazar: las series vuelven a Disponible en el stock general

## 10. Regla de Todo o Nada

- El Excel se aplica completo o no se aplica
- Si hay algún error (serie inválida, duplicada, no disponible, cantidad excesiva), no se guarda ningún recojo
- Nunca quedan asignaciones a medias
