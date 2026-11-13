# Investigación y decisiones: 010 Conciliación de Stock

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/010-conciliacion-de-stock/spec.md`

Resuelve las incógnitas del plan y fija las decisiones que no deben quedar a criterio de la
implementación. No hay `NEEDS CLARIFICATION` pendientes; las deudas documentales se listan al final.

## Contexto de dependencias

| Dependencia | Estado esperado | Uso en 010 |
|---|---|---|
| 001 — acceso y tenants | Implementada | Cuenta, tenant, región, middleware y auditoría |
| 002 — materiales | Implementada | Catálogo, código, lote y `es_seriado` |
| 003 — técnicos | Implementada | NIF, tenant y región |
| 004 — series | Implementada | `Serie`, `EstadoSerie` y `crear_serie` |
| 005/008 — stock | Implementadas | `StockTecnico`, incrementos/decrementos y auditoría |
| 009 — traspasos | Implementada | Custodia `Serie.tecnico/asignada_en` |
| PostgreSQL 16+ | Infraestructura | Restricciones, bloqueos, transacciones y RLS |

## Decisiones

### D-01. Reporte regional y política de técnicos

- **Decisión**: el reporte de Lari contiene técnicos de varios tenants de la región. Las filas de
  técnicos de **otro tenant de la misma región** se ignoran silenciosamente y nunca se muestran. Las
  filas de técnicos **desconocidos o de otra región** rechazan el archivo completo.
- **Justificación**: es la única forma de que un reporte regional sea usable por cada tenant. La
  spec 010 decía “rechazar técnicos que no pertenecen al tenant” y también “ignorar técnicos de
  otros tenants”; ambas no pueden ser ciertas. Se adopta la regla del contrato regional y se corrige
  la spec. La validación de región evita cargar datos de otra región.
- **Alternativas descartadas**: rechazar todo archivo con técnicos de otros tenants (haría imposible
  la carga); ignorar técnicos desconocidos (ocultaría errores y perdería diferencias).

### D-02. Solo Excel `.xlsx`

- **Decisión**: aceptar únicamente `.xlsx`, leído con `openpyxl`. Rechazar `.xls`, CSV y texto
  tabulado.
- **Justificación**: `openpyxl` no lee `.xls`; agregar `xlrd` sería una dependencia no aprobada. La
  spec menciona CSV/texto en una historia, pero el alcance y el contrato definen Excel. Se corrige la
  historia.
- **Alternativas descartadas**: `.xls` con `xlrd` (dependencia extra); CSV/texto (no es el contrato).

### D-03. Cargar no modifica stock

- **Decisión**: la carga solo lee, valida, compara y persiste la conciliación y sus diferencias. No
  escribe `Serie`, `StockTecnico` ni `StockGeneral`.
- **Justificación**: RF-39, RF-44 y principio VII. El reporte se aprueba humanamente.
- **Alternativas descartadas**: aplicar ajustes al cargar (elimina la revisión humana); guardar solo
  el archivo y recalcular en cada vista (no detecta cambios con facilidad).

### D-04. Estado terminal `INSTALADA`

- **Decisión**: añadir `INSTALADA` a `series.EstadoSerie`. Una serie no reportada para un técnico
  presente pasa a `INSTALADA`, con `tecnico=None` y `asignada_en=None`. No se elimina.
- **Justificación**: la spec y el contrato hablan de “estado instalado” para la liquidación; 012 ya
  espera contar series instaladas. Borrar la serie rompería la trazabilidad y la unicidad histórica.
- **Alternativas descartadas**: borrar la serie (pierde historia); usar `INACTIVO` (011 lo usa para
  bajas, pero 010 necesita distinguir liquidación por reporte); dejar la serie `ASIGNADA` (stock
  incorrecto).

### D-05. Series faltantes, no reportadas y en otro técnico

- **Decisión**:
  - Serie del reporte que no existe en el sistema: se crea `ASIGNADA` con el técnico reportado y
    `asignada_en=ahora`.
  - Serie `ASIGNADA` de un técnico presente que no aparece en el reporte: pasa a `INSTALADA`.
  - Serie existente en el sistema pero con otro técnico: se reasigna al técnico reportado y se
    reinicia `asignada_en`; se muestra como inconsistencia, no como serie nueva.
  - Serie `INSTALADA` que aparece en el reporte: se rechaza con `SerieInstalada`; no se resucita.
  - Serie existente en otro tenant: se rechaza con `SerieFueraTenant`; no se revela ni se reasigna.
- **Justificación**: mantiene la unicidad global, refleja la custodia real y evita duplicar series.
  Reasignar es la única acción coherente cuando el mismo número aparece bajo otro técnico del mismo
  tenant.
- **Alternativas descartadas**: crear una segunda serie (viola unicidad); ignorar la diferencia de
  técnico (deja stock incorrecto); reactivar una instalada (contradice la liquidación).

### D-06. Fungibles a la cantidad reportada

- **Decisión**: para materiales no seriados, el stock del técnico se fija exactamente a “Libre
  utilización” del reporte. La diferencia se aplica con `incrementar_stock_tecnico` o
  `decrementar_stock_tecnico` de 008; si el material no aparece para un técnico presente, la cantidad
  es `0`.
- **Justificación**: RF-64 y contrato §5.2. No se calcula consumo propio. Usar los servicios de 008
  mantiene bloqueo y auditoría.
- **Alternativas descartadas**: calcular consumo (el sistema no lo mide); escribir `StockTecnico`
  directamente (sin auditoría); ignorar materiales ausentes (stock viejo).

### D-07. Stock general intocable

- **Decisión**: 010 nunca lee ni escribe `StockGeneral`. Solo ajusta `StockTecnico` y series.
- **Justificación**: el reporte concilia custodia por técnico; el stock general no forma parte del
  reporte. Principio III y VII.
- **Alternativas descartadas**: devolver series instaladas al stock general (no lo pide el reporte);
  ajustar el general con la diferencia (rompe la separación de niveles).

### D-08. Una sola conciliación en revisión

- **Decisión**: índice único parcial `(tenant)` con `estado=EN_REVISION`. La segunda carga recibe
  `409`.
- **Justificación**: RF-40 y simplicidad de la revisión. La base impone la regla ante concurrencia.
- **Alternativas descartadas**: validar solo en el servicio (dos cargas simultáneas podrían pasar);
  permitir varias (complica la revisión y la aprobación).

### D-09. Diferencias persistidas y huella de stock

- **Decisión**: persistir `DiferenciaSerie`, `DiferenciaCantidad` y `MaterialNoCatalogado`. Guardar
  `huella_stock` (SHA-256 de un JSON canónico de técnicos, materiales, cantidades y series
  afectadas). Al aprobar, recalcular la huella; si cambió, recalcular diferencias y exigir revisión.
- **Justificación**: permite mostrar el detalle sin recalcular en cada vista y detectar cambios de
  stock de forma barata. RF-47.
- **Alternativas descartadas**: calcular todo al vuelo (no persiste el estado revisado); comparar
  fila por fila en cada aprobación (más lento y complejo).

### D-10. Recálculo antes de aprobar

- **Decisión**: si la huella cambió, `aprobar_conciliacion` ejecuta `recalcular_diferencias` en su
  propia transacción, marca `requiere_revision=True` y lanza `HuboCambios`; no aplica ajustes. El
  tenant revisa y vuelve a aprobar.
- **Justificación**: RF-47 y CA-11. El recálculo debe persistir para que la segunda aprobación use
  datos frescos; si se hiciera dentro de la transacción de aprobación y se lanzara la excepción, se
  perdería.
- **Alternativas descartadas**: aplicar con datos viejos (peligroso); recalcular en memoria y no
  persistir (el usuario no ve qué cambió).

### D-11. Aprobación todo o nada con servicios de 008

- **Decisión**: la aprobación es una sola transacción. Bloquea conciliación, tenant, filas de
  `StockTecnico` de los técnicos afectados por `(material, técnico)` y series por `id`; revalida la
  huella dentro del bloqueo; aplica series y stock; audita; cambia a `APROBADA`. Cualquier fallo
  revierte todo.
- **Justificación**: RF-44, RF-46 y principio V. Los servicios de 008 ya bloquean y auditan el stock.
- **Alternativas descartadas**: aplicar por lotes con commits parciales (viola todo o nada); escribir
  stock directamente (sin auditoría).

### D-12. Materiales no catalogados

- **Decisión**: al cargar, un material que no existe se registra en `MaterialNoCatalogado` y no
  impide la carga. La aprobación se bloquea hasta que el material exista y se recalcule.
- **Justificación**: RF-43 y CA-07. Permite corregir el catálogo sin perder el reporte.
- **Alternativas descartadas**: rechazar la carga (obliga a corregir antes de ver diferencias);
  ignorar el material (aprobación incompleta).

### D-13. RLS y aislamiento

- **Decisión**: `Conciliacion` por `tenant_id`/`region_id`; diferencias y materiales no catalogados
  por `tenant_id`. Si 001 no está disponible, deuda registrada y filtrado ORM.
- **Justificación**: principio I y patrón 001/004/005/007/008/009.
- **Alternativas descartadas**: omitir RLS (pierde respaldo); políticas ad hoc sin middleware
  (inoperantes).

### D-14. Sin correo, Celery ni notificaciones

- **Decisión**: 010 no envía correos, no usa Celery ni publica SSE. La carga y aprobación son
  síncronas.
- **Justificación**: la spec no lo pide; se evita duplicar 007 y mantener simplicidad.
- **Alternativas descartadas**: procesar el Excel en background (la respuesta necesitaría sondeo);
  notificar por correo (fuera de spec).

### D-15. Rendimiento

- **Decisión**: leer el Excel en streaming/lotes, indexar por `numero`, `tenant/material` y usar
  `bulk_create` para diferencias. Reporte de 10 000 filas y 1 000 series en tiempo razonable, sin
  N+1.
- **Justificación**: requisito 6.1.
- **Alternativas descartadas**: una consulta por fila (N+1); cargar todo en memoria sin índices.

## Correcciones documentales necesarias

1. `010-conciliacion-de-stock/spec.md` §5.1, §5.3, §5.9, RF-48 y CA-12: filas de otros tenants de la
   misma región se ignoran; técnicos desconocidos o de otra región rechazan el archivo.
2. `010-conciliacion-de-stock/spec.md` HU-18 y §8: solo Excel `.xlsx`; no CSV ni texto.
3. `04-contratos/excel-conciliacion.md` §2, §5.3 y §6: solo `.xlsx`; precisar la política de
   técnicos.
4. `004-recojo-de-materiales/data-model.md`, `plan.md` y `tasks.md`: añadir `INSTALADA` a
   `EstadoSerie` y al check; ampliar la coherencia de custodia.
5. `009-traspaso-entre-tecnicos/data-model.md`: permitir `INSTALADA` sin custodia en
   `serie_tecnico_coherente_estado`.
6. `012-reportes-mensuales/plan.md`: usar `INSTALADA` (no `INSTALADO`) para liquidados.

## Deudas y riesgos abiertos

| Deuda / riesgo | Tratamiento |
|---|---|
| Datos históricos de series sin `INSTALADA` | No se reescriben; el estado se usa desde la aprobación |
| Reporte con series `INSTALADA` | Se rechaza la fila; no se resucita una serie liquidada |
| Serie reportada bajo un técnico ausente | Se reasigna si otro técnico presente la reporta; se ajusta el stock de ambos |
| Serie reportada bajo otro tenant de la región | La fila se ignora; no se muestra ni se modifica |
| RLS no disponible | Deuda registrada; el ORM filtra por tenant/región |
| Reportes muy grandes | Lectura por lotes, índices y prueba de rendimiento |
| Material no catalogado | Se registra; la aprobación se bloquea hasta corregir y recalcular |

## Conclusión

No quedan incógnitas bloqueantes. La conciliación carga sin tocar stock, persiste diferencias
revisables, aprueba todo o nada con prevalencia del reporte, usa `INSTALADA` para liquidar series y
mantiene el stock general intacto.
