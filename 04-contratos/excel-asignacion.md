# Excel de Asignación

Formato y estructura del archivo Excel de asignación generado por el sistema.

## 1. Propósito

El Excel de asignación es el documento estandarizado que el sistema genera automáticamente cuando un tenant envía una solicitud de asignación de materiales a uno o más técnicos. Este Excel se envía al almacén central de la región para su confirmación y contiene toda la información necesaria para el despacho físico de los materiales.

## 2. Generación

- El sistema genera el Excel automáticamente al enviar la solicitud (`BORRADOR → ENVIADA`)
- No se puede editar manualmente el Excel antes de generarlo
- Un único Excel por solicitud, aunque incluya varios técnicos
- El Excel se guarda de forma inmutable con firma SHA-256 para garantizar su integridad
- El Excel se envía por correo al buzón del almacén de la región, con reintentos si falla
- El tenant puede descargar el Excel desde el detalle de la solicitud, verificando su hash

## 3. Estructura del Archivo

El Excel de asignación es una **única tabla** con una hoja. Cada fila es una unidad seriada o una línea de material no seriado de un técnico.

| Columna | Descripción | Valor |
|---|---|---|
| **Movimiento** | Tipo de movimiento SAP | `Z31` (asignación: el técnico recibe) |
| **Centro** | Centro de costo | Parámetro de la región (hoy `PR05`) |
| **Almacén** | Código de almacén | Parámetro de la región (hoy `BE03`) |
| **Material** | Código del material (11 dígitos) | Del catálogo |
| **Descripción de materiales** | Descripción del material | Del catálogo |
| **Cantidad** | Unidades de la fila | `1` para seriados; cantidad total para no seriados |
| **NIF Técnico** | Identificador del técnico de la fila | `LAxxxx`, completado desde el técnico elegido |
| **Lote** | Lote del material | Del catálogo |
| **Serie** | Serie individual (12 caracteres) | Vacía para no seriados |

**Reglas:**

- Movimiento, Centro y Almacén son fijos y se autorrellenan; Centro y Almacén son parámetros de la región y no están fijados en el código
- Cada serie seleccionada es una fila con Cantidad = 1 y su Serie
- Cada material no seriado de un técnico es una fila con su cantidad total
- Las filas siguen el **orden de captura**: el orden en que se agregaron las líneas a la solicitud, sin reordenar por técnico ni por material
- Un mismo material puede aparecer para varios técnicos; cada técnico tiene sus propias filas
- Código, Descripción y Lote se completan desde el catálogo de materiales
- Las series se eligen del inventario general del tenant (solo estado Disponible)
- No se escriben series ni NIF manualmente

## 4. Campos No Editables

Los siguientes campos se completan automáticamente y **no son editables** por el usuario:
- NIF Técnico (se completa desde la lista de técnicos del tenant)
- Movimiento (Z31)
- Centro y Almacén (parámetros de la región)
- Material, Descripción de materiales y Lote

## 5. Validaciones del Excel

El sistema valida que:
- Cada serie tenga el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- Las series sean únicas en la solicitud, aunque se asignen a técnicos distintos
- Las series estén disponibles en el inventario del tenant
- La suma de cantidades de no seriados de un material, entre todos los técnicos de la solicitud, no supere el disponible (descontando lo reservado)
- Código, Descripción y Lote coincidan con el catálogo de materiales
- Cada técnico pertenezca al tenant y esté activo

## 6. Integridad del Archivo

- El Excel se guarda con una firma SHA-256 para garantizar que no fue alterado
- El hash se registra en el sistema junto con el envío
- El almacén puede verificar el hash del Excel recibido contra el registrado
- El tenant puede descargar el Excel de sus solicitudes verificando el hash; si no coincide, la descarga se bloquea
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

- El Responsable de almacén confirma o rechaza la solicitud completa dentro del sistema
- Puede añadir un comentario del error si se rechaza
- Al confirmar: cada serie pasa a Asignada a su técnico de la línea, el stock de cada técnico sube y el stock general baja
- Al rechazar: las series vuelven a Disponible en el stock general

## 10. Regla de Todo o Nada

- El Excel se aplica completo o no se aplica
- Si hay algún error (serie inválida, duplicada, no disponible, cantidad excesiva), no se guarda ninguna asignación
- Nunca quedan asignaciones a medias, ni entre técnicos de la misma solicitud
