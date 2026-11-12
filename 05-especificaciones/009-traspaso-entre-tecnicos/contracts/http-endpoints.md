# Contrato: endpoints de 009

Todas las rutas exigen sesión, CSRF en `POST` y validación de rol/tenant/región en el servicio. No se
acepta `tenant_id`, `region_id`, NIF, tipo de material, lote ni estado desde el cliente.

## Rutas del tenant

| Ruta | Método | Rol | Respuesta |
|---|---|---|---|
| `/traspasos/` | `GET` | `USUARIO_TENANT` | `200` con listado paginado y filtro por estado |
| `/traspasos/nuevo/` | `GET` | `USUARIO_TENANT` | `200` con formulario vacío |
| `/traspasos/nuevo/` | `POST` | `USUARIO_TENANT` | `302` al detalle si se crea; `400` con errores |
| `/traspasos/<id>/` | `GET` | `USUARIO_TENANT` | `200` con detalle, líneas, cuadre y Excel |
| `/traspasos/<id>/editar/` | `GET` | `USUARIO_TENANT` | `200` con formulario editable si `BORRADOR` |
| `/traspasos/<id>/editar/` | `POST` | `USUARIO_TENANT` | `302` al detalle; `409` si no es `BORRADOR` |
| `/traspasos/<id>/enviar/` | `POST` | `USUARIO_TENANT` | `302` al detalle; `409` si no es `BORRADOR` |
| `/traspasos/<id>/cancelar/` | `POST` | `USUARIO_TENANT` | `302` al detalle; `409` si no es `BORRADOR` |
| `/traspasos/<id>/excel/` | `GET` | `USUARIO_TENANT` | `200` con `.xlsx`; `404` si no existe; `409` si el hash no coincide |
| `/traspasos/series-tecnico/` | `GET` | `USUARIO_TENANT` | `200` fragmento HTML de series del origen |
| `/traspasos/validar-disponibilidad/` | `POST` | `USUARIO_TENANT` | `200` JSON con disponible, reservado y errores |

## Rutas del almacén

| Ruta | Método | Rol | Respuesta |
|---|---|---|---|
| `/almacen/traspasos/` | `GET` | `RESPONSABLE_ALMACEN` | `200` con bandeja de la región |
| `/almacen/traspasos/<id>/` | `GET` | `RESPONSABLE_ALMACEN` | `200` con detalle y cuadre |
| `/almacen/traspasos/<id>/excel/` | `GET` | `RESPONSABLE_ALMACEN` | `200` con `.xlsx` verificado |
| `/almacen/traspasos/<id>/confirmar/` | `POST` | `RESPONSABLE_ALMACEN` | `302` al detalle; `409` si no está `ENVIADA` |
| `/almacen/traspasos/<id>/rechazar/` | `POST` | `RESPONSABLE_ALMACEN` | `302` al detalle; `400` sin motivo; `409` si no está `ENVIADA` |

- No existe `GET` para enviar, cancelar, confirmar ni rechazar.
- Un `GET` a una ruta de acción devuelve `405`.
- Un recurso de otro tenant o región devuelve `404`, sin revelar su existencia.
- Un rol sin permiso devuelve `403`.
- Un estado inválido devuelve `409` con el mensaje de negocio.
- Un motivo vacío o solo espacios devuelve `400` con “El motivo de rechazo es obligatorio”.

## Formulario de creación/edición

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `tecnico_origen` | select | Sí | Técnico del tenant; puede estar inactivo si tiene stock |
| `tecnico_destino` | select | Sí | Técnico activo del tenant y distinto del origen |
| `fecha` | date | Sí | Por defecto hoy |
| `lineas` | formset | Sí | Al menos una línea |
| `lineas[].material` | select | Sí | Material del catálogo |
| `lineas[].series` | multi-select | Condicional | Solo para seriados; series del origen no reservadas |
| `lineas[].cantidad` | number | Condicional | Solo para no seriados; entero `> 0` |

- Tipo de material y lote son de solo lectura y se completan desde el catálogo.
- No se envía `tenant`, `region`, `estado`, `excel_ruta`, `excel_hash` ni `creado_por`.
- El formulario no permite escribir números de serie manualmente.
- El selector de series se carga con `/traspasos/series-tecnico/?tecnico=<id>&material=<id>&q=`.
- La validación en tiempo real devuelve JSON y no escribe en base.

### Respuesta de validación

```json
{
  "valido": true,
  "disponible": 10,
  "reservado": 2,
  "errores": [],
  "cuadre": {
    "series_salida": 3,
    "series_entrada": 3,
    "materiales": [{"material_id": 1, "salida": 20, "entrada": 20}]
  }
}
```

## Errores

| Situación | Código | Mensaje |
|---|---|---|
| Sin sesión | `302` a login | — |
| Rol incorrecto | `403` | “No tienes permiso para crear traspasos” / “No tienes permiso para gestionar traspasos” |
| Traspaso ajeno o inexistente | `404` | “El traspaso no existe” |
| Técnicos de otro tenant | `400` | “Los técnicos deben ser del mismo tenant” |
| Origen igual a destino | `400` | “El técnico origen y destino no pueden ser el mismo” |
| Destino inactivo | `400` | “El técnico destino no está activo” |
| Serie no asignada al origen | `409` | “La serie no está asignada al técnico origen” |
| Serie reservada | `409` | “La serie está reservada en otro traspaso” |
| Cantidad insuficiente | `409` | “La cantidad supera el stock del técnico” |
| Cuadre incorrecto | `409` | “Lo que sale debe cuadrar con lo que entra” |
| Estado inválido para enviar/cancelar | `409` | “Solo se pueden enviar/cancelar traspasos en borrador” |
| Estado inválido para confirmar/rechazar | `409` | “Solo se pueden confirmar/rechazar traspasos enviados” |
| Motivo vacío | `400` | “El motivo de rechazo es obligatorio” |
| Excel ausente | `404` | “El archivo no está disponible” |
| Hash alterado | `409` | “El archivo fue modificado, descarga bloqueada” |

## Descarga

- `Content-Type`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- `Content-Disposition`: `attachment; filename="traspaso-<id>.xlsx"`.
- Se resuelve la ruta relativa bajo `MEDIA_ROOT`/`TRASPASOS_EXCEL_DIR`; se rechazan rutas absolutas,
  `..` y salidas del directorio.
- Se verifica el hash antes de servir; no se regenera el archivo.
- Nunca se expone la ruta física ni el hash en cabeceras.

## Pruebas de contrato

- Cada ruta devuelve los códigos indicados para rol correcto, rol incorrecto, recurso ajeno y estado
  inválido.
- Un `GET` a una acción devuelve `405`.
- El formulario ignora `tenant_id`/`region_id` enviados y usa la sesión.
- La descarga devuelve un `.xlsx` con dos hojas y falla si el hash no coincide.
- La bandeja del almacén solo muestra traspasos de su región.
- Ninguna respuesta revela datos de otro tenant.
