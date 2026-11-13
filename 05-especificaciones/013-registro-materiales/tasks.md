---
description: "Lista de tareas para la implementación de 013 Registro de Materiales"
---

# Tareas: 013 Registro de Materiales

**Entrada**: Documentos de diseño en `05-especificaciones/013-registro-materiales/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **specs 001, 002 y 003 implementadas**. **013 base existente**:
`MaterialHabilitado`, `SaldoInicialPeriodo`, `DespachoAlmacen`, `OrdenLiquidacion`,
`UsoMaterialOrden` y `auditoria.RegistroCambio` con `tenant`. Si alguna tabla base no existe en el
entorno, se crea una sola vez en la migración inicial de 013; no se duplica `DespachoAlmacen`.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-23. Cada historia escribe primero sus pruebas,
las ve fallar y luego implementa. Todas las pruebas usan PostgreSQL, nunca SQLite.

**Organización**: `spec.md` declara HU-30…HU-33 sin descripción individual; se agrupan en cuatro
historias derivadas por área funcional, sin agregar alcance.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia asociada (`US1`…`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Carga masiva de órdenes y pendientes | P1 | CA-03…CA-07, CA-19; flujo 7.1 y 7.5 |
| US2 — Registro de materiales, negativos y advertencias | P2 | CA-08…CA-13, CA-18; flujo 7.2 |
| US3 — Saldos, despachos, dashboard y exportación | P3 | CA-14…CA-17, CA-23; flujos 7.3, 7.4 y 7.8 |
| US4 — Cierre mensual y reapertura | P4 | CA-20…CA-22; flujos 7.6 y 7.7 |

## Convenciones de rutas

Proyecto Django único en la raíz: app `registro_materiales/`, plantillas en
`templates/registro_materiales/`, pruebas en `tests/{unit,integration,contract}/`. Las apps `acceso`,
`tenants`, `auditoria`, `materiales` y `tecnicos` son propiedad de sus specs. 013 **no** crea tablas de
materiales, técnicos, stock, series ni conciliación; **no** modifica `DespachoAlmacen` ni registra
despachos desde materiales; **no** usa permisos Django por cadena.

---

## Fase 1: Setup (infraestructura compartida)

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `registro_materiales/models.py` y `auditoria/models.py`: roles, `Material`, `Tecnico`, `MaterialHabilitado`, `SaldoInicialPeriodo`, `DespachoAlmacen`, tablas base de 013 y `RegistroCambio` con `tenant`; detenerse y reportar si falta alguna
- [ ] T002 [P] Verificar que `DespachoAlmacen` exista con `tenant`, `material`, `fecha` y `cantidad`; si no existe en el entorno, incluirla una sola vez en `registro_materiales/migrations/0001_initial.py` sin crear una segunda tabla
- [ ] T003 Crear/ajustar el esqueleto de `registro_materiales` en `models.py`, `services.py`, `carga.py`, `dashboard.py`, `cierre.py`, `exportacion.py`, `forms.py`, `views.py`, `urls.py` y `migrations/`; registrar la app y `REGISTRO_FACTOR_ADVERTENCIA=3`, `REGISTRO_MESES_PROMEDIO=3` y `REGISTRO_BACKUP_REQUERIDO=True` en `config/settings/base.py`; incluir `registro_materiales.urls` en `config/urls.py`, el enlace del menú y la ruta de catálogo en `templates/base.html`
- [ ] T004 [P] Extender `conftest.py` con fixtures: `tenant_registro`, `tenant_registro_otro`, `usuario_tenant_registro`, `tecnico_registro`, `tecnico_otro`, `material_registro`, `material_otro`, `material_habilitado`, `despacho_registro`, `carga_registro`, `orden_registro`, `uso_registro`, `cierre_cerrado` y `registro_cambios_registro`
- [ ] T005 [P] Comprobar si la infraestructura RLS de 001 está disponible; si no, registrar la deuda en `research.md` y no crear una infraestructura paralela
- [ ] T006 [P] Verificar que `spec.md`, `plan.md`, `data-model.md`, `contracts/`, `quickstart.md` y `03-reglas-de-dominio/registro-materiales.md` reflejen el flujo aprobado; corregir antes de implementar si algo no coincide

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelos nuevos, migraciones, RLS, normalización, validadores, auditoría y cálculo base.

### Pruebas fundacionales (escribir primero, deben fallar)

- [ ] T007 [P] Escribir en `tests/unit/test_registro_materiales.py` las pruebas de restricciones de `MaterialHabilitado`, `SaldoInicialPeriodo`, `CargaOrdenes`, `OrdenLiquidacion`, `UsoMaterialOrden`, `AdvertenciaUso`, `CierreMensual`, `SaldoMensualMaterial` y `JustificacionCierre`: claves únicas, regex, cantidades, estados y relaciones
- [ ] T008 [P] Escribir en `tests/unit/test_registro_carga.py` las pruebas de `procesar_lista`: `strip`, vacías, espacios internos, tabs/comas, deduplicación sin distinguir mayúsculas y conservación del original
- [ ] T009 Escribir en `tests/unit/test_registro_materiales.py` las pruebas de `validar_cantidad`, `validar_periodo`, `normalizar_numero_orden`, `saldo_inicial_efectivo` y `saldo_final`: 0, negativos, decimales, texto, periodos inválidos y herencia
- [ ] T010 [P] Escribir en `tests/contract/test_registro_http.py` las pruebas de contrato de firmas y excepciones de `services.py`, `carga.py`, `dashboard.py`, `cierre.py` y `exportacion.py`

### Implementación fundacional

- [ ] T011 Ajustar/crear `CargaOrdenes` en `registro_materiales/models.py` con `tenant`, `tecnico`, `periodo`, `hash_texto`, conteos, actor, fechas y campos de deshacer
- [ ] T012 Ajustar/crear en `registro_materiales/models.py` `OrdenLiquidacion` con `numero_original`, `numero_normalizado`, `periodo`, `fecha_instalacion`, `carga`, actores y timestamps; `UniqueConstraint(tenant, tecnico, periodo, numero_normalizado)`, regex de número y periodo
- [ ] T013 Ajustar/crear en `registro_materiales/models.py` `UsoMaterialOrden` con `tenant`, `orden`, `tecnico`, `material`, `cantidad`, actores y timestamps; `UniqueConstraint(orden, material)` y `CheckConstraint(cantidad >= 0)`
- [ ] T014 Crear `AdvertenciaUso`, `CierreMensual`, `SaldoMensualMaterial` y `JustificacionCierre` con los campos, restricciones e índices de `data-model.md`
- [ ] T015 Crear `registro_materiales/migrations/0001_initial.py` con `MaterialHabilitado`, `SaldoInicialPeriodo`, `DespachoAlmacen` (solo si no existe), `CargaOrdenes`, `OrdenLiquidacion`, `UsoMaterialOrden` y `AdvertenciaUso`; y `0002_cierre.py` con cierre/snapshot/justificación; aplicar con `python manage.py migrate`
- [ ] T016 Crear `registro_materiales/migrations/0003_rls.py` con RLS por `tenant_id`; si 001 no está disponible, dejar inactiva y documentar la deuda
- [ ] T017 Implementar en `services.py` las excepciones y validadores: `PermisoDenegado`, `TecnicoNoExiste`, `MaterialNoHabilitado`, `MaterialInactivo`, `CantidadInvalida`, `NumeroOrdenInvalido`, `PeriodoInvalido`, `SaldoInsuficiente`, `PeriodoCerrado`, `CargaNoDeshacible`, `CierreBloqueado`, `BackupRequerido`, `NoEncontrado`
- [ ] T018 Implementar en `services.py` `periodo_de_fecha`, `validar_periodo`, `normalizar_numero_orden`, `validar_cantidad`, `validar_cuenta_tenant` y `validar_tecnico`
- [ ] T019 Implementar en `registro_materiales/services.py` el helper de auditoría para carga, orden, uso, saldo, catálogo, advertencia, cierre y justificación con `auditoria.services.registrar_cambio` y `tenant`
- [ ] T020 Ejecutar `pytest tests/unit/test_registro_materiales.py tests/unit/test_registro_carga.py tests/contract/test_registro_http.py`; corregir hasta que la fase fundacional esté en verde

**Checkpoint**: modelos, migraciones, RLS, validadores y auditoría listos.

---

## Fase 3: US1 — Carga masiva de órdenes y pendientes (P1) 🎯 MVP

**Objetivo**: cargar órdenes por técnico y mes, normalizar, deduplicar, previsualizar, confirmar,
deshacer sin materiales y ver pendientes.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T021 [P] [US1] Prueba de **CA-03** en `tests/integration/test_carga_ordenes.py`: normalización y rechazo de líneas inválidas
- [ ] T022 [US1] Prueba de **CA-04/CA-06** en `tests/integration/test_carga_ordenes.py`: carga idempotente y resumen con leídas/nuevas/omitidas
- [ ] T023 [US1] Prueba de **CA-05** en `tests/integration/test_carga_ordenes.py`: mismo número para otro técnico se crea para el seleccionado y se informa
- [ ] T024 [US1] Prueba de **CA-07** en `tests/integration/test_carga_ordenes.py`: deshacer sin materiales; bloqueo si alguna tiene materiales
- [ ] T025 [US1] Prueba de **CA-19** en `tests/integration/test_carga_ordenes.py`: panel de pendientes con filtro por antigüedad
- [ ] T026 [P] [US1] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: preview, confirmar, deshacer, pendientes y menú con `200/302/400/403/404/409`
- [ ] T027 [P] [US1] Prueba de menú y aislamiento en `tests/integration/test_aislamiento.py`: solo el tenant ve el menú y sus cargas/órdenes; no ve las de otro tenant

### Implementación de US1

- [ ] T028 [US1] Implementar `procesar_lista` y `previsualizar_carga` en `registro_materiales/carga.py`, con deduplicación, conteos y comparación por técnico/mes y otros técnicos
- [ ] T029 [US1] Implementar `confirmar_carga` en `carga.py`: transacción, `CargaOrdenes`, creación de solo órdenes nuevas y auditoría
- [ ] T030 [US1] Implementar en `registro_materiales/carga.py` `deshacer_carga`: validar que no haya usos con cantidad > 0, eliminar solo las órdenes del lote y auditar
- [ ] T031 [US1] Implementar `ordenes_pendientes` y la consulta de resumen en `services.py`/`dashboard.py`
- [ ] T032 [US1] Implementar formularios, vistas, URLs y plantillas `templates/registro_materiales/cargar_ordenes.html`, `_resumen_carga.html` y `pendientes.html`
- [ ] T033 [US1] Ejecutar `pytest tests/integration/test_carga_ordenes.py tests/integration/test_aislamiento.py tests/contract/test_registro_http.py` y corregir hasta que US1 esté en verde

**Checkpoint**: US1 funcional; la carga masiva es segura, idempotente y deshacible.

---

## Fase 4: US2 — Registro de materiales, negativos y advertencias (P2)

**Objetivo**: buscar/crear orden, registrar fecha y cantidades, bloquear negativos, advertir
cantidades atípicas y guardar historial.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T034 [P] [US2] Prueba de **CA-08** en `tests/integration/test_materiales_uso.py`: orden existente se abre dentro del mes seleccionado; misma orden en otro mes no se mezcla; orden inexistente muestra catálogo 0 y se crea; material deshabilitado no aparece
- [ ] T035 [US2] Prueba de **CA-09** en `tests/integration/test_materiales_uso.py`: cambio de fecha a otro mes revalida clave y recalcula
- [ ] T036 [US2] Prueba de **CA-10/CA-11** en `tests/integration/test_materiales_uso.py`: 0 no suma; negativos, decimales y texto se rechazan
- [ ] T037 [P] [US2] Prueba de **CA-12** en `tests/integration/test_bloqueo_negativo.py`: disponible 45, usado 40, intento 10 → bloqueo con faltante 5
- [ ] T038 [US2] Prueba de **CA-13** en `tests/integration/test_materiales_uso.py`: advertencia atípica con promedio mensual de 3 meses cerrados no bloquea y crea `AdvertenciaUso`; sin historial no advierte
- [ ] T039 [P] [US2] Prueba de **CA-18** en `tests/integration/test_auditoria.py`: editar orden/usos deja valores anterior/nuevo; líneas a 0 se conservan
- [ ] T040 [P] [US2] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: contexto, guardar, historial y errores de saldo/mes cerrado

### Implementación de US2

- [ ] T041 [US2] Implementar en `services.py` `materiales_habilitados`, `habilitar_material`, `deshabilitar_material`, `buscar_orden(tenant, tecnico, periodo, numero)`, `crear_orden_manual` y `guardar_uso`: mes seleccionado, técnico, fecha, materiales, cantidades, revalidación de periodo y clave
- [ ] T042 [US2] Implementar en `registro_materiales/services.py` el cálculo de disponible/uso total y el bloqueo `SaldoInsuficiente` con disponible, usado y faltante
- [ ] T043 [US2] Implementar en `registro_materiales/services.py` la detección de cantidad atípica con promedio mensual de los últimos 3 meses cerrados, `AdvertenciaUso` y `resolver_advertencia`; sin historial no advertir
- [ ] T044 [US2] Implementar en `registro_materiales/services.py` la persistencia de usos (conservar 0), actualización de fecha/periodo y auditoría
- [ ] T045 [US2] Implementar formularios, vistas, URLs y plantillas `templates/registro_materiales/registrar_materiales.html`, `_catalogo_orden.html`, `catalogo.html` e `historial.html`
- [ ] T046 [US2] Ejecutar `pytest tests/integration/test_materiales_uso.py tests/integration/test_bloqueo_negativo.py tests/integration/test_auditoria.py tests/contract/test_registro_http.py` y corregir hasta que US2 esté en verde

**Checkpoint**: US2 funcional; el uso se registra, se bloquea el negativo y se advierte lo atípico.

---

## Fase 5: US3 — Saldos, despachos, dashboard y exportación (P3)

**Objetivo**: saldo inicial manual/heredado, despachos leídos de `DespachoAlmacen`, dashboard por
material/técnico y exportación Excel/CSV.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T047 [P] [US3] Prueba de **CA-14/CA-15/CA-16** en `tests/integration/test_dashboard.py`: saldo final, herencia, saldo manual prevalece/audita y bloqueo si el saldo manual deja el mes negativo
- [ ] T048 [US3] Prueba de **CA-17** en `tests/integration/test_dashboard.py`: los despachos suman desde `DespachoAlmacen` sin doble registro
- [ ] T049 [US3] Prueba de dashboard en `tests/integration/test_dashboard.py`: filtros, detalle por técnico y alerta de saldo negativo
- [ ] T050 [US3] Prueba de **CA-23** en `tests/integration/test_dashboard.py`/`tests/unit/test_registro_exportacion.py`: Excel/CSV con datos del tenant
- [ ] T051 [P] [US3] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: entradas, dashboard y exportación

### Implementación de US3

- [ ] T052 [US3] Implementar en `services.py` `registrar_saldo_inicial` (con bloqueo si deja el mes negativo), `saldo_inicial_efectivo`, `saldo_final` y `despachos_del_periodo`
- [ ] T053 [US3] Implementar `dashboard_mensual` y las consultas de detalle por técnico en `dashboard.py`
- [ ] T054 [US3] Implementar `exportar_reporte_mensual` y `exportar_detalle_ordenes` en `exportacion.py` para `.xlsx` y `.csv`
- [ ] T055 [US3] Implementar vistas, URLs y plantillas `templates/registro_materiales/entradas.html`, `dashboard.html` y `_exportacion.html`; no agregar formulario de despacho
- [ ] T056 [US3] Ejecutar `pytest tests/integration/test_dashboard.py tests/unit/test_registro_exportacion.py tests/contract/test_registro_http.py` y corregir hasta que US3 esté en verde

**Checkpoint**: US3 funcional; saldos, despachos, dashboard y exportación operan sin doble registro.

---

## Fase 6: US4 — Cierre mensual y reapertura (P4)

**Objetivo**: checklist, cierre con backup, congelamiento, traspaso al mes siguiente y reapertura con
motivo.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T057 [P] [US4] Prueba de **CA-20** en `tests/integration/test_cierre_mensual.py`: cierre bloqueado por órdenes pendientes, negativos o advertencias sin resolver; se libera al resolver/justificar la advertencia
- [ ] T058 [US4] Prueba de **CA-21** en `tests/integration/test_cierre_mensual.py`: cierre congela y traspasa el saldo
- [ ] T059 [US4] Prueba de backup en `tests/integration/test_cierre_mensual.py`: sin `backup_ref`, vacío o con formato inválido no se cierra
- [ ] T060 [US4] Prueba de **CA-22** en `tests/integration/test_cierre_mensual.py`: reapertura con motivo, auditoría y nuevo cierre
- [ ] T061 [US4] Prueba de mes cerrado en `tests/integration/test_cierre_mensual.py`: usos, saldos y el alta/edición existente de despachos rechazan cambios con `PeriodoCerrado`
- [ ] T062 [P] [US4] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: cierre, justificar y reabrir

### Implementación de US4

- [ ] T063 [US4] Implementar en `cierre.py` `lista_chequeo`, `resolver_advertencia`, `justificar_pendiente`, `cerrar_mes` y `reabrir_mes`
- [ ] T064 [US4] Implementar en `registro_materiales/cierre.py` el snapshot `SaldoMensualMaterial`, `validar_backup_ref` y el comando `registro_materiales/management/commands/respaldar_bd.py`
- [ ] T065 [US4] Implementar en `registro_materiales/services.py` las guardas `PeriodoCerrado` en usos y saldos, y en el servicio existente de alta/edición de `DespachoAlmacen`
- [ ] T066 [US4] Implementar vistas, URLs y plantillas `templates/registro_materiales/cierre.html` con checklist, justificación, resolución de advertencias, campo `backup_ref`, cierre y reapertura
- [ ] T067 [US4] Ejecutar `pytest tests/integration/test_cierre_mensual.py tests/contract/test_registro_http.py` y corregir hasta que US4 esté en verde

**Checkpoint**: US4 funcional; el cierre es auditable y el mes cerrado queda protegido.

---

## Fase 7: Polish y preocupaciones transversales

- [ ] T068 [P] Ejecutar `pytest -k "registro"` sobre `tests/unit`, `tests/integration` y `tests/contract`
- [ ] T069 [P] Ejecutar `pytest --cov=registro_materiales tests/unit tests/integration tests/contract` y revisar cobertura de servicios
- [ ] T070 [P] Probar en `tests/integration/test_concurrencia.py` la concurrencia: doble carga, doble guardado de uso, dos cierres y dos reaperturas
- [ ] T071 Probar en `tests/integration/test_concurrencia.py` el rendimiento: 100 materiales, 1 000 órdenes y 5 000 usos sin N+1
- [ ] T072 [P] Revisar `registro_materiales/services.py` y `registro_materiales/dashboard.py`: sin escrituras a stock, series, asignaciones, traspasos ni conciliaciones
- [ ] T073 [P] Revisar `registro_materiales/models.py` y `registro_materiales/services.py`: no se crea otra tabla de despachos y `DespachoAlmacen` es de solo lectura
- [ ] T074 [P] Revisar `registro_materiales/migrations/`: RLS, restricciones e índices
- [ ] T075 [P] Actualizar `05-especificaciones/013-registro-materiales/quickstart.md` y `03-reglas-de-dominio/registro-materiales.md` con el flujo final
- [ ] T076 [P] Verificar en `05-especificaciones/013-registro-materiales/` que spec, plan, data-model, contracts y tasks estén alineados
- [ ] T077 Ejecutar `python manage.py check` y `python manage.py migrate --check`
- [ ] T078 Recorrer los escenarios de `05-especificaciones/013-registro-materiales/quickstart.md` para CA-01…CA-23 y registrar resultados
- [ ] T079 Revisar `registro_materiales/views.py`, `config/settings/base.py` y `requirements-dev.txt`: sin dependencias nuevas, correo, Celery ni permisos Django
- [ ] T080 Revisar `registro_materiales/views.py`, `registro_materiales/exportacion.py` y `tests/integration/test_aislamiento.py`: un tenant no ve datos de otro

---

## Dependencias y orden de ejecución

- **Setup** depende de 001–003 y de la base de 013.
- **Fundacional** bloquea las historias.
- **US1** entrega carga y pendientes.
- **US2** depende de US1 (órdenes) y del bloqueo base.
- **US3** depende de US1/US2 para usos y saldos.
- **US4** depende de US3 para calcular y congelar.
- **Polish** depende de todas.

## Oportunidades de paralelización

- T002–T006 en Setup.
- T007–T010 en Fundacional (archivos distintos; T007/T009 comparten `test_registro_materiales.py`).
- T021–T027 en US1: carga, aislamiento y contrato en archivos distintos.
- T034–T040 en US2: materiales, bloqueo, auditoría y contrato.
- T047–T051 en US3: dashboard, exportación y contrato.
- T057–T062 en US4: cierre y contrato.
- T068–T076 en Polish.

**Nota**: `services.py`, `carga.py`, `dashboard.py`, `cierre.py` y `exportacion.py` deben
secuenciarse por ser archivos de alta contención.

## Estrategia de implementación

### MVP (Fundacional + US1)

1. Completar Setup y Fundacional.
2. Completar US1.
3. Validar carga, resumen, deshacer y pendientes.

### Entrega incremental

1. US1 → carga de órdenes.
2. US2 → materiales y bloqueo.
3. US3 → saldos, dashboard y exportación.
4. US4 → cierre y reapertura.
5. Polish → concurrencia, rendimiento y documentación.

## Trazabilidad de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US1 | T027 |
| CA-02 | US2 | T034 |
| CA-03 | US1 | T021 |
| CA-04 | US1 | T022 |
| CA-05 | US1 | T023 |
| CA-06 | US1 | T022 |
| CA-07 | US1 | T024 |
| CA-08 | US2 | T034 |
| CA-09 | US2 | T035 |
| CA-10 | US2 | T036 |
| CA-11 | US2 | T036 |
| CA-12 | US2 | T037 |
| CA-13 | US2 | T038 |
| CA-14 | US3 | T047 |
| CA-15 | US3 | T047 |
| CA-16 | US3 | T047 |
| CA-17 | US3 | T048 |
| CA-18 | US2 | T039 |
| CA-19 | US1 | T025 |
| CA-20 | US4 | T057 |
| CA-21 | US4 | T058 |
| CA-22 | US4 | T060 |
| CA-23 | US3 | T050 |

## Notas

- [P] solo para archivos distintos y sin dependencia pendiente.
- [Story] solo en fases de historia.
- Toda prueba se escribe antes de la implementación.
- No se duplica `DespachoAlmacen`.
- No se acepta `tenant_id` del cliente.
- No se borran datos, salvo deshacer una carga sin materiales.
- No se toca stock, series, asignaciones, traspasos ni conciliaciones.
