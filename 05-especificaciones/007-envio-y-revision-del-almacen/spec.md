# Spec 007 - Envío y Revisión del Almacén

Especificación técnica para el envío de solicitudes de asignación al almacén y su revisión/confirmación por parte del Responsable de almacén.

## 1. Propósito

Permitir que las solicitudes de asignación creadas por los tenants sean enviadas al almacén central de la región, y que el Responsable de almacén las revise, confirme o rechace. Incluye el envío del Excel por correo, la bandeja de despachos en tiempo real, la previsualización del Excel, y la confirmación/rechazo con comentarios.

## 2. Alcance

- Envío del Excel por correo al buzón del almacén de la región
- Registro de envíos (destinatario, fecha, archivo exacto)
- Bandeja de despachos en tiempo real para el almacén
- Notificaciones sonoras y visuales para el almacén
- Previsualización de detalles y descarga del Excel original
- Confirmación de solicitudes de asignación
- Rechazo de solicitudes con motivo y notificación al tenant
- Búsqueda y descarga de Excels históricos con verificación de hash SHA-256

## 3. Actores

- **Tenant (ACT-01)**: Crea solicitudes (spec 006) y recibe notificaciones de rechazo
- **Responsable de almacén (ACT-03)**: Recibe solicitudes, las revisa, confirma o rechaza
- **Administrador de plataforma (ACT-02)**: Puede buscar y descargar Excels históricos

## 4. Trazabilidad

### Historias de Usuario
- **HU-14** (RF-29, RF-30): Como Almacén, quiero una bandeja de despachos en tiempo real con notificaciones sonoras y visuales, para atender solicitudes inmediatamente
- **HU-15** (RF-28): Como Almacén, quiero previsualizar detalles y descargar el Excel original, para revisar antes de confirmar
- **HU-16** (RF-29, RF-32): Como Almacén, quiero confirmar la asignación
- **HU-17** (RF-29, RF-31): Como Almacén, quiero rechazar o solicitar corrección de una asignación con motivo, notificando al remitente
- **HU-27** (RF-28): Como Administrador de plataforma o Almacén, quiero buscar y descargar Excels históricos verificando su hash SHA-256

### Requisitos Funcionales
- **RF-27**: El Excel se envía por correo al buzón del almacén de la región, con reintentos si falla
- **RF-28**: Registrar cada envío: destinatario, fecha y archivo exacto enviado
- **RF-29**: El Responsable de almacén confirma o rechaza la solicitud dentro del sistema con un comentario del error si se rechaza
- **RF-30**: Estados de la solicitud: Borrador, Enviada, Confirmada, Rechazada, Cancelada
- **RF-31**: Al rechazar, las series vuelven a Disponible

### Atributos de Calidad
- RF-27: Disponibilidad (reintentos si falla el envío)
- RF-28: Trazabilidad (registro de envíos)
- RF-29: Usabilidad (comentarios de rechazo)

## 5. Requisitos Funcionales

### 5.1 Envío por Correo (RF-27)
- El Excel se envía automáticamente al buzón de correo del almacén de la región
- El buzón es un parámetro de la región (configurado en spec 001)
- Si el envío falla, el sistema reintenta automáticamente
- Los reintentos tienen un límite (ej: 3 intentos con intervalo de 5 minutos)
- Si fallan todos los reintentos, se registra el error y se notifica al tenant

### 5.2 Registro de Envíos (RF-28)
- Cada envío se registra con:
  - Destinatario (buzón del almacén)
  - Fecha y hora del envío
  - Archivo exacto enviado (nombre y ruta)
  - Hash SHA-256 del archivo
  - Estado del envío (exitoso, fallido, reintentando)
- El registro es inmutable y auditable

### 5.3 Bandeja de Despachos (RF-29, RF-30)
- El Responsable de almacén tiene una bandeja de despachos en tiempo real
- La bandeja muestra las solicitudes de asignación de su región
- La bandeja se actualiza automáticamente cuando llega una nueva solicitud
- Las solicitudes se pueden filtrar por estado (Enviada, Confirmada, Rechazada)
- La bandeja muestra: fecha, tenant, técnico, total series, total cantidad

### 5.4 Notificaciones en Tiempo Real (HU-14)
- El almacén recibe notificaciones sonoras y visuales cuando llega una nueva solicitud
- Las notificaciones usan WebSocket o Server-Sent Events (SSE)
- Las notificaciones se pueden silenciar temporalmente
- Solo el almacén de la región correspondiente recibe las notificaciones

### 5.5 Previsualización y Descarga (HU-15, RF-28)
- El almacén puede previsualizar los detalles de una solicitud antes de confirmar
- Puede descargar el Excel original desde el sistema
- El sistema verifica el hash SHA-256 del Excel al descargar para garantizar que no fue alterado
- Si el hash no coincide, se alerta que el archivo fue modificado

### 5.6 Confirmación de Solicitud (HU-16, RF-29)
- El Responsable de almacén confirma la solicitud dentro del sistema
- Al confirmar, la solicitud pasa a estado Confirmada
- La confirmación actualiza el stock (spec 008):
  - Las series pasan a Asignada al técnico
  - El stock del técnico sube
  - El stock general baja
- Se inicia el conteo de días en mano para los seriados (RF-61)

### 5.7 Rechazo de Solicitud (HU-17, RF-29, RF-31)
- El Responsable de almacén puede rechazar la solicitud
- El rechazo requiere un comentario explicando el motivo
- Motivos comunes: serie no coincide, cantidad no cuadra, material no disponible
- Al rechazar:
  - La solicitud pasa a estado Rechazada
  - Las series vuelven a estado Disponible
  - El stock general se libera (las cantidades reservadas vuelven a estar disponibles)
- El tenant recibe una notificación del rechazo con el motivo

### 5.8 Estados de Solicitud (RF-30)
- **Borrador:** Solicitud creada pero no enviada
- **Enviada:** Solicitud enviada al almacén, espera confirmación
- **Confirmada:** Solicitud confirmada por el almacén, stock actualizado
- **Rechazada:** Solicitud rechazada por el almacén, series liberadas
- **Cancelada:** Solicitud cancelada por el tenant (solo en borrador)

### 5.9 Búsqueda de Excels Históricos (HU-27, RF-28)
- El Administrador de plataforma y el Almacén pueden buscar Excels históricos
- La búsqueda permite filtrar por: fecha, tenant, técnico, estado
- Al descargar un Excel, el sistema verifica su hash SHA-256
- Si el hash coincide con el registrado, se permite la descarga
- Si el hash no coincide, se alerta que el archivo fue alterado y se bloquea la descarga

## 6. Requisitos No Funcionales

### 6.1 Disponibilidad
- El envío de correos debe ser fiable (reintentos automáticos)
- La bandeja de despachos debe estar siempre disponible
- Las notificaciones en tiempo real deben ser rápidas (< 1 segundo)

### 6.2 Rendimiento
- La bandeja de despachos debe cargar rápidamente
- La previsualización de solicitudes debe ser rápida
- La búsqueda de Excels históricos debe ser eficiente

### 6.3 Usabilidad
- Las notificaciones deben ser claras pero no intrusivas
- El formulario de rechazo debe requerir comentario obligatorio
- La bandeja debe permitir filtrado y ordenamiento

## 7. Criterios de Aceptación

### CA-01: Envío por Correo Exitoso
Dado una solicitud de asignación enviada
Cuando el sistema envía el Excel al almacén
Entonces el correo llega al buzón de la región y se registra el envío

### CA-02: Reintento de Envío
Dado que el envío de correo falla
Cuando el sistema reintenta
Entonces reintenta hasta 3 veces con intervalo de 5 minutos

### CA-03: Registro de Envío Completo
Dado un envío de Excel
Cuando se consulta el registro
Entonces muestra destinatario, fecha, archivo y hash SHA-256

### CA-04: Bandeja de Despachos Muestra Solicitudes de Región
Dado un Responsable de almacén de la región "Ayacucho"
Cuando accede a su bandeja de despachos
Entonces solo ve solicitudes de tenants de Ayacucho

### CA-05: Notificación en Tiempo Real
Dado que llega una nueva solicitud al almacén
Cuando el almacén está en la bandeja
Entonces recibe notificación sonora y visual inmediata

### CA-06: Previsualización de Solicitud
Dado una solicitud en la bandeja
Cuando el almacén previsualiza
Entonces ve detalles y puede descargar el Excel original

### CA-07: Verificación de Hash al Descargar
Dado un Excel histórico
Cuando el almacén lo descarga
Entonces el sistema verifica el hash SHA-256

### CA-08: Confirmación de Solicitud
Dado una solicitud Enviada
Cuando el almacén la confirma
Entonces pasa a Confirmada y se actualiza el stock

### CA-09: Rechazo con Comentario
Dado una solicitud Enviada
Cuando el almacén la rechaza con motivo
Entonces pasa a Rechazada, series vuelven a Disponible y el tenant es notificado

### CA-10: Comentario Obligatorio al Rechazar
Dado que el almacén intenta rechazar sin comentario
Cuando el sistema valida
Entonces rechaza la acción y exige un comentario

### CA-11: Búsqueda de Excels Históricos
Dado que el Administrador busca Excels por fecha
Cuando ejecuta la búsqueda
Entonces devuelve los Excels de esa fecha con sus hashes

### CA-12: Hash No Coincide Bloquea Descarga
Dado un Excel modificado (hash alterado)
Cuando se intenta descargar
Entonces el sistema alerta y bloquea la descarga

## 8. Datos de Entrada

### Formulario de Confirmación/Rechazo

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Solicitud | Read-only | Sí | Solicitud a confirmar/rechazar |
| Acción | Select | Sí | Confirmar o Rechazar |
| Comentario | Textarea | Condicional | Motivo del rechazo (obligatorio si Rechazar) |

### Filtros de Búsqueda

| Campo | Tipo | Descripción |
|---|---|---|
| Fecha desde | Date | Fecha inicial del rango |
| Fecha hasta | Date | Fecha final del rango |
| Tenant | Select | Tenant específico |
| Técnico | Select | Técnico específico |
| Estado | Select | Estado de la solicitud |

## 9. Datos de Salida

### Registro de Envío

| Campo | Descripción |
|---|---|
| ID de envío | Identificador único del envío |
| Solicitud | Solicitud asociada |
| Destinatario | Buzón de correo del almacén |
| Fecha envío | Fecha y hora del envío |
| Archivo | Nombre y ruta del archivo enviado |
| Hash SHA-256 | Firma del archivo |
| Estado | Exitoso, Fallido, Reintentando |
| Reintentos | Número de reintentos realizados |

### Bandeja de Despachos

| Campo | Descripción |
|---|---|
| ID de solicitud | Identificador de la solicitud |
| Fecha | Fecha de creación |
| Tenant | Tenant que creó la solicitud |
| Técnico | Técnico destinatario |
| Total series | Número de series |
| Total cantidad | Suma de cantidades |
| Estado | Estado actual |
| Acciones | Confirmar, Rechazar, Previsualizar |

## 10. Reglas de Negocio

1. El Excel se envía al buzón del almacén de la región
2. El envío tiene reintentos automáticos si falla
3. Cada envío se registra con todos los detalles
4. El almacén solo ve solicitudes de su región
5. El almacén recibe notificaciones en tiempo real
6. Al confirmar, la solicitud pasa a Confirmada y se actualiza el stock
7. Al rechazar, se requiere comentario obligatorio
8. Al rechazar, las series vuelven a Disponible
9. El hash SHA-256 se verifica al descargar Excels históricos
10. Si el hash no coincide, se bloquea la descarga

## 11. Consideraciones de Implementación

- El envío de correos se implementa con Celery + Redis para procesamiento asíncrono
- Las notificaciones en tiempo real usan SSE sobre `StreamingHttpResponse` con pub/sub de Redis (ver `plan.md` y `research.md`)
- La verificación de hash SHA-256 se hace al descargar el archivo
- La actualización de stock al confirmar se implementa en spec 008
- El conteo de días en mano se inicia al confirmar (RF-61)
- El buzón del almacén es un parámetro de la región (configurado en spec 001)
- Los reintentos de correo son 3 reintentos además del intento inicial (4 intentos en total), con intervalo fijo de 5 minutos y sin backoff exponencial
- La bandeja de despachos usa polling o push para actualizaciones en tiempo real
