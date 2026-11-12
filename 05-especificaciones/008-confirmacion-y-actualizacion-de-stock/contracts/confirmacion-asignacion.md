# Contrato: integración con la confirmación de 007

008 actualiza stock y series; 007 orquesta la confirmación y es dueño del estado de la solicitud.
Este contrato fija la frontera para que ninguna de las dos specs escriba lo que le corresponde a la
otra.

## Propiedad de cada dato

| Dato | Dueño | 008 | 007 |
|---|---|---|---|
| `SolicitudAsignacion.estado` | 006/007 | Solo lee | Escribe `ENVIADA→CONFIRMADA` |
| `SolicitudAsignacion.confirmada_en` | 007 | Solo lee | Escribe en la misma transacción |
| `Serie.estado` al confirmar | 008 | `RESERVADA→ASIGNADA` | No escribe |
| `StockGeneral.cantidad` | 008 | Decrementa | No escribe |
| `StockTecnico.cantidad` | 008 | Incrementa | No escribe |
| Auditoría `SolicitudAsignacion/estado` | 007 | No escribe | Escribe |
| Auditoría `Serie/estado`, `StockGeneral/cantidad`, `StockTecnico/cantidad` | 008 | Escribe | No duplica |
| Rechazo y liberación de series | 007 | No participa | `RESERVADA→DISPONIBLE` |

## Secuencia obligatoria

```text
007.confirmar_solicitud(solicitud, actor)
├── valida rol RESPONSABLE_ALMACEN y región de la solicitud
├── valida estado ENVIADA
├── transaction.atomic
│   ├── SELECT ... FOR UPDATE de la solicitud
│   ├── stock.services.actualizar_stock_confirmacion_asignacion(solicitud, actor)
│   │   ├── valida técnico, series RESERVADA, cantidades y stock suficiente
│   │   ├── bloquea Tenant → StockGeneral → StockTecnico → Serie
│   │   ├── Serie: RESERVADA → ASIGNADA
│   │   ├── StockTecnico += series + no seriados (por material)
│   │   ├── StockGeneral -= series + no seriados (por material)
│   │   ├── audita Serie/estado
│   │   └── audita StockTecnico/cantidad y StockGeneral/cantidad
│   ├── solicitud.estado = CONFIRMADA
│   ├── solicitud.confirmada_en = ahora
│   └── audita SolicitudAsignacion/estado
└── después del commit: notifica al tenant
```

## Requisitos de la llamada

- La llamada a 008 ocurre **dentro** de la transacción de 007, después del bloqueo de la solicitud.
- 007 no escribe stock ni series antes ni después de la llamada.
- 007 no captura `StockInsuficiente` para continuar: cualquier excepción revierte la confirmación
  completa y la solicitud queda `ENVIADA`.
- 008 no captura ni silencia las excepciones de 007; se propaga el error para que la transacción
  aborte.
- Si 008 termina y 007 falla al fijar `estado`/`confirmada_en` o al auditar, también se revierte el
  stock y las series.
- La notificación al tenant se publica solo después del commit; un correo no puede anunciar una
  confirmación revertida.
- La segunda confirmación de la misma solicitud recibe `409` en 007 y no llega a 008.

## Orden de bloqueo

`SolicitudAsignacion` (007) → `Tenant` → `StockGeneral` por `material_id` → `StockTecnico` por
`material_id` → `Serie` por `id`.

- 008 no vuelve a bloquear la solicitud; confía en el bloqueo de 007.
- El orden ascendente por `material_id` y por `id` evita interbloqueos con 006 (envío), 004 (recojo)
  y 009 (traspaso).
- Si 008 detecta que la solicitud ya no está `ENVIADA` porque otra transacción la confirmó, lanza
  `ConfirmacionStockInvalida` y no mueve stock.

## Días en mano

- 007 fija `confirmada_en` en la misma transacción de la confirmación.
- 008 **no** escribe `confirmada_en`, no crea contador ni tabla de días en mano.
- `ResultadoConfirmacionStock.confirmada_en` es de solo lectura y sirve para verificar que 007 fijó
  la fecha.
- 006 calcula los días en mano a demanda desde `confirmada_en` (CA-05).

## Rechazo

- 008 no participa en el rechazo.
- 007 cambia la solicitud a `RECHAZADA`, fija `rechazada_en` y libera cada serie
  `RESERVADA→DISPONIBLE` con su auditoría.
- El reservado de no seriados se libera solo porque `calcular_reservado` cuenta únicamente
  solicitudes `ENVIADA`; no hay fila de reserva que borrar.
- No se mueve stock general ni técnico en un rechazo.

## Errores visibles para el almacén

| Situación | Excepción de 008 | Respuesta de 007 |
|---|---|---|
| Stock general insuficiente al confirmar | `StockInsuficiente` | `409` con “El tenant no tiene suficiente stock general” |
| Serie ya no `RESERVADA` | `SerieNoReservada` | `409` con “La serie no está reservada para esta asignación” |
| Solicitud ya no `ENVIADA` | `ConfirmacionStockInvalida` | `409` |
| Técnico de otro tenant | `TenantNoCoincide` | `403` |
| Cantidad de línea inválida | `CantidadInvalida` | `400` |

Después de cualquier error, la solicitud sigue `ENVIADA`, las series conservan su estado y el stock
no cambia.

## Pruebas de contrato

- Confirmar una solicitud mueve series y stock exactamente una vez y deja la solicitud
  `CONFIRMADA` con `confirmada_en`.
- Si 008 lanza `StockInsuficiente`, la solicitud sigue `ENVIADA`, las series siguen `RESERVADA` y
  no hay registros de auditoría de stock.
- Si 007 falla después de 008 (por ejemplo, al auditar la solicitud), el stock y las series se
  revierten.
- 007 no contiene escrituras a `StockGeneral` ni `StockTecnico` (verificado por revisión y por
  prueba).
- Una segunda confirmación no vuelve a mover stock.
- El rechazo libera series y no toca stock.
- La notificación se emite solo si la transacción hizo commit.
