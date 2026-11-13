# Contrato: auditoría de 013

Toda operación de 013 se audita con `auditoria.services.registrar_cambio` en la misma transacción.
La auditoría es inmutable y compartida; 013 no crea un modelo propio.

## Eventos obligatorios

### Carga masiva

| Campo | Valor |
|---|---|
| Entidad | `CargaOrdenes` |
| ID entidad | `carga.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | técnico, periodo, leídas, nuevas, omitidas, otro técnico, hash |
| Actor | `USUARIO_TENANT` |

### Deshacer carga

| Campo | Valor |
|---|---|
| Entidad | `CargaOrdenes` |
| ID entidad | `carga.id` |
| Campo | `deshecha` |
| Valor anterior | activa |
| Valor nuevo | deshecha, motivo |
| Actor | `USUARIO_TENANT` |

### Orden

| Campo | Valor |
|---|---|
| Entidad | `OrdenLiquidacion` |
| ID entidad | `orden.id` |
| Campo | `alta`, `numero_orden`, `fecha_instalacion` o `periodo` |
| Valor anterior | vacío o anterior |
| Valor nuevo | nuevo |
| Actor | `USUARIO_TENANT` |
| Extra | Técnico, carga |

### Uso

| Campo | Valor |
|---|---|
| Entidad | `UsoMaterialOrden` |
| ID entidad | `uso.id` |
| Campo | `alta` o `cantidad` |
| Valor anterior | vacío o cantidad anterior |
| Valor nuevo | material, cantidad |
| Actor | `USUARIO_TENANT` |
| Extra | Orden, técnico |

### Saldo inicial

| Campo | Valor |
|---|---|
| Entidad | `SaldoInicialPeriodo` |
| ID entidad | `saldo.id` |
| Campo | `alta` o `cantidad` |
| Valor anterior | vacío o cantidad anterior |
| Valor nuevo | material, periodo, cantidad |
| Actor | `USUARIO_TENANT` |

### Catálogo habilitado

| Campo | Valor |
|---|---|
| Entidad | `MaterialHabilitado` |
| ID entidad | `material_habilitado.id` |
| Campo | `alta` o `activo` |
| Valor anterior | vacío o estado anterior |
| Valor nuevo | material, activo |
| Actor | `USUARIO_TENANT` |

### Advertencia

| Campo | Valor |
|---|---|
| Entidad | `AdvertenciaUso` |
| ID entidad | `advertencia.id` |
| Campo | `alta` o `resuelta` |
| Valor anterior | vacío o pendiente |
| Valor nuevo | tipo, mensaje, justificación |
| Actor | `USUARIO_TENANT` |

### Cierre y reapertura

| Campo | Valor |
|---|---|
| Entidad | `CierreMensual` |
| ID entidad | `cierre.id` |
| Campo | `alta`, `cerrado` o `reabierto` |
| Valor anterior | estado anterior |
| Valor nuevo | `CERRADO`/`ABIERTO`, versión, backup_ref/motivo |
| Actor | `USUARIO_TENANT` |

### Justificación de cierre

| Campo | Valor |
|---|---|
| Entidad | `JustificacionCierre` |
| ID entidad | `justificacion.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | tipo, referencia, motivo |
| Actor | `USUARIO_TENANT` |

## Reglas

- Auditoría síncrona y transaccional; si falla, se revierte la operación.
- `tenant` se puebla desde la entidad/actor.
- No se auditan secretos, binarios, rutas ni datos de otro tenant.
- No se audita cada descarga de Excel/CSV; son de solo lectura.
- El historial de una orden incluye orden y usos.

## Pruebas de contrato

- Carga, deshacer, orden, uso, saldo, catálogo, advertencia y cierre generan sus eventos.
- Cada cambio tiene valor anterior y nuevo.
- El cierre con reapertura conserva ambos eventos.
- Un fallo de auditoría revierte la operación.
- Ningún registro contiene datos de otro tenant.
