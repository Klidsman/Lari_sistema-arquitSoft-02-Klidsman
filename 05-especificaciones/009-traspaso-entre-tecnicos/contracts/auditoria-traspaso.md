# Contrato: auditoría de 009

Toda operación de 009 se audita con `auditoria.services.registrar_cambio` en la misma transacción.
La auditoría es inmutable y compartida con el resto del sistema; 009 no crea un modelo propio.

## Eventos obligatorios

### Alta de solicitud

| Campo | Valor |
|---|---|
| Entidad | `SolicitudTraspaso` |
| ID entidad | `solicitud.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | `BORRADOR` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Tenant, región, técnico origen, técnico destino, fecha |

### Alta y baja de líneas

| Campo | Valor |
|---|---|
| Entidad | `LineaTraspaso` |
| ID entidad | `linea.id` |
| Campo | `alta` o `baja` |
| Valor anterior | vacío o datos de la línea |
| Valor nuevo | datos de la línea o vacío |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Material, lote, serie o cantidad |

Se escribe un registro por línea creada o eliminada.

### Envío

| Campo | Valor |
|---|---|
| Entidad | `SolicitudTraspaso` |
| ID entidad | `solicitud.id` |
| Campo | `estado` |
| Valor anterior | `BORRADOR` |
| Valor nuevo | `ENVIADA` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | `enviada_en` |

Además, al guardar el Excel:

| Campo | Valor |
|---|---|
| Entidad | `SolicitudTraspaso` |
| ID entidad | `solicitud.id` |
| Campo | `excel` |
| Valor anterior | vacío |
| Valor nuevo | ruta relativa y hash |
| Actor | `USUARIO_TENANT` de la sesión |

No se audita el contenido binario del archivo.

### Confirmación

| Campo | Valor |
|---|---|
| Entidad | `SolicitudTraspaso` |
| ID entidad | `solicitud.id` |
| Campo | `estado` |
| Valor anterior | `ENVIADA` |
| Valor nuevo | `CONFIRMADA` |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |
| Extra | `confirmada_en` |

Por cada serie:

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `tecnico` |
| Valor anterior | `tecnico_origen.id` |
| Valor nuevo | `tecnico_destino.id` |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |

Y por cada serie, para reiniciar días en mano:

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `asignada_en` |
| Valor anterior | fecha anterior |
| Valor nuevo | fecha de confirmación del traspaso |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |

Los cambios de `StockTecnico/cantidad` de origen y destino los escribe 008 al usar sus servicios; 009
no los duplica.

### Rechazo

| Campo | Valor |
|---|---|
| Entidad | `SolicitudTraspaso` |
| ID entidad | `solicitud.id` |
| Campo | `estado` |
| Valor anterior | `ENVIADA` |
| Valor nuevo | `RECHAZADA` |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |
| Extra | `rechazada_en`, `motivo_rechazo` |

Además:

| Campo | Valor |
|---|---|
| Entidad | `SolicitudTraspaso` |
| ID entidad | `solicitud.id` |
| Campo | `motivo_rechazo` |
| Valor anterior | vacío |
| Valor nuevo | comentario |
| Actor | `RESPONSABLE_ALMACEN` de la sesión |

No se audita ningún cambio de serie ni de stock porque no ocurre.

### Cancelación

| Campo | Valor |
|---|---|
| Entidad | `SolicitudTraspaso` |
| ID entidad | `solicitud.id` |
| Campo | `estado` |
| Valor anterior | `BORRADOR` |
| Valor nuevo | `CANCELADA` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | `cancelada_en` |

No hay series reservadas ni stock que auditar.

## Reglas

- La auditoría es síncrona y transaccional: si falla, se revierte la operación completa.
- El valor anterior se toma de la fila bajo bloqueo.
- El actor es siempre el usuario de la sesión; nunca `None` ni un usuario inventado.
- Los registros son inmutables: no se editan ni se eliminan desde 009.
- No se auditan contraseñas, tokens, secretos TOTP, credenciales, cuerpos de correo, contenido
  binario del Excel, rutas absolutas ni datos de otro tenant.
- La auditoría no sustituye al dato: `SolicitudTraspaso.estado`, `Serie.tecnico` y
  `StockTecnico.cantidad` siguen siendo la fuente actual.

## Eventos de otras specs que no se duplican

| Evento | Dueño |
|---|---|
| `SolicitudAsignacion/estado` y `confirmada_en` | 007 |
| `Serie/estado` al confirmar una asignación | 008 |
| `StockGeneral/cantidad` | 004/008/011 |
| `StockTecnico/cantidad` por asignación o stock inicial | 008/005 |
| Devolución y baja de series | 011 |
| Conciliación | 010 |

## Consulta

- La auditoría se consulta con las vistas de 001 según el rol.
- 009 no crea una pantalla de auditoría propia.
- El almacén ve la auditoría de su región; el tenant, la de su tenant.

## Pruebas de contrato

- Crear produce un alta de solicitud y una por línea.
- Editar un borrador produce bajas y altas de líneas.
- Enviar produce `BORRADOR→ENVIADA` y un registro de Excel con ruta relativa y hash.
- Confirmar produce `ENVIADA→CONFIRMADA`, un `Serie/tecnico` y un `Serie/asignada_en` por serie.
- Los `StockTecnico/cantidad` aparecen una sola vez y son los de 008.
- Rechazar produce `ENVIADA→RECHAZADA` y el motivo, sin eventos de serie ni stock.
- Cancelar produce `BORRADOR→CANCELADA`, sin eventos de serie ni stock.
- Ningún registro contiene secretos, binarios, rutas absolutas ni datos de otro tenant.
- Si la auditoría falla, la operación se revierte completa.
