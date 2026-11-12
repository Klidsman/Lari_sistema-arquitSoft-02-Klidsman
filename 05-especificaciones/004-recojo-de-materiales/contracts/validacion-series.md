# Contrato del fragmento de validación de series

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/004-recojo-de-materiales/spec.md`

Contrato de `POST /recojos/validar-series/` para la vista previa en tiempo real del formulario de
recojo. El endpoint es de solo lectura: no crea recojos, líneas ni series. HTMX reemplaza el
contenedor de la línea con el fragmento devuelto.

## Petición

| Aspecto | Valor |
|---|---|
| Método | `POST` |
| Autenticación | Cookie de sesión; rol `TENANT` activo y tenant activo |
| CSRF | Obligatorio |
| Parámetros | `material_id` (entero), `series` (texto con una serie por línea) |
| `material_id` | Debe existir en el catálogo y ser seriado |
| `series` | Se divide por saltos de línea; las líneas vacías se ignoran |
| Normalización | Cada serie se normaliza antes de clasificar: se eliminan todos los espacios en blanco y se convierte a mayúsculas |
| Filtro de tenant | Solo para autorización y para el material; la consulta de existencia de series es global porque la unicidad lo es |
| Escritura | Ninguna |

## Respuesta

`200 OK` con `Content-Type: text/html; charset=utf-8` y un fragmento HTML (sin `<html>`, `<head>`
ni `<body>`) que HTMX inserta en el contenedor de la línea.

Cada serie ocupa una fila con los dos atributos obligatorios:

| Atributo | Contenido | Ejemplo |
|---|---|---|
| `data-serie` | Serie normalizada | `data-serie="ABC123456789"` |
| `data-estado` | `valida`, `invalida`, `duplicada` o `ya_existe` | `data-estado="valida"` |

Forma esperada (ilustrativa, no normativa en clases CSS):

```html
<table class="vista-previa-series">
  <thead>
    <tr><th>Serie</th><th>Estado</th></tr>
  </thead>
  <tbody>
    <tr data-serie="ABC123456789" data-estado="valida">
      <td>ABC123456789</td>
      <td>Válida</td>
    </tr>
    <tr data-serie="ABC123" data-estado="invalida">
      <td>ABC123</td>
      <td>Inválida: debe tener 12 caracteres alfanuméricos</td>
    </tr>
    <tr data-serie="ABC123456789" data-estado="duplicada">
      <td>ABC123456789</td>
      <td>Duplicada en el recojo</td>
    </tr>
    <tr data-serie="XYZ987654321" data-estado="ya_existe">
      <td>XYZ987654321</td>
      <td>Ya está registrada en el sistema</td>
    </tr>
  </tbody>
</table>
```

- Los atributos `data-*` son el contrato; el texto visible puede variar en formato.
- La serie mostrada es la normalizada, no el texto original.
- El estado `duplicada` se aplica a la segunda y posteriores ocurrencias de la misma serie
  normalizada dentro de la misma petición.
- El estado `ya_existe` se aplica si la serie ya está en `series.Serie`, en cualquier tenant.
- El orden de las filas es el orden de entrada, después de ignorar líneas vacías.
- El fragmento no incluye `tenant_id`, `region_id`, nombre del tenant, región, stock, creador ni
  identificador de otro recojo.

## Estados

| Estado | Significado | ¿Bloquea el guardado? |
|---|---|---|
| `valida` | Formato correcto, no duplicada en la petición y no existente en el sistema | No |
| `invalida` | No cumple `^[A-Z0-9]{12}$` después de normalizar | Sí |
| `duplicada` | Repetida dentro de la misma petición de recojo | Sí |
| `ya_existe` | Ya registrada en el sistema, en cualquier tenant | Sí |

El formulario puede mostrar los estados y deshabilitar el botón Guardar como ayuda visual, pero el
`POST /recojos/nuevo/` revalida y es la autoridad. La vista previa no garantiza que la serie siga
libre al momento de guardar.

## Estado vacío

| Caso | Respuesta |
|---|---|
| `series` vacío o solo líneas en blanco | `200` con "No se ingresaron series" dentro del contenedor |
| Material seriado sin series | `200` con el mismo estado vacío |
| Material no seriado | `400` "El material no es seriado; indique la cantidad" |

## Errores

| Caso | Respuesta |
|---|---|
| Sesión ausente | `401` o redirección a `/login/` |
| Sesión `pendiente_2fa` | Redirección a `/login/2fa/`; no devuelve filas |
| Rol distinto de `TENANT` | `403` "No tienes permiso para registrar recojos" |
| Tenant suspendido | `403` "El tenant está suspendido" |
| `material_id` ausente, no numérico o inexistente | `404` "El material no existe en el catálogo" |
| Material no seriado | `400` "El material no es seriado; indique la cantidad" |
| Método distinto de `POST` | `405` |
| Serie inválida, duplicada o existente | `200` con el estado correspondiente; no es un error HTTP |

- Un error de validación de series no devuelve `400`: la vista previa debe poder mostrar todas las
  filas y sus estados.
- La respuesta de error no revela datos de otro tenant.

## Garantías para el consumidor

1. El endpoint no escribe en la base de datos; se puede invocar en cada cambio del texto.
2. La consulta de existencia es global y se hace en una sola operación para todas las series de la
   petición.
3. El mensaje de `ya_existe` es uniforme y no revela el tenant, la región ni el recojo de origen.
4. La normalización es la misma que usa el guardado: mayúsculas y eliminación de todos los espacios
   en blanco.
5. El fragmento solo contiene series y estados; no contiene datos de stock, tenants, regiones ni
   creadores.
6. El guardado vuelve a validar todo; una vista previa `valida` no exime de la validación
   transaccional.

## Pruebas de contrato asociadas

- Una serie válida devuelve `data-estado="valida"` y la serie normalizada.
- `abc123456789` y `" abc 123456789 "` devuelven `data-serie="ABC123456789"` y estado `valida`.
- `ABC123` devuelve `data-estado="invalida"`.
- La segunda ocurrencia de la misma serie devuelve `data-estado="duplicada"`.
- Una serie de otro tenant devuelve `data-estado="ya_existe"` sin datos del tenant.
- `series` vacío devuelve el estado vacío explícito.
- El endpoint no crea filas en `recojos_recojo`, `recojos_linearecojo`, `series_serie` ni
  `stock_stockgeneral`.
- `ADMIN`, `ALMACEN` y tenant suspendido: `403`.
- `GET`, `PUT` o `DELETE`: `405`.
- El fragmento no contiene `tenant_id`, `region_id`, stock ni datos del creador.
