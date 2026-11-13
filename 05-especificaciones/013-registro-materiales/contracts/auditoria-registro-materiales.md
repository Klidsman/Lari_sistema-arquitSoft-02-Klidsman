# Contrato: auditoría de 013

Toda operación de 013 se audita con `auditoria.services.registrar_cambio` en la misma transacción.
La auditoría es inmutable y compartida; 013 no crea un modelo propio.

## Eventos obligatorios

### Catálogo habilitado

| Campo | Valor |
|---|---|
| Entidad | `MaterialHabilitado` |
| ID entidad | `material_habilitado.id` |
| Campo | `alta` o `activo` |
| Valor anterior | vacío o estado anterior |
| Valor nuevo | material, activo |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Tenant |

### Saldo inicial

| Campo | Valor |
|---|---|
| Entidad | `SaldoInicialPeriodo` |
| ID entidad | `saldo.id` |
| Campo | `alta` o `cantidad` |
| Valor anterior | vacío o cantidad anterior |
| Valor nuevo | material, periodo, cantidad |
| Actor | `USUARIO_TENANT` de la sesión |

### Orden de liquidación

| Campo | Valor |
|---|---|
| Entidad | `OrdenLiquidacion` |
| ID entidad | `orden.id` |
| Campo | `alta`, `numero_orden`, `fecha_liquidacion` o `periodo` |
| Valor anterior | vacío o valor anterior |
| Valor nuevo | valor nuevo |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Técnico |

### Uso de material

| Campo | Valor |
|---|---|
| Entidad | `UsoMaterialOrden` |
| ID entidad | `uso.id` |
| Campo | `alta` o `cantidad` |
| Valor anterior | vacío o cantidad anterior |
| Valor nuevo | material, cantidad |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Orden, técnico |

Se escribe un registro por línea creada o modificada. Una línea que pasa a 0 se audita con valor
nuevo 0; no se borra.

### Despacho del almacén

| Campo | Valor |
|---|---|
| Entidad | `DespachoAlmacen` |
| ID entidad | `despacho.id` |
| Campo | `alta`, `fecha` o `cantidad` |
| Valor anterior | vacío o valor anterior |
| Valor nuevo | recojo, línea, material, fecha, cantidad |
| Actor | `USUARIO_TENANT` de la sesión |

## Reglas

- La auditoría es síncrona y transaccional: si falla, se revierte el cambio.
- El actor es el usuario de la sesión; nunca `None`.
- `tenant` se puebla desde el actor/entidad; nunca se acepta del cliente.
- Los registros son inmutables: no se editan ni se borran desde 013.
- No se auditan secretos, binarios, rutas ni datos de otro tenant.
- No se auditan los cálculos del reporte (solo lectura).

## Consulta

- El historial de una orden se consulta por `OrdenLiquidacion` y sus `UsoMaterialOrden` del tenant.
- No se crea una pantalla de auditoría general en 013.
- La auditoría global se consulta con 001 según el rol.

## Pruebas de contrato

- Habilitar/deshabilitar produce el evento correspondiente.
- Crear/editar saldo produce alta/cantidad con valor anterior/nuevo.
- Crear/editar orden produce alta y cambios de número/fecha/periodo.
- Crear/editar uso produce alta/cantidad; el 0 se conserva y audita.
- Crear/editar despacho produce alta/fecha/cantidad.
- Un fallo de auditoría revierte la operación.
- Ningún registro contiene secretos ni datos de otro tenant.
