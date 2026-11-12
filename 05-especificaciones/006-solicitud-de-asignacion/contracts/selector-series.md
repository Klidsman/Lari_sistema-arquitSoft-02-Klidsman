# Contrato del selector de series

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

Contrato de `GET /asignaciones/series-disponibles/` para el selector HTMX del formulario de
asignación. El endpoint es de solo lectura: no reserva, no crea líneas y no modifica series. HTMX
reemplaza el contenedor del selector con el fragmento devuelto.

## Petición

| Aspecto | Valor |
|---|---|
| Método | `GET` |
| Autenticación | Cookie de sesión; rol `TENANT` activo y tenant activo |
| Parámetros | `material_id` (entero, obligatorio), `q` (texto, opcional), `page` (entero, opcional), `excluir` (ids separados por coma, opcional) |
| `material_id` | Debe existir en el catálogo y ser seriado |
| `q` | Búsqueda por `Serie.numero` o por código/descripción del material; se normaliza a mayúsculas |
| `excluir` | Series ya elegidas en el formulario, para no ofrecerlas dos veces; ids inválidos se ignoran |
| Filtro de tenant | `Serie.tenant` = tenant de la sesión; una serie ajena no aparece ni se revela |
| Filtro de estado | Solo `Serie.estado = DISPONIBLE` |
| Paginación | 20 series por página |
| Orden | `Serie.numero` ascendente |
| Escritura | Ninguna |

- El endpoint no acepta `tenant_id` ni `region_id`; si se envían, se ignoran.
- `CA-10` y `CA-11` se satisfacen por el filtro `estado = DISPONIBLE`: una serie `ASIGNADA` o
  `RESERVADA` no aparece aunque coincida con la búsqueda.
- El material debe ser del catálogo global; no se filtra por tenant porque el catálogo es global.

## Respuesta

`200 OK` con `Content-Type: text/html; charset=utf-8` y un fragmento HTML (sin `<html>`, `<head>` ni
`<body>`) que HTMX inserta en el contenedor del selector.

Cada serie ocupa una fila con estos atributos obligatorios:

| Atributo | Contenido | Ejemplo |
|---|---|---|
| `data-serie-id` | ID de `Serie` | `data-serie-id="42"` |
| `data-serie` | Número de serie | `data-serie="ABC123456789"` |
| `data-material-id` | ID del material | `data-material-id="7"` |
| `data-disponible` | `true` | `data-disponible="true"` |

Forma esperada (ilustrativa; las clases CSS no son contrato):

```html
<table class="selector-series">
  <thead>
    <tr><th></th><th>Serie</th><th>Material</th><th>Lote</th></tr>
  </thead>
  <tbody>
    <tr data-serie-id="42" data-serie="ABC123456789" data-material-id="7" data-disponible="true">
      <td><input type="checkbox" name="lineas-0-serie_ids" value="42"></td>
      <td>ABC123456789</td>
      <td>12345678901 — Equipo de prueba</td>
      <td>LOTE-A</td>
    </tr>
  </tbody>
</table>
<nav class="paginacion" data-page="1" data-has-next="false">
  <span>1</span>
</nav>
```

- Los atributos `data-*` son el contrato; el texto visible puede variar en formato.
- La fila solo se emite si la serie sigue `DISPONIBLE` al ejecutar la consulta.
- El fragmento no incluye `tenant_id`, nombre del tenant, región, stock, creador ni solicitud.
- El número mostrado es `Serie.numero`; el material se identifica por código y descripción.
- La paginación expone `data-page` y `data-has-next` para que HTMX pida la siguiente página.

## Estados de la respuesta

| Situación | Código | Cuerpo |
|---|---|---|
| Hay series disponibles | `200` | Fragmento con filas y paginación |
| No hay series que coincidan | `200` | Fragmento con "No hay series disponibles" y sin filas |
| `material_id` ausente o no entero | `400` | "El material es obligatorio" / "El material no es válido" |
| Material inexistente | `400` | "El material no existe en el catálogo" |
| Material no seriado | `400` | "El material no es seriado" |
| Rol incorrecto | `403` | "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` | "El tenant está suspendido" |
| Método distinto de `GET` | `405` | Sin cuerpo relevante |

- En peticiones HTMX, el error se devuelve como fragmento con el mismo texto.
- Un `q` vacío devuelve la primera página sin filtrar por texto.
- `page` fuera de rango devuelve una página vacía con `data-has-next="false"`, no `404`.

## Verificación en pruebas

- Solo aparecen series `DISPONIBLE` del tenant y material solicitados.
- Una serie `ASIGNADA` no aparece (CA-10).
- Una serie `RESERVADA` no aparece (CA-11).
- Una serie de otro tenant no aparece y no se revela su existencia.
- La búsqueda por número y por código/descripción devuelve los resultados esperados.
- La paginación devuelve 20 filas y `data-has-next` coherente.
- `excluir` elimina las series ya elegidas.
- La respuesta es `text/html` y no contiene JSON.
