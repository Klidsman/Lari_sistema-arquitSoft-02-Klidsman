# Contrato del fragmento de búsqueda de materiales

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/002-materiales/spec.md`

Contrato de `GET /materiales/buscar/` para los módulos que necesitan elegir un material del
catálogo compartido y autocompletar descripción, lote y tipo: specs 004 (recojo), 005 (stock
inicial), 006 (asignación), 009 (traspaso) y 013 (registro de materiales).

## Petición

| Aspecto | Valor |
|---|---|
| Método | `GET` |
| Autenticación | Cookie de sesión; cualquier cuenta activa de los tres roles |
| Parámetros | `q` (texto libre, opcional), `limit` (entero, opcional) |
| `limit` | Por defecto `20`; máximo `50`; valores no numéricos o fuera de rango se acotan |
| `q` vacío | Devuelve los primeros `limit` materiales ordenados por `codigo` |
| `q` con texto | Filtra por `codigo__icontains` **o** `descripcion__icontains` |
| Orden | `codigo` ascendente, estable |
| Filtro de tenant | **Ninguno**: el catálogo es global |
| CSRF | No aplica (`GET`) |

## Respuesta

`200 OK` con `Content-Type: text/html; charset=utf-8` y un fragmento HTML (sin `<html>`,
`<head>` ni `<body>`) que HTMX inserta en el contenedor del consumidor.

Cada resultado es una fila con los cuatro atributos de datos obligatorios:

| Atributo | Contenido | Ejemplo |
|---|---|---|
| `data-codigo` | Código de 11 dígitos | `data-codigo="10402520323"` |
| `data-descripcion` | Descripción normalizada | `data-descripcion="ROSETA ÓPTICA"` |
| `data-lote` | Lote normalizado o cadena vacía | `data-lote="FIBERHOME"` |
| `data-tipo` | `SERIADO` o `NO_SERIADO` | `data-tipo="NO_SERIADO"` |

Forma esperada (ilustrativa, no normativa en clases CSS):

```html
<ul class="resultados-materiales">
  <li class="resultado-material"
      role="option"
      data-codigo="10402520323"
      data-descripcion="ROSETA ÓPTICA"
      data-lote="FIBERHOME"
      data-tipo="NO_SERIADO">
    <span class="codigo">10402520323</span>
    <span class="descripcion">ROSETA ÓPTICA</span>
    <span class="lote">FIBERHOME</span>
    <span class="tipo">No seriado</span>
  </li>
</ul>
```

- Los atributos `data-*` son el contrato; el texto visible puede variar en formato.
- La descripción, el lote y el tipo mostrados al usuario deben ser los mismos que el formulario
  consumidor usa para autocompletar; no se recalcula ni se transforma en el cliente.
- `data-lote` es cadena vacía cuando el material no tiene lote.

## Estado vacío y errores

| Caso | Respuesta |
|---|---|
| Sin coincidencias | `200` con `"No se encontraron materiales"` dentro del contenedor |
| Catálogo sin materiales y `q` vacío | `200` con el mismo estado vacío |
| Sesión ausente | `401` o redirección a `/login/` |
| Sesión `pendiente_2fa` | Redirección a `/login/2fa/`; no devuelve filas |
| Método distinto de `GET` | `405` |

## Garantías para los consumidores

1. El fragmento no incluye datos de stock, de tenants ni de regiones.
2. El catálogo devuelto es el mismo para todos los tenants; un consumidor no debe volver a
   filtrarlo por tenant ni por región.
3. El código es estable e inmutable: sirve como clave de selección.
4. La descripción y el lote devueltos son los normalizados y persistidos; el consumidor no debe
   permitir editarlos en su propio formulario (regla de la spec 002).
5. El fragmento está pensado para HTMX; no requiere JavaScript propio del módulo de materiales.

## Pruebas de contrato asociadas

- `GET /materiales/buscar/?q=ROSETA` devuelve el material 10402520279 con `data-lote` y
  `data-tipo`.
- `GET /materiales/buscar/?q=10402520323` devuelve el material por código.
- `GET /materiales/buscar/` con `q` vacío devuelve hasta `limit` filas ordenadas por código.
- El fragmento no contiene `tenant_id`, `region_id`, stock ni datos de la cuenta creadora.
- La misma consulta desde cuentas de dos tenants distintos devuelve los mismos resultados.
