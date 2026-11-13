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

### Hoja 1: `Desasignación` (Z32)

Metadatos:

| Campo | Valor |
|---|---|
| Movimiento | `Z32` |
| Centro | `region.almacen.centro` |
| Almacén | `region.almacen.codigo_almacen` |
| NIF | `tecnico_origen.nif` |
| Fecha de solicitud | `solicitud.fecha` |
| Tenant | `solicitud.tenant.codigo` |
| Región | `solicitud.region.codigo` |
| ID de solicitud | `solicitud.id` |

Tabla de seriales:

| Columna | Contenido |
|---|---|
| Código de material | `material.codigo` |
| Descripción | `material.descripcion` |
| Lote | `linea.lote` |
| Serie | `serie.numero` |
| Cantidad | `1` |

Tabla de material menor:

| Columna | Contenido |
|---|---|
| Código de material | `material.codigo` |
| Descripción | `material.descripcion` |
| Lote | `linea.lote` |
| Cantidad | `linea.cantidad` agregada por material |

### Hoja 2: `Asignación` (Z31)

- Misma estructura y mismas líneas que la hoja 1.
- Movimiento `Z31`.
- NIF del `tecnico_destino`.
- El resto de metadatos es idéntico.

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

- Contraseñas, tokens, secretos TOTP ni credenciales.
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
