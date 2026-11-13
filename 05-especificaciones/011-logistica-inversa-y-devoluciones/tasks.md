---
description: "Lista de tareas para la implementación de 011 Logística Inversa y Devoluciones"
---

# Tareas: 011 Logística Inversa y Devoluciones

**Entrada**: Documentos de diseño en `05-especificaciones/011-logistica-inversa-y-devoluciones/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`,
`ContextoUsuarioMiddleware`, `tenants.Tenant`, `tenants.Region` y `auditoria.RegistroCambio`),
**spec 002 implementada** (`materiales.Material`), **spec 003 implementada**
(`tecnicos.Tecnico`), **spec 004 implementada** (`series.Serie`, `EstadoSerie` y
`tecnico`/`asignada_en`), **spec 005/008 implementadas** (`StockTecnico`, `StockGeneral`,
incrementos/decrementos y auditoría), **spec 009 implementada** (custodia y reservas de traspaso) y
**spec 010 implementada** (`INSTALADA`). También deben estar aplicadas las correcciones de `plan.md`:
`INACTIVA` en 004/009, distinción con `INSTALADA` en 012 y acta automática en el contrato. La app
`logistica_inversa` se crea aquí; no se duplican tablas de stock, series, técnicos ni materiales.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-06. Cada historia escribe primero sus pruebas,
las ve fallar y luego implementa. Todas las pruebas usan PostgreSQL, nunca SQLite.

**Organización**: `spec.md` declara HU-23, HU-24 y HU-25 sin prioridad explícita; se agrupan en cuatro
historias derivadas para permitir entregas incrementales, sin agregar funcionalidad fuera de la spec.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia asociada (`US1`…`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Registrar devolución y liberar custodia | P1 | HU-23; RF-65; CA-01, CA-02; §5.1 |
| US2 — Registrar baja con causa | P2 | HU-24; RF-66; CA-03, CA-04; §5.2 |
| US3 — Generar y descargar el acta | P3 | HU-25; RF-67; CA-05; §5.3 |
| US4 — Auditar y proteger la integridad | P4 | CA-06; §6.1–§6.3 |

## Convenciones de rutas

Proyecto Django único en la raíz: app nueva `logistica_inversa/`, plantillas en
`templates/logistica_inversa/`, pruebas en `tests/{unit,integration,contract}/` y migración
transversal en `series/migrations/`. Las apps `acceso`, `tenants`, `auditoria`, `materiales`,
`tecnicos`, `series`, `asignaciones` y `stock` son propiedad de sus specs. 011 **no** crea tablas de
stock, series ni técnicos, **no** elimina series, **no** envía correo, **no** usa Celery y **no** usa
permisos Django por cadena.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: verificar prerrequisitos y correcciones, crear la app, registrar rutas, preparar
fixtures y comprobar RLS.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `series/models.py`, `stock/models.py`, `stock/services.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware`, roles, `Material.es_seriado`/`lote`, `Tecnico.tenant`/`nif`, `Serie` con `numero`/estado/`tecnico`/`asignada_en`, `StockTecnico`/`StockGeneral` y servicios de incremento/decremento, y `registrar_cambio`; detenerse y reportar si falta alguno
- [ ] T002 Crear el esqueleto de `logistica_inversa` en `logistica_inversa/__init__.py`, `apps.py`, `models.py`, `services.py`, `acta.py`, `forms.py`, `views.py`, `urls.py` y `migrations/__init__.py`; registrar `"logistica_inversa"` y `ACTAS_DIR` en `config/settings/base.py` e incluir `logistica_inversa.urls` desde `config/urls.py`
- [ ] T003 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region_logistica`, `tenant_logistica`, `tenant_logistica_otro`, `usuario_tenant_logistica`, `tecnico_logistica`, `tecnico_otro_tenant`, `material_seriado_logistica`, `serie_asignada_logistica`, `serie_disponible_logistica`, `serie_reservada_logistica`, `serie_instalada_logistica`, `stock_tecnico_logistica`, `stock_general_logistica`, `devolucion_registrada`, `baja_registrada` y `registro_cambios_logistica`
- [ ] T004 [P] Comprobar si la infraestructura RLS de 001 está disponible en `config/settings/base.py` y en las migraciones de `tenants`; si no lo está, registrar la deuda en `05-especificaciones/011-logistica-inversa-y-devoluciones/research.md` y no crear una infraestructura paralela
- [ ] T005 [P] Verificar que las correcciones documentales estén aplicadas en `05-especificaciones/011-logistica-inversa-y-devoluciones/spec.md`, `004-recojo-de-materiales/`, `009-traspaso-entre-tecnicos/data-model.md`, `012-reportes-mensuales/plan.md` y `04-contratos/acta-devoluciones.md`: `INACTIVA`, distinción con `INSTALADA`, acta automática y envío manual; corregir antes de implementar si algo no coincide

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: estado `INACTIVA`, modelos de devolución/baja, RLS, excepciones, validadores, acta y
auditoría base que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

### Pruebas fundacionales (escribir primero, deben fallar)

- [ ] T006 [P] Escribir en `tests/unit/test_logistica_inversa_servicios.py` las pruebas de restricciones de `Devolucion`, `LineaDevolucion` y `BajaEquipo`: `tenant`/`region` obligatorios, `CASCADE`/`PROTECT`, `unique(devolucion, serie)`, `OneToOneField(serie)` en baja, causa válida, cantidades no negativas y campos del acta
- [ ] T007 [P] Escribir en `tests/integration/test_devolucion_registro.py` las pruebas de `series.EstadoSerie.INACTIVA`: valor en choices, `CheckConstraint` de estado, coherencia `INACTIVA`/custodia nula, `ASIGNADA` con técnico/fecha y migración sin cambios de datos
- [ ] T008 [P] Escribir en `tests/unit/test_logistica_inversa_acta.py` las pruebas de `generar_acta_devolucion`: una hoja, metadatos tenant/región/fecha/ID, tabla NIF/material/descripción/serie/fecha, orden estable, hash SHA-256, nombre relativo seguro y sin binarios en base
- [ ] T009 Escribir en `tests/unit/test_logistica_inversa_servicios.py` las pruebas de validadores: cuenta/tenant, técnico del tenant/región, serie del tenant, serie no asignada, reservada, instalada/inactiva, fecha futura, causa requerida/inválida y al menos una serie
- [ ] T010 [P] Escribir en `tests/contract/test_logistica_inversa_http.py` las pruebas de contrato de firmas y excepciones de `logistica_inversa/services.py` según `contracts/servicios-logistica-inversa.md`

### Implementación fundacional

- [ ] T011 Añadir `INACTIVA` a `EstadoSerie` en `series/models.py`, incluirlo en `serie_estado_valido` y ampliar `serie_tecnico_coherente_estado` para exigir custodia nula
- [ ] T012 Crear `series/migrations/0005_serie_inactiva.py`: actualizar choices/check y coherencia de custodia; no reescribir series existentes ni crear datos
- [ ] T013 Implementar `Devolucion`, `LineaDevolucion` y `BajaEquipo` en `logistica_inversa/models.py`: devolución con `tenant`/`region`/`tecnico`/`fecha`/`observaciones`/acta/`creado_por`/`creado_en`; línea con `tenant`/`devolucion`/`serie` FK/`material`/`descripcion`/`lote`; baja con `tenant`/`region`/`serie` OneToOne/`material`/`causa`/`observaciones`/`creado_por`/`creado_en`; restricciones e índices de `data-model.md`
- [ ] T014 Crear `logistica_inversa/migrations/0001_initial.py` con T013, revisar que no cree devoluciones ni bajas por migración y aplicar con `python manage.py migrate`
- [ ] T015 Crear `logistica_inversa/migrations/0002_rls.py` con RLS por `tenant_id`/`region_id` en devoluciones y bajas y por `tenant_id` en líneas; si T004 determinó que 001 no está disponible, dejar la migración inactiva y registrar la deuda
- [ ] T016 Implementar en `logistica_inversa/acta.py` `generar_acta_devolucion`: una hoja, metadatos, tabla ordenada, ruta relativa segura, hash SHA-256 y actualización de `acta_ruta`/`acta_hash`/`acta_generada_en`; no envía correo
- [ ] T017 Implementar en `logistica_inversa/services.py` las excepciones y mensajes exactos de `contracts/servicios-logistica-inversa.md`: `PermisoDenegado`, `TecnicoNoExiste`, `SerieNoEnTecnico`, `SerieNoDisponible`, `SerieReservada`, `SerieYaInactiva`, `SerieInstalada`, `SerieFueraTenant`, `CausaRequerida`, `CausaInvalida`, `FechaInvalida`, `SinSeries`, `NoEncontrado`, `ArchivoNoDisponible` y `HashNoCoincide`
- [ ] T018 Implementar en `logistica_inversa/services.py` `validar_cuenta_tenant`, `validar_tecnico`, `validar_serie_para_devolucion`, `validar_serie_para_baja` y `validar_fecha_devolucion`, incluyendo la exclusión de series referenciadas por traspasos `ENVIADA`
- [ ] T019 Implementar en `logistica_inversa/services.py` el helper de auditoría para `Devolucion/alta`, `LineaDevolucion/alta`, `Devolucion/acta`, `BajaEquipo/alta`, `Serie/estado`, `Serie/tecnico` y `Serie/asignada_en`, usando `auditoria.services.registrar_cambio`, sin secretos ni binarios
- [ ] T020 Ejecutar `pytest tests/unit/test_logistica_inversa_servicios.py tests/unit/test_logistica_inversa_acta.py tests/integration/test_devolucion_registro.py tests/contract/test_logistica_inversa_http.py`; corregir hasta que la fase fundacional esté en verde

**Checkpoint**: estado `INACTIVA`, modelos, RLS, validadores, acta y auditoría listos; las historias
pueden comenzar.

---

## Fase 3: US1 — Registrar devolución y liberar custodia (P1) 🎯 MVP

**Objetivo**: el tenant registra la devolución de series de un técnico; las series vuelven a
`DISPONIBLE`, se libera la custodia, el stock del técnico baja y el general sube, y se genera el acta.

**Prueba independiente**: devolver 3 series de un técnico y verificar `DISPONIBLE`, custodia nula,
`StockTecnico` −3, `StockGeneral` +3, acta generada y auditoría. Intentar devolver una serie no
asignada, reservada o de otro tenant y recibir rechazo.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T021 [P] [US1] Prueba de **CA-01** en `tests/integration/test_devolucion_registro.py`: `test_devolucion_libera_custodia`; series `DISPONIBLE`, `tecnico=None`, `asignada_en=None`, stock técnico abajo y general arriba
- [ ] T022 [US1] Prueba de **CA-02** en `tests/integration/test_devolucion_registro.py`: `test_series_devueltas_pueden_reasignarse`; la serie vuelve a estar disponible y puede asignarse a otro técnico
- [ ] T023 [US1] Prueba de stock en `tests/integration/test_devolucion_stock.py`: por material, `StockTecnico` baja y `StockGeneral` sube por el mismo total; total del tenant invariante; no hay negativos
- [ ] T024 [US1] Pruebas de validación en `tests/integration/test_devolucion_registro.py`: serie no asignada, reservada, instalada/inactiva, de otro tenant, fecha futura, sin series o duplicada se rechazan sin cambios
- [ ] T025 [P] [US1] Prueba de contrato HTTP en `tests/contract/test_logistica_inversa_http.py`: listado, formulario, detalle y `POST` de devolución con `200/302/400/403/404/405/409`
- [ ] T026 [P] [US1] Prueba de auditoría de devolución en `tests/integration/test_logistica_inversa_auditoria.py`: `Devolucion/alta`, una `LineaDevolucion/alta` por serie, `Devolucion/acta`, `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en` y stock de 008

### Implementación de US1

- [ ] T027 [US1] Implementar en `logistica_inversa/services.py` `registrar_devolucion`: validar cuenta, técnico, fecha, series y duplicados; en `transaction.atomic` bloquear `Tenant`, `StockGeneral` y `StockTecnico` por material y series por `id`; revalidar y crear cabecera/líneas
- [ ] T028 [US1] Implementar en `logistica_inversa/services.py` el cambio de cada serie a `DISPONIBLE` con `tecnico=None`/`asignada_en=None`, y los ajustes agrupados por material con `decrementar_stock_tecnico` e `incrementar_stock_general`; no tocar otros niveles
- [ ] T029 [US1] Integrar en `registrar_devolucion` la generación del acta dentro de la transacción, el guardado de ruta/hash, la auditoría `Devolucion/acta` y la limpieza del archivo si falla
- [ ] T030 [US1] Implementar en `logistica_inversa/forms.py` el formulario de devolución: técnico del tenant, fecha por defecto hoy, series `ASIGNADA` del técnico no reservadas, observaciones; no aceptar tenant/región/material/estado del cliente
- [ ] T031 [US1] Implementar en `logistica_inversa/views.py` y `logistica_inversa/urls.py` listado, creación y detalle de devoluciones, con login, CSRF y mapeo `400/403/404/405/409`; crear `templates/logistica_inversa/devoluciones_listado.html`, `devolucion_formulario.html` y `devolucion_detalle.html`
- [ ] T032 [US1] Ejecutar `pytest tests/integration/test_devolucion_registro.py tests/integration/test_devolucion_stock.py tests/integration/test_logistica_inversa_auditoria.py tests/contract/test_logistica_inversa_http.py` y corregir hasta que CA-01, CA-02 y CA-06 de devolución estén en verde

**Checkpoint**: US1 funcional; la devolución libera custodia, mueve stock al general y genera acta.

---

## Fase 4: US2 — Registrar baja con causa (P2)

**Objetivo**: el tenant registra una baja/recuperación con causa; la serie sale del stock del técnico
o del general, según dónde esté, y queda `INACTIVA`, sin posibilidad de reasignarse.

**Prueba independiente**: dar de baja una serie `ASIGNADA` por avería y una `DISPONIBLE` por migración;
verificar `INACTIVA`, stock del nivel correcto descontado, causa registrada y auditoría. Intentar dar
de baja una reservada o instalada y recibir rechazo.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T033 [P] [US2] Prueba de **CA-03** en `tests/integration/test_baja_registro.py`: `test_recuperacion_con_causa`; serie `ASIGNADA` con causa `AVERIA` queda `INACTIVA`, baja `StockTecnico`, no toca general y registra la causa
- [ ] T034 [US2] Prueba de **CA-04** en `tests/integration/test_baja_registro.py`: `test_baja_por_migracion`; serie `DISPONIBLE` con causa `MIGRACION` queda `INACTIVA`, baja `StockGeneral`, no toca técnico y registra la causa
- [ ] T035 [US2] Prueba de stock en `tests/integration/test_baja_stock.py`: solo se descuenta el nivel donde estaba la serie; no hay doble descuento ni negativos; el total del tenant baja en 1
- [ ] T036 [US2] Pruebas de validación en `tests/integration/test_baja_registro.py`: causa faltante/inválida, serie reservada/instalada/inactiva, serie de otro tenant, serie inexistente y doble baja se rechazan
- [ ] T037 [P] [US2] Prueba de contrato HTTP en `tests/contract/test_logistica_inversa_http.py`: listado, formulario, detalle y `POST` de baja con `200/302/400/403/404/405/409`
- [ ] T038 [P] [US2] Prueba de auditoría de baja en `tests/integration/test_logistica_inversa_auditoria.py`: `BajaEquipo/alta`, `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en` y stock del nivel correcto, con causa

### Implementación de US2

- [ ] T039 [US2] Implementar en `logistica_inversa/services.py` `registrar_baja_equipo`: validar cuenta, serie, causa y estado; en `transaction.atomic` bloquear `Tenant`, la fila de stock correspondiente y la serie; revalidar y crear `BajaEquipo`
- [ ] T040 [US2] Implementar en `logistica_inversa/services.py` `registrar_baja_equipo` el ajuste de stock correcto: `decrementar_stock_tecnico` si estaba `ASIGNADA`, `decrementar_stock_general` si estaba `DISPONIBLE`; nunca ambos
- [ ] T041 [US2] Implementar en `registrar_baja_equipo` el cambio a `INACTIVA`, la limpieza de `tecnico`/`asignada_en` y la auditoría `BajaEquipo/alta`, `Serie/estado` y custodia
- [ ] T042 [US2] Implementar en `logistica_inversa/forms.py` el formulario de baja: serie existente del tenant, causa `AVERIA`/`MIGRACION`/`OTRO`, observaciones; no aceptar material, tenant ni estado del cliente
- [ ] T043 [US2] Implementar en `logistica_inversa/views.py` y `logistica_inversa/urls.py` listado, creación y detalle de bajas; crear `templates/logistica_inversa/bajas_listado.html` y `baja_formulario.html`
- [ ] T044 [US2] Ejecutar `pytest tests/integration/test_baja_registro.py tests/integration/test_baja_stock.py tests/integration/test_logistica_inversa_auditoria.py tests/contract/test_logistica_inversa_http.py` y corregir hasta que CA-03 y CA-04 estén en verde

**Checkpoint**: US2 funcional; la baja saca la serie del nivel correcto y la deja `INACTIVA`.

---

## Fase 5: US3 — Generar y descargar el acta (P3)

**Objetivo**: la devolución entrega un acta de una hoja con todas las series, técnico y fecha; el
tenant la descarga verificando su hash y no puede alterarla.

**Prueba independiente**: registrar una devolución de 3 series, descargar el acta y verificar una hoja,
metadatos, tabla completa y hash; alterar el archivo y comprobar que la descarga se bloquea.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T045 [US3] Prueba de **CA-05** en `tests/unit/test_logistica_inversa_acta.py`: `test_generacion_acta`; el acta contiene todas las series devueltas, NIF, material, descripción y fecha, con metadatos correctos
- [ ] T046 [US3] Prueba de hash y descarga en `tests/integration/test_logistica_inversa_acta.py`: descarga `200` con `.xlsx`; archivo ausente `404`; hash alterado `409`; no se expone la ruta física
- [ ] T047 [P] [US3] Prueba de rollback del acta en `tests/integration/test_devolucion_registro.py`: si falla la generación, no se crea la devolución, no se mueve stock y no queda archivo parcial
- [ ] T048 [P] [US3] Prueba de contrato HTTP en `tests/contract/test_logistica_inversa_http.py`: `GET /logistica-inversa/devoluciones/<id>/acta/` con `200/404/405/409` y sin `POST`

### Implementación de US3

- [ ] T049 [US3] Implementar en `logistica_inversa/services.py` `verificar_hash_acta` y la resolución segura de ruta bajo `ACTAS_DIR`/`MEDIA_ROOT`; rechazar `..`, rutas absolutas y salidas del directorio
- [ ] T050 [US3] Implementar en `logistica_inversa/views.py` y `logistica_inversa/urls.py` la descarga del acta con verificación de hash, nombre seguro y sin exponer la ruta física; añadir el enlace en `templates/logistica_inversa/devolucion_detalle.html`
- [ ] T051 [US3] Ejecutar `pytest tests/unit/test_logistica_inversa_acta.py tests/integration/test_logistica_inversa_acta.py tests/integration/test_devolucion_registro.py tests/contract/test_logistica_inversa_http.py` y corregir hasta que CA-05 esté en verde

**Checkpoint**: US3 funcional; el acta es completa, inmutable y se descarga verificando el hash.

---

## Fase 6: US4 — Auditar y proteger la integridad (P4)

**Objetivo**: devoluciones y bajas son atómicas, auditables, aisladas y resistentes a concurrencia; no
se eliminan series ni se duplican los movimientos de stock de 008.

**Prueba independiente**: ejecutar devoluciones y bajas, revisar la auditoría completa, forzar fallos y
operaciones concurrentes, y comprobar que no hay estados parciales ni datos de otro tenant.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T052 [US4] Prueba de **CA-06** en `tests/integration/test_logistica_inversa_auditoria.py`: `test_auditoria_devoluciones`; todos los eventos de devolución con actor, fecha y valores anterior/nuevo
- [ ] T053 [US4] Prueba de auditoría de baja en `tests/integration/test_logistica_inversa_auditoria.py`: `BajaEquipo/alta`, estado y stock del nivel correcto, sin duplicar 008
- [ ] T054 [US4] Prueba de prohibiciones en `tests/integration/test_logistica_inversa_auditoria.py`: sin contraseñas, tokens, secretos, binarios, rutas absolutas ni datos de otro tenant
- [ ] T055 [US4] Prueba de concurrencia en `tests/integration/test_logistica_inversa_concurrencia.py`: dos devoluciones de la misma serie, dos bajas de la misma serie, devolución vs traspaso y orden de bloqueo sin interbloqueo
- [ ] T056 [US4] Prueba de aislamiento en `tests/integration/test_logistica_inversa_concurrencia.py`: tenant A no ve ni opera devoluciones/bajas de B; región ajena `404`; series/stock de otro tenant no se consultan; RLS activa si está disponible
- [ ] T057 [US4] Prueba de rendimiento en `tests/integration/test_logistica_inversa_concurrencia.py`: devolución de 100 series en menos de 2 segundos, sin una consulta por serie

### Implementación de US4

- [ ] T058 [US4] Completar en `logistica_inversa/services.py` las guardas de atomicidad y bloqueo: una sola transacción externa, sin commit propio, revalidación dentro del bloqueo, orden `Tenant → StockGeneral (material) → StockTecnico (material) → Serie` y limpieza del acta si falla
- [ ] T059 [US4] Revisar `logistica_inversa/services.py`, `logistica_inversa/acta.py`, `logistica_inversa/models.py` y `logistica_inversa/views.py`: sin `F()` ciego, sin eliminar series, sin doble decremento, sin permisos Django, sin correo/Celery y sin `tenant_id` del cliente
- [ ] T060 [US4] Ejecutar `pytest tests/integration/test_logistica_inversa_auditoria.py tests/integration/test_logistica_inversa_concurrencia.py` y corregir hasta que la auditoría, el aislamiento y la concurrencia estén en verde

**Checkpoint**: US4 funcional; la logística inversa es atómica, auditable, aislada y concurrente.

---

## Fase 7: Polish y preocupaciones transversales

- [ ] T061 [P] Ejecutar `pytest -k "logistica_inversa or devolucion or baja"` sobre `tests/unit`, `tests/integration` y `tests/contract` con PostgreSQL y corregir cualquier fallo
- [ ] T062 [P] Ejecutar `pytest --cov=logistica_inversa` y revisar que cada validación, excepción y transición de `logistica_inversa/services.py` tenga al menos una prueba
- [ ] T063 [P] Revisar `logistica_inversa/acta.py` y `logistica_inversa/services.py`: acta de una hoja, hash, ruta segura, sin binarios en base/auditoría y sin correo
- [ ] T064 [P] Revisar `logistica_inversa/models.py` y las migraciones: `tenant`/`region` obligatorios, RLS, `OneToOneField` de baja, `unique(devolucion, serie)` y ningún cambio a tablas de stock o series fuera de `INACTIVA`
- [ ] T065 [P] Revisar `logistica_inversa/views.py`, `logistica_inversa/urls.py` y `templates/logistica_inversa/`: sin lógica de negocio, sin datos de otro tenant, sin `POST` para el acta y con CSRF
- [ ] T066 [P] Actualizar `05-especificaciones/011-logistica-inversa-y-devoluciones/quickstart.md` con los comandos y resultados reales de la suite, sin duplicar contratos ni modelos
- [ ] T067 [P] Verificar que las correcciones de 004/009/012 y `04-contratos/acta-devoluciones.md` siguen aplicadas
- [ ] T068 Ejecutar `python manage.py check` y `python manage.py migrate --check`; confirmar que no hay migraciones pendientes ni errores de configuración
- [ ] T069 Recorrer los escenarios de `quickstart.md` para CA-01…CA-06 y registrar el resultado; corregir implementación o documento antes de cerrar
- [ ] T070 Revisar `logistica_inversa/services.py`, `logistica_inversa/views.py`, `config/settings/base.py` y `requirements-dev.txt`: 011 no agrega dependencias, correo, Celery ni permisos Django, y ninguna serie se elimina

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Setup (Fase 1)**: depende de 001–010 implementadas y de las correcciones documentales.
- **Fundacional (Fase 2)**: depende de Setup; **bloquea** las historias.
- **US1 (Fase 3)**: depende de Fundacional; entrega devolución y acta.
- **US2 (Fase 4)**: depende de Fundacional; puede ejecutarse en paralelo con US1 si se coordinan archivos.
- **US3 (Fase 5)**: depende de US1 (acta generada).
- **US4 (Fase 6)**: depende de US1–US3.
- **Polish (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1** es el MVP: sin devolución no hay custodia liberada ni acta.
- **US2** es independiente de US1 una vez que Fundacional existe; ambas comparten `services.py`.
- **US3** valida y expone el acta generada por US1.
- **US4** verifica propiedades de las tres anteriores.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar.
- Modelos y migraciones antes de servicios.
- Servicios antes de vistas y plantillas.
- No se avanza con pruebas en rojo.

### Oportunidades de paralelización

- T003–T005 en Setup.
- T006–T010 en Fundacional (archivos de prueba distintos; T006/T009 comparten `test_logistica_inversa_servicios.py` y van en secuencia).
- T021–T024 y T026 en US1: las pruebas de `test_devolucion_registro.py` van en secuencia; T025/T026 usan archivos distintos.
- T033–T036 y T038 en US2: las pruebas de `test_baja_registro.py` van en secuencia; T037/T038 usan archivos distintos.
- T045/T046 en US3 comparten `test_logistica_inversa_acta.py`; T047/T048 usan archivos distintos.
- T052–T054 en US4 comparten auditoría; T055–T057 comparten concurrencia.
- T061–T067 en Polish usan archivos distintos.

**Nota**: `logistica_inversa/services.py` es el archivo de mayor contención; T027–T029, T039–T041,
T049 y T058 deben secuenciarse.

---

## Ejemplo de paralelización: US1 y US2

```text
# US1: pruebas en archivos distintos
Tarea: "Contrato HTTP de devoluciones en tests/contract/test_logistica_inversa_http.py"  # T025
Tarea: "Auditoría de devolución en tests/integration/test_logistica_inversa_auditoria.py" # T026

# US2: pruebas en archivos distintos
Tarea: "Contrato HTTP de bajas en tests/contract/test_logistica_inversa_http.py"         # T037
Tarea: "Auditoría de baja en tests/integration/test_logistica_inversa_auditoria.py"       # T038

# Implementación compartida: secuenciar services.py
T027 → T028 → T029
T039 → T040 → T041
```

## Estrategia de implementación

### MVP (Fundacional + US1)

1. Completar Setup.
2. Completar Fundacional; validar estado `INACTIVA`, modelos, validadores y acta.
3. Completar US1.
4. **DETENERSE y VALIDAR**: CA-01, CA-02 y CA-06 de devolución en verde.
5. Demostrar devolución con liberación de custodia y acta.

### Entrega incremental

1. Fundacional → modelos y acta listos.
2. US1 → devolución y liberación de custodia.
3. US2 → baja con causa.
4. US3 → descarga verificada del acta.
5. US4 → auditoría, concurrencia y aislamiento.
6. Polish → cobertura, rendimiento y documentación.

---

## Trazabilidad de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US1 | T021, T032 |
| CA-02 | US1 | T022, T032 |
| CA-03 | US2 | T033, T044 |
| CA-04 | US2 | T034, T044 |
| CA-05 | US3 | T045, T051 |
| CA-06 | US4 | T052, T060 |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id`, `region_id`, material, estado ni NIF del cliente.
- 011 no elimina series, no crea series, no envía correo, no usa Celery y no crea permisos Django.
- La devolución mueve stock del técnico al general; la baja descuenta solo el nivel donde estaba la
  serie.
- Evitar tareas vagas y conflictos de archivo; `logistica_inversa/services.py` debe secuenciarse.
