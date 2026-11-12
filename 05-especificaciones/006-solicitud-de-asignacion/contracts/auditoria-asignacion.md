# Contrato de auditoría de asignaciones

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

Contrato de los registros que 006 escribe en `auditoria.RegistroCambio`. La auditoría es inmutable,
se escribe en la misma transacción que el cambio y usa `auditoria.services.registrar_cambio` de la
spec 001. 006 no crea una tabla de auditoría propia.

## Reglas generales

- Cada alta, cambio de estado y reserva de serie produce al menos un registro.
- Si la operación falla, no se escribe auditoría; si la auditoría falla, se revierte la operación.
- El actor es siempre `request.usuario`; nunca se acepta `creado_por` ni `usuario_id` del cliente.
- El tenant se deduce del actor y de la entidad auditada; no se guarda un `tenant_id` separado.
- `valor_anterior` y `valor_nuevo` son texto o JSON serializado estable, sin objetos de modelo.
- No se auditan contraseñas, tokens, secretos TOTP ni `token_hash`.
- No se audita el contenido binario del Excel; solo ruta relativa y hash.
- La auditoría de movimientos de stock es responsabilidad de 008; 006 no la duplica.
- Los registros de un tenant no son visibles para otro tenant.

## Eventos de 006

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Alta de solicitud | `SolicitudAsignacion` | `alta` | — | `{"fecha", "tecnico_nif", "estado": "BORRADOR", "total_lineas", "total_series", "total_cantidad"}` |
| Alta de línea seriada | `LineaAsignacion` | `alta` | — | `{"material_codigo", "lote", "serie", "cantidad": 1}` |
| Alta de línea no seriada | `LineaAsignacion` | `alta` | — | `{"material_codigo", "lote", "serie": null, "cantidad"}` |
| Envío | `SolicitudAsignacion` | `estado` | `BORRADOR` | `{"estado": "ENVIADA", "total_lineas", "total_series", "total_cantidad", "excel_hash"}` |
| Reserva de serie | `Serie` | `estado` | `DISPONIBLE` | `RESERVADA` |
| Generación de Excel | `SolicitudAsignacion` | `excel` | — | `{"ruta": "<ruta relativa>", "hash": "<sha256>"}` |
| Cancelación | `SolicitudAsignacion` | `estado` | `BORRADOR` | `CANCELADA` |

- El alta de la solicitud se registra una vez; las líneas se registran una por una.
- El alta incluye el NIF del técnico, nunca datos personales adicionales.
- El envío incluye los totales y el hash para vincular el estado con el documento.
- La reserva de serie se registra una vez por serie y por solicitud.
- La generación de Excel puede registrarse en el mismo evento de envío o como evento separado; en
  ambos casos el hash debe quedar registrado antes del commit.
- La cancelación no registra liberación de series ni cantidades porque el borrador no reservó.

## Eventos de 007/008 (contrato de integración)

006 no los implementa, pero deja el modelo preparado para que 007 los escriba:

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Confirmación | `SolicitudAsignacion` | `estado` | `ENVIADA` | `CONFIRMADA` |
| Rechazo | `SolicitudAsignacion` | `estado` | `ENVIADA` | `RECHAZADA` |
| Serie al confirmar | `Serie` | `estado` | `RESERVADA` | `ASIGNADA` |
| Serie al rechazar | `Serie` | `estado` | `RESERVADA` | `DISPONIBLE` |
| Movimiento de stock | `StockGeneral` / `StockTecnico` | `cantidad` | anterior | nueva |

- La confirmación fija `SolicitudAsignacion.confirmada_en`, que 006 usa para días en mano.
- La auditoría de stock la escribe 008 con sus propios servicios.
- 006 no duplica estos eventos ni los simula en producción.

## Datos prohibidos

| Dato | Motivo |
|---|---|
| Contraseña o hash de contraseña | Secreto |
| Token de sesión o `token_hash` | Secreto |
| Secreto TOTP o código de recuperación | Secreto |
| Contenido binario del Excel | Tamaño y exposición innecesaria |
| Datos de otro tenant | Aislamiento |
| Ruta absoluta del archivo | Expone el sistema de archivos |
| `tenant_id` como campo separado | El tenant se deduce de la entidad |

## Verificación en pruebas

- El alta de la solicitud y de cada línea deja registros con el actor correcto.
- El envío deja un registro de estado y un registro de reserva por serie.
- El hash auditado coincide con `SolicitudAsignacion.excel_hash`.
- La cancelación deja un registro `BORRADOR→CANCELADA`.
- Un envío fallido no deja registros de estado, reserva ni Excel.
- Ningún registro contiene contraseñas, tokens, secretos TOTP ni contenido del Excel.
- Ningún registro contiene `tenant_id` separado ni datos de otro tenant.
- La auditoría se conserva al desactivar la cuenta o suspender el tenant.
