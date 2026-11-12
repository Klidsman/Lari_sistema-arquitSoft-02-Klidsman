# Contrato de auditoría de materiales

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/002-materiales/spec.md`

Contrato de escritura de los registros de `auditoria.RegistroCambio` producidos por el módulo de
materiales. Se apoya en `03-reglas-de-dominio/auditoria.md`, en el principio VI de la
constitución y en el modelo compartido planificado por la spec 001.

## Estructura del registro

Se reutiliza la tabla de la spec 001; no se crea una tabla nueva.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `entidad` | texto(50) | Sí | Siempre `Material` |
| `entidad_id` | entero | Sí | `Material.id` |
| `campo` | texto(50) | Sí | `alta`, `descripcion`, `lote` o `tipo` |
| `valor_anterior` | texto | No | Vacío en el alta |
| `valor_nuevo` | texto | No | Valor después del cambio |
| `usuario` | FK `Usuario` | Sí | Cuenta autenticada que ejecuta la acción |
| `fecha` | fecha/hora | Sí | Generada por el servidor al insertar |

## Eventos mínimos obligatorios

| Evento | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|
| Alta de material | `alta` | — | `codigo`, `descripcion`, `lote`, `tipo` |
| Edición de descripción | `descripcion` | descripción anterior | descripción nueva |
| Edición de lote | `lote` | lote anterior | lote nuevo |
| Cambio de tipo | `tipo` | `SERIADO` / `NO_SERIADO` | `NO_SERIADO` / `SERIADO` |

- El alta registra los cuatro datos en una sola fila de evento compuesto, sin ocultar campos.
- Cada campo modificado en una edición genera su propia fila.
- Si una edición cambia descripción y lote, se generan dos filas.
- Una edición que no modifica ningún valor no genera auditoría.
- Un intento rechazado (permiso, duplicado, código inmutable, tipo inmutable) **no** genera
  auditoría: no hubo cambio.

## Reglas de escritura

1. **Solo inserción**: el código de aplicación no ejecuta `UPDATE` ni `DELETE` sobre la tabla.
2. **Misma transacción**: el registro se inserta dentro de la `transaction.atomic` que crea o
   modifica el material; si el cambio falla, no queda auditoría.
3. **Autor obligatorio**: `usuario` es la cuenta autenticada que ejecuta la acción; nunca nulo y
   nunca un usuario anónimo.
4. **Valores como texto**: `tipo` se registra como `SERIADO`/`NO_SERIADO`, nunca como `True` /
   `False`; `lote` vacío se registra como cadena vacía.
5. **Sin secretos**: no se registran contraseñas, hashes, tokens, `token_hash`, secretos TOTP ni
   claves de cifrado.
6. **Corrección**: un valor equivocado se corrige con una edición nueva; no se edita el registro
   anterior.
7. **Sin tenant**: el material es global; el registro tampoco lleva `tenant_id`. El alcance se
   deriva de la cuenta que aparece en `usuario`.

## Consulta

- Esta spec **no** expone una ruta de consulta de auditoría de materiales.
- La consulta pertenece a la auditoría administrativa (spec 001 y su pantalla
  `/auditoria/acceso/`).
- Regla para cuando se implemente: el Administrador de plataforma ve todos los registros de
  `Material`; una cuenta de tenant solo ve los registros donde `usuario` es su propia cuenta.
- Los registros se conservan aunque la cuenta creadora se desactive; no se borran ni se ocultan
  a los roles autorizados.

## Pruebas de contrato asociadas

- Un alta de material produce un registro `entidad="Material"`, `campo="alta"` con código,
  descripción, lote y tipo.
- Editar la descripción produce un registro con el valor anterior y el nuevo.
- Editar descripción y lote a la vez produce dos registros.
- Un intento sin permiso o con código duplicado no produce registros.
- Ningún registro contiene contraseñas, tokens ni secretos.
- El alta de un material no escribe `tenant_id` en la auditoría.
