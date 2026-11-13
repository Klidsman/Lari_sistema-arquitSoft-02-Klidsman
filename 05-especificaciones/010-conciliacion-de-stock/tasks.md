---
description: "Lista de tareas para la implementación de 010 Conciliación de Stock"
---

# Tareas: 010 Conciliación de Stock

**Entrada**: Documentos de diseño en `05-especificaciones/010-conciliacion-de-stock/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`,
`ContextoUsuarioMiddleware`, `tenants.Tenant`, `tenants.Region` y `auditoria.RegistroCambio`),
**spec 002 implementada** (`materiales.Material`), **spec 003 implementada**
(`tecnicos.Tecnico`), **spec 004 implementada** (`series.Serie`, `EstadoSerie`,
`tecnico`/`asignada_en` y `crear_serie`), **spec 005/008 implementadas** (`StockTecnico`,
`incrementar_stock_tecnico`, `decrementar_stock_tecnico` y auditoría de stock) y **spec 009
implementada** (custodia de series y traspasos). También deben estar aplicadas las correcciones
documentales de `plan.md`: estado `INSTALADA` en 004/009/012, solo `.xlsx`, y política regional de
técnicos en 010 y en `04-contratos/excel-conciliacion.md`. La app `conciliaciones` se crea aquí; no se
duplican tablas de stock, series, técnicos ni materiales.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-12. Cada historia escribe primero sus pruebas,
las ve fallar y luego implementa. Todas las pruebas usan PostgreSQL, nunca SQLite.

**Organización**: `spec.md` declara HU-18…HU-22 y HU-03 sin prioridad explícita; se agrupan en cuatro
historias derivadas para permitir entregas incrementales, sin agregar funcionalidad fuera de la spec.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia asociada (`US1`…`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Cargar el reporte y revisar diferencias | P1 | HU-18, HU-19, HU-22; RF-39, RF-40, RF-41, RF-42, RF-43, RF-48; CA-01…CA-06, CA-12 |
| US2 — Aprobar y ajustar stock | P2 | HU-20, HU-21, HU-03; RF-44, RF-45, RF-46, RF-64; CA-07…CA-10 |
| US3 — Recalcular si hubo cambios | P3 | HU-03; RF-47; CA-11 |
| US4 — Rechazar sin cambios | P4 | HU-03; RF-44; §5.6 |

## Convenciones de rutas

Proyecto Django único en la raíz: app nueva `conciliaciones/`, plantillas en
`templates/conciliaciones/`, pruebas en `tests/{unit,integration,contract}/` y migración transversal
en `series/migrations/`. Las apps `acceso`, `tenants`, `auditoria`, `materiales`, `tecnicos`,
`series`, `asignaciones` y `stock` son propiedad de sus specs. 010 **no** crea tablas de stock,
series ni técnicos, **no** toca `StockGeneral`, **no** elimina series, **no** envía correo, **no** usa
Celery y **no** usa permisos Django por cadena.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: verificar prerrequisitos y correcciones, crear la app, registrar rutas, preparar
fixtures y comprobar RLS.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `series/models.py`, `series/services.py`, `stock/models.py`, `stock/services.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware`, roles, `Material.es_seriado`/`lote`, `Tecnico.tenant`/`nif`, `Serie` con `numero`/estado/`tecnico`/`asignada_en` y `crear_serie`, `StockTecnico` y servicios de incremento/decremento, y `registrar_cambio`; detenerse y reportar si falta alguno
- [ ] T002 Crear el esqueleto de `conciliaciones` en `conciliaciones/__init__.py`, `apps.py`, `models.py`, `services.py`, `excel.py`, `forms.py`, `views.py`, `urls.py` y `migrations/__init__.py`; registrar `"conciliaciones"` y `CONCILIACIONES_DIR` en `config/settings/base.py` e incluir `conciliaciones.urls` desde `config/urls.py`
- [ ] T003 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region_conciliacion`, `tenant_conciliacion`, `tenant_conciliacion_otro`, `tenant_otra_region`, `usuario_tenant_conciliacion`, `tecnico_conciliacion`, `tecnico_ausente`, `tecnico_otro_tenant`, `material_seriado_conciliacion`, `material_no_seriado_conciliacion`, `material_no_catalogado`, `serie_asignada_conciliacion`, `stock_tecnico_conciliacion`, `conciliacion_en_revision`, `reporte_xlsx_valido` y `registro_cambios_conciliacion`
- [ ] T004 [P] Comprobar si la infraestructura RLS de 001 está disponible en `config/settings/base.py` y en las migraciones de `tenants`; si no lo está, registrar la deuda en `05-especificaciones/010-conciliacion-de-stock/research.md` y no crear una infraestructura paralela
- [ ] T005 [P] Verificar que las correcciones documentales estén aplicadas en `05-especificaciones/010-conciliacion-de-stock/spec.md`, `04-contratos/excel-conciliacion.md`, `004-recojo-de-materiales/`, `009-traspaso-entre-tecnicos/data-model.md` y `012-reportes-mensuales/plan.md`: solo `.xlsx`, política regional de técnicos, estado `INSTALADA` y coherencia de custodia; corregir antes de implementar si algo no coincide

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: estado `INSTALADA`, modelos de conciliación, RLS, excepciones, lectura del Excel,
clasificación de técnicos, comparación, huella y auditoría base que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

### Pruebas fundacionales (escribir primero, deben fallar)

- [ ] T006 [P] Escribir en `tests/unit/test_conciliacion_servicios.py` las pruebas de restricciones de `Conciliacion`, `DiferenciaSerie`, `DiferenciaCantidad` y `MaterialNoCatalogado`: una sola `EN_REVISION` por tenant, estado válido, `tenant`/`region` obligatorios, unicidad de diferencias, cantidades no negativas, formatos de serie y `PROTECT`/`CASCADE` según `data-model.md`
- [ ] T007 [P] Escribir en `tests/integration/test_conciliacion_carga.py` las pruebas de `series.EstadoSerie.INSTALADA`: valor en choices, `CheckConstraint` de estado, coherencia `INSTALADA`/custodia nula, `ASIGNADA` con técnico/fecha y migración sin cambios de datos
- [ ] T008 [P] Escribir en `tests/unit/test_conciliacion_excel.py` las pruebas de `leer_reporte`: `.xlsx` válido, `.xls`/CSV/texto/vacío/corrupto rechazados, hoja `GENERAL` ausente, columnas faltantes, encabezados normalizados, filas tipadas y sin escritura en base
- [ ] T009 Escribir en `tests/unit/test_conciliacion_servicios.py` las pruebas de `clasificar_tecnicos`: NIF `LAXXXX`, técnico del tenant, técnico de otro tenant de la misma región ignorado, técnico desconocido o de otra región rechazado, y ningún dato del tenant ignorado se expone
- [ ] T010 [P] Escribir en `tests/unit/test_conciliacion_comparacion.py` las pruebas de `comparar_series`: `EN_REPORTE_NO_SISTEMA`, `EN_SISTEMA_NO_REPORTE`, `EN_OTRO_TECNICO`, serie `INSTALADA`, serie de otro tenant y serie duplicada en el reporte
- [ ] T011 Escribir en `tests/unit/test_conciliacion_comparacion.py` las pruebas de `comparar_cantidades`: diferencia por técnico/material, material ausente para técnico presente = 0, técnico ausente ignorado, suma de filas no seriadas y cantidades negativas rechazadas
- [ ] T012 Escribir en `tests/unit/test_conciliacion_comparacion.py` las pruebas de `calcular_huella_stock`: huella estable, cambio de cantidad/serie/técnico cambia la huella, solo incluye técnicos presentes y no incluye `StockGeneral`
- [ ] T013 [P] Escribir en `tests/contract/test_conciliacion_http.py` las pruebas de contrato de firmas y excepciones de `conciliaciones/services.py` según `contracts/servicios-conciliacion.md`

### Implementación fundacional

- [ ] T014 Añadir `INSTALADA` a `EstadoSerie` en `series/models.py`, incluirlo en `serie_estado_valido` y ampliar `serie_tecnico_coherente_estado` para exigir custodia nula
- [ ] T015 Crear `series/migrations/0004_serie_instalada.py`: actualizar choices/check y la coherencia de custodia; no reescribir series existentes ni crear datos
- [ ] T016 Implementar `Conciliacion`, `DiferenciaSerie`, `DiferenciaCantidad` y `MaterialNoCatalogado` en `conciliaciones/models.py` con los campos, restricciones e índices de `data-model.md`: `tenant`, `region`, estado, archivo, hash, huella, `requiere_revision`, fechas, actor; diferencias con `tenant`, técnico, material, número/tipo o cantidades; material no catalogado con código/descripción/NIF/filas
- [ ] T017 Crear `conciliaciones/migrations/0001_initial.py` con T016, revisar que no cree conciliaciones ni modifique stock y aplicar con `python manage.py migrate`
- [ ] T018 Crear `conciliaciones/migrations/0002_rls.py` con RLS por `tenant_id`/`region_id` en conciliación y por `tenant_id` en diferencias y materiales no catalogados; si T004 determinó que 001 no está disponible, dejar la migración inactiva y registrar la deuda
- [ ] T019 Implementar en `conciliaciones/services.py` las excepciones y mensajes exactos de `contracts/servicios-conciliacion.md`: `PermisoDenegado`, `ConciliacionEnRevision`, `FormatoInvalido`, `HojaGeneralAusente`, `ColumnasFaltantes`, `TecnicosFueraRegion`, `TecnicoFormatoInvalido`, `MaterialNoExiste`, `SerieFormatoInvalido`, `SerieDuplicada`, `SerieInstalada`, `SerieFueraTenant`, `EstadoConciliacionInvalido`, `AprobacionBloqueada`, `HuboCambios`, `NoEncontrado` y `ArchivoNoDisponible`
- [ ] T020 Implementar en `conciliaciones/excel.py` `leer_reporte`: solo `.xlsx`, hoja `GENERAL`, columnas requeridas, normalización de encabezados, filas tipadas y errores de formato; no escribir en base
- [ ] T021 Implementar en `conciliaciones/services.py` `validar_cuenta_tenant`, `clasificar_tecnicos` y `validar_filas`: técnicos del tenant/otros tenants de la región/desconocidos, materiales no catalogados, serie con formato/duplicada/instalada/de otro tenant, coherencia seriado/cantidad y cantidades no negativas
- [ ] T022 Implementar en `conciliaciones/services.py` `construir_estado_sistema`, `comparar_series`, `comparar_cantidades`, `calcular_huella_stock` y `resumen_alertas`, con consultas agregadas y sin N+1
- [ ] T023 Implementar en `conciliaciones/services.py` el helper de auditoría para `Conciliacion/alta`, `Conciliacion/archivo`, `Conciliacion/estado`, `Conciliacion/recalculo`, `Conciliacion/hubo_cambios`, `Conciliacion/motivo_rechazo`, `Serie/alta`, `Serie/estado`, `Serie/tecnico` y `Serie/asignada_en`, usando `auditoria.services.registrar_cambio`, sin secretos ni binarios
- [ ] T024 Ejecutar `pytest tests/unit/test_conciliacion_excel.py tests/unit/test_conciliacion_servicios.py tests/unit/test_conciliacion_comparacion.py tests/integration/test_conciliacion_carga.py tests/contract/test_conciliacion_http.py`; corregir hasta que la fase fundacional esté en verde

**Checkpoint**: estado `INSTALADA`, modelos, RLS, lectura, clasificación, comparación y huella listos;
las historias pueden comenzar.

---

## Fase 3: US1 — Cargar el reporte y revisar diferencias (P1) 🎯 MVP

**Objetivo**: el tenant carga un `.xlsx` válido, el sistema valida el reporte, filtra sus técnicos,
compara series/cantidades, crea una conciliación `EN_REVISION` con diferencias y alertas, y **no
modifica stock**.

**Prueba independiente**: cargar un `.xlsx` con 2 series faltantes, 1 serie no reportada, 10 unidades
de diferencia y un material no catalogado; verificar `EN_REVISION`, diferencias agrupadas, alertas y
stock intacto. Repetir la carga y recibir `409`.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T025 [US1] Prueba de **CA-01** en `tests/integration/test_conciliacion_carga.py`: `test_cargar_reporte_crea_conciliacion_en_revision`; estado `EN_REVISION`, archivo/hash guardados, diferencias creadas y stock/series intactos
- [ ] T026 [US1] Prueba de **CA-02** en `tests/integration/test_conciliacion_carga.py`: `test_solo_una_conciliacion_en_revision`; la segunda carga devuelve `409` y el índice parcial impide dos
- [ ] T027 [US1] Prueba de **CA-03** en `tests/integration/test_conciliacion_carga.py`: `test_tecnico_ausente_se_ignora`; no genera diferencias ni ajustes para el técnico ausente
- [ ] T028 [US1] Prueba de **CA-04** en `tests/integration/test_conciliacion_carga.py`: `test_material_ausente_se_asume_0`; un material del técnico presente ausente en el reporte genera `cantidad_reporte=0`
- [ ] T029 [US1] Prueba de **CA-05** en `tests/integration/test_conciliacion_carga.py`: `test_diferencias_series_se_muestran_dos_grupos`; grupos “En reporte, no en sistema” y “En sistema, no en reporte”, con listado de series
- [ ] T030 [US1] Prueba de **CA-06** en `tests/integration/test_conciliacion_carga.py`: `test_alertas_categorizadas`; material ajeno, técnicos con inconsistencias y series faltantes
- [ ] T031 [US1] Prueba de **CA-12** en `tests/integration/test_conciliacion_carga.py`: `test_tecnico_fuera_region_rechaza_archivo`; NIF desconocido o de otra región rechaza todo; NIF de otro tenant de la misma región se ignora y no aparece
- [ ] T032 [US1] Prueba de material no catalogado en `tests/integration/test_conciliacion_carga.py`: se registra `MaterialNoCatalogado`, la carga continúa y no se crea una diferencia con material inexistente
- [ ] T033 [P] [US1] Prueba de auditoría de carga en `tests/integration/test_conciliacion_auditoria.py`: `Conciliacion/alta` y `Conciliacion/archivo` con hash, ruta relativa y actor; sin binarios ni secretos
- [ ] T034 [P] [US1] Prueba de contrato HTTP en `tests/contract/test_conciliacion_http.py`: listado, formulario de carga, detalle, `POST` de carga con `302/400/403/409`, `404` ajeno y `405` en métodos incorrectos

### Implementación de US1

- [ ] T035 [US1] Implementar en `conciliaciones/services.py` `validar_puede_cargar` y `crear_conciliacion`: validar cuenta, leer/validar el archivo, clasificar técnicos, comparar, calcular huella y guardar el archivo con nombre relativo y hash
- [ ] T036 [US1] Implementar en `conciliaciones/services.py` la persistencia transaccional de `Conciliacion` `EN_REVISION`, `DiferenciaSerie`, `DiferenciaCantidad` y `MaterialNoCatalogado`, con `bulk_create` y auditoría `Conciliacion/alta`/`Conciliacion/archivo`; no tocar series ni stock
- [ ] T037 [US1] Implementar en `conciliaciones/services.py` `listar_conciliaciones`, `obtener_conciliacion`, `detalle_conciliacion` y `alertas_conciliacion`, con filtros por tenant y sin N+1
- [ ] T038 [US1] Implementar en `conciliaciones/forms.py` el formulario de carga de archivo `.xlsx`, con validación de extensión, tamaño, no vacío y nombre seguro; no aceptar tenant/región/estado del cliente
- [ ] T039 [US1] Implementar en `conciliaciones/views.py` y `conciliaciones/urls.py` las rutas de listado, carga y detalle, con login, CSRF, mapeo `400/403/404/405/409` y sin exponer rutas físicas
- [ ] T040 [US1] Crear `templates/conciliaciones/listado.html`, `cargar.html` y `detalle.html`: estado, archivo, diferencias por grupo, cantidades, materiales no catalogados, alertas y aviso de `requiere_revision`
- [ ] T041 [US1] Ejecutar `pytest tests/integration/test_conciliacion_carga.py tests/integration/test_conciliacion_auditoria.py tests/contract/test_conciliacion_http.py` y corregir hasta que CA-01…CA-06 y CA-12 estén en verde

**Checkpoint**: US1 funcional; la carga crea una conciliación revisable sin modificar stock.

---

## Fase 4: US2 — Aprobar y ajustar stock (P2)

**Objetivo**: el tenant aprueba una conciliación `EN_REVISION`; las series faltantes se crean, las no
reportadas pasan a `INSTALADA`, las de otro técnico se reasignan y los fungibles quedan en la cantidad
reportada. Todo en una transacción y sin tocar el stock general.

**Prueba independiente**: aprobar una conciliación con 3 series faltantes, 2 no reportadas, 1 en otro
técnico y fungibles 50→40; verificar series, custodia, stock, `INSTALADA`, stock general invariante y
auditoría. Forzar un fallo y comprobar la reversión total.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T042 [US2] Prueba de **CA-07** en `tests/integration/test_conciliacion_aprobacion.py`: `test_aprobacion_bloquea_si_material_no_existe`; la aprobación devuelve `409` y no cambia nada
- [ ] T043 [US2] Prueba de **CA-08** en `tests/integration/test_conciliacion_aprobacion.py`: `test_aprobacion_todo_o_nada`; un fallo de serie, stock o auditoría revierte todo y deja `EN_REVISION`
- [ ] T044 [US2] Prueba de **CA-09** para series faltantes en `tests/integration/test_conciliacion_aprobacion.py`: se crean `ASIGNADA` con tenant, región, material, lote, técnico y `asignada_en`
- [ ] T045 [US2] Prueba de **CA-09** para series no reportadas en `tests/integration/test_conciliacion_aprobacion.py`: pasan a `INSTALADA`, con `tecnico=None` y `asignada_en=None`, y no se eliminan
- [ ] T046 [US2] Prueba de **CA-09** para series en otro técnico en `tests/integration/test_conciliacion_aprobacion.py`: se reasignan al técnico reportado y se reinicia `asignada_en`; se ajusta el stock de ambos técnicos
- [ ] T047 [US2] Prueba de **CA-09** para fungibles en `tests/integration/test_conciliacion_aprobacion.py`: el stock queda exactamente en la cantidad reportada, incluso si baja a 0; material ausente para técnico presente queda en 0
- [ ] T048 [P] [US2] Prueba de **CA-10** en `tests/integration/test_conciliacion_auditoria.py`: cada ajuste registra valor anterior y nuevo: `Serie/alta`, `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en` y `StockTecnico/cantidad` de 008
- [ ] T049 [US2] Prueba de stock general invariante en `tests/integration/test_conciliacion_aprobacion.py`: `StockGeneral` es idéntico antes y después de aprobar
- [ ] T050 [US2] Prueba de estado/errores en `tests/integration/test_conciliacion_aprobacion.py`: aprobar fuera de `EN_REVISION` devuelve `409`; falta de stock o serie inválida revierte; segunda aprobación no aplica de nuevo
- [ ] T051 [P] [US2] Prueba de contrato HTTP en `tests/contract/test_conciliacion_http.py`: `POST /conciliaciones/<id>/aprobar/` con `302/403/404/405/409`, y detalle con acciones según estado

### Implementación de US2

- [ ] T052 [US2] Implementar en `conciliaciones/services.py` `aprobar_conciliacion`: validar cuenta/estado, recalcular huella, bloquear si hay materiales no catalogados y delegar el recálculo si cambió
- [ ] T053 [US2] Implementar en `conciliaciones/services.py` el cálculo de objetivos por técnico/material: fungibles = cantidad reportada (0 si falta); seriados = número de series `ASIGNADA`; técnicos ausentes sin cambios salvo reasignaciones puntuales
- [ ] T054 [US2] Implementar en `conciliaciones/services.py` la transacción de aprobación: bloquear conciliación, tenant, `StockTecnico` por `(material_id, tecnico_id)` y series por `id`; revalidar huella/diferencias y aplicar todo o nada
- [ ] T055 [US2] Implementar en `conciliaciones/services.py` las operaciones de series: crear faltantes con `series.services.crear_serie(..., estado=ASIGNADA, tecnico, asignada_en)`, reasignar las de otro técnico y marcar `INSTALADA` las no reportadas; auditar cada cambio
- [ ] T056 [US2] Implementar en `conciliaciones/services.py` los ajustes de `StockTecnico` con los servicios de 008, calculando el delta contra el objetivo y agrupando por técnico/material; no tocar `StockGeneral`
- [ ] T057 [US2] Implementar en `conciliaciones/services.py` el cierre de la aprobación: `APROBADA`, `fecha_aprobacion`, `aprobado_por`, `requiere_revision=False`, `ajustes_aplicados` con el total de series y cantidades ajustadas, auditoría y `ResultadoConciliacion`
- [ ] T058 [US2] Implementar en `conciliaciones/views.py` y `conciliaciones/urls.py` la acción `POST aprobar`, con confirmación, CSRF, mapeo de errores y sin `GET`
- [ ] T059 [US2] Completar `templates/conciliaciones/detalle.html` con el resumen de ajustes, botón “Aprobar” solo en `EN_REVISION`, aviso de bloqueo por material no catalogado y confirmación
- [ ] T060 [US2] Ejecutar `pytest tests/integration/test_conciliacion_aprobacion.py tests/integration/test_conciliacion_auditoria.py tests/contract/test_conciliacion_http.py` y corregir hasta que CA-07…CA-10 estén en verde

**Checkpoint**: US2 funcional; la aprobación aplica el reporte completo sin tocar el stock general.

---

## Fase 5: US3 — Recalcular si hubo cambios (P3)

**Objetivo**: si el stock o la custodia cambian entre la carga y la aprobación, el sistema recalcula
las diferencias, marca `requiere_revision` y exige revisar de nuevo antes de aprobar.

**Prueba independiente**: cargar una conciliación, cambiar el stock de un técnico y aprobar; recibir
`409` “Hubo cambios, revise de nuevo”, ver las diferencias recalculadas y `requiere_revision=True`;
tras revisar, la segunda aprobación funciona.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T061 [US3] Prueba de **CA-11** en `tests/integration/test_conciliacion_recalculo.py`: `test_recalculo_si_hubo_cambios`; la huella cambia, se recalcula, se marca `requiere_revision` y no se aplica ningún ajuste
- [ ] T062 [US3] Prueba de recálculo en `tests/integration/test_conciliacion_recalculo.py`: reemplaza diferencias y materiales no catalogados, actualiza huella, audita `Conciliacion/recalculo` y no toca stock
- [ ] T063 [US3] Prueba de segunda aprobación en `tests/integration/test_conciliacion_recalculo.py`: tras recalcular y revisar, la aprobación aplica los datos frescos; una conciliación `APROBADA`/`RECHAZADA` no se recalcula
- [ ] T064 [P] [US3] Prueba de contrato HTTP en `tests/contract/test_conciliacion_http.py`: `POST recalcular` con `302/403/404/405/409`; el detalle muestra el aviso de cambios

### Implementación de US3

- [ ] T065 [US3] Implementar en `conciliaciones/services.py` `recalcular_diferencias`: releer el archivo, revalidar, comparar, reemplazar diferencias/materiales no catalogados, actualizar huella y `requiere_revision=True`, auditar y no tocar stock
- [ ] T066 [US3] Integrar en `aprobar_conciliacion` la comparación de huella: si cambió, recalcular en su propia transacción, auditar `Conciliacion/hubo_cambios` y lanzar `HuboCambios`; no aplicar ajustes
- [ ] T067 [US3] Implementar en `conciliaciones/views.py` y `conciliaciones/urls.py` la acción `POST recalcular`, con CSRF y mapeo de errores; añadir el botón “Recalcular” en `templates/conciliaciones/detalle.html`
- [ ] T068 [US3] Ejecutar `pytest tests/integration/test_conciliacion_recalculo.py tests/contract/test_conciliacion_http.py` y corregir hasta que CA-11 esté en verde

**Checkpoint**: US3 funcional; los cambios de stock obligan a recalcular y revisar.

---

## Fase 6: US4 — Rechazar sin cambios (P4)

**Objetivo**: el tenant rechaza una conciliación `EN_REVISION`; no se modifica ninguna serie ni
stock y se conserva el motivo y la auditoría.

**Prueba independiente**: rechazar una conciliación con diferencias y comprobar que series, stock y
stock general no cambian; la conciliación queda `RECHAZADA` con fecha y motivo; se puede cargar otra.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T069 [US4] Prueba de rechazo en `tests/integration/test_conciliacion_rechazo.py`: `test_rechazar_no_cambia_nada`; series, stock, custodia y stock general intactos; estado `RECHAZADA` con fecha/motivo
- [ ] T070 [US4] Prueba de estado/motivo en `tests/integration/test_conciliacion_rechazo.py`: rechazar fuera de `EN_REVISION` devuelve `409`; motivo opcional, sin secretos; se audita `Conciliacion/estado` y el motivo
- [ ] T071 [P] [US4] Prueba de contrato HTTP en `tests/contract/test_conciliacion_http.py`: `POST /conciliaciones/<id>/rechazar/` con `302/400/403/404/405/409`; no hay `GET`

### Implementación de US4

- [ ] T072 [US4] Implementar en `conciliaciones/services.py` `rechazar_conciliacion`: validar cuenta/estado; en transacción pasar a `RECHAZADA`, fijar `fecha_rechazo`/`motivo_rechazo` y auditar; no tocar series ni stock
- [ ] T073 [US4] Implementar en `conciliaciones/views.py` y `conciliaciones/urls.py` la acción `POST rechazar`, con CSRF y mapeo de errores; añadir el formulario/motivo y el botón “Rechazar” en `templates/conciliaciones/detalle.html`
- [ ] T074 [US4] Ejecutar `pytest tests/integration/test_conciliacion_rechazo.py tests/contract/test_conciliacion_http.py` y corregir hasta que el rechazo esté en verde

**Checkpoint**: US4 funcional; rechazar no modifica stock ni series y libera la carga de una nueva
conciliación.

---

## Fase 7: Polish y preocupaciones transversales

- [ ] T075 [P] Ejecutar `pytest -k "conciliacion"` sobre `tests/unit`, `tests/integration` y `tests/contract` con PostgreSQL y corregir cualquier fallo
- [ ] T076 [P] Ejecutar `pytest --cov=conciliaciones` y revisar que cada validación, excepción y transición de `conciliaciones/services.py` tenga al menos una prueba
- [ ] T077 [P] Agregar en `tests/integration/test_conciliacion_concurrencia.py` las pruebas de dos cargas simultáneas, dos aprobaciones simultáneas y cambio de stock durante la aprobación, sin interbloqueo
- [ ] T078 Agregar en `tests/integration/test_conciliacion_concurrencia.py` la prueba de rendimiento con 10 000 filas y 1 000 series, sin N+1
- [ ] T079 Agregar en `tests/integration/test_conciliacion_concurrencia.py` las pruebas de aislamiento: tenant A no ve conciliaciones de B, región ajena `404`, filas de otros tenants ignoradas y RLS activa si está disponible
- [ ] T080 [P] Revisar `conciliaciones/models.py`, `conciliaciones/services.py`, `conciliaciones/excel.py` y `conciliaciones/views.py`: sin escrituras a `StockGeneral`, sin eliminar series, sin permisos Django, sin correo/Celery, sin `tenant_id` del cliente y con mensajes en español
- [ ] T081 [P] Revisar `conciliaciones/migrations/` y `series/migrations/0004_serie_instalada.py`: restricciones, RLS, índice parcial de una sola `EN_REVISION`, estado `INSTALADA` y ningún cambio a tablas de stock
- [ ] T082 [P] Actualizar `05-especificaciones/010-conciliacion-de-stock/quickstart.md` con los comandos y resultados reales de la suite, sin duplicar contratos ni modelos
- [ ] T083 [P] Verificar que las correcciones de 004/009/012, 010 spec y `04-contratos/excel-conciliacion.md` siguen aplicadas
- [ ] T084 Ejecutar `python manage.py check` y `python manage.py migrate --check`; confirmar que no hay migraciones pendientes ni errores de configuración
- [ ] T085 Recorrer los escenarios de `quickstart.md` para CA-01…CA-12 y registrar el resultado; corregir implementación o documento antes de cerrar
- [ ] T086 Revisar `conciliaciones/services.py`, `conciliaciones/views.py`, `config/settings/base.py` y `requirements-dev.txt`: 010 no agrega dependencias, correo, Celery, SSE ni permisos Django, y `StockGeneral` es idéntico antes y después de todo el ciclo

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Setup (Fase 1)**: depende de 001–009 implementadas y de las correcciones documentales.
- **Fundacional (Fase 2)**: depende de Setup; **bloquea** las historias.
- **US1 (Fase 3)**: depende de Fundacional; entrega carga y revisión.
- **US2 (Fase 4)**: depende de US1.
- **US3 (Fase 5)**: depende de US2 (aprobación y huella).
- **US4 (Fase 6)**: depende de US1; puede ejecutarse en paralelo con US2/US3 si se coordinan archivos.
- **Polish (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1** es el MVP: sin carga no hay conciliación.
- **US2** aplica los ajustes; sin US1 no hay diferencias.
- **US3** protege la aprobación ante cambios; depende de US2.
- **US4** es independiente de US2/US3 una vez que US1 existe.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar.
- Modelos y migraciones antes de servicios.
- Servicios antes de vistas y plantillas.
- No se avanza con pruebas en rojo.

### Oportunidades de paralelización

- T003–T005 en Setup.
- T006–T013 en Fundacional (archivos de prueba distintos; T010–T012 comparten `test_conciliacion_comparacion.py` y van en secuencia).
- T025–T034 en US1: las pruebas de `test_conciliacion_carga.py` van en secuencia; T033/T034 usan archivos distintos.
- T042–T051 en US2: las pruebas de `test_conciliacion_aprobacion.py` van en secuencia; T048/T051 usan archivos distintos.
- T061–T064 en US3: T061–T063 comparten `test_conciliacion_recalculo.py`; T064 usa otro archivo.
- T069–T071 en US4: T069/T070 comparten archivo; T071 usa otro.
- T075–T083 en Polish usan archivos distintos.

**Nota**: `conciliaciones/services.py` es el archivo de mayor contención; T035–T037, T052–T057 y
T065–T066 deben secuenciarse.

---

## Ejemplo de paralelización: US1

```text
# Pruebas en archivos distintos
Tarea: "Auditoría de carga en tests/integration/test_conciliacion_auditoria.py"  # T033
Tarea: "Contrato HTTP en tests/contract/test_conciliacion_http.py"               # T034

# Implementación secuencial en services.py
T035 → T036 → T037

# Formulario, vistas y plantillas
T038 → T039 → T040
```

## Ejemplo de paralelización: US2

```text
# Pruebas en archivos distintos
T048 (auditoría) y T051 (contrato HTTP) pueden ir en paralelo.
# Implementación secuencial en services.py
T052 → T053 → T054 → T055 → T056 → T057
# Vistas/plantillas
T058 → T059
```

## Estrategia de implementación

### MVP (Fundacional + US1)

1. Completar Setup.
2. Completar Fundacional; validar lectura, comparación y huella.
3. Completar US1.
4. **DETENERSE y VALIDAR**: CA-01…CA-06 y CA-12 en verde.
5. Demostrar carga y revisión sin cambios de stock.

### Entrega incremental

1. Fundacional → modelos y comparación listos.
2. US1 → carga y revisión.
3. US2 → aprobación y ajustes.
4. US3 → recálculo por cambios.
5. US4 → rechazo.
6. Polish → concurrencia, rendimiento y documentación.

---

## Trazabilidad de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US1 | T025, T041 |
| CA-02 | US1 | T026, T041 |
| CA-03 | US1 | T027, T041 |
| CA-04 | US1 | T028, T041 |
| CA-05 | US1 | T029, T041 |
| CA-06 | US1 | T030, T041 |
| CA-07 | US2 | T042, T060 |
| CA-08 | US2 | T043, T060 |
| CA-09 | US2 | T044–T047, T060 |
| CA-10 | US2 | T048, T060 |
| CA-11 | US3 | T061, T068 |
| CA-12 | US1 | T031, T041 |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id`, `region_id`, estado ni rutas del cliente.
- 010 no toca `StockGeneral`, no elimina series, no envía correo, no usa Celery y no crea permisos
  Django.
- Cargar no modifica stock; aprobar aplica todo o nada; rechazar no cambia nada.
- Evitar tareas vagas y conflictos de archivo; `conciliaciones/services.py` debe secuenciarse.
