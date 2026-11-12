# Contrato: auditoría de stock y series de 008

Toda escritura de 008 se audita con `auditoria.services.registrar_cambio` en la misma transacción.
La auditoría es inmutable y compartida con el resto del sistema; 008 no crea un modelo propio.

## Eventos obligatorios

### Serie asignada

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `estado` |
| Valor anterior | `RESERVADA` |
| Valor nuevo | `ASIGNADA` |
| Actor | Usuario de la sesión que confirma (007) |
| Momento | Dentro de la transacción de confirmación |
| Extra | Material y técnico de la solicitud, para trazabilidad legible |

Se escribe **un registro por cada serie** confirmada.

### Stock del técnico

| Campo | Valor |
|---|---|
| Entidad | `StockTecnico` |
| ID entidad | `stock_tecnico.id` |
| Campo | `cantidad` |
| Valor anterior | Cantidad antes de la confirmación |
| Valor nuevo | Cantidad después de la confirmación |
| Actor | Usuario de la sesión que confirma |
| Momento | Dentro de la transacción de confirmación |
| Extra | `tecnico_id`, `material_id` y cantidad agregada |

Se escribe **un registro por material agregado**, no uno por línea ni por serie.

### Stock general

| Campo | Valor |
|---|---|
| Entidad | `StockGeneral` |
| ID entidad | `stock_general.id` |
| Campo | `cantidad` |
| Valor anterior | Cantidad antes de la confirmación |
| Valor nuevo | Cantidad después de la confirmación |
| Actor | Usuario de la sesión que confirma |
| Momento | Dentro de la transacción de confirmación |
| Extra | `material_id` y cantidad agregada |

Se escribe **un registro por material agregado**.

## Eventos de otras specs que usan el mismo modelo

| Evento | Dueño | Entidad / campo |
|---|---|---|
| Recojo registrado | 004 | `StockGeneral/cantidad` |
| Stock inicial de técnico | 005 | `StockTecnico/cantidad` |
| Confirmación de solicitud | 007 | `SolicitudAsignacion/estado`, `confirmada_en` |
| Rechazo y liberación de series | 007 | `SolicitudAsignacion/estado`, `Serie/estado` |
| Traspaso entre técnicos | 009 | `StockTecnico/cantidad` (origen y destino) |
| Conciliación aprobada | 010 | Ajuste auditado de stock |
| Devolución | 011 | `StockGeneral/cantidad`, `StockTecnico/cantidad`, `Serie/estado` |

008 no duplica ninguno de estos eventos.

## Reglas

- La auditoría de la confirmación es **síncrona y transaccional**: si falla, se revierte la
  confirmación completa (series, stock general, stock técnico y solicitud).
- El actor es siempre el usuario autenticado de la sesión que confirma; nunca un usuario inventado
  por el sistema ni un `actor=None` en la confirmación.
- El valor anterior se toma de la fila **bajo bloqueo**, no de una lectura previa sin bloqueo.
- El valor nuevo coincide con el `ResultadoConfirmacionStock` devuelto.
- Los registros son inmutables: no se editan ni se eliminan desde 008.
- La auditoría no sustituye al dato: `StockGeneral.cantidad` y `StockTecnico.cantidad` siguen siendo
  la fuente del stock actual.

## Prohibiciones

Nunca se auditan:

- contraseñas, tokens, secretos TOTP ni credenciales;
- cuerpos de correo o adjuntos;
- contenido binario de Excel;
- rutas físicas absolutas;
- datos de otro tenant o región;
- series o stock no afectados por la operación.

## Consulta

- La auditoría se consulta con las vistas de 001 según el alcance del rol.
- 008 no crea una pantalla de auditoría propia.
- El Administrador de plataforma consulta la auditoría global según 001; el almacén, la de su
  región.

## Pruebas de contrato

- Confirmar 5 series produce exactamente 5 registros `Serie/estado` `RESERVADA→ASIGNADA`.
- Confirmar 5 series de un material y 50 unidades no seriadas de otro produce un registro
  `StockTecnico/cantidad` y uno `StockGeneral/cantidad` por material, no uno por serie.
- Los valores anterior y nuevo coinciden con los del `ResultadoConfirmacionStock`.
- El actor es el usuario de la sesión, no `None` ni el sistema.
- Si la auditoría falla, no queda stock modificado ni serie asignada.
- Ningún registro contiene secretos, binarios, rutas absolutas ni datos de otro tenant.
- La auditoría `SolicitudAsignacion/estado` aparece una sola vez y es la de 007.
