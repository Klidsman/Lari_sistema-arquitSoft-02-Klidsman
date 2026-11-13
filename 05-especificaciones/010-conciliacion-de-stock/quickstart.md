# Quickstart y validación: 010 Conciliación de Stock

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/010-conciliacion-de-stock/spec.md`

Guía para validar la carga del reporte de Lari, la comparación de series y cantidades, las alertas, la
aprobación/rechazo y el recálculo cuando el stock cambia. Los detalles de datos están en
`data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Python 3.12+.
- PostgreSQL 16+ con rol sin `SUPERUSER` ni `BYPASSRLS`.
- Specs 001, 002, 003, 004, 005, 006, 007, 008 y 009 implementadas hasta lo que 010 consume.
- `series.Serie` con `tecnico`/`asignada_en` y estado `INSTALADA` (migración de 010/004).
- `StockTecnico` y servicios `incrementar_stock_tecnico`/`decrementar_stock_tecnico` de 008.
- App `conciliaciones` registrada en `config/settings/base.py` y migraciones aplicadas.
- Un reporte `.xlsx` de prueba con hoja `GENERAL` y las columnas del contrato.

Si falta cualquiera, la validación se detiene y se reporta.

## Configuración inicial

Seguir la configuración de `05-especificaciones/001-tenants-y-acceso/quickstart.md` (venv,
dependencias, PostgreSQL y `.env`). Después:

```powershell
python manage.py migrate
python manage.py check
```

Comprobar las tablas y el estado terminal:

```powershell
python manage.py shell -c "from conciliaciones.models import Conciliacion, DiferenciaSerie, DiferenciaCantidad, MaterialNoCatalogado; from series.models import EstadoSerie; print(Conciliacion._meta.db_table, EstadoSerie.INSTALADA)"
```

**Esperado**: `conciliaciones_conciliacion` y `INSTALADA`, sin errores.

No se crean conciliaciones por migración. Los datos de prueba se crean con fixtures o con el flujo
normal de 004/005/008/009.

## Pruebas automatizadas

```powershell
# Excel, servicios y comparación
pytest tests/unit/test_conciliacion_excel.py tests/unit/test_conciliacion_servicios.py
pytest tests/unit/test_conciliacion_comparacion.py

# Integración
pytest tests/integration/test_conciliacion_carga.py tests/integration/test_conciliacion_aprobacion.py
pytest tests/integration/test_conciliacion_rechazo.py tests/integration/test_conciliacion_recalculo.py
pytest tests/integration/test_conciliacion_concurrencia.py tests/integration/test_conciliacion_auditoria.py

# Contrato HTTP
pytest tests/contract/test_conciliacion_http.py

# Todo 010
pytest -k "conciliacion"

# Cobertura
pytest --cov=conciliaciones
```

Las pruebas requieren PostgreSQL real; validan restricciones parciales, bloqueos, RLS y concurrencia.

## Escenarios de validación

Los escenarios usan pruebas con datos propios: tenant, región, técnicos, materiales seriados/no
seriados, stock y series. El detalle de firmas está en `contracts/servicios-conciliacion.md`.

### CA-01: Carga crea conciliación en revisión

1. Cargar un `.xlsx` válido con hoja `GENERAL`.
2. Consultar la conciliación y el stock.

**Esperado**: estado `EN_REVISION`, archivo y hash guardados, diferencias creadas, stock y series
intactos.

Prueba principal: `test_cargar_reporte_crea_conciliacion_en_revision`.

### CA-02: Solo una conciliación en revisión

1. Cargar un reporte válido.
2. Intentar cargar otro sin aprobar/rechazar el primero.

**Esperado**: `409` “Ya hay una conciliación en revisión”; el índice parcial impide dos.

Prueba principal: `test_solo_una_conciliacion_en_revision`.

### CA-03: Técnico ausente se ignora

1. Tener un técnico con stock que no aparece en el reporte.
2. Cargar y aprobar.

**Esperado**: no se generan diferencias por ese técnico ni se modifica su stock.

Prueba principal: `test_tecnico_ausente_se_ignora`.

### CA-04: Material ausente se asume 0

1. Tener un técnico presente con un material no seriado que no aparece en el reporte.
2. Cargar y aprobar.

**Esperado**: se registra `cantidad_reporte=0` y, al aprobar, el stock de ese material queda en 0.

Prueba principal: `test_material_ausente_se_asume_0`.

### CA-05: Diferencias de series se muestran

1. Reportar una serie que no existe y omitir una serie asignada a un técnico presente.
2. Consultar el detalle.

**Esperado**: dos grupos con listado de series: “En reporte, no en sistema” y “En sistema, no en
reporte”. Las series en otro técnico se muestran como inconsistencia.

Prueba principal: `test_diferencias_series_se_muestran_dos_grupos`.

### CA-06: Alertas categorizadas

1. Cargar un reporte con material ajeno, un técnico con varias diferencias y series faltantes.
2. Consultar las alertas.

**Esperado**: categorías “material ajeno”, “técnicos con inconsistencias” y “series faltantes”.

Prueba principal: `test_alertas_categorizadas`.

### CA-07: Aprobación bloquea si material no existe

1. Cargar un reporte con un código de material inexistente.
2. Intentar aprobar.

**Esperado**: la carga se permite y registra `MaterialNoCatalogado`; la aprobación devuelve `409`
“Aprobación bloqueada: hay materiales que no existen en el catálogo”. Tras crear el material y
recalcular, se puede aprobar.

Prueba principal: `test_aprobacion_bloquea_si_material_no_existe`.

### CA-08: Aprobación todo o nada

1. Preparar una aprobación con varias series y cantidades.
2. Forzar un fallo en una escritura de stock o en la auditoría.

**Esperado**: no se aplica ningún ajuste; series, stock y estado quedan como antes.

Prueba principal: `test_aprobacion_todo_o_nada`.

### CA-09: Ajustes al aprobar

1. Aprobar una conciliación con series faltantes, series no reportadas y fungibles.
2. Consultar series y stock.

**Esperado**: series faltantes creadas `ASIGNADA` al técnico; no reportadas `INSTALADA`; fungibles
en la cantidad reportada; stock general sin cambios.

Prueba principal: `test_ajustes_al_aprobar`.

### CA-10: Auditoría de ajustes

1. Aprobar una conciliación.
2. Consultar `RegistroCambio`.

**Esperado**: cada ajuste registra valor anterior y nuevo: `Serie/alta`, `Serie/estado`,
`Serie/tecnico`, `Serie/asignada_en` y `StockTecnico/cantidad`; actor correcto y sin secretos.

Prueba principal: `test_auditoria_ajustes`.

### CA-11: Recálculo si hubo cambios

1. Cargar una conciliación.
2. Cambiar el stock o la custodia de una serie.
3. Intentar aprobar.

**Esperado**: `409` “Hubo cambios, revise de nuevo”; las diferencias se recalculan,
`requiere_revision=True` y no se aplica ningún ajuste. Tras revisar, la segunda aprobación funciona.

Prueba principal: `test_recalculo_si_hubo_cambios`.

### CA-12: Técnico fuera de la región rechaza el archivo

1. Incluir un NIF desconocido o de otra región.
2. Cargar el archivo.

**Esperado**: rechazo completo con “El reporte contiene técnicos que no pertenecen a la región”; no
se crea conciliación. Un NIF de otro tenant de la misma región se ignora y no aparece.

Prueba principal: `test_tecnico_fuera_region_rechaza_archivo`.

## Escenarios complementarios

### Lectura del Excel

- `.xlsx` válido se lee; `.xls`, CSV, texto, vacío o corrupto se rechazan.
- Hoja `GENERAL` ausente o columnas faltantes se rechazan.
- Series con formato inválido, duplicadas, `INSTALADA` o de otro tenant se rechazan; en el último
  caso no se revela el tenant.
- Material seriado sin serie o no seriado con serie se rechaza.
- Cantidad no seriada negativa o no entera se rechaza.

### Comparación

- La huella de stock es estable para el mismo estado y cambia si cambia una serie o cantidad.
- Técnicos de otro tenant de la misma región no aparecen en diferencias.
- Material ausente para técnico presente se registra como 0.
- Serie en otro técnico se clasifica como `EN_OTRO_TECNICO`.
- La comparación no genera N+1 en un reporte grande.

### Aprobación

- Series faltantes se crean con el formato y lote del reporte.
- Series no reportadas pasan a `INSTALADA` y no vuelven al stock.
- Series en otro técnico se reasignan y reinician `asignada_en`.
- Fungibles se fijan a la cantidad reportada, incluso si baja a 0.
- `StockGeneral` no cambia en ningún caso.
- No se elimina ninguna serie.
- Un fallo deja la conciliación en `EN_REVISION`.

### Rechazo

- Rechazar deja `RECHAZADA`, con fecha y motivo opcional.
- No cambia series ni stock.
- Permite cargar una nueva conciliación.

### Concurrencia

- Dos cargas simultáneas dejan una sola `EN_REVISION`; la otra recibe `409`.
- Dos aprobaciones simultáneas dejan una sola `APROBADA`.
- Un cambio de stock durante la aprobación se detecta por la huella y obliga a revisar.
- El orden `Conciliacion → Tenant → StockTecnico (material, técnico) → Serie` no produce interbloqueo.

### Auditoría

- Carga, recálculo, cambios, aprobación, rechazo y ajustes quedan auditados.
- Los ajustes de stock son los de 008 y no se duplican.
- No hay secretos, binarios, rutas absolutas ni datos de otro tenant.

### Aislamiento

- El tenant A no ve conciliaciones de B.
- Las filas de otros tenants de la región no se muestran ni se auditan con sus datos.
- Un recurso de otro tenant devuelve `404`; un rol incorrecto, `403`.
- `DiferenciaSerie`, `DiferenciaCantidad` y `MaterialNoCatalogado` tienen el `tenant` de la
  conciliación.

### Rendimiento

- Un reporte de 10 000 filas y 1 000 series se procesa en tiempo razonable y sin N+1.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest -k "conciliacion"` pasa completo sobre PostgreSQL.
- [ ] CA-01…CA-12 tienen al menos una prueba automatizada en verde.
- [ ] Cargar no modifica series, stock técnico ni stock general.
- [ ] Aprobar aplica todo o nada y el stock general no cambia.
- [ ] Las series no reportadas quedan `INSTALADA` y no se eliminan.
- [ ] Los fungibles quedan exactamente en la cantidad reportada.
- [ ] Un cambio entre carga y aprobación obliga a recalcular y revisar.
- [ ] Los materiales no catalogados bloquean la aprobación, no la carga.
- [ ] La auditoría está completa y no duplica la de 008.
- [ ] Ningún tenant ve datos de otro.
- [ ] No se agregaron dependencias, correo, Celery ni permisos Django por cadena.
