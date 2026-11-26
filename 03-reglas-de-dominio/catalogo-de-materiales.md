# Reglas de dominio: catálogo de materiales

**Fuente vigente**: `05-especificaciones/002-materiales/spec.md`.
**Entidad**: `materiales.Material` (app `materiales`).

## Naturaleza del catálogo

- El catálogo es **compartido por todos los tenants**. Es la única excepción documentada al
  aislamiento multitenant.
- `Material` **no tiene** `tenant_id` ni `region_id`.
- Cualquier cuenta activa de los tres roles (Administrador de plataforma, cuenta del tenant y
  Responsable de almacén) puede **consultar** el catálogo.
- **Solo el Responsable de almacén** puede registrar materiales y darlos de baja.
- El catálogo no se filtra por tenant en listados, búsquedas ni fragmentos HTMX.
- Listados y búsquedas solo muestran materiales activos.

## Datos del material

| Campo | Obligatorio | Regla |
|---|---|---|
| Código | Sí | Exactamente 11 dígitos (`^[0-9]{11}$`), único global, inmutable |
| Descripción | Sí | 1–100 caracteres, normalizada sin espacios externos ni repetidos |
| Lote | No | Hasta 50 caracteres; se normaliza en mayúsculas; vacío permitido |
| Tipo | Sí | `SERIADO` o `NO_SERIADO` (`es_seriado` booleano) |
| Creador | Sí | `creado_por`, cuenta que registró el material |
| Fecha de alta | Sí | `creado_en` |
| Última edición | No | `actualizado_por` y `actualizado_en` |
| Estado | Sí | `activo=True` por defecto; `False` tras la baja lógica |

## Normalización

| Campo | Transformación | Ejemplo |
|---|---|---|
| Código | `strip()` externo; no se quitan separadores internos | `" 10402520279 "` → `"10402520279"` |
| Descripción | `strip()` + colapsar espacios internos | `"  ROSETA   ÓPTICA "` → `"ROSETA ÓPTICA"` |
| Lote | `strip()` + colapsar espacios + `upper()` | `" fiberhome "` → `"FIBERHOME"` |

La normalización ocurre antes de validar y antes de escribir.

## Reglas de negocio

1. **Código único global.** Un código repetido se rechaza con `"El material ya existe"`, sin
   revelar qué cuenta o tenant lo creó. La restricción `unique(codigo)` es la fuente de verdad
   ante altas concurrentes y dobles clics.
2. **Código inmutable.** No se edita después del alta. El formulario de edición no lo incluye y
   el servicio rechaza la clave con `"El código no se puede cambiar"`.
3. **Un solo lote por material.** El lote es informativo y no separa stock.
4. **Edición restringida al almacén.** Cualquier Responsable de almacén activo o el
   Administrador de plataforma pueden editar descripción y lote de cualquier material activo,
   aunque lo haya creado otra cuenta. Una cuenta de tenant que lo intente recibe
   `"No tienes permiso para editar este material"`.
5. **Tipo inmutable con movimientos.** El tipo solo cambia si ninguna verificación de stock o
   movimientos lo impide. Si hay movimientos:
   `"El tipo no se puede cambiar: el material tiene movimientos"`.
6. **Baja lógica, sin borrado físico.** Cualquier Responsable de almacén puede dar de baja
   cualquier material (`activo=False`). La fila, su creador y su auditoría se conservan; el
   material deja de aparecer en listados y búsquedas. `DELETE` responde `405`. El material se
   conserva aunque su creador se desactive.
7. **Baja idempotente.** Dar de baja un material ya inactivo no cambia nada ni audita de nuevo.
8. **Reactivación al re-registrar.** Si se registra un código que pertenece a un material dado
   de baja, se reactiva la misma fila (`activo=True`) y se actualizan descripción, lote y tipo.
   No se crea un duplicado. Los cambios y la reactivación se auditan.
9. **Auditoría obligatoria.** Cada alta, cambio de descripción, lote o tipo, baja y reactivación
   deja uno o más registros en `auditoria.RegistroCambio`, en la misma transacción.
10. **Búsqueda global.** Filtra por `codigo__icontains` **o** `descripcion__icontains`, ordena por
    `codigo`, nunca por tenant y solo devuelve materiales activos.

## Permisos

| Acción | ADMIN | TENANT | ALMACEN |
|---|---|---|---|
| Ver catálogo y buscar | Sí | Sí | Sí |
| Registrar material | No | No | Sí |
| Editar descripción/lote | Sí | No | Sí (cualquier material activo) |
| Cambiar tipo | Sí | No | Sí, si no hay movimientos |
| Dar de baja | No | No | Sí (cualquier material) |
| Cambiar código | No | No | No |
| Borrar físicamente | No | No | No |

## Mensajes de error

- `"El código debe tener 11 dígitos"`
- `"El material ya existe"`
- `"La descripción es obligatoria"`
- `"La descripción no puede superar los 100 caracteres"`
- `"El lote no puede superar los 50 caracteres"`
- `"El tipo es obligatorio"`
- `"El código no se puede cambiar"`
- `"No tienes permiso para editar este material"`
- `"El tipo no se puede cambiar: el material tiene movimientos"`
- `"Solo el Responsable de almacén puede registrar materiales"`
- `"Solo el Responsable de almacén puede dar de baja materiales"`

## Auditoría

| Evento | `entidad` | `campo` | Valores |
|---|---|---|---|
| Alta | `Material` | `alta` | vacío → `codigo=...; descripcion=...; lote=...; tipo=...` |
| Edición de descripción | `Material` | `descripcion` | anterior → nuevo |
| Edición de lote | `Material` | `lote` | anterior → nuevo |
| Cambio de tipo | `Material` | `tipo` | `SERIADO`/`NO_SERIADO` → el otro |
| Baja lógica | `Material` | `activo` | `True` → `False` |
| Reactivación | `Material` | `activo` | `False` → `True` |

- Un registro por campo modificado.
- Una operación rechazada (permiso, duplicado, tipo inmutable, validación) **no** escribe
  auditoría.
- Nunca se auditan contraseñas, tokens ni claves.

## Fragmento de búsqueda

`GET /materiales/buscar/?q=&limit=` devuelve filas con `data-codigo`, `data-descripcion`,
`data-lote` y `data-tipo`. `limit` es 20 por defecto y 50 como máximo. El fragmento no incluye
datos de stock, tenant, región ni creador.
