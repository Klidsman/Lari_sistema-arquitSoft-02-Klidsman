---
description: "Lista de tareas para la implementación de 012 Reportes Mensuales"
---

# Tareas: 012 Reportes Mensuales

**Entrada**: Documentos de diseño en `05-especificaciones/012-reportes-mensuales/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **specs 001–011 implementadas** hasta lo que 012 consume. En
particular: `RegistroCambio` con `tenant` nullable, `Conciliacion` con `ajustes_aplicados`,
`SolicitudAsignacion`/`LineaAsignacion` con `fecha`/`confirmada_en`, `Serie` con `INSTALADA`/
`INACTIVA`, `Devolucion`/`LineaDevolucion` y `StockTecnico`/`StockGeneral` de solo lectura. La app
`reportes` se crea aquí; no se duplican tablas de stock, series, asignaciones ni conciliaciones.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-04. Cada historia escribe primero sus pruebas,
las ve fallar y luego implementa. Todas las pruebas usan PostgreSQL, nunca SQLite.

**Organización**: `spec.md` declara HU-28 y HU-29 sin prioridad explícita; se agrupan en cuatro
historias derivadas para permitir entregas incrementales, sin agregar funcionalidad fuera de la spec.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia asociada (`US1`…`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Generar el corte mensual con totales y merma | P1 | HU-28; RF-68; CA-01, CA-02; §5.1–§5.2 |
| US2 — Exportar la auditoría mensual a Excel | P2 | HU-29; RF-69; CA-03; §5.3 |
| US3 — Exportar la conciliación mensual a Excel | P3 | HU-29; RF-69; CA-04; §5.3 |
| US4 — Consultar historial y regenerar el corte | P4 | HU-28; §5.1, §9; consulta histórica |

## Convenciones de rutas

Proyecto Django único en la raíz: app nueva `reportes/`, plantillas en `templates/reportes/`, pruebas
en `tests/{unit,integration,contract}/` y migraciones transversales en `auditoria/migrations/` y
`conciliaciones/migrations/`. Las apps `acceso`, `tenants`, `auditoria`, `materiales`, `tecnicos`,
`series`, `asignaciones`, `stock`, `conciliaciones` y `logistica_inversa` son propiedad de sus specs.
012 **no** escribe stock, series, asignaciones ni conciliaciones, **no** envía correo, **no** usa
Celery y **no** usa permisos Django por cadena.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: verificar prerrequisitos y correcciones, añadir los campos de apoyo, crear la app,
registrar rutas, preparar fixtures y comprobar RLS.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `series/models.py`, `asignaciones/models.py`, `stock/models.py`, `logistica_inversa/models.py`, `conciliaciones/models.py` y `auditoria/models.py`: roles, `RegistroCambio.tenant`, `Conciliacion.ajustes_aplicados`, `SolicitudAsignacion.fecha`/`confirmada_en`, `LineaAsignacion.serie`/`cantidad`, `Serie`/`INSTALADA`/`INACTIVA`, `Devolucion`/`LineaDevolucion` y servicios de stock; detenerse y reportar si falta alguno
- [ ] T002 Añadir `tenant` FK `tenants.Tenant` `PROTECT` `null=True` `related_name="registros_cambio"` a `RegistroCambio` en `auditoria/models.py` y crear la migración correspondiente en `auditoria/migrations/`; añadir índice `(tenant, fecha)` y actualizar `auditoria/services.py` para poblarlo desde el actor o el registro de entidades auditables
- [ ] T003 Añadir `ajustes_aplicados = PositiveIntegerField(default=0)` a `Conciliacion` en `conciliaciones/models.py` y crear la migración correspondiente en `conciliaciones/migrations/`; asegurar que 010 lo fija al aprobar y que 012 solo lo lee
- [ ] T004 Crear el esqueleto de `reportes` en `reportes/__init__.py`, `apps.py`, `models.py`, `services.py`, `excel.py`, `forms.py`, `views.py`, `urls.py` y `migrations/__init__.py`; registrar `"reportes"` en `config/settings/base.py` e incluir `reportes.urls` desde `config/urls.py`
- [ ] T005 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `admin_reportes`, `usuario_tenant_reportes`, `usuario_otro_tenant_reportes`, `tenant_reportes`, `tenant_reportes_otro`, `corte_mensual`, `corte_global`, `movimientos_auditoria`, `conciliaciones_mes`, `devoluciones_mes` y `registro_cambios_reportes`
- [ ] T006 [P] Comprobar si la infraestructura RLS de 001 está disponible en `config/settings/base.py` y en las migraciones de `tenants`; si no lo está, registrar la deuda en `05-especificaciones/012-reportes-mensuales/research.md` y no crear una infraestructura paralela

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelo `CorteMensual`, migraciones, RLS, excepciones, rango del mes, cálculo de totales
y auditoría base que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

### Pruebas fundacionales (escribir primero, deben fallar)

- [ ] T007 [P] Escribir en `tests/unit/test_reportes_servicios.py` las pruebas de restricciones de `CorteMensual`: dos restricciones parciales (tenant/global), mes 1–12, año 2000–2100, porcentaje 0–100, totales no negativos, índices y `tenant=None` para global
- [ ] T008 Escribir en `tests/unit/test_reportes_servicios.py` las pruebas de `rango_mes`, `validar_cuenta_admin`, `validar_cuenta_tenant_o_admin` y `resolver_alcance`: mes/año inválidos, admin global, tenant propio, tenant ajeno y global desde tenant
- [ ] T009 Escribir en `tests/unit/test_reportes_servicios.py` las pruebas de `calcular_totales`: definición de solicitados/asignados, series y no seriados, `INSTALADA` vía auditoría, devueltos, filtro por tenant/global, mes sin datos y `[inicio, fin)`
- [ ] T010 Escribir en `tests/unit/test_reportes_servicios.py` las pruebas de merma: 100/80/5 = 15,00; asignados 0 → 0; no justificado negativo acotado a 0; redondeo a dos decimales
- [ ] T011 [P] Escribir en `tests/contract/test_reportes_http.py` las pruebas de contrato de firmas y excepciones de `reportes/services.py` según `contracts/servicios-reportes.md`

### Implementación fundacional

- [ ] T012 Implementar `CorteMensual` en `reportes/models.py` con los campos, restricciones e índices de `data-model.md`: `tenant` nullable, `anio`/`mes`, cinco totales, `porcentaje_merma` `DecimalField(5,2)`, `version`, `generado_por`, `generado_en`, `actualizado_por`, `actualizado_en`, `regenerado_en`; `CorteMensual/alta` y `CorteMensual/regenerado`
- [ ] T013 Crear `reportes/migrations/0001_initial.py` con T012, revisar que no cree cortes por migración y aplicar con `python manage.py migrate`
- [ ] T014 Crear `reportes/migrations/0002_rls.py` con RLS por `tenant_id`; las filas globales (`tenant_id IS NULL`) solo para Admin. Si T006 determinó que 001 no está disponible, dejar la migración inactiva y registrar la deuda
- [ ] T015 Implementar en `reportes/services.py` las excepciones `PermisoDenegado`, `CorteExistente`, `CorteNoExiste`, `MesInvalido` y `AnioInvalido`, y `rango_mes` con `[inicio, fin)` en la zona configurada
- [ ] T016 Implementar en `reportes/services.py` `validar_cuenta_admin`, `validar_cuenta_tenant_o_admin`, `resolver_alcance` y `calcular_totales` con agregaciones, `distinct` y las definiciones de `data-model.md`; no escribir en stock ni en otras entidades
- [ ] T017 Implementar en `reportes/services.py` el helper de auditoría para `CorteMensual/alta` y `CorteMensual/regenerado`, con alcance, mes, año, totales, versión y actor
- [ ] T018 Ejecutar `pytest tests/unit/test_reportes_servicios.py tests/contract/test_reportes_http.py`; corregir hasta que la fase fundacional esté en verde

**Checkpoint**: modelo `CorteMensual`, restricciones, rango, cálculo y auditoría listos; las historias
pueden comenzar.

---

## Fase 3: US1 — Generar el corte mensual con totales y merma (P1) 🎯 MVP

**Objetivo**: el Admin o el tenant genera un corte por mes/año y alcance; el sistema calcula
solicitados, asignados, liquidados/instalados, devueltos, no justificado y % merma, y lo guarda.

**Prueba independiente**: generar un corte con 100 asignados, 80 instalados y 5 devueltos; verificar
15,00% de merma, totales correctos, persistencia y `version=1`. Repetir la generación y recibir `409`.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T019 [P] [US1] Prueba de **CA-01** en `tests/integration/test_corte_mensual.py`: `test_corte_mensual_con_totales`; muestra solicitados, asignados, liquidados/instalados, devueltos y % merma, y guarda el corte
- [ ] T020 [US1] Prueba de **CA-02** en `tests/integration/test_corte_mensual.py`: `test_calculo_merma_correcto`; 100/80/5 = 15,00; asignados 0 = 0; no justificado negativo = 0
- [ ] T021 [US1] Pruebas de cálculo en `tests/integration/test_corte_mensual.py`: series y no seriados, solicitados excluye `BORRADOR`/`CANCELADA`, asignados usa `confirmada_en`, liquidados usa `Serie/estado → INSTALADA` y no `INACTIVA`, devueltos usa `Devolucion.fecha`
- [ ] T022 [US1] Pruebas de alcance/duplicados en `tests/integration/test_corte_mensual.py`: corte de tenant, global, duplicado por tenant, duplicado global, mes/año inválidos y tenant ajeno
- [ ] T023 [P] [US1] Prueba de contrato HTTP en `tests/contract/test_reportes_http.py`: listado, formulario, `POST generar` y detalle con `200/302/400/403/404/405/409`
- [ ] T024 [P] [US1] Prueba de auditoría del alta en `tests/integration/test_reportes_auditoria.py`: `CorteMensual/alta` con alcance, mes, año, totales y actor

### Implementación de US1

- [ ] T025 [US1] Implementar en `reportes/services.py` `generar_corte`: resolver alcance, validar mes/año, rechazar duplicado, calcular totales y crear `CorteMensual` en transacción con `version=1`; auditar alta
- [ ] T026 [US1] Implementar en `reportes/forms.py` el formulario de generación: mes 1–12, año 2000–2100 y tenant/global solo para Admin; no aceptar totales ni actor del cliente
- [ ] T027 [US1] Implementar en `reportes/views.py` y `reportes/urls.py` listado, generación y detalle de cortes, con login, CSRF y mapeo `400/403/404/405/409`; crear `templates/reportes/cortes_listado.html`, `corte_formulario.html` y `corte_detalle.html`
- [ ] T028 [US1] Ejecutar `pytest tests/integration/test_corte_mensual.py tests/integration/test_reportes_auditoria.py tests/contract/test_reportes_http.py` y corregir hasta que CA-01, CA-02 y el alta auditada estén en verde

**Checkpoint**: US1 funcional; el corte se calcula con métricas definidas y se guarda con auditoría.

---

## Fase 4: US2 — Exportar la auditoría mensual a Excel (P2)

**Objetivo**: el Admin o el tenant descarga un `.xlsx` con los movimientos de auditoría del mes,
filtrados por su alcance, sin persistir archivos.

**Prueba independiente**: generar un corte con movimientos auditados del mes, descargar la auditoría y
verificar columnas, orden y que no aparezcan registros de otro tenant.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T029 [P] [US2] Prueba de **CA-03** en `tests/integration/test_exportacion_auditoria.py`: `test_exportar_auditoria_excel`; el `.xlsx` contiene todos los movimientos del mes con Fecha, Usuario, Entidad, Acción, Valor anterior y Valor nuevo
- [ ] T030 [US2] Pruebas de alcance/columnas en `tests/integration/test_exportacion_auditoria.py`: tenant solo sus registros, global incluye todos, orden por fecha/id, mes sin registros con encabezados y sin secretos
- [ ] T031 [P] [US2] Prueba de contrato HTTP en `tests/contract/test_reportes_http.py`: `GET .../exportar/auditoria/` con `200/403/404/405`, `Content-Disposition` correcto y sin ruta física
- [ ] T032 [P] [US2] Prueba unitaria del Excel en `tests/unit/test_reportes_excel.py`: encabezados, formato de fechas, valores como texto, una hoja y sin fórmulas/macros

### Implementación de US2

- [ ] T033 [US2] Implementar en `reportes/excel.py` `construir_excel_auditoria(registros) -> bytes` con una hoja, columnas y formato de `contracts/excel-reportes.md`; no persistir archivo
- [ ] T034 [US2] Implementar en `reportes/services.py` `exportar_auditoria`: resolver alcance, filtrar `RegistroCambio` por `fecha` y `tenant`, ordenar y devolver `ArchivoReporte`
- [ ] T035 [US2] Implementar en `reportes/views.py` y `reportes/urls.py` la descarga de auditoría desde el corte, con `Content-Disposition`, sin exponer rutas y sin `POST`
- [ ] T036 [US2] Ejecutar `pytest tests/integration/test_exportacion_auditoria.py tests/unit/test_reportes_excel.py tests/contract/test_reportes_http.py` y corregir hasta que CA-03 esté en verde

**Checkpoint**: US2 funcional; la auditoría del mes se exporta según alcance y sin archivos persistidos.

---

## Fase 5: US3 — Exportar la conciliación mensual a Excel (P3)

**Objetivo**: el Admin o el tenant descarga un `.xlsx` con las conciliaciones del mes, sus diferencias
y los ajustes aplicados, filtrado por alcance.

**Prueba independiente**: generar un corte con conciliaciones, descargar la conciliación y verificar
fecha, estado, diferencias y ajustes; el global incluye el tenant y el tenant no ve a otros.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T037 [P] [US3] Prueba de **CA-04** en `tests/integration/test_exportacion_conciliacion.py`: `test_exportar_conciliacion_excel`; contiene todas las conciliaciones del mes con Fecha, Estado, Tenant (global), Diferencias series, Diferencias cantidades y Ajustes aplicados
- [ ] T038 [US3] Pruebas de conteos/alcance en `tests/integration/test_exportacion_conciliacion.py`: conteos de diferencias, `ajustes_aplicados`, filtro por `fecha_carga`, tenant vs global y mes sin conciliaciones
- [ ] T039 [P] [US3] Prueba de contrato HTTP en `tests/contract/test_reportes_http.py`: `GET .../exportar/conciliacion/` con `200/403/404/405`, `Content-Disposition` correcto y sin ruta física
- [ ] T040 [P] [US3] Prueba unitaria del Excel en `tests/unit/test_reportes_excel.py`: encabezados, columna Tenant solo en global, conteos y una hoja

### Implementación de US3

- [ ] T041 [US3] Implementar en `reportes/excel.py` `construir_excel_conciliacion(conciliaciones, es_global) -> bytes` con las columnas y formato de `contracts/excel-reportes.md`; no persistir archivo
- [ ] T042 [US3] Implementar en `reportes/services.py` `exportar_conciliacion`: resolver alcance, filtrar `Conciliacion` por `fecha_carga` y tenant, anotar conteos de diferencias y devolver `ArchivoReporte`
- [ ] T043 [US3] Implementar en `reportes/views.py` y `reportes/urls.py` la descarga de conciliación desde el corte, con `Content-Disposition` y sin `POST`
- [ ] T044 [US3] Ejecutar `pytest tests/integration/test_exportacion_conciliacion.py tests/unit/test_reportes_excel.py tests/contract/test_reportes_http.py` y corregir hasta que CA-04 esté en verde

**Checkpoint**: US3 funcional; la conciliación del mes se exporta con diferencias y ajustes.

---

## Fase 6: US4 — Consultar historial y regenerar el corte (P4)

**Objetivo**: el Admin o el tenant consulta cortes históricos según su alcance y regenera un corte
existente, incrementando la versión y auditando los valores anteriores y nuevos.

**Prueba independiente**: listar cortes de dos tenants y globales; el tenant solo ve los suyos; el
Admin ve todo. Regenerar un corte cambia totales/versión y deja auditoría.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T045 [P] [US4] Pruebas de historial en `tests/integration/test_corte_mensual.py`: listado por tenant/año, corte ajeno `404`, global solo Admin, orden por año/mes
- [ ] T046 [US4] Prueba de regeneración en `tests/integration/test_corte_mensual.py`: recalcula totales, `version += 1`, `regenerado_en`, `actualizado_por` y auditoría con valores anterior/nuevo
- [ ] T047 [P] [US4] Prueba de contrato HTTP en `tests/contract/test_reportes_http.py`: `POST regenerar` con `302/403/404/405/409`; `GET` devuelve `405`

### Implementación de US4

- [ ] T048 [US4] Implementar en `reportes/services.py` `listar_cortes`, `obtener_corte`, `detalle_corte` y `regenerar_corte`, con alcance, `select_for_update`, versión y auditoría
- [ ] T049 [US4] Implementar en `reportes/views.py` y `reportes/urls.py` la regeneración y el historial, y completar `templates/reportes/cortes_listado.html`/`corte_detalle.html` con versión, fechas y acciones
- [ ] T050 [US4] Ejecutar `pytest tests/integration/test_corte_mensual.py tests/contract/test_reportes_http.py` y corregir hasta que el historial y la regeneración estén en verde

**Checkpoint**: US4 funcional; el historial respeta el alcance y la regeneración es versionada y
auditada.

---

## Fase 7: Polish y preocupaciones transversales

- [ ] T051 [P] Ejecutar `pytest -k "reporte or corte or merma"` sobre `tests/unit`, `tests/integration` y `tests/contract` con PostgreSQL y corregir cualquier fallo
- [ ] T052 [P] Ejecutar `pytest --cov=reportes` y revisar que cada validación, excepción y transición de `reportes/services.py` tenga al menos una prueba
- [ ] T053 [P] Agregar en `tests/integration/test_reportes_concurrencia.py` las pruebas de dos generaciones simultáneas, dos regeneraciones simultáneas y ausencia de interbloqueo
- [ ] T054 Agregar en `tests/integration/test_reportes_concurrencia.py` la prueba de rendimiento: 10 000 líneas para el corte y 5 000 registros de auditoría para la exportación, sin N+1
- [ ] T055 Agregar en `tests/integration/test_reportes_concurrencia.py` las pruebas de aislamiento: tenant A no ve cortes/exportaciones de B; global solo Admin; RLS activa si está disponible
- [ ] T056 [P] Revisar `reportes/models.py`, `reportes/services.py`, `reportes/excel.py` y `reportes/views.py`: sin escrituras a stock/series/asignaciones/conciliaciones, sin permisos Django, sin correo/Celery, sin `tenant_id` del cliente y con mensajes en español
- [ ] T057 [P] Revisar `reportes/migrations/`, `auditoria/migrations/` y `conciliaciones/migrations/`: restricciones parciales, RLS, `RegistroCambio.tenant` y `ajustes_aplicados`
- [ ] T058 [P] Actualizar `05-especificaciones/012-reportes-mensuales/quickstart.md` con los comandos y resultados reales de la suite, sin duplicar contratos ni modelos
- [ ] T059 [P] Verificar en `05-especificaciones/012-reportes-mensuales/spec.md`, `001-tenants-y-acceso/data-model.md`, `auditoria/services.py` y `conciliaciones/models.py` que las correcciones de 012/001/010 siguen aplicadas y que `RegistroCambio.tenant` se puebla en todos los flujos
- [ ] T060 Ejecutar `python manage.py check` y `python manage.py migrate --check`; confirmar que no hay migraciones pendientes ni errores de configuración
- [ ] T061 Recorrer los escenarios de `quickstart.md` para CA-01…CA-04 y registrar el resultado; corregir implementación o documento antes de cerrar
- [ ] T062 Revisar `reportes/services.py`, `reportes/views.py`, `config/settings/base.py` y `requirements-dev.txt`: 012 no agrega dependencias, correo, Celery ni permisos Django, y no hay escrituras a stock/series/conciliaciones

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Setup (Fase 1)**: depende de 001–011 implementadas y de las correcciones documentales.
- **Fundacional (Fase 2)**: depende de Setup; **bloquea** las historias.
- **US1 (Fase 3)**: depende de Fundacional; entrega el corte.
- **US2 (Fase 4)**: depende de US1 (necesita un corte para exportar).
- **US3 (Fase 5)**: depende de US1; puede ejecutarse en paralelo con US2.
- **US4 (Fase 6)**: depende de US1; puede ejecutarse en paralelo con US2/US3.
- **Polish (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1** es el MVP: sin corte no hay exportaciones ni regeneración.
- **US2** y **US3** son independientes entre sí una vez que US1 existe.
- **US4** usa el mismo `CorteMensual` y comparte `services.py` con US1.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar.
- Modelos y migraciones antes de servicios.
- Servicios antes de vistas y plantillas.
- No se avanza con pruebas en rojo.

### Oportunidades de paralelización

- T005/T006 en Setup.
- T007–T011 en Fundacional (archivos de prueba distintos; T007–T010 comparten `test_reportes_servicios.py` y van en secuencia).
- T019–T022 en US1 comparten `test_corte_mensual.py`; T023/T024 usan archivos distintos.
- T029/T030 en US2 comparten `test_exportacion_auditoria.py`; T031/T032 usan archivos distintos.
- T037/T038 en US3 comparten `test_exportacion_conciliacion.py`; T039/T040 usan archivos distintos.
- T045–T046 en US4 comparten `test_corte_mensual.py`; T047 usa otro archivo.
- T051–T059 en Polish usan archivos distintos.

**Nota**: `reportes/services.py` es el archivo de mayor contención; T015–T017, T025, T034, T042 y
T048 deben secuenciarse.

---

## Ejemplo de paralelización: US2 y US3

```text
# US2: pruebas en archivos distintos
Tarea: "Contrato HTTP de auditoría en tests/contract/test_reportes_http.py"        # T031
Tarea: "Excel de auditoría en tests/unit/test_reportes_excel.py"                   # T032

# US3: pruebas en archivos distintos
Tarea: "Contrato HTTP de conciliación en tests/contract/test_reportes_http.py"     # T039
Tarea: "Excel de conciliación en tests/unit/test_reportes_excel.py"                # T040

# Implementación comparte services.py/excel.py: secuenciar
T033 → T034 → T035
T041 → T042 → T043
```

## Estrategia de implementación

### MVP (Fundacional + US1)

1. Completar Setup y campos de apoyo.
2. Completar Fundacional; validar cálculo y merma.
3. Completar US1.
4. **DETENERSE y VALIDAR**: CA-01 y CA-02 en verde.
5. Demostrar corte mensual por tenant y global.

### Entrega incremental

1. Fundacional → cálculo y modelo.
2. US1 → corte y merma.
3. US2 → exportación de auditoría.
4. US3 → exportación de conciliación.
5. US4 → historial y regeneración.
6. Polish → concurrencia, rendimiento y documentación.

---

## Trazabilidad de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US1 | T019, T028 |
| CA-02 | US1 | T020, T028 |
| CA-03 | US2 | T029, T036 |
| CA-04 | US3 | T037, T044 |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id` del cliente para una cuenta de tenant.
- 012 no escribe stock, series, asignaciones ni conciliaciones; solo `CorteMensual`.
- Los Excel se generan en memoria y no se persisten.
- Evitar tareas vagas y conflictos de archivo; `reportes/services.py` debe secuenciarse.
