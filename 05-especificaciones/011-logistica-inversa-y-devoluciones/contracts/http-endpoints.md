# Contrato: endpoints de 011

Todas las rutas exigen sesión y rol `USUARIO_TENANT`. El tenant y la región salen de la sesión. No se
acepta `tenant_id`, `region_id`, estado, material ni NIF del cliente.

| Ruta | Método | Respuesta |
|---|---|---|
| `/logistica-inversa/devoluciones/` | `GET` | `200` con listado paginado y filtro por fecha |
| `/logistica-inversa/devoluciones/nueva/` | `GET` | `200` con formulario |
| `/logistica-inversa/devoluciones/nueva/` | `POST` | `302` al detalle; `400` por validación |
| `/logistica-inversa/devoluciones/<id>/` | `GET` | `200` con detalle y series |
| `/logistica-inversa/devoluciones/<id>/acta/` | `GET` | `200` con `.xlsx`; `404` si falta; `409` si hash no coincide |
| `/logistica-inversa/bajas/` | `GET` | `200` con listado y filtro por causa |
| `/logistica-inversa/bajas/nueva/` | `GET` | `200` con formulario |
| `/logistica-inversa/bajas/nueva/` | `POST` | `302` al detalle; `400` por validación |
| `/logistica-inversa/bajas/<id>/` | `GET` | `200` con detalle |

- No hay `POST` para generar el acta: se genera al registrar la devolución.
- No hay `GET` para acciones de escritura.
- Un recurso ajeno devuelve `404`; un rol incorrecto, `403`; un estado inválido, `409`.
- No se expone la ruta física del acta ni su hash en cabeceras.

## Formulario de devolución

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `tecnico` | select | Sí | Técnico del tenant y la región |
| `fecha` | date | Sí | Por defecto hoy; no futura |
| `series` | multi-select | Sí | Series `ASIGNADA` del técnico, no reservadas |
| `observaciones` | textarea | No | Texto libre |

- El selector de series solo muestra series del técnico y no reservadas.
- No se envían material, lote, estado ni tenant.
- Al guardar se genera el acta automáticamente.

## Formulario de baja

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `serie` | text | Sí | Serie existente del tenant; `ASIGNADA` o `DISPONIBLE` |
| `causa` | select | Sí | `AVERIA`, `MIGRACION`, `OTRO` |
| `observaciones` | textarea | No | Texto libre |

- El material se obtiene de la serie; no se acepta del cliente.
- No se aceptan series `RESERVADA`, `INSTALADA` ni `INACTIVA`.

## Errores

| Situación | Código | Mensaje |
|---|---|---|
| Sin sesión | `302` a login | — |
| Rol incorrecto | `403` | “No tienes permiso para registrar devoluciones” |
| Devolución/baja ajena | `404` | “La devolución no existe” |
| Técnico ajeno | `400` | “El técnico no existe o no pertenece al tenant” |
| Serie no asignada | `409` | “La serie no está asignada al técnico” |
| Serie reservada | `409` | “La serie está reservada en otro traspaso” |
| Serie ya inactiva | `409` | “La serie ya fue dada de baja” |
| Serie instalada | `409` | “La serie está instalada y no puede devolverse ni darse de baja” |
| Serie de otro tenant | `404`/`400` | “La serie no pertenece a este tenant” |
| Causa faltante | `400` | “Debe indicar la causa de la baja” |
| Causa inválida | `400` | “La causa de la baja no es válida” |
| Fecha futura | `400` | “La fecha de devolución no es válida” |
| Sin series | `400` | “Debe seleccionar al menos una serie” |
| Acta ausente | `404` | “El acta no está disponible” |
| Hash alterado | `409` | “El acta fue modificada, descarga bloqueada” |

## Descarga del acta

- `Content-Type`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- `Content-Disposition`: `attachment; filename="acta-devolucion-<id>.xlsx"`.
- Se resuelve la ruta relativa bajo `MEDIA_ROOT`/`ACTAS_DIR`; se rechazan rutas absolutas, `..` y
  salidas del directorio.
- Se verifica el hash antes de servir; no se regenera.
- No se expone la ruta física.

## Pruebas de contrato

- Cada ruta devuelve los códigos indicados para rol correcto, ajeno y validación fallida.
- El formulario ignora `tenant_id`/`region_id`/material/estado enviados.
- El listado solo muestra devoluciones y bajas del tenant.
- El detalle no muestra series de otro tenant.
- La descarga devuelve un `.xlsx` de una hoja y falla si el hash no coincide.
