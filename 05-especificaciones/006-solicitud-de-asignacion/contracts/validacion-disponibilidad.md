# Contrato del fragmento de validación de disponibilidad

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

Contrato de `POST /asignaciones/validar-disponibilidad/` para la validación en tiempo real del
formulario de asignación. El endpoint es de solo lectura: no crea solicitudes, no reserva series, no
reserva cantidades y no modifica stock. HTMX reemplaza el contenedor de resumen con el fragmento
devuelto.

## Petición

| Aspecto | Valor |
|---|---|
| Método | `POST` |
| Autenticación | Cookie de sesión; rol `TENANT` activo y tenant activo |
| CSRF | Obligatorio |
| Parámetros | `tecnico_id` (entero, obligatorio), `lineas-TOTAL_FORMS`, `lineas-<n>-material_id`, `lineas-<n>-cantidad`, `lineas-<n>-serie_ids` (opcional) |
| `tecnico_id` | Debe existir, ser del tenant y estar activo |
| Líneas | Se evalúan solo las no seriadas con material y cantidad; las seriadas se informan como seleccionadas sin validar cantidad |
| Filtro de tenant | Stock, reservado y técnico se consultan con el tenant de la sesión |
| Escritura | Ninguna |
| Autoridad | La validación es informativa; el envío revalida dentro de la transacción con bloqueo |

- No se acepta `tenant_id`, `region_id`, `nif` ni `estado`; si se envían, se ignoran.
- Una línea incompleta no se considera error de formato si el usuario aún está escribiendo; se
  informa como pendiente.
- Si el material no existe o no es no seriado, se devuelve un error de esa línea.

## Cálculo

Para cada material no seriado:

```text
Reservado   = SUM(cantidad) de LineaAsignacion sin serie
              con solicitud.estado = ENVIADA, mismo tenant y material
Stock       = StockGeneral.cantidad (0 si no existe)
Disponible  = max(0, Stock - Reservado)
Valido      = 0 < cantidad_solicitada <= Disponible
```

- El reservado no incluye borradores, canceladas, rechazadas ni confirmadas.
- La consulta es agregada: no se ejecuta una consulta de stock y reservado por cada fila.
- La alerta de cupo se calcula con las series en custodia del técnico: se alerta si algún equipo
  seriado supera `settings.DIAS_ALERTA_CUSTODIA` (20 días). No se suman días entre equipos.

## Respuesta

`200 OK` con `Content-Type: text/html; charset=utf-8` y un fragmento HTML que HTMX inserta en el
contenedor de resumen.

Atributos obligatorios del contenedor raíz:

| Atributo | Contenido | Ejemplo |
|---|---|---|
| `data-valido` | `true` si todas las líneas evaluadas son válidas; `false` si alguna falla | `data-valido="false"` |
| `data-alerta-cupo` | `true` si algún equipo supera el umbral; `false` en caso contrario | `data-alerta-cupo="true"` |
| `data-dias-maximo` | Mayor cantidad de días en mano entre los equipos en custodia; `0` si no hay | `data-dias-maximo="25"` |

Cada línea evaluada ocupa una fila con:

| Atributo | Contenido | Ejemplo |
|---|---|---|
| `data-material-id` | ID del material | `data-material-id="7"` |
| `data-disponible` | Disponible calculado | `data-disponible="30"` |
| `data-solicitado` | Cantidad solicitada | `data-solicitado="60"` |
| `data-valido` | `true`/`false` para esa línea | `data-valido="false"` |
| `data-error` | Mensaje exacto si falla; vacío si es válida | `data-error="La cantidad supera el stock disponible"` |

Forma esperada (ilustrativa; las clases CSS no son contrato):

```html
<div class="validacion-disponibilidad"
     data-valido="false"
     data-alerta-cupo="true"
     data-dias-maximo="25">
  <p class="alerta">El técnico supera los 20 días en mano</p>
  <table>
    <tbody>
      <tr data-material-id="7"
          data-disponible="30"
          data-solicitado="60"
          data-valido="false"
          data-error="La cantidad supera el stock disponible">
        <td>12345678902 — Material no seriado</td>
        <td>Disponible: 30</td>
        <td>Solicitado: 60</td>
        <td>La cantidad supera el stock disponible</td>
      </tr>
    </tbody>
  </table>
</div>
```

- Los atributos `data-*` son el contrato; el texto visible puede variar en formato.
- La alerta de cupo no cambia `data-valido`; es informativa y no bloquea el envío.
- El fragmento no incluye `tenant_id`, nombre del tenant, región, creador ni datos de otro tenant.
- `data-disponible` puede ser `0`; nunca es negativo.

## Estados de la respuesta

| Situación | Código | Cuerpo |
|---|---|---|
| Líneas evaluadas | `200` | Fragmento con atributos y filas |
| Sin líneas no seriadas | `200` | `data-valido="true"` y sin filas de cantidad |
| Técnico inexistente, ajeno o inactivo | `400` | Fragmento con "El técnico no existe en este tenant" / "El técnico está desactivado" |
| Material inexistente | `400` | Fragmento con "El material no existe en el catálogo" |
| Cantidad no entera | `400` | Fragmento con "La cantidad debe ser un número entero" |
| Cantidad `<= 0` | `400` | Fragmento con "La cantidad debe ser mayor a 0" |
| Cantidad sobre el disponible | `200` | `data-valido="false"` y `data-error="La cantidad supera el stock disponible"` |
| Rol incorrecto | `403` | Fragmento con "No tienes permiso para crear asignaciones" |
| Tenant suspendido | `403` | Fragmento con "El tenant está suspendido" |
| Método distinto de `POST` | `405` | Sin cuerpo relevante |

- La cantidad sobre el disponible no es un error de formato; se informa en el fragmento como
  inválida para que el usuario corrija antes de enviar.
- En peticiones HTMX, todos los errores se devuelven como fragmento HTML.

## Verificación en pruebas

- `data-disponible` refleja `Stock General − Reservado` (CA-04).
- Una cantidad igual al disponible es válida; una mayor no lo es (CA-03).
- El reservado solo cuenta solicitudes `ENVIADA`.
- `data-alerta-cupo="true"` con una serie de 25 días (CA-09).
- La alerta no impide que `data-valido="true"` si las cantidades son correctas.
- El endpoint no crea ni modifica registros: se verifica el conteo antes y después.
- La respuesta es `text/html` y no contiene JSON.
