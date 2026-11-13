# Contrato: acta de devolución de 011

Concreta `04-contratos/acta-devoluciones.md` para la implementación de 011.

## Generación

- Se genera automáticamente al registrar una devolución, dentro de la misma transacción.
- No se genera a demanda ni se regenera; es inmutable.
- Usa `openpyxl` y una sola hoja.
- Se guarda en `ACTAS_DIR`/`MEDIA_ROOT` con nombre relativo seguro:
  `actas/<tenant_id>/devolucion-<id>-<hash>.xlsx`.
- Se calcula SHA-256 sobre los bytes finales y se guarda en `Devolucion.acta_hash`.
- Si falla la generación o el guardado, se revierte la devolución y se elimina el archivo parcial.
- El binario no se guarda en la base ni se audita.

## Metadatos

| Campo | Valor |
|---|---|
| Tenant | `devolucion.tenant.codigo` |
| Región | `devolucion.region.codigo` |
| Fecha de generación | Fecha y hora de generación |
| ID de devolución | `devolucion.id` |

## Tabla

| Columna | Contenido |
|---|---|
| NIF | `devolucion.tecnico.nif` |
| Material | `linea.material.codigo` |
| Descripción | `linea.descripcion` |
| Serie | `linea.serie.numero` |
| Fecha de devolución | `devolucion.fecha` |

- Una fila por `LineaDevolucion`.
- Las series se ordenan por número para que el acta sea estable.
- No se incluyen causas de baja: las bajas no generan acta en 011.

## Inmutabilidad y descarga

- El archivo no se edita después de generado.
- La descarga resuelve la ruta relativa y rechaza rutas absolutas, `..` y salidas del directorio.
- Antes de servir, recalcula SHA-256 y compara con `acta_hash` usando `hmac.compare_digest`.
- Si el hash no coincide, `409` “El acta fue modificada, descarga bloqueada”.
- Si el archivo no existe, `404` “El acta no está disponible”.
- `Content-Disposition` usa `acta-devolucion-<id>.xlsx`; no expone la ruta física.
- El sistema no envía el acta por correo; el tenant la descarga y la envía a Lari.

## Prohibiciones

- Contraseñas, tokens, secretos TOTP ni credenciales.
- Datos de otro tenant o región.
- Series de otro técnico o material.
- Rutas absolutas o hashes en celdas.
- Varias hojas o metadatos SAP complejos.

## Pruebas de contrato

- El acta tiene una sola hoja y los metadatos correctos.
- La tabla contiene todas las series devueltas, con NIF, material, descripción, serie y fecha.
- El hash es estable para el mismo contenido y cambia si el archivo se altera.
- La descarga con hash alterado se bloquea y no expone la ruta física.
- Un fallo de generación revierte la devolución y no deja archivo huérfano.
- El acta no contiene secretos ni datos de otro tenant.
