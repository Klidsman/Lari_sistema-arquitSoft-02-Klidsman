# Contrato: servicios de logística inversa

Los servicios viven en `logistica_inversa/services.py`; las vistas solo orquestan.

## Tipos

| Tipo | Definición |
|---|---|
| `tenant` | `tenants.Tenant` de la sesión |
| `tecnico` | `tecnicos.Tecnico` del tenant |
| `series` | Lista de `series.Serie` |
| `actor` | `acceso.Usuario` de la sesión |
| `fecha` | `date` de devolución |

## Excepciones

| Excepción | Mensaje |
|---|---|
| `PermisoDenegado` | “No tienes permiso para registrar devoluciones” |
| `TecnicoNoExiste` | “El técnico no existe o no pertenece al tenant” |
| `SerieNoEnTecnico` | “La serie no está asignada al técnico” |
| `SerieNoDisponible` | “La serie no está disponible para la baja” |
| `SerieReservada` | “La serie está reservada en otro traspaso” |
| `SerieYaInactiva` | “La serie ya fue dada de baja” |
| `SerieInstalada` | “La serie está instalada y no puede devolverse ni darse de baja” |
| `SerieFueraTenant` | “La serie no pertenece a este tenant” |
| `CausaRequerida` | “Debe indicar la causa de la baja” |
| `CausaInvalida` | “La causa de la baja no es válida” |
| `FechaInvalida` | “La fecha de devolución no es válida” |
| `SinSeries` | “Debe seleccionar al menos una serie” |
| `NoEncontrado` | “La devolución no existe” |
| `ArchivoNoDisponible` | “El acta no está disponible” |
| `HashNoCoincide` | “El acta fue modificada, descarga bloqueada” |

## Validación de alcance

### `validar_cuenta_tenant(actor, tenant) -> None`

- Exige `USUARIO_TENANT`, cuenta activa, tenant activo y `actor.tenant_id == tenant.id`.
- Si no, `PermisoDenegado`.

### `validar_tecnico(tenant, tecnico) -> None`

- Existe, pertenece al tenant y a la región; si no, `TecnicoNoExiste`.

## Validación de series

### `validar_serie_para_devolucion(serie, tecnico) -> None`

- Mismo tenant que el técnico; si no, `SerieFueraTenant`.
- `estado=ASIGNADA` y `serie.tecnico_id == tecnico.id`; si no, `SerieNoEnTecnico`.
- No referenciada por una `LineaTraspaso` de solicitud `ENVIADA`; si lo está, `SerieReservada`.
- No `INSTALADA` ni `INACTIVA`; si lo está, `SerieInstalada`/`SerieYaInactiva`.

### `validar_serie_para_baja(serie, tenant) -> None`

- Mismo tenant; si no, `SerieFueraTenant`.
- `estado=ASIGNADA` con técnico/fecha, o `estado=DISPONIBLE` sin técnico; si no,
  `SerieNoDisponible`.
- No `RESERVADA` (`SerieReservada`), `INSTALADA` (`SerieInstalada`) ni `INACTIVA`
  (`SerieYaInactiva`).

### `validar_fecha_devolucion(fecha) -> None`

- No futura; si lo es, `FechaInvalida`.

## Operaciones

### `registrar_devolucion(tenant, tecnico, fecha, series, observaciones, actor) -> Devolucion`

1. `validar_cuenta_tenant`, `validar_tecnico`, `validar_fecha_devolucion`; exigir al menos una serie.
2. Validar cada serie con `validar_serie_para_devolucion`; sin duplicados.
3. `transaction.atomic`:
   - Bloquear `Tenant`, `StockGeneral` por `material_id`, `StockTecnico` del técnico por
     `material_id` y series por `id`.
   - Revalidar series y stock.
   - Crear `Devolucion` con `region=tenant.region` y `creado_por=actor`.
   - Crear `LineaDevolucion` por serie con `tenant`, material, descripción y lote.
   - Por serie: `estado=DISPONIBLE`, `tecnico=None`, `asignada_en=None`; auditar estado y custodia.
   - Por material: `decrementar_stock_tecnico(tecnico, material, n, actor)` e
     `incrementar_stock_general(tenant, material, n, actor)`.
   - Generar el acta, guardar ruta/hash y auditar `Devolucion/acta`.
   - Auditar `Devolucion/alta` y `LineaDevolucion/alta`.
4. Si falla el acta, revertir y borrar el archivo parcial.
5. Devolver la devolución.

### `registrar_baja_equipo(tenant, serie, causa, observaciones, actor) -> BajaEquipo`

1. `validar_cuenta_tenant`; la serie debe existir en el tenant.
2. Validar `causa` en `AVERIA`/`MIGRACION`/`OTRO`; si falta, `CausaRequerida`; si no es válida,
   `CausaInvalida`.
3. `validar_serie_para_baja`.
4. `transaction.atomic`:
   - Bloquear `Tenant`, la fila de stock correspondiente y la serie.
   - Revalidar estado/custodia/stock.
   - Crear `BajaEquipo` con `region=tenant.region`, material, causa y observaciones.
   - Si `ASIGNADA`: `decrementar_stock_tecnico(tecnico, material, 1, actor)`.
   - Si `DISPONIBLE`: `decrementar_stock_general(tenant, material, 1, actor)`.
   - Pasar la serie a `INACTIVA`, limpiar `tecnico`/`asignada_en`; auditar estado y custodia.
   - Auditar `BajaEquipo/alta`.
5. Devolver la baja.

### `generar_acta_devolucion(devolucion) -> tuple[str, str]`

- Genera un `.xlsx` de una hoja con metadatos y tabla.
- Guarda en `ACTAS_DIR`/`MEDIA_ROOT` con nombre relativo seguro.
- Calcula SHA-256 y actualiza `acta_ruta`/`acta_hash`/`acta_generada_en`.
- Se invoca dentro de la transacción de registro; no se regenera.

### `verificar_hash_acta(devolucion, contenido: bytes) -> None`

- Recalcula SHA-256 y compara con `hmac.compare_digest`.
- Si no coincide, `HashNoCoincide`.

## Consultas

- `listar_devoluciones(tenant, fecha_desde=None, fecha_hasta=None)`.
- `obtener_devolucion(tenant, devolucion_id)`.
- `detalle_devolucion(devolucion)`.
- `listar_bajas(tenant, causa=None)`.
- `obtener_baja(tenant, baja_id)`.

## Reglas transversales

- Toda escritura ocurre en una transacción y audita en la misma transacción.
- Nunca se acepta `tenant_id`/`region_id` del cliente.
- 011 no elimina series, no crea series y no toca conciliaciones.
- No se usan permisos Django por cadena.
- No se usa `F()` ciego para stock; se usan los servicios de 008.

## Pruebas de contrato

- Cada firma, retorno y excepción coincide con este documento.
- Devolución: serie no asignada, reservada, instalada o de otro tenant se rechaza.
- Baja: causa obligatoria, serie reservada/instalada/inactiva se rechaza; stock del nivel correcto.
- Acta: se genera dentro de la transacción y un fallo revierte la devolución.
- Ningún servicio expone datos de otro tenant.
