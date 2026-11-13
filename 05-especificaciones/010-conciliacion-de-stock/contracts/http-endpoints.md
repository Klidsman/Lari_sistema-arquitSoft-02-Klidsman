# Contrato: endpoints de 010

Todas las rutas exigen sesión y rol `USUARIO_TENANT`; el tenant y la región salen de la sesión. No se
acepta `tenant_id`, `region_id` ni estado desde el cliente.

| Ruta | Método | Respuesta |
|---|---|---|
| `/conciliaciones/` | `GET` | `200` con listado paginado y filtro por estado |
| `/conciliaciones/cargar/` | `GET` | `200` con formulario de carga |
| `/conciliaciones/cargar/` | `POST` | `302` al detalle si se crea; `400` por archivo inválido; `409` si ya hay una en revisión |
| `/conciliaciones/<id>/` | `GET` | `200` con detalle, diferencias, alertas y aviso de cambios |
| `/conciliaciones/<id>/recalcular/` | `POST` | `302` al detalle; `409` si no está `EN_REVISION` |
| `/conciliaciones/<id>/aprobar/` | `POST` | `302` al detalle; `409` por estado, materiales faltantes o cambios |
| `/conciliaciones/<id>/rechazar/` | `POST` | `302` al detalle; `400` por motivo inválido; `409` por estado |

- No existe `GET` para recalcular, aprobar ni rechazar; devuelven `405`.
- Un recurso de otro tenant devuelve `404`; un rol incorrecto, `403`.
- Un archivo que no es `.xlsx`, no tiene `GENERAL` o no tiene columnas devuelve `400`.
- Una segunda carga con una conciliación `EN_REVISION` devuelve `409` con “Ya hay una conciliación en
  revisión”.
- La aprobación con materiales no catalogados devuelve `409` con “Aprobación bloqueada: hay
  materiales que no existen en el catálogo”.
- La aprobación con stock cambiado devuelve `409` con “Hubo cambios, revise de nuevo” y deja la
  conciliación recalculada y `requiere_revision=True`.

## Formulario de carga

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `archivo` | file | Sí | `.xlsx`, tamaño máximo configurable, no vacío |

- No se envían tenant, región, estado, fechas ni usuario.
- El nombre se guarda con `Path(nombre).name`, sin rutas.
- El hash se calcula sobre los bytes originales antes de abrir el Excel.

## Detalle

- Cabecera: estado, fecha de carga, archivo, hash, `requiere_revision`.
- Diferencias de series:
  - “En reporte, no en sistema”.
  - “En sistema, no en reporte”.
  - “En otro técnico” dentro de “Técnicos con inconsistencias”.
- Diferencias de cantidades por técnico/material.
- Materiales no catalogados, si existen.
- Alertas categorizadas: material ajeno, técnicos con inconsistencias, series faltantes.
- Acciones: aprobar, rechazar, recalcular, según estado.
- Aviso visible si `requiere_revision`.

## Errores

| Situación | Código | Mensaje |
|---|---|---|
| Sin sesión | `302` a login | — |
| Rol incorrecto | `403` | “No tienes permiso para cargar conciliaciones” |
| Conciliación ajena | `404` | “La conciliación no existe” |
| Archivo no `.xlsx` | `400` | “El archivo debe ser un Excel .xlsx válido” |
| Hoja `GENERAL` ausente | `400` | “El archivo no contiene la hoja GENERAL” |
| Columnas faltantes | `400` | “Faltan columnas requeridas en la hoja GENERAL” |
| Técnico desconocido o de otra región | `400` | “El reporte contiene técnicos que no pertenecen a la región” |
| NIF inválido | `400` | “El NIF del técnico no tiene el formato LAXXXX” |
| Serie inválida o duplicada | `400` | “La serie no tiene el formato correcto” / “La serie está duplicada en el reporte” |
| Serie instalada reportada | `400` | “La serie está instalada y no puede reasignarse” |
| Ya hay una en revisión | `409` | “Ya hay una conciliación en revisión” |
| Estado inválido | `409` | “Solo se puede aprobar o rechazar una conciliación en revisión” |
| Material no catalogado al aprobar | `409` | “Aprobación bloqueada: hay materiales que no existen en el catálogo” |
| Huella de stock cambiada | `409` | “Hubo cambios, revise de nuevo” |
| Archivo no disponible | `404` | “El archivo no está disponible” |

## Pruebas de contrato

- Cada ruta devuelve los códigos indicados para rol correcto, ajeno, estado inválido y archivo
  inválido.
- `GET` en acciones devuelve `405`.
- El formulario ignora `tenant_id`/`region_id` enviados.
- El detalle agrupa las diferencias y muestra las alertas.
- La aprobación con cambios deja `requiere_revision=True` y no aplica ajustes.
- Ninguna respuesta revela datos de otro tenant ni rutas físicas.
