# Contrato: auditoría de 011

Toda operación de 011 se audita con `auditoria.services.registrar_cambio` en la misma transacción.
La auditoría es inmutable y compartida; 011 no crea un modelo propio.

## Devolución

### Alta de devolución

| Campo | Valor |
|---|---|
| Entidad | `Devolucion` |
| ID entidad | `devolucion.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | `REGISTRADA` |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Tenant, región, técnico, fecha, total de series |

### Alta de líneas

| Campo | Valor |
|---|---|
| Entidad | `LineaDevolucion` |
| ID entidad | `linea.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | serie, material, lote |
| Actor | `USUARIO_TENANT` de la sesión |

Se escribe un registro por línea.

### Acta

| Campo | Valor |
|---|---|
| Entidad | `Devolucion` |
| ID entidad | `devolucion.id` |
| Campo | `acta` |
| Valor anterior | vacío |
| Valor nuevo | ruta relativa y hash |
| Actor | `USUARIO_TENANT` de la sesión |

No se audita el contenido binario.

### Serie devuelta

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `estado` |
| Valor anterior | `ASIGNADA` |
| Valor nuevo | `DISPONIBLE` |
| Actor | `USUARIO_TENANT` de la sesión |

Además, por serie:

- `Serie/tecnico`: técnico anterior → vacío.
- `Serie/asignada_en`: fecha anterior → vacío.

### Stock

- `StockTecnico/cantidad`: lo escribe 008 al decrementar; valor anterior y nuevo.
- `StockGeneral/cantidad`: lo escribe 008 al incrementar; valor anterior y nuevo.

011 no duplica estos registros.

## Baja

### Alta de baja

| Campo | Valor |
|---|---|
| Entidad | `BajaEquipo` |
| ID entidad | `baja.id` |
| Campo | `alta` |
| Valor anterior | vacío |
| Valor nuevo | serie, material, causa |
| Actor | `USUARIO_TENANT` de la sesión |
| Extra | Observaciones, región |

### Serie inactiva

| Campo | Valor |
|---|---|
| Entidad | `Serie` |
| ID entidad | `serie.id` |
| Campo | `estado` |
| Valor anterior | `ASIGNADA` o `DISPONIBLE` |
| Valor nuevo | `INACTIVA` |
| Actor | `USUARIO_TENANT` de la sesión |

Además, por serie:

- `Serie/tecnico`: técnico anterior → vacío (si estaba asignada).
- `Serie/asignada_en`: fecha anterior → vacío.

### Stock

- Si estaba `ASIGNADA`: `StockTecnico/cantidad` lo escribe 008.
- Si estaba `DISPONIBLE`: `StockGeneral/cantidad` lo escribe 008.
- Solo se registra el nivel afectado.

## Reglas

- La auditoría es síncrona y transaccional: si falla, se revierte la operación completa.
- El valor anterior se toma de la fila bajo bloqueo.
- El actor es siempre el usuario de la sesión; nunca `None` ni un usuario inventado.
- Los registros son inmutables: no se editan ni se eliminan desde 011.
- No se auditan contraseñas, tokens, secretos, cuerpos de correo, binarios, rutas absolutas ni datos
  de otro tenant.
- La auditoría no sustituye al dato: `Serie.estado`, `Serie.tecnico` y el stock actual son la fuente.

## Eventos que no se duplican

| Evento | Dueño |
|---|---|
| `StockTecnico/cantidad` por asignación/traspaso/stock inicial | 008/009/005 |
| `StockGeneral/cantidad` por recojo | 004 |
| `SolicitudAsignacion/estado` | 007 |
| `SolicitudTraspaso/estado` | 009 |
| `Conciliacion/estado` | 010 |

## Consulta

- La auditoría se consulta con las vistas de 001 según el rol.
- 011 no crea una pantalla de auditoría propia.
- El tenant ve su auditoría; nunca la de otro tenant.

## Pruebas de contrato

- Devolver produce `Devolucion/alta`, una `LineaDevolucion/alta` por serie, `Devolucion/acta`,
  `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en` y los cambios de stock de 008.
- Dar de baja produce `BajaEquipo/alta`, `Serie/estado` y el cambio de stock del nivel correcto.
- Cada registro tiene valor anterior y nuevo.
- Rechazar una operación no deja registros parciales.
- Ningún registro contiene secretos, binarios, rutas absolutas ni datos de otro tenant.
- Si la auditoría falla, la operación se revierte completa.
