# Contrato de auditoría de técnicos

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/003-tecnicos/spec.md`

Contrato de escritura de los registros de `auditoria.RegistroCambio` producidos por el módulo de
técnicos. Se apoya en `03-reglas-de-dominio/auditoria.md`, en el principio VI de la constitución y
en el modelo compartido planificado por la spec 001.

## Estructura del registro

Se reutiliza la tabla de la spec 001; no se crea una tabla nueva.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `entidad` | texto(50) | Sí | Siempre `Tecnico` |
| `entidad_id` | entero | Sí | `Tecnico.id` |
| `campo` | texto(50) | Sí | `alta`, `nombre` o `activo` |
| `valor_anterior` | texto | No | Vacío en el alta |
| `valor_nuevo` | texto | No | Valor después del cambio |
| `usuario` | FK `Usuario` | Sí | Cuenta autenticada que ejecuta la acción |
| `fecha` | fecha/hora | Sí | Generada por el servidor al insertar |

## Eventos mínimos obligatorios

| Evento | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|
| Alta de técnico | `alta` | — | `nif=LA1234; nombre=Juan Pérez; estado=ACTIVO` |
| Edición de nombre | `nombre` | nombre anterior | nombre nuevo |
| Desactivación | `activo` | `ACTIVO` | `DESACTIVADO` |
| Reactivación | `activo` | `DESACTIVADO` | `ACTIVO` |

- El alta registra NIF, nombre y estado en una sola fila de evento compuesto, sin ocultar campos.
- Cada campo modificado en una edición genera su propia fila.
- Una edición que no modifica el nombre no genera auditoría.
- Una desactivación o reactivación repetida (idempotente) no genera auditoría nueva.
- Un intento rechazado (permiso, NIF duplicado, NIF/tenant inmutable, tenant suspendido) **no**
  genera auditoría: no hubo cambio.
- `nif` y `tenant` no se auditan como cambios porque son inmutables; el alta sí registra el NIF.
- La desactivación no borra ni modifica registros anteriores.

## Reglas de escritura

1. **Solo inserción**: el código de aplicación no ejecuta `UPDATE` ni `DELETE` sobre la tabla.
2. **Misma transacción**: el registro se inserta dentro de la `transaction.atomic` que crea,
   modifica o cambia el estado del técnico; si el cambio falla, no queda auditoría.
3. **Autor obligatorio**: `usuario` es la cuenta autenticada que ejecuta la acción; nunca nulo y
   nunca un usuario anónimo.
4. **Valores como texto**: `activo` se registra como `ACTIVO`/`DESACTIVADO`, nunca como
   `True`/`False`; el alta incluye `nif`, `nombre` y `estado=ACTIVO`.
5. **Sin secretos**: no se registran contraseñas, hashes, tokens, `token_hash`, secretos TOTP ni
   claves de cifrado.
6. **Corrección**: un valor equivocado se corrige con una edición nueva; no se edita el registro
   anterior.
7. **Sin `tenant_id` en la auditoría**: la entidad `Tecnico` ya pertenece a un tenant; el alcance
   del registro se deriva de la entidad y de la cuenta autora. No se duplica el tenant en la fila
   de auditoría.
8. **Sin datos de stock**: la auditoría de técnicos no registra stock, series, asignaciones ni
   conciliaciones; esos eventos pertenecen a sus módulos.
9. **Sin auditoría de lectura**: listar, buscar o consultar el detalle no genera registros.

## Relación con las transiciones de estado

| Operación | ¿Cambia el estado? | ¿Audita? |
|---|---|---|
| Alta | Sí, a `ACTIVO` | Sí, evento `alta` |
| Edición de nombre con cambio | No cambia el estado | Sí, evento `nombre` |
| Edición de nombre sin cambio | No | No |
| Desactivar un activo | Sí, a `DESACTIVADO` | Sí, evento `activo` |
| Desactivar un desactivado | No | No |
| Reactivar un desactivado | Sí, a `ACTIVO` | Sí, evento `activo` |
| Reactivar un activo | No | No |
| Eliminar | No permitido | No |

## Consulta

- Esta spec **no** expone una ruta de consulta de auditoría de técnicos.
- La consulta pertenece a la auditoría administrativa (spec 001 y su pantalla
  `/auditoria/acceso/`).
- Regla para cuando se implemente: la cuenta del tenant ve los registros de `Tecnico` de su propio
  tenant; el Administrador de plataforma puede consultar la auditoría administrativa global; el
  Responsable de almacén consulta la de su región cuando corresponda.
- La cuenta del tenant no puede ver auditoría de otro tenant.
- Los registros se conservan aunque la cuenta creadora se desactive o el tenant se suspenda; no se
  borran ni se ocultan a los roles autorizados.

## Pruebas de contrato asociadas

- Un alta de técnico produce un registro `entidad="Tecnico"`, `campo="alta"` con NIF, nombre y
  `estado=ACTIVO`.
- Editar el nombre produce un registro con el valor anterior y el nuevo.
- Una edición sin cambios no produce registros.
- Desactivar produce `activo` con `ACTIVO` → `DESACTIVADO`.
- Reactivar produce `activo` con `DESACTIVADO` → `ACTIVO`.
- Desactivar o reactivar dos veces no duplica registros.
- Un intento sin permiso, con NIF duplicado, con NIF/tenant forzado o con tenant suspendido no
  produce registros.
- Ningún registro contiene contraseñas, tokens ni secretos.
- El alta no escribe un `tenant_id` separado en la auditoría.
- La auditoría se conserva al desactivar la cuenta o suspender el tenant.
