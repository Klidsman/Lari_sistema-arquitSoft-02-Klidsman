# Contrato: servicios de conciliación

Los servicios viven en `conciliaciones/services.py`; las vistas solo orquestan. No hay lógica de
negocio en modelos, formularios ni plantillas.

## Tipos

| Tipo | Definición |
|---|---|
| `tenant` | `tenants.Tenant` de la sesión |
| `region` | `tenants.Region` de `tenant.region` |
| `actor` | `acceso.Usuario` de la sesión |
| `conciliacion` | `conciliaciones.Conciliacion` |
| `archivo` | Archivo `.xlsx` subido (nombre y bytes) |

```python
@dataclass(frozen=True)
class ReporteLeido:
    filas: list[FilaReporte]
    errores: list[ErrorReporte]
    columnas: list[str]
    total_filas: int

@dataclass(frozen=True)
class FilaReporte:
    material_codigo: str
    lote: str
    libre_utilizacion: int | None
    numero_serie: str | None
    nif: str
    descripcion: str
    fila: int
```

## Excepciones

| Excepción | Mensaje |
|---|---|
| `PermisoDenegado` | “No tienes permiso para cargar conciliaciones” |
| `ConciliacionEnRevision` | “Ya hay una conciliación en revisión” |
| `FormatoInvalido` | “El archivo debe ser un Excel .xlsx válido” |
| `HojaGeneralAusente` | “El archivo no contiene la hoja GENERAL” |
| `ColumnasFaltantes` | “Faltan columnas requeridas en la hoja GENERAL” |
| `TecnicosFueraRegion` | “El reporte contiene técnicos que no pertenecen a la región” |
| `TecnicoFormatoInvalido` | “El NIF del técnico no tiene el formato LAXXXX” |
| `MaterialNoExiste` | “El reporte contiene materiales que no existen en el catálogo” |
| `SerieFormatoInvalido` | “La serie no tiene el formato correcto” |
| `SerieDuplicada` | “La serie está duplicada en el reporte” |
| `SerieInstalada` | “La serie está instalada y no puede reasignarse” |
| `SerieFueraTenant` | “La serie no pertenece a este tenant” |
| `EstadoConciliacionInvalido` | “Solo se puede aprobar o rechazar una conciliación en revisión” |
| `AprobacionBloqueada` | “Aprobación bloqueada: hay materiales que no existen en el catálogo” |
| `HuboCambios` | “Hubo cambios, revise de nuevo” |
| `NoEncontrado` | “La conciliación no existe” |
| `ArchivoNoDisponible` | “El archivo no está disponible” |

## Lectura y validación

### `leer_reporte(archivo) -> ReporteLeido`

- Solo `.xlsx`; `.xls`, CSV y texto producen `FormatoInvalido`.
- Abre con `openpyxl` y lee solo la hoja `GENERAL`; si no existe, `HojaGeneralAusente`.
- Exige columnas `Material`, `Lote`, `Libre utilización`, `Número de serie`, `Nº ident.fis.1`,
  `Texto breve material`; si faltan, `ColumnasFaltantes`.
- Normaliza encabezados y valores; no escribe en base.

### `clasificar_tecnicos(tenant, filas) -> ClasificacionTecnicos`

- Valida formato `LAXXXX`; si no, `TecnicoFormatoInvalido`.
- Técnico del tenant: `presentes`.
- Técnico de otro tenant de la misma región: `ignorados`.
- Técnico desconocido o de otra región: `TecnicosFueraRegion` y rechazo completo.
- No revela a qué tenant pertenece un NIF ignorado.

### `validar_filas(tenant, filas) -> ReporteValidado`

- Material existente; si no, se registra en `MaterialNoCatalogado` (no bloquea la carga).
- Serie con formato; duplicada en el reporte; material seriado con serie y no seriado sin serie.
- Cantidad no seriada entera `>= 0`.
- Serie existente `INSTALADA`: `SerieInstalada`.
- Serie existente en otro tenant: `SerieFueraTenant`; no se revela el tenant.
- Agrupa filas por técnico y material.

## Comparación

### `calcular_huella_stock(tenant, tecnicos_presentes) -> str`

- SHA-256 de un JSON canónico y ordenado con técnico, material, `StockTecnico.cantidad`, número de
  serie, estado y técnico custodio.
- Solo técnicos presentes del tenant; sin stock general ni otros tenants.

### `comparar_series(tenant, tecnicos_presentes, filas) -> list[DiferenciaSerie]`

- `EN_REPORTE_NO_SISTEMA`: número inexistente; se creará.
- `EN_SISTEMA_NO_REPORTE`: serie `ASIGNADA` de un técnico presente no reportada; se instalará.
- `EN_OTRO_TECNICO`: número existente con otro técnico; se reasignará.
- Serie `INSTALADA` reportada: `SerieInstalada`.

### `comparar_cantidades(tenant, tecnicos_presentes, filas) -> list[DiferenciaCantidad]`

- Solo no seriados.
- Material ausente para técnico presente: `cantidad_reporte=0`.
- Técnico ausente: no se compara.

## Carga

### `crear_conciliacion(tenant, archivo, actor) -> Conciliacion`

1. `validar_cuenta_tenant`, `validar_puede_cargar`.
2. `leer_reporte`, `clasificar_tecnicos`, `validar_filas`.
3. Comparar series/cantidades y calcular huella.
4. Guardar archivo con nombre relativo seguro y hash SHA-256.
5. `transaction.atomic`: crear `Conciliacion` `EN_REVISION`, diferencias y materiales no catalogados;
   auditar `Conciliacion/alta` y `Conciliacion/archivo`.
6. No modificar series, `StockTecnico` ni `StockGeneral`.
7. Devolver la conciliación.

### `recalcular_diferencias(conciliacion, actor) -> Conciliacion`

1. Exigir `EN_REVISION`.
2. Releer el archivo guardado, revalidar, comparar y recalcular huella.
3. `transaction.atomic`: reemplazar diferencias y materiales no catalogados; actualizar huella y
   `requiere_revision=True`; auditar `Conciliacion/recalculo`.
4. No modificar stock.

## Aprobación

### `aprobar_conciliacion(conciliacion, actor) -> ResultadoConciliacion`

1. `validar_cuenta_tenant` y exigir `EN_REVISION`.
2. Calcular huella actual; si difiere:
   - `recalcular_diferencias` en su propia transacción.
   - Auditar `Conciliacion/hubo_cambios`.
   - Lanzar `HuboCambios`; no aplicar ajustes.
3. Si hay `MaterialNoCatalogado`, `AprobacionBloqueada`.
4. `transaction.atomic`:
   - Bloquear conciliación, tenant, `StockTecnico` de técnicos afectados por
     `(material_id, tecnico_id)` y series por `id`.
   - Recalcular huella dentro del bloqueo; abortar con `HuboCambios` si cambió.
   - Revalidar técnicos, materiales, series y diferencias.
   - Series del reporte inexistentes: crear con `series.services.crear_serie(..., estado=ASIGNADA,
     tecnico=tecnico, asignada_en=ahora)`; auditar `Serie/alta`.
   - Series en otro técnico: reasignar `tecnico` y reiniciar `asignada_en`; auditar
     `Serie/tecnico` y `Serie/asignada_en`.
   - Series `ASIGNADA` de técnicos presentes no reportadas: `INSTALADA`, limpiar custodia; auditar
     `Serie/estado`.
   - No seriados: fijar `StockTecnico` a la cantidad reportada (0 si el material no aparece para un
     técnico presente), usando incrementos/decrementos de 008.
   - Seriados: fijar `StockTecnico` al número de series `ASIGNADA` del técnico/material, usando 008
     para el delta.
   - Cambiar a `APROBADA`, `fecha_aprobacion`, `aprobado_por`, `requiere_revision=False`; auditar
     `Conciliacion/estado`.
5. No tocar `StockGeneral`; no eliminar series.
6. Devolver conteos y ajustes.

### `rechazar_conciliacion(conciliacion, actor, motivo="") -> Conciliacion`

- Exigir `EN_REVISION`.
- `transaction.atomic`: `RECHAZADA`, `fecha_rechazo`, `motivo_rechazo`; auditar estado y motivo.
- No modificar series ni stock.

## Resultado

```python
@dataclass(frozen=True)
class ResultadoConciliacion:
    conciliacion_id: int
    series_creadas: list[int]
    series_instaladas: list[int]
    series_reasignadas: list[int]
    ajustes_cantidad: list[AjusteCantidad]
    fecha_aprobacion: datetime
```

`AjusteCantidad`: `tecnico_id`, `material_id`, `cantidad_anterior`, `cantidad_nueva`.

## Consultas

- `listar_conciliaciones(tenant, estado=None)`.
- `obtener_conciliacion(tenant, conciliacion_id)`.
- `detalle_conciliacion(conciliacion)`.
- `alertas_conciliacion(conciliacion)`.

## Reglas transversales

- Toda escritura ocurre en una transacción y audita en la misma transacción.
- Nunca se acepta `tenant_id`/`region_id` del cliente.
- 010 no toca `StockGeneral`, no elimina series y no reabre conciliaciones.
- No se usan permisos Django por cadena.
- No se usa `F()` ciego para stock; se usan los servicios de 008.

## Pruebas de contrato

- Cada firma, retorno y excepción coincide con este documento.
- Cargar no cambia stock; aprobar aplica todo; rechazar no cambia nada.
- La huella detecta cambios y exige revisión.
- Los materiales no catalogados bloquean la aprobación, no la carga.
- Un fallo de auditoría o de serie revierte toda la aprobación.
- Ningún servicio expone datos de otro tenant.
