# Contrato: Excel de traspaso de 009

Este contrato concreta `04-contratos/excel-traspaso.md` para la implementación de 009. Corrige dos
puntos del contrato general:

1. El Excel se genera **al enviar** (`BORRADOR→ENVIADA`), no al crear el borrador.
2. El **envío por correo no forma parte de 009**; queda como deuda documental. 009 almacena y sirve
   el archivo para descarga verificada.

## Generación

- Se ejecuta dentro de la transacción de `enviar_solicitud_traspaso`.
- Usa `openpyxl` y la lista canónica de líneas de la solicitud.
- El archivo refleja la lista definitiva; no se regenera después del envío.
- Si la generación o el guardado fallan, se revierte el estado `ENVIADA` y se elimina el archivo
  parcial.
- El nombre es seguro y relativo: `traspasos/<tenant_id>/traspaso-<solicitud_id>-<hash>.xlsx`.
- Se calcula SHA-256 sobre los bytes finales y se guarda en `SolicitudTraspaso.excel_hash`.
- No se guarda el binario en la base de datos ni se audita su contenido.

## Estructura

Cada hoja tiene una sola tabla con una fila por línea del traspaso. La fila 1 es la cabecera y los
datos empiezan en la fila 2.

| Columna | Contenido |
|---|---|
| `Movimiento` | `Z32` en `Desasignación`, `Z31` en `Asignación` |
| `Centro` | `region.almacen.centro` |
| `Almacén` | `region.almacen.codigo_almacen` |
| `Material` | `material.codigo` |
| `Descripción de materiales` | `material.descripcion` |
| `Cantidad` | `1` si la línea es seriada; `linea.cantidad` si no lo es |
| `NIF Técnico` | `tecnico_origen.nif` en `Desasignación`; `tecnico_destino.nif` en `Asignación` |
| `Lote` | `linea.lote` |
| `Serie` | `serie.numero` para seriados; vacío para no seriados |

### Hoja 1: `Desasignación` (Z32)

- `NIF Técnico` es el técnico origen de esa línea.
- Para materiales **no seriados**, agrupa por `(tecnico_origen, material, lote)` y suma `Cantidad`:
  si el técnico A entrega 2 al técnico B y 2 al técnico C del mismo material, la hoja muestra
  **una sola fila de A con cantidad 4**.
- Para materiales **seriados**, cada serie conserva su propia fila.
- No hay bloques de metadatos separados ni tablas adicionales.

### Hoja 2: `Asignación` (Z31)

- Misma estructura y mismas columnas que la hoja 1.
- `NIF Técnico` es el técnico destino de esa línea.
- Para materiales **no seriados**, agrupa por `(tecnico_destino, material, lote)` y suma `Cantidad`:
  si el técnico A entrega 2 y el técnico B entrega 2 del mismo material al técnico C, la hoja
  muestra **una sola fila de C con cantidad 4**.
- Para materiales **seriados**, cada serie conserva su propia fila porque la columna `Serie` es
  distinta.

### Presentación

- Cabecera con `Movimiento`, `Centro` y `Almacén` en azul oscuro; el resto en ámbar.
- Filas de datos con fondo azul claro y bordes finos.
- Filtro automático en `A1:I<n>` y panel congelado en `A2`.
- Anchos de columna fijos para que la tabla se lea sin ajustes manuales.

## Cuadre

- Ambas hojas se generan desde la misma lista canónica.
- Por serie: cada serie aparece exactamente una vez en cada hoja, con el mismo material y lote.
- Por material no seriado: la cantidad total de la hoja 1 es igual a la de la hoja 2.
- El servicio `validar_cuadre_traspaso` compara las dos proyecciones antes de escribir el archivo y
  al confirmar.
- Cualquier diferencia produce `CuadreIncorrecto` y no se guarda el Excel ni se cambia el estado.

## Inmutabilidad y descarga

- El archivo no se edita después de generado.
- La descarga resuelve la ruta relativa bajo `MEDIA_ROOT`/`TRASPASOS_EXCEL_DIR`; rechaza rutas
  absolutas, `..` y salidas del directorio.
- Antes de servir, recalcula SHA-256 y compara con `excel_hash` usando `hmac.compare_digest`.
- Si el hash no coincide, responde `409` con “El archivo fue modificado, descarga bloqueada”.
- Si el archivo no existe, responde `404` con “El archivo no está disponible”.
- `Content-Disposition` usa un nombre seguro `traspaso-<id>.xlsx`; no expone la ruta física.

## Datos que nunca se escriben en el Excel

- Contraseñas, tokens, secretos ni credenciales.
- Datos de otro tenant o región.
- Series de otro técnico o material.
- Rutas absolutas o hashes en celdas.

## Pruebas de contrato

- El archivo generado tiene exactamente dos hojas con los nombres `Desasignación` y `Asignación`.
- Los metadatos Z32/Z31, Centro, Almacén, NIF, tenant, región e ID son correctos.
- Las tablas de seriales y material menor contienen las líneas de la solicitud.
- La hoja 1 y la hoja 2 cuadran por serie, material y cantidad.
- El hash es estable para el mismo contenido y cambia si el archivo se altera.
- Una descarga con hash alterado se bloquea y no expone la ruta física.
- El Excel no contiene secretos ni datos de otro tenant.
- Un fallo de generación revierte el envío y no deja archivo huérfano.
