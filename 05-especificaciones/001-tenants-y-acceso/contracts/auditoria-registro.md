# Contrato del registro de auditoría de acceso

**Fase**: 1 | **Fecha**: 2026-11-11 | **Spec**: `05-especificaciones/001-tenants-y-acceso/spec.md`

Contrato del libro inmutable `auditoria.RegistroCambio` para las entidades de esta spec.
Se apoya en `03-reglas-de-dominio/auditoria.md` y en el principio VI de la constitución.

## Estructura de un registro

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `id` | entero | Sí | Clave primaria |
| `entidad` | texto(50) | Sí | `Region`, `Almacen`, `Tenant`, `Usuario` o `Invitacion` |
| `entidad_id` | entero | Sí | Identificador de la entidad auditada |
| `campo` | texto(50) | Sí | Campo modificado o evento (`alta`, `suspension`, `activacion`, `desactivacion`, `reactivacion`, `cambio_rol`, `invitacion_enviada`, `invitacion_aceptada`) |
| `valor_anterior` | texto | No | Valor antes del cambio; vacío en altas |
| `valor_nuevo` | texto | No | Valor después del cambio |
| `usuario` | FK `Usuario` | Sí | Autor de la acción; nunca nulo |
| `fecha` | fecha/hora | Sí | Generada por el servidor al insertar |

## Eventos mínimos obligatorios

| Evento | Entidad | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Alta de región | `Region` | `alta` | — | `codigo`, `nombre` |
| Alta de almacén | `Almacen` | `alta` | — | `region`, `centro`, `codigo_almacen`, `buzon` |
| Edición de región/almacén | `Region` / `Almacen` | nombre del campo | valor anterior | valor nuevo |
| Alta de tenant | `Tenant` | `alta` | — | `codigo`, `nombre`, `region`, `estado` |
| Suspensión de tenant | `Tenant` | `estado` | `ACTIVO` | `SUSPENDIDO` |
| Activación de tenant | `Tenant` | `estado` | `SUSPENDIDO` | `ACTIVO` |
| Alta de cuenta | `Usuario` | `alta` | — | `email`, `rol`, `tenant`/`region` |
| Cambio de rol | `Usuario` | `rol` | rol anterior | rol nuevo |
| Desactivación de cuenta | `Usuario` | `is_active` | `True` | `False` |
| Reactivación de cuenta | `Usuario` | `is_active` | `False` | `True` |
| Invitación enviada | `Invitacion` | `invitacion_enviada` | — | correo y fecha de expiración |
| Invitación aceptada | `Invitacion` | `invitacion_aceptada` | — | correo y fecha de uso |

Cada campo modificado genera un registro propio. Una operación que cambia tres campos genera
tres filas (o una fila de evento compuesto cuando la regla lo permita, nunca ocultando un
campo).

## Reglas de escritura

1. **Solo inserción**: el código de aplicación no ejecuta `UPDATE` ni `DELETE` sobre la tabla;
   el rol de aplicación de PostgreSQL no tiene esos privilegios.
2. **Misma transacción**: el registro se inserta en la misma `transaction.atomic` que el
   cambio auditado. Si el cambio falla, no queda auditoría.
3. **Autor obligatorio**: `usuario` es la cuenta autenticada que ejecuta la acción. Las tareas
   de sistema (p. ej. envío de correo) usan la cuenta que originó la operación, no un usuario
   anónimo.
4. **Valores como texto**: fechas en ISO 8601, booleanos como `True`/`False`, FK como su
   identificador y, cuando aporte legibilidad, su código o correo.
5. **Sin secretos**: nunca se registran contraseñas, hashes de contraseña, tokens de
   invitación, `token_hash`, secretos TOTP ni claves de cifrado.
6. **Corrección**: un valor equivocado se corrige con un cambio nuevo; no se edita el registro
   anterior.

## Consulta

| Rol | Alcance |
|---|---|
| Administrador de plataforma | Toda la auditoría administrativa |
| Cuenta del tenant | Solo registros de su tenant, sus cuentas e invitaciones |
| Responsable de almacén | Solo registros de su región cuando corresponda |

- El filtro de alcance se aplica en el backend a partir de la sesión.
- Un registro de otro tenant o región se trata como inexistente (`404` si se consulta
  directamente).
- La consulta es de solo lectura y paginada.
- Desactivar una cuenta o suspender un tenant no borra ni oculta su auditoría histórica a los
  roles autorizados.

## Ejemplo (ilustrativo, no normativo)

```json
{
  "entidad": "Usuario",
  "entidad_id": 42,
  "campo": "rol",
  "valor_anterior": "RESPONSABLE_ALMACEN",
  "valor_nuevo": "ADMIN_PLATAFORMA",
  "usuario": 7,
  "fecha": "2026-11-11T10:15:00-05:00"
}
```

## Pruebas de contrato asociadas

- Un alta de región, tenant y cuenta produce sus registros de auditoría.
- Un cambio de rol registra el valor anterior y el nuevo.
- Una desactivación y una suspensión producen registro y conservan el historial.
- Un intento de `UPDATE` o `DELETE` sobre la tabla falla por permisos de base de datos.
- Ningún registro contiene contraseñas, tokens ni secretos TOTP.
- La consulta de auditoría de un tenant no devuelve registros de otro tenant.
