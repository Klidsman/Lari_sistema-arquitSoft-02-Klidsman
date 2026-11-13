# Contrato: endpoints de 012

Todas las rutas exigen sesión. El Administrador puede operar sobre cualquier tenant o global; el
tenant solo sobre el suyo. No se acepta `tenant_id` del cliente para una cuenta de tenant.

| Ruta | Método | Respuesta |
|---|---|---|
| `/reportes/cortes/` | `GET` | `200` con listado según alcance y filtro por año |
| `/reportes/cortes/generar/` | `GET` | `200` con formulario de mes, año y tenant/global |
| `/reportes/cortes/generar/` | `POST` | `302` al detalle; `400` por mes/año; `409` si ya existe |
| `/reportes/cortes/<id>/` | `GET` | `200` con detalle y totales |
| `/reportes/cortes/<id>/regenerar/` | `POST` | `302` al detalle; `409` si no existe o es ajeno |
| `/reportes/cortes/<id>/exportar/auditoria/` | `GET` | `200` con `.xlsx` de auditoría del mes |
| `/reportes/cortes/<id>/exportar/conciliacion/` | `GET` | `200` con `.xlsx` de conciliación del mes |

- No hay `POST` para exportar; son descargas `GET`.
- No hay `GET` para regenerar; devuelve `405`.
- Un corte ajeno devuelve `404`; un rol incorrecto, `403`.
- Un mes/año inválido devuelve `400`; un duplicado, `409`.
- El global solo lo ofrece el formulario al Administrador.

## Formulario de generación

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `mes` | select/number | Sí | 1–12 |
| `anio` | number | Sí | 2000–2100 |
| `tenant` | select | No | Solo Admin; vacío = global |

- El tenant no ve el selector global ni puede forzarlo.
- No se aceptan totales, estado ni actor del cliente.

## Detalle

- Mes/año, alcance (tenant/global), versión, fechas.
- Solicitados, asignados, liquidados/instalados, devueltos, no justificado y % merma.
- Acciones: regenerar, exportar auditoría, exportar conciliación.

## Descargas

- `Content-Type`:
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- `Content-Disposition`: `attachment; filename="auditoria-<alcance>-<anio>-<mes>.xlsx"` o
  `conciliacion-<alcance>-<anio>-<mes>.xlsx`.
- No se expone ninguna ruta física.
- No se persiste el archivo en el servidor.

## Errores

| Situación | Código | Mensaje |
|---|---|---|
| Sin sesión | `302` a login | — |
| Rol incorrecto | `403` | “No tienes permiso para generar este corte” |
| Global desde tenant | `403` | “Solo el administrador puede generar cortes globales” |
| Corte ajeno | `404` | “El corte no existe” |
| Mes inválido | `400` | “El mes debe estar entre 1 y 12” |
| Año inválido | `400` | “El año no es válido” |
| Duplicado | `409` | “Ya existe un corte para este mes/año” |
| Método incorrecto | `405` | — |

## Pruebas de contrato

- Cada ruta devuelve los códigos indicados para rol correcto, ajeno, global desde tenant y
  duplicado.
- El formulario ignora `tenant_id` enviado por una cuenta de tenant.
- El listado de tenant no muestra cortes de otro tenant ni globales.
- El Admin puede generar/ver el global y cualquier tenant.
- Las descargas devuelven `.xlsx` y no exponen rutas.
- `GET` en regenerar devuelve `405`; `POST` en exportar devuelve `405`.
