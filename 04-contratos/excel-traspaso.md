# Excel de Traspaso

Formato y estructura del archivo Excel de traspaso generado por el sistema.

## 1. Propósito

El Excel de traspaso es el documento estandarizado que el sistema genera automáticamente cuando un tenant crea una solicitud de traspaso de materiales entre técnicos. Este Excel tiene dos hojas: Desasignación (Z32) para el técnico origen y Asignación (Z31) para el técnico destino.

## 2. Generación

- El sistema genera el Excel automáticamente al crear una solicitud de traspaso
- No se puede editar manualmente el Excel antes de generarlo
- El Excel se guarda de forma inmutable con firma SHA-256 para garantizar su integridad
- El Excel se envía por correo al buzón del almacén de la región, con reintentos si falla

## 3. Estructura del Archivo

El Excel de traspaso contiene dos hojas principales:

### 3.1 Hoja 1: Desasignación (Z32)

Esta hoja representa el técnico origen (el que cede los materiales).

#### Metadatos de Cuadrilla

| Campo | Descripción | Valor |
|---|---|---|
| **Movimiento** | Tipo de movimiento SAP | Z32 (desasignación - el técnico cede) |
| **Centro** | Centro de costo | PR05 (parámetro de la región) |
| **Almacén** | Código de almacén | BE03 (parámetro de la región) |
| **NIF** | Identificador del técnico origen | LAxxxx (completado desde el técnico origen) |
| **Fecha de solicitud** | Fecha de creación de la solicitud | Fecha actual |
| **Tenant** | Nombre/código del tenant | Completado automáticamente |
| **Región** | Región del tenant | Completado automáticamente |
| **ID de solicitud** | Identificador único de la solicitud | Generado por el sistema |

#### Tabla de Seriales

Para materiales seriados, cada serie individual se lista en una fila separada.

| Columna | Descripción | Ejemplo |
|---|---|---|
| **Código de material** | Código del material (11 dígitos) | 12345678901 |
| **Descripción** | Descripción del material | Router Huawei |
| **Lote** | Lote del material | LOT-2024-001 |
| **Serie** | Serie individual (12 caracteres) | ABC123456789 |
| **Cantidad** | Cantidad de unidades | 1 (siempre 1 para seriados) |

#### Tabla de Material Menor

Para materiales no seriados, se agrupan por material con la cantidad total.

| Columna | Descripción | Ejemplo |
|---|---|---|
| **Código de material** | Código del material (11 dígitos) | 98765432109 |
| **Descripción** | Descripción del material | Cable coaxial 10m |
| **Lote** | Lote del material | LOT-2024-002 |
| **Cantidad** | Cantidad total de unidades | 50 |

### 3.2 Hoja 2: Asignación (Z31)

Esta hoja representa el técnico destino (el que recibe los materiales).

#### Metadatos de Cuadrilla

| Campo | Descripción | Valor |
|---|---|---|
| **Movimiento** | Tipo de movimiento SAP | Z31 (asignación - el técnico recibe) |
| **Centro** | Centro de costo | PR05 (parámetro de la región) |
| **Almacén** | Código de almacén | BE03 (parámetro de la región) |
| **NIF** | Identificador del técnico destino | LAxxxx (completado desde el técnico destino) |
| **Fecha de solicitud** | Fecha de creación de la solicitud | Fecha actual |
| **Tenant** | Nombre/código del tenant | Completado automáticamente |
| **Región** | Región del tenant | Completado automáticamente |
| **ID de solicitud** | Identificador único de la solicitud | Generado por el sistema |

#### Tabla de Seriales

Idéntica a la hoja de Desasignación, pero representa las series que el técnico destino recibirá.

#### Tabla de Material Menor

Idéntica a la hoja de Desasignación, pero representa las cantidades que el técnico destino recibirá.

## 4. Campos No Editables

Los siguientes campos se completan automáticamente y **no son editables** por el usuario:
- NIF (origen y destino) - se completan desde los técnicos elegidos
- Movimiento (Z32 en hoja 1, Z31 en hoja 2)
- Centro (PR05)
- Almacén (BE03)
- Código de material
- Descripción
- Lote

## 5. Validaciones del Excel

El sistema valida que:
- Cada serie tenga el formato correcto (12 caracteres alfanuméricos A-Z, 0-9)
- Las series sean únicas (no haya duplicados)
- Las series estén disponibles en el técnico origen
- Código, Descripción y Lote coincidan con el catálogo de materiales
- La cantidad de no seriados no supere el disponible del técnico origen
- Lo que sale del técnico origen debe cuadrar con lo que entra al técnico destino (por material y por serie)

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

La solicitud de traspaso (y su Excel asociado) puede estar en los siguientes estados:

| Estado | Descripción |
|---|---|
| **Borrador** | La solicitud está siendo creada, aún no enviada |
| **Enviada** | El Excel ha sido enviado al almacén, espera confirmación |
| **Confirmada** | El almacén confirmó el traspaso, las series cambiaron de técnico |
| **Rechazada** | El almacén rechazó el traspaso, no hubo cambios |
| **Cancelada** | El tenant canceló la solicitud antes de confirmación |

## 9. Confirmación del Almacén

- El Responsable de almacén confirma o rechaza la solicitud dentro del sistema
- Puede añadir un comentario del error si se rechaza
- Al confirmar: las series cambian de técnico (origen → destino)
- Al rechazar: no cambia nada, las series siguen en el técnico origen

## 10. Regla de Todo o Nada

- El Excel se aplica completo o no se aplica
- Si hay algún error (serie inválida, duplicada, no disponible, cantidad excesiva, no cuadra), no se guarda ningún traspaso
- Nunca quedan traspasos a medias
