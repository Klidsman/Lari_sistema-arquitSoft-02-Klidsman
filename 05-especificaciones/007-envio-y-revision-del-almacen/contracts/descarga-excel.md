# Contrato: descarga y verificación SHA-256 del Excel

Define cómo 007 entrega el Excel archivado por 006, tanto desde el detalle del almacén como desde la
búsqueda histórica. El archivo nunca se regenera: se lee el original y se verifica su integridad.

## Rutas

| Ruta | Rol | Alcance |
|---|---|---|
| `/almacen/solicitudes/<id>/descargar-excel/` | `RESPONSABLE_ALMACEN` | Solo su región |
| `/almacen/excels-historicos/<id>/descargar/` | `RESPONSABLE_ALMACEN` / `ADMIN_PLATAFORMA` | Región / global |

## Requisitos previos

- La solicitud existe, tiene `excel_ruta` no vacía y `excel_hash` de 64 caracteres hexadecimales.
- El alcance del actor cubre la solicitud; si no, `404` sin revelar existencia.
- La solicitud no está en `BORRADOR` (no tiene Excel) ni en `CANCELADA` para el detalle operativo.

## Resolución segura de la ruta

1. `ruta = (Path(settings.MEDIA_ROOT) / solicitud.excel_ruta).resolve()`.
2. `ruta` debe estar dentro de `Path(settings.MEDIA_ROOT).resolve()`; se rechaza cualquier `..`,
   ruta absoluta o enlace que salga de `MEDIA_ROOT`.
3. El archivo debe existir y ser legible.
4. Si falla cualquier paso: `404` con "La solicitud no existe" o `409` con
   "El archivo del Excel no está disponible o fue modificado".

## Verificación

```text
hash_calculado = sha256(contenido_del_archivo)
coincide = hmac.compare_digest(hash_calculado, solicitud.excel_hash)
```

- Se lee el archivo completo en memoria o por bloques y se calcula el hash.
- La comparación es en tiempo constante.
- Si coincide: se construye la respuesta con el mismo contenido leído.
- Si no coincide: se responde `409` y **no** se entrega ningún byte del archivo.
- No se recalcula ni se reescribe el Excel; no se actualiza `excel_hash`.

## Respuesta exitosa

```http
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="asignacion-<id>.xlsx"
X-Content-Type-Options: nosniff
Cache-Control: private, no-store
```

- El nombre no contiene NIF, correo ni nombre del técnico.
- No se expone la ruta física ni el hash en cabeceras.
- El archivo se sirve desde memoria; no se crea una copia temporal persistente.

## Errores

| Situación | Código | Mensaje |
|---|---|---|
| Solicitud inexistente o de otra región | `404` | "La solicitud no existe" |
| Solicitud sin `excel_ruta` | `404` | "La solicitud no existe" |
| Archivo ausente o fuera de `MEDIA_ROOT` | `409` | "El archivo del Excel no está disponible o fue modificado" |
| Hash calculado distinto del registrado | `409` | "El archivo fue modificado, descarga bloqueada" |
| Rol sin permiso | `403` | "No tienes permiso para gestionar despachos" |
| Sin sesión | `302` | Redirección al login |
| Método distinto de `GET` | `405` | — |

## Registro y auditoría

- La descarga exitosa no modifica la solicitud ni el envío; es una operación de lectura.
- La descarga bloqueada se registra en el log de la aplicación con solicitud, actor y motivo, sin
  volcar el hash completo ni la ruta física.
- No se audita cada descarga exitosa para no inflar `RegistroCambio`; si el negocio lo requiere, se
  agrega un evento `SolicitudAsignacion/descarga` sin contenido binario.
- Nunca se audita el contenido del Excel.

## Pruebas de contrato

- `200` con `Content-Type` y `Content-Disposition` correctos y bytes idénticos al archivo archivado.
- `404` por solicitud ajena, sin Excel o inexistente.
- `409` cuando el archivo fue modificado y el hash no coincide.
- `409` cuando el archivo no existe en disco.
- `403` para Admin en la ruta del detalle y `200` en la histórica global.
- La ruta con `../` no permite salir de `MEDIA_ROOT`.
- El archivo descargado conserva el hash original.
