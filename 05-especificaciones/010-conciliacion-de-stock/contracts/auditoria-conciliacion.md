# Contrato: auditoría de 010

Toda operación de 010 se audita con `auditoria.services.registrar_cambio` en la misma transacción.
La auditoría es inmutable y compartida; 010 no crea un modelo propio.

## Eventos obligatorios

### Carga

| Campo | Valor |
|---|---|
| Entidad | `Conciliacion` |
| ID entidad | `conciliacion.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | `EN_REVISION` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Tenant, región, archivo, hash, total de diferencias |

Y:

| Campo | Valor |
|---|---|
| Entidad | `Conciliacion` |
| ID entidad | `conciliacion.id` |
| Campo | `archivo` |
| Valor anterior | vacío |
| Valor nuevo | ruta relativa y hash |
| Actor | `USUARIO_TENANT` de la sesión |

No se audita el contenido binario.

### Recálculo

| Campo | Valor |
|---|---|
| Entidad | `Conciliacion` |
| ID entidad | `conciliacion.id` |
| Campo | `recalculo` |
| Valor anterior | huella y conteos anteriores |
| Valor nuevo | huella y conteos nuevos |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | `requiere_revision=True` |

### Cambios detectados al aprobar

| Campo | Valor |
|---|---|
| Entidad | `Conciliacion` |
| ID entidad | `conciliacion.id` |
| Campo | `hubo_cambios` |
| Valor anterior | huella guardada |
| Valor nuevo | huella actual |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Recálculo realizado; no se aplicaron ajustes |

### Aprobación

| Campo | Valor |
|---|---|
| Entidad | `Conciliacion` |
| ID entidad | `conciliacion.id` |
| Campo | `estado` |
| Valor anterior | `EN_REVISION` |
| Valor nuevo | `APROBADA` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | `fecha_aprobacion`, conteos de series y cantidades |

### Series creadas

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | número, material, técnico, `asignada_en` |
| Actor | `USUARIO_TENANT` de la sesión |

### Series instaladas

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `estado` |
| Valor anterior | `ASIGNADA` |
| Valor nuevo | `INSTALADA` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | `tecnico` anterior y fecha de instalación |

### Series reasignadas

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `tecnico` |
| Valor anterior | técnico anterior |
| Valor nuevo | técnico reportado |
| Actor | `USUARIO_TENANT` de la sesión |

Y `Serie/asignada_en` con fecha anterior y nueva.

### Ajustes de cantidad

Los `StockTecnico/cantidad` los escribe 008 al usar `incrementar_stock_tecnico` o
`decrementar_stock_tecnico`; 010 no los duplica. Cada registro tiene técnico, material, valor anterior
y valor nuevo.

### Rechazo

| Campo | Valor |
|---|---|
| Entidad | `Conciliacion` |
| ID entidad | `conciliacion.id` |
| Campo | `estado` |
| Valor anterior | `EN_REVISION` |
| Valor nuevo | `RECHAZADA` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | `fecha_rechazo`, `motivo_rechazo` si existe |

No hay eventos de serie ni stock.

## Reglas

- La auditoría es síncrona y transaccional: si falla, se revierte la operación completa.
- El valor anterior se toma de la fila bajo bloqueo.
- El actor es siempre el usuario de la sesión; nunca `None` ni un usuario inventado.
- Los registros son inmutables: no se editan ni se eliminan desde 010.
- No se auditan contraseñas, tokens, secretos, cuerpos de correo, binarios, rutas absolutas ni datos
  de otro tenant.
- La auditoría no sustituye al dato: `Conciliacion.estado`, `Serie.estado/tecnico` y
  `StockTecnico.cantidad` siguen siendo la fuente actual.

## Eventos que no se duplican

| Evento | Dueño |
|---|---|
| `StockGeneral/cantidad` | 004/008/011 |
| `StockTecnico/cantidad` por asignación, traspaso o stock inicial | 008/009/005 |
| `SolicitudAsignacion/estado` | 007 |
| `SolicitudTraspaso/estado` | 009 |

## Consulta

- La auditoría se consulta con las vistas de 001 según el rol.
- 010 no crea una pantalla de auditoría propia.
- El tenant ve su auditoría; nunca la de otro tenant.

## Pruebas de contrato

- Cargar produce `Conciliacion/alta` y `Conciliacion/archivo` con hash y ruta relativa.
- Recalcular produce `Conciliacion/recalculo` con huellas y conteos.
- Aprobar con cambios produce `Conciliacion/hubo_cambios` y no aplica ajustes.
- Aprobar produce `EN_REVISION→APROBADA`, un `Serie/alta`, `Serie/estado` o `Serie/tecnico` por
  serie afectada, y los `StockTecnico/cantidad` de 008.
- Rechazar produce `EN_REVISION→RECHAZADA` y el motivo, sin eventos de serie ni stock.
- Cada ajuste tiene valor anterior y nuevo.
- Ningún registro contiene secretos, binarios, rutas absolutas ni datos de otro tenant.
- Si la auditoría falla, la operación se revierte completa.
