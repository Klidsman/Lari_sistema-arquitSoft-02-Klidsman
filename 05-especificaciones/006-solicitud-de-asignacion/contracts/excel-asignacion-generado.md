# Contrato del Excel de asignación generado

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

Contrato del archivo `.xlsx` que 006 genera al enviar una solicitud y que 007 envía al almacén.
Complementa `04-contratos/excel-asignacion.md`; ante contradicción, este documento prevalece para
el momento de generación y el formato verificable.

## Cuándo se genera

| Evento | ¿Genera Excel? |
|---|---|
| Guardar borrador (`BORRADOR`) | No |
| Enviar (`BORRADOR`→`ENVIADA`) | Sí, dentro de la misma transacción |
| Crear y enviar (`accion=enviar`) | Sí, dentro de la misma transacción |
| Cancelar (`BORRADOR`→`CANCELADA`) | No |
| Confirmar o rechazar (007) | No; se usa el archivo existente |
| Consultar el detalle | No; solo se lee la ruta y el hash |

El Excel no se regenera ni se modifica después del envío. Si el envío falla, el archivo se elimina
y no queda solicitud `ENVIADA`.

## Formato del archivo

- Tipo: Office Open XML (`.xlsx`), generado con `openpyxl`.
- Sin macros, sin fórmulas y sin enlaces externos.
- Nombre: `<uuid>.xlsx`; no contiene NIF, nombre del técnico, código del tenant ni fecha.
- Ruta: `MEDIA_ROOT/<ASIGNACIONES_EXCEL_DIR>/<tenant.codigo>/<solicitud.id>/<uuid>.xlsx`.
- `ASIGNACIONES_EXCEL_DIR` por defecto `asignaciones`.
- En base se guarda `excel_ruta` relativa a `MEDIA_ROOT`, nunca una ruta absoluta.
- El archivo es de solo lectura para la aplicación una vez escrito.

## Metadatos de la solicitud

Hoja de metadatos o bloque superior, con etiqueta y valor:

| Etiqueta | Valor | Fuente |
|---|---|---|
| Movimiento | `settings.MOVIMIENTO_ASIGNACION` (`Z31`) | Configuración |
| Centro | `region.almacen.centro` | Almacén de la región del tenant (001) |
| Almacén | `region.almacen.codigo_almacen` | Almacén de la región del tenant (001) |
| NIF | `solicitud.tecnico.nif` | Técnico (003) |
| Fecha de solicitud | `solicitud.fecha.isoformat()` | Solicitud |
| Tenant | `tenant.codigo` | Sesión (001) |
| Región | `region.codigo` | `tenant.region` (001) |
| ID de solicitud | `solicitud.id` | Solicitud |

- `Centro` y `Almacén` no se escriben como literales en el código; se leen del almacén de la región.
- Los valores `PR05` y `BE03` de la spec son datos de ejemplo de una región; el contrato exige que
  provengan de la configuración real del almacén.
- El NIF se copia del técnico; no se acepta del formulario ni del request.
- No se incluye `tenant_id`, `region_id`, correo, teléfono ni dirección.

## Tabla de seriales

Una fila por línea seriada, en el orden de las líneas de la solicitud:

| Columna | Valor |
|---|---|
| Código | `material.codigo` |
| Descripción | `material.descripcion` |
| Lote | `linea.lote` (copiado de `material.lote`) |
| Serie | `linea.serie.numero` |
| Cantidad | `1` |

- El número de serie corresponde a una `Serie` del tenant y del material.
- No se incluyen series de otro tenant ni series que no estén en la solicitud.
- Las series deben estar `RESERVADA` al momento de generar el archivo.

## Tabla de material menor (no seriado)

Una fila por línea no seriada, en el orden de las líneas:

| Columna | Valor |
|---|---|
| Código | `material.codigo` |
| Descripción | `material.descripcion` |
| Lote | `linea.lote` (copiado de `material.lote`) |
| Cantidad | `linea.cantidad` |

- Una sola fila por material dentro de la solicitud.
- La cantidad es un entero mayor que 0.

## Integridad

- Se calcula `hashlib.sha256(contenido).hexdigest()` sobre los bytes exactos del archivo escrito.
- `excel_hash` guarda 64 caracteres hexadecimales en minúsculas.
- `excel_generado_en` guarda la marca de tiempo UTC de generación.
- El hash se audita junto con la ruta relativa; no se audita el contenido.
- 007 verifica el hash antes de enviar y al descargar; 006 no expone ruta de descarga ni de envío.

## Errores

| Situación | Resultado |
|---|---|
| `openpyxl` falla al escribir | `500` "No se pudo generar el Excel de asignación"; se revierte la transacción |
| El almacén de la región no tiene `centro` o `codigo_almacen` | `500` interno y se registra la inconsistencia; no se genera un Excel incompleto |
| El archivo no se puede escribir en disco | `500` interno; se revierte la transacción |
| La solicitud no está `ENVIADA` | No se genera; el servicio exige la transición en curso |

- Los mensajes al usuario no incluyen rutas del sistema, trazas ni detalles de `openpyxl`.
- No se sirve el archivo por una ruta de 006.

## Verificación en pruebas

- Leer el `.xlsx` con `openpyxl` y comprobar etiquetas y valores de metadatos.
- Comprobar que `Movimiento="Z31"`, `Centro` y `Almacén` coinciden con el almacén de la región.
- Comprobar que el NIF coincide con `Tecnico.nif` y no con un valor inyectado en el `POST`.
- Comprobar una fila por serie y una por material no seriado.
- Recalcular el SHA-256 y compararlo con `excel_hash`.
- Comprobar que no aparecen datos de otro tenant ni de otra solicitud.
