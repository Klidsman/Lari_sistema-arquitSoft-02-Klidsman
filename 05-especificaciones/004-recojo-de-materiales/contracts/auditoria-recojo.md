# Contrato de auditoría: recojos y stock general

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/004-recojo-de-materiales/spec.md`

Contrato de los registros que deja un recojo en `auditoria.RegistroCambio` (spec 001) y de los que
escribe el servicio de stock de la spec 008. La auditoría es de solo inserción y se escribe en la
misma transacción que el cambio.

## Eventos

| Evento | `entidad` | `entidad_id` | `campo` | `valor_anterior` | `valor_nuevo` | Autor |
|---|---|---|---|---|---|---|
| Alta de recojo | `Recojo` | `Recojo.id` | `alta` | vacío | resumen legible del recojo | Cuenta del tenant |
| Incremento de stock general | `StockGeneral` | `StockGeneral.id` | `cantidad` | cantidad anterior | cantidad nueva | Cuenta del tenant |

### Alta de recojo

`valor_nuevo` es un texto legible con, como mínimo:

```text
fecha=2026-11-12; region=Ayacucho; lineas=4; series=3; cantidad=25
```

- `lineas` es el número total de `LineaRecojo` creadas.
- `series` es el número de líneas con serie (unidades seriadas).
- `cantidad` es la suma de las líneas no seriadas.
- `region` es el nombre o código de la región del tenant; no es un `region_id` suelto ni un dato
  enviado por el cliente.
- No se incluye la lista completa de series: la trazabilidad individual está en las filas
  `series.Serie` y en su vínculo `LineaRecojo → Recojo`.

### Incremento de stock general

Lo escribe `stock.services.incrementar_stock_general` (spec 008):

- `entidad="StockGeneral"`, `entidad_id` del registro de stock del tenant y material.
- `campo="cantidad"`.
- `valor_anterior` y `valor_nuevo` como texto legible.
- Se escribe una vez por material, no una vez por serie, porque 004 agrupa las líneas por material.
- La auditoría de stock es responsabilidad de 008; 004 no la duplica.

## Datos prohibidos

Nunca se guardan en `RegistroCambio`:

- Contraseñas, hashes de contraseña ni `token_hash`.
- Tokens de invitación o de recuperación.
- Secretos TOTP, códigos de segundo factor ni claves.
- Datos personales innecesarios, números de documento distintos del NIF cuando no correspondan, ni
  contenido de archivos.
- `tenant_id` o `region_id` como campos separados: el alcance se deriva de la entidad auditada y de
  la cuenta autora.

## Reglas de escritura

1. La auditoría del alta de recojo se escribe en la misma `transaction.atomic` que el recojo, sus
   líneas, las series y el incremento de stock.
2. Si cualquier validación falla (formato, duplicado, serie existente, material, cantidad, stock),
   no se escribe ninguna auditoría de recojo ni de stock.
3. Si la base rechaza una serie por `unique`, la transacción se revierte y no queda auditoría
   parcial.
4. El alta del recojo genera un solo registro `Recojo/alta`; no se escribe uno por línea ni uno por
   serie.
5. Los incrementos de stock generan un registro por material incrementado, con valor anterior y
   nuevo.
6. La auditoría no se actualiza ni se borra; una corrección posterior se registra como un evento
   nuevo de la operación que la produzca.
7. Desactivar la cuenta o suspender el tenant no borra la auditoría.

## Consulta

- La cuenta del tenant puede consultar la auditoría de sus propios recojos a través de la consulta
  de auditoría de la spec 001.
- El Administrador de plataforma consulta la auditoría administrativa global; no registra recojos.
- El Responsable de almacén consulta la auditoría de su región cuando corresponda.
- Un tenant no puede ver la auditoría de otro tenant.
- Esta spec no expone una ruta propia de consulta de auditoría.

## Pruebas de contrato asociadas

- Un alta válida deja exactamente un `RegistroCambio` con `entidad="Recojo"`, `campo="alta"` y el
  resumen con fecha, región, líneas, series y cantidad.
- El alta deja registros `StockGeneral/cantidad` con valor anterior y nuevo por cada material
  incrementado.
- Un alta con una serie inválida, duplicada o existente no deja ningún `RegistroCambio` de recojo ni
  de stock.
- Un fallo del servicio de stock revierte el recojo y no deja auditoría.
- Ningún registro contiene contraseñas, tokens, secretos TOTP ni `tenant_id` separado.
- La auditoría del recojo se conserva si se desactiva la cuenta o se suspende el tenant.
