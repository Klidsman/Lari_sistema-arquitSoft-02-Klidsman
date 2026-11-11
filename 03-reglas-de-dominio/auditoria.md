# Auditoría

Reglas de dominio para el registro inmutable de cambios del sistema.

## 1. Propósito

Dejar rastro de toda alta, cambio y desactivación relevante, con el usuario que lo hizo, la fecha, el valor anterior y el valor nuevo.

## 2. Alcance

Se auditan, como mínimo:

- Altas y cambios de región, almacén y tenant.
- Altas, cambios de rol y desactivación de cuentas.
- Suspensión y reactivación de tenants.
- Altas y cambios de materiales.
- Movimientos y ajustes de stock.
- Ajustes de conciliación.
- Cambios de saldo inicial, despachos y uso de materiales.

## 3. Registro

Cada registro contiene:

| Campo | Significado |
|---|---|
| Entidad | Tipo de dato afectado, por ejemplo `Tenant`, `Usuario`, `Material` |
| Entidad ID | Identificador del dato afectado |
| Campo | Campo modificado |
| Valor anterior | Valor antes del cambio |
| Valor nuevo | Valor después del cambio |
| Usuario | Cuenta que realizó la acción |
| Fecha | Fecha y hora del cambio |

## 4. Reglas

- El registro es de solo inserción.
- No se actualizan ni se borran registros de auditoría.
- Una corrección se registra como un cambio nuevo.
- Cada campo modificado genera un registro.
- El registro se guarda en la misma transacción que el cambio.
- Si el cambio falla, no se guarda la auditoría.
- Los valores se guardan como texto legible.
- No se registran contraseñas, tokens de invitación, secretos de segundo factor ni datos sensibles equivalentes.
- La auditoría no reemplaza el historial de movimientos de stock; lo complementa.

## 5. Consulta

- El Administrador de plataforma puede consultar la auditoría administrativa global.
- La cuenta del tenant puede consultar la auditoría de su tenant.
- Un Responsable de almacén puede consultar la auditoría de su región cuando corresponda.
- La cuenta del tenant no puede ver auditoría de otro tenant.
- El alcance se determina por la entidad auditada y por el tenant o la región de la cuenta autenticada.

## 6. Conservación

- La auditoría se conserva durante toda la vida del sistema.
- Desactivar una cuenta o suspender un tenant no borra su auditoría.
- No existe purga automática de auditoría en esta versión.
