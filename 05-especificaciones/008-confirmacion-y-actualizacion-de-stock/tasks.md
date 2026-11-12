---
description: "Lista de tareas para la implementación de 008 Confirmación y Actualización de Stock"
---

# Tareas: 008 Confirmación y Actualización de Stock

**Entrada**: Documentos de diseño en `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`,
`ContextoUsuarioMiddleware`, `tenants.Tenant`, `tenants.Region` y `auditoria.RegistroCambio`),
**spec 002 implementada** (`materiales.Material` con `codigo`, `descripcion`, `lote` y
`es_seriado`), **spec 003 implementada** (`tecnicos.Tecnico` con `tenant`, `nif` y `activo`),
**spec 004 implementada** (`series.Serie` y `EstadoSerie` con `DISPONIBLE`, `RESERVADA` y
`ASIGNADA`), **spec 006 implementada** (`asignaciones.SolicitudAsignacion` con `tenant`, `region`,
`tecnico`, `estado`, `confirmada_en` y `LineaAsignacion` con `material`, `serie` y `cantidad`) y
**spec 007 con `confirmar_solicitud` y su transacción listas** para llamar a 008. La parte
fundacional de 008 (`StockGeneral`, `StockTecnico` y sus servicios) se implementa **antes** de 004
y 005; la parte de confirmación, después de 006 y 007. La creación de solicitudes, el envío, el
rechazo y la interfaz del almacén pertenecen a 006/007 y no se repiten aquí.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-07. Cada historia escribe primero sus
pruebas, las ve fallar y luego implementa. Todas las pruebas usan PostgreSQL, nunca SQLite.

**Organización**: `spec.md` declara una sola historia, HU-16, sin prioridad explícita. Para permitir
entregas incrementales se derivan cuatro historias a partir de los criterios de aceptación, igual
que en 007. Las historias no crean funcionalidad fuera de la spec.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia asociada (`US1`…`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Confirmar y mover series y stock | P1 | HU-16; RF-32; CA-01, CA-02, CA-03, CA-07; §5.1–§5.3 |
| US2 — Revertir todo si falla una parte | P2 | HU-16; CA-04; §5.5, §6.1 |
| US3 — Iniciar los días en mano | P3 | HU-16; CA-05; §5.4 |
| US4 — Auditar series y stock | P4 | HU-16; CA-06; §5.6, §6.3 |

## Convenciones de rutas

Proyecto Django único en la raíz: app nueva `stock/`, pruebas en `tests/{unit,integration,contract}/`
y configuración en `config/settings/`. Las apps `acceso`, `tenants`, `auditoria` (001), `materiales`
(002), `tecnicos` (003), `series` (004), `asignaciones` (006/007) y `stock` (008) son propiedad de
sus specs. 008 **no** crea endpoints, vistas, plantillas ni tareas Celery, **no** cambia el estado de
la solicitud y **no** implementa el rechazo.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: crear la app, registrarla, preparar fixtures, comprobar la infraestructura RLS y
confirmar que las correcciones documentales están aplicadas.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `series/models.py`, `asignaciones/models.py`, `asignaciones/services.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware`, `Material.es_seriado`/`lote`, `Tecnico.tenant`/`nif`/`activo`, `Serie.estado` con `DISPONIBLE`/`RESERVADA`/`ASIGNADA`, `SolicitudAsignacion.estado`/`confirmada_en`, `LineaAsignacion.material`/`serie`/`cantidad`, `confirmar_solicitud` y `auditoria.services.registrar_cambio`; detenerse y reportar si falta alguno
- [ ] T002 Crear el esqueleto de la app `stock` en `stock/__init__.py`, `stock/apps.py`, `stock/models.py`, `stock/services.py` y `stock/migrations/__init__.py`, y registrar `"stock"` en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T003 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region_stock`, `tenant_stock`, `tenant_stock_otro`, `tecnico_stock`, `tecnico_stock_otro_tenant`, `material_seriado`, `material_no_seriado`, `stock_general`, `stock_tecnico`, `solicitud_enviada_series`, `solicitud_enviada_no_seriada`, `solicitud_enviada_mixta` y `registro_cambios_stock`
- [ ] T004 [P] Comprobar si la infraestructura RLS de 001 está disponible en `config/settings/base.py` y en las migraciones de `tenants`; si no lo está, registrar la deuda en `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/research.md` y no crear una infraestructura paralela
- [ ] T005 [P] Verificar en `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/plan.md`, `data-model.md`, `contracts/` y `05-especificaciones/005-stock-inicial-de-tecnicos/data-model.md` que no quede `cantidad=-1`, que `StockTecnico` incluya `tenant` copiado de `tecnico.tenant` y que 007 conserve la propiedad de `estado`/`confirmada_en`; corregir antes de implementar si algo no coincide

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelos, restricciones, migraciones, RLS, excepciones, consultas y servicios
fundacionales que consumen 004, 005, 006, 007, 009, 010 y 011.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase. Esta fase debe estar
lista antes de implementar 004 y 005.

### Pruebas fundacionales (escribir primero, deben fallar)

- [ ] T006 [P] Escribir en `tests/unit/test_stock_validaciones.py` las pruebas de restricciones de `StockGeneral` y `StockTecnico`: `unique(tenant, material)` con nombre `stock_general_tenant_material_unico`, `unique(tecnico, material)` con nombre `stock_tecnico_tecnico_material_unico`, `CheckConstraint` `cantidad >= 0` en ambas, `PROTECT` en `tenant`/`material`/`tecnico`, `cantidad` entera con `default=0`, índices `stock_general_tenant_material`, `stock_tecnico_tenant_material` y `stock_tecnico_tecnico_material`, y `tenant` obligatorio en `StockTecnico`
- [ ] T007 [P] Escribir en `tests/unit/test_stock_servicios.py` las pruebas de consultas: `obtener_stock_general`/`obtener_stock_tecnico` devuelven `0` sin crear filas, `calcular_reservado` suma solo líneas no seriadas (`serie__isnull=True`) de solicitudes `ENVIADA` del mismo tenant y material, ignora `BORRADOR`/`CONFIRMADA`/`RECHAZADA`, y `calcular_disponible` aplica `max(0, general - reservado)` incluyendo material sin stock
- [ ] T008 [P] Escribir en `tests/integration/test_stock_incrementos.py` las pruebas de `incrementar_stock_general` y `incrementar_stock_tecnico`: creación si no existe, suma sobre fila existente, cantidad resultante devuelta, `tenant` copiado de `tecnico.tenant`, `CantidadInvalida` para `0`, negativo y no entero, y una entrada de auditoría con valor anterior y nuevo
- [ ] T009 [P] Escribir en `tests/integration/test_stock_decrementos.py` las pruebas de `decrementar_stock_general` y `decrementar_stock_tecnico`: resta sobre fila existente, `StockInsuficiente` sin escribir cuando no alcanza o la fila no existe, `CantidadInvalida` para `0`/negativo/no entero, `TenantNoCoincide` si la fila del técnico tiene otro tenant, y nunca una cantidad negativa
- [ ] T010 [P] Escribir en `tests/contract/test_stock_servicios_contrato.py` las pruebas de firma y contrato de `obtener_stock_general`, `obtener_stock_tecnico`, `calcular_reservado`, `calcular_disponible`, `incrementar_stock_general`, `decrementar_stock_general`, `incrementar_stock_tecnico` y `decrementar_stock_tecnico`, con los nombres, parámetros, tipos de retorno y mensajes exactos de `contracts/servicios-stock.md`
- [ ] T011 [P] Escribir en `tests/integration/test_stock_concurrencia.py` las pruebas fundacionales: dos decrementos simultáneos no dejan negativo, dos creaciones simultáneas de la misma clave fallan por restricción única, el bloqueo del `Tenant` evita duplicados y no se produce interbloqueo al ordenar por `material_id`

### Implementación fundacional

- [ ] T012 Implementar `StockGeneral` y `StockTecnico` en `stock/models.py`: `StockGeneral` con `tenant` FK `"tenants.Tenant"` `PROTECT` `related_name="stock_general"`, `material` FK `"materiales.Material"` `PROTECT` `related_name="stock_general"`, `cantidad = IntegerField(default=0)`, `UniqueConstraint(fields=["tenant","material"], name="stock_general_tenant_material_unico")`, `CheckConstraint(condition=Q(cantidad__gte=0), name="stock_general_cantidad_no_negativa")` e `Index(fields=["tenant","material"], name="stock_general_tenant_material")`; `StockTecnico` con `tenant` FK `"tenants.Tenant"` `PROTECT` `related_name="stock_tecnico"`, `tecnico` FK `"tecnicos.Tecnico"` `PROTECT` `related_name="stock_tecnico"`, `material` FK `"materiales.Material"` `PROTECT` `related_name="stock_tecnico"`, `cantidad = IntegerField(default=0)`, `UniqueConstraint(fields=["tecnico","material"], name="stock_tecnico_tecnico_material_unico")`, `CheckConstraint(condition=Q(cantidad__gte=0), name="stock_tecnico_cantidad_no_negativa")` e índices `stock_tecnico_tenant_material` y `stock_tecnico_tecnico_material`
- [ ] T013 Crear `stock/migrations/0001_initial.py` con T012, revisar que no cree stock ni series por migración y aplicar con `python manage.py migrate`
- [ ] T014 Crear `stock/migrations/0002_rls.py` con políticas RLS por `tenant_id` para `stock_general` y `stock_tecnico`; si T004 determinó que la infraestructura de 001 no está disponible, dejar la migración inactiva y registrar la deuda en `research.md`
- [ ] T015 Implementar en `stock/services.py` las excepciones `StockInsuficiente`, `CantidadInvalida`, `StockNoExiste`, `TecnicoNoExiste`, `SerieNoReservada`, `ConfirmacionStockInvalida` y `TenantNoCoincide` con los mensajes exactos: “La cantidad debe ser mayor a 0”, “El tenant no tiene suficiente stock general”, “El técnico no tiene suficiente stock”, “La serie no está reservada para esta asignación” y “No se puede confirmar el stock de la asignación”
- [ ] T016 Implementar en `stock/services.py` el helper de auditoría de stock que llama a `auditoria.services.registrar_cambio` con `entidad="StockGeneral"`/`"StockTecnico"`, `campo="cantidad"`, valor anterior, valor nuevo, actor y fecha, sin secretos ni `tenant_id` separado
- [ ] T017 Implementar en `stock/services.py` `obtener_stock_general(tenant, material)` y `obtener_stock_tecnico(tecnico, material)`: devolver `0` si no existe, sin crear ni bloquear; y `calcular_reservado(tenant, material)` y `calcular_disponible(tenant, material)` según `data-model.md`, usando `Sum` y sin N+1
- [ ] T018 Implementar en `stock/services.py` `incrementar_stock_general(tenant, material, cantidad, actor)` y `decrementar_stock_general(tenant, material, cantidad, actor)`: validar entero `> 0`, `transaction.atomic`, bloqueo del `Tenant`, `select_for_update` de la fila, validación de suficiente antes de restar, auditoría y retorno de la cantidad resultante; el decremento nunca crea una fila ni usa `F()` ciego
- [ ] T019 Implementar en `stock/services.py` `incrementar_stock_tecnico(tecnico, material, cantidad, actor)` y `decrementar_stock_tecnico(tecnico, material, cantidad, actor)`: validar entero `> 0` y existencia del técnico, copiar `tenant = tecnico.tenant`, rechazar con `TenantNoCoincide` una fila con otro tenant, bloquear con `select_for_update`, crear si no existe, validar suficiente antes de restar, auditar y devolver el resultado; nunca dejar cantidad negativa
- [ ] T020 Asegurar en `stock/services.py` que la creación concurrente de una fila inexistente se hace dentro del bloqueo del `Tenant` y que un `IntegrityError` de unicidad se traduce en un error de negocio legible, sin duplicar stock ni auditoría
- [ ] T021 Ejecutar `pytest tests/unit/test_stock_validaciones.py tests/unit/test_stock_servicios.py tests/integration/test_stock_incrementos.py tests/integration/test_stock_decrementos.py tests/integration/test_stock_concurrencia.py tests/contract/test_stock_servicios_contrato.py`; no avanzar con pruebas en rojo

**Checkpoint**: modelos, migraciones, RLS, excepciones, consultas y servicios fundacionales listos.
004 y 005 pueden consumirlos; las historias de confirmación pueden comenzar cuando 006 y 007 estén
disponibles.

---

## Fase 3: US1 — Confirmar y mover series y stock (P1) 🎯 MVP

**Objetivo**: al confirmar una solicitud `ENVIADA`, las series pasan de `RESERVADA` a `ASIGNADA`,
el `StockTecnico` sube y el `StockGeneral` baja por material, con validación previa y sin doble
movimiento.

**Prueba independiente**: confirmar una solicitud con 5 series del material A y 50 unidades del
material B; verificar series `ASIGNADA`, técnico 10→15 en A y 0→50 en B, general 100→95 en A y
200→150 en B, sin cambiar `SolicitudAsignacion.estado` ni `confirmada_en` desde 008.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T022 [US1] Prueba de integración de **CA-01** en `tests/integration/test_stock_confirmacion.py`: `test_series_pasan_a_asignada_al_confirmar`; solo las series de la solicitud cambian a `ASIGNADA`, las de otra solicitud y otro tenant permanecen igual
- [ ] T023 [US1] Prueba de integración de **CA-02** en `tests/integration/test_stock_confirmacion.py`: `test_stock_tecnico_sube_con_series_y_no_seriados`; 10 + 5 series = 15 y creación desde 0 cuando no existe la fila
- [ ] T024 [US1] Prueba de integración de **CA-03** en `tests/integration/test_stock_confirmacion.py`: `test_stock_general_baja_con_series_y_no_seriados`; 100 − 5 series = 95 y rechazo con `StockInsuficiente` sin escribir si no alcanza
- [ ] T025 [US1] Prueba de integración de **CA-07** en `tests/integration/test_stock_confirmacion.py`: `test_no_seriados_actualizan_cantidad_agregada`; 50 unidades no seriadas suman 50 al técnico y restan 50 del general, agregadas por material
- [ ] T026 [P] [US1] Prueba de contrato del resultado en `tests/contract/test_stock_confirmacion_contrato.py`: `ResultadoConfirmacionStock` contiene `solicitud_id`, `series_actualizadas`, `cambios_por_material`, `confirmada_en`, `total_series` y `total_cantidad`, y `CambioStockMaterial` contiene `material_id`, `stock_general_anterior`, `stock_general_nuevo`, `stock_tecnico_anterior` y `stock_tecnico_nuevo`
- [ ] T027 [US1] Prueba de integración de mezcla y agregación en `tests/integration/test_stock_confirmacion.py`: una solicitud con varios materiales y varias series del mismo material escribe una sola vez `StockTecnico`/`StockGeneral` por material y audita una vez por material
- [ ] T028 [US1] Pruebas de validación en `tests/integration/test_stock_confirmacion.py`: serie no `RESERVADA`, serie de otro tenant o de otro material, técnico de otro tenant, línea no seriada con cantidad `0` y solicitud sin líneas abortan con `SerieNoReservada`, `TenantNoCoincide`, `CantidadInvalida` o `ConfirmacionStockInvalida` sin mover stock
- [ ] T029 [US1] Prueba de idempotencia en `tests/integration/test_stock_confirmacion.py`: una segunda confirmación de la misma solicitud no vuelve a mover stock ni series y, desde 007, recibe `409`
- [ ] T030 [P] [US1] Prueba de orden de bloqueo en `tests/integration/test_stock_concurrencia.py`: `Tenant` → `StockGeneral` por `material_id` → `StockTecnico` del mismo tenant por `material_id` → `Serie` por `id`, sin interbloqueo entre dos confirmaciones con materiales invertidos

### Implementación de US1

- [ ] T031 [US1] Definir en `stock/services.py` los `dataclass` inmutables `CambioStockMaterial` y `ResultadoConfirmacionStock` con los campos de `data-model.md`, sin lógica de persistencia
- [ ] T032 [US1] Implementar en `stock/services.py` `actualizar_stock_confirmacion_asignacion(solicitud, actor)`: validar `solicitud.estado == "ENVIADA"`, existencia de líneas, técnico del mismo tenant, series `RESERVADA` del tenant/material, cantidades no seriadas `> 0` y stock general suficiente antes de escribir
- [ ] T033 [US1] Implementar en `stock/services.py` la agregación por material: series suman 1 cada una y líneas no seriadas suman su `cantidad`; agrupar en un diccionario por `material_id` sin una consulta por línea
- [ ] T034 [US1] Implementar en `stock/services.py` los bloqueos en orden estable: `select_for_update` del `Tenant`, de `StockGeneral` por `tenant` y `material_id` ascendente, de `StockTecnico` del mismo tenant por `material_id` ascendente y de `Serie` por `id` ascendente; no bloquear la solicitud, que ya bloquea 007
- [ ] T035 [US1] Implementar en `stock/services.py` la transición de cada serie `RESERVADA→ASIGNADA` y su auditoría `Serie/estado`, dentro de la misma transacción y con el actor de la sesión
- [ ] T036 [US1] Implementar en `stock/services.py` las escrituras de stock por material: incrementar `StockTecnico` (crear con `tenant = solicitud.tenant` si no existe), decrementar `StockGeneral`, auditar ambos con valor anterior y nuevo, y devolver `ResultadoConfirmacionStock` con `confirmada_en` leído de la solicitud
- [ ] T037 [US1] Asegurar en `stock/services.py` que la confirmación no escribe `SolicitudAsignacion.estado` ni `confirmada_en`, no libera series, no hace commit propio y propaga cualquier excepción para que 007 revierta toda la transacción
- [ ] T038 [US1] Verificar en `asignaciones/services.py` que `confirmar_solicitud` llama a `stock.services.actualizar_stock_confirmacion_asignacion(solicitud, actor)` dentro de su `transaction.atomic`, después del bloqueo de la solicitud y antes de fijar `CONFIRMADA`/`confirmada_en`; si falta, coordinarlo con 007 sin duplicar la escritura de stock
- [ ] T039 [US1] Ejecutar `pytest tests/integration/test_stock_confirmacion.py tests/contract/test_stock_confirmacion_contrato.py tests/integration/test_stock_concurrencia.py` y corregir hasta que CA-01, CA-02, CA-03 y CA-07 estén en verde

**Checkpoint**: US1 funcional; la confirmación mueve series y stock una sola vez y es independiente de
la interfaz de 007.

---

## Fase 4: US2 — Revertir todo si falla una parte (P2)

**Objetivo**: garantizar que series, stock técnico, stock general y auditoría se revierten completos
ante cualquier fallo, sin estados parciales ni cantidades negativas.

**Prueba independiente**: inyectar un fallo en la actualización del stock técnico durante la
confirmación y comprobar que series, stock general, stock técnico, auditoría y solicitud quedan
exactamente como antes.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T040 [US2] Prueba de **CA-04** en `tests/integration/test_stock_confirmacion.py`: `test_confirmacion_fallida_revierte_todo`; un fallo inyectado en `incrementar_stock_tecnico` deja series `RESERVADA`, `StockGeneral` y `StockTecnico` intactos, sin auditoría de stock y con la solicitud `ENVIADA`
- [ ] T041 [P] [US2] Prueba de reversión por auditoría en `tests/integration/test_stock_auditoria.py`: si `registrar_cambio` falla durante la confirmación, se revierten series y stock, y no queda un registro parcial
- [ ] T042 [US2] Prueba de reversión desde 007 en `tests/integration/test_stock_confirmacion.py`: si 007 falla después de 008 al fijar `CONFIRMADA`/`confirmada_en` o al auditar la solicitud, el stock y las series vuelven al estado anterior
- [ ] T043 [P] [US2] Prueba de defensa de base en `tests/integration/test_stock_concurrencia.py`: intentar insertar o actualizar `cantidad` negativa por SQL falla por `CheckConstraint` y no deja fila parcial
- [ ] T044 [US2] Prueba de stock insuficiente en `tests/integration/test_stock_confirmacion.py`: cuando el general no alcanza, `StockInsuficiente` revierte todo y no se crea ninguna fila con `cantidad` negativa

### Implementación de US2

- [ ] T045 [US2] Revisar `stock/services.py` y `asignaciones/services.py` para confirmar que solo existe una transacción externa, que 008 no hace commit ni captura excepciones para continuar, y que los `transaction.atomic` internos de los servicios fundacionales actúan como savepoints
- [ ] T046 [US2] Añadir en `stock/services.py` las guardas necesarias para que un fallo de auditoría o de escritura de stock cancele la confirmación completa y no se reintente parcialmente
- [ ] T047 [US2] Ejecutar `pytest tests/integration/test_stock_confirmacion.py tests/integration/test_stock_auditoria.py tests/integration/test_stock_concurrencia.py` y verificar que CA-04 queda en verde sin pruebas en rojo

**Checkpoint**: US2 funcional; la confirmación es todo o nada y la base rechaza cualquier negativo.

---

## Fase 5: US3 — Iniciar los días en mano (P3)

**Objetivo**: los días en mano de los seriados se calculan desde la fecha de confirmación que fija
007, sin que 008 cree un contador, campo o tabla adicional.

**Prueba independiente**: confirmar una asignación de material seriado, leer `confirmada_en` y
calcular los días en mano con la lógica de 006 para el día siguiente; debe mostrar 1 día.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T048 [US3] Prueba de **CA-05** en `tests/integration/test_stock_confirmacion.py`: `test_dias_en_mano_inician_en_confirmada_en`; `confirmada_en` queda fijado por 007 en la misma transacción y el cálculo de 006 con la fecha del día siguiente devuelve 1 día
- [ ] T049 [US3] Prueba de no duplicación en `tests/integration/test_stock_confirmacion.py`: 008 no escribe `confirmada_en`, no crea campos `dias_en_mano` ni tablas de conteo, y una confirmación fallida no deja fecha de confirmación
- [ ] T050 [P] [US3] Prueba de contrato del resultado en `tests/contract/test_stock_confirmacion_contrato.py`: `ResultadoConfirmacionStock.confirmada_en` es de solo lectura y coincide con `SolicitudAsignacion.confirmada_en` fijado por 007

### Implementación de US3

- [ ] T051 [US3] Asegurar en `stock/services.py` que `ResultadoConfirmacionStock.confirmada_en` se lee de la solicitud y nunca se escribe desde 008; retirar cualquier campo o cálculo de días en mano si apareció durante la implementación
- [ ] T052 [US3] Verificar en `asignaciones/services.py` y `asignaciones/models.py` que `confirmada_en` se fija solo en `confirmar_solicitud` de 007 y que 006 calcula los días a demanda; documentar la comprobación en `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/quickstart.md`
- [ ] T053 [US3] Ejecutar `pytest tests/integration/test_stock_confirmacion.py tests/contract/test_stock_confirmacion_contrato.py` y verificar que CA-05 queda en verde

**Checkpoint**: US3 funcional; los días en mano usan una única fuente y 008 no duplica el dato.

---

## Fase 6: US4 — Auditar series y stock (P4)

**Objetivo**: cada serie y cada cambio agregado de stock deja un registro inmutable con actor, fecha,
valor anterior y valor nuevo, sin duplicar la auditoría de la solicitud que escribe 007.

**Prueba independiente**: confirmar 5 series del material A y 50 unidades del material B; consultar
la auditoría y encontrar 5 registros `Serie/estado`, un `StockTecnico/cantidad` y un
`StockGeneral/cantidad` por material, con el actor de la sesión y sin secretos.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T054 [US4] Prueba de **CA-06** para series en `tests/integration/test_stock_auditoria.py`: `test_auditoria_completa_de_series_y_stock`; exactamente un registro `Serie/estado` `RESERVADA→ASIGNADA` por serie, con actor, fecha y datos de la solicitud
- [ ] T055 [US4] Prueba de **CA-06** para stock en `tests/integration/test_stock_auditoria.py`: un registro `StockTecnico/cantidad` y uno `StockGeneral/cantidad` por material agregado, con valores anterior y nuevo iguales a los del resultado
- [ ] T056 [US4] Prueba de actor y prohibiciones en `tests/integration/test_stock_auditoria.py`: el actor es el usuario de la sesión y nunca `None` ni el sistema; no hay contraseñas, tokens, secretos, binarios, rutas absolutas ni datos de otro tenant
- [ ] T057 [US4] Prueba de no duplicación en `tests/integration/test_stock_auditoria.py`: el registro `SolicitudAsignacion/estado` aparece una sola vez y es el de 007; 008 no audita el estado de la solicitud ni el rechazo

### Implementación de US4

- [ ] T058 [US4] Revisar y completar en `stock/services.py` las llamadas de auditoría de T035/T036: una por serie y una por material agregado, con valor anterior tomado bajo bloqueo y valor nuevo persistido
- [ ] T059 [US4] Verificar en `auditoria/services.py` que `registrar_cambio` acepta los eventos de 008 sin crear un modelo ni una tabla paralela, y que la auditoría se escribe en la misma transacción
- [ ] T060 [US4] Ejecutar `pytest tests/integration/test_stock_auditoria.py` y verificar que CA-06 queda en verde sin duplicar la auditoría de 007

**Checkpoint**: US4 funcional; la auditoría de series y stock es completa, legible e inmutable.

---

## Fase 7: Polish y preocupaciones transversales

**Propósito**: concurrencia real, rendimiento, aislamiento, documentación y validación final.

- [ ] T061 [P] Agregar en `tests/integration/test_stock_concurrencia.py` la prueba de dos confirmaciones simultáneas de solicitudes distintas que compiten por el mismo stock: solo una mueve stock y la otra recibe `StockInsuficiente`, sin interbloqueo
- [ ] T062 [P] Agregar en `tests/integration/test_stock_concurrencia.py` la prueba de confirmación con 100 series en menos de 2 segundos y sin una consulta por línea, usando `django_assert_num_queries` o medición equivalente
- [ ] T063 [P] Agregar en `tests/integration/test_stock_concurrencia.py` las pruebas de aislamiento entre dos tenants: `StockGeneral` y `StockTecnico` de otro tenant no se leen ni se modifican; la RLS, si está activa, bloquea el acceso directo; `StockTecnico.tenant` coincide con `tecnico.tenant`
- [ ] T064 [P] Actualizar `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/quickstart.md` con los comandos y resultados reales de la suite, sin duplicar el detalle de `contracts/` ni `data-model.md`
- [ ] T065 [P] Revisar `stock/services.py` y `stock/models.py`: sin lógica de negocio en modelos, sin endpoints, vistas, plantillas ni tareas Celery, sin `tenant_id` del cliente, sin `F()` ciego en decrementos, sin cantidades negativas y con mensajes en español
- [ ] T066 [P] Revisar el orden global en `06-plan-implementacion/desglose-tareas.md` y corregirlo si no deja la parte fundacional de 008 antes de 004 y 005
- [ ] T067 Ejecutar `pytest -k "stock"` sobre `tests/unit`, `tests/integration` y `tests/contract` con PostgreSQL y corregir cualquier fallo; no cerrar la feature con pruebas en rojo
- [ ] T068 Ejecutar `pytest --cov=stock` y revisar que cada rama de validación y cada excepción de `stock/services.py` tenga al menos una prueba
- [ ] T069 Recorrer los escenarios de `quickstart.md` para CA-01…CA-07 y registrar el resultado; si un escenario falla, corregir la implementación o el documento antes de cerrar
- [ ] T070 Revisar `stock/models.py`, `stock/services.py` y `config/settings/base.py`: 008 no agrega dependencias nuevas ni modifica tablas de 004, 006, 007, 009, 010 u 011 fuera de lo previsto, y `StockTecnico` conserva `tenant` validado

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Setup (Fase 1)**: depende de 001, 002 y 003 implementadas para poder registrar la app y crear fixtures.
- **Fundacional (Fase 2)**: depende de Setup; **bloquea** las historias y debe completarse antes de 004 y 005.
- **US1 (Fase 3)**: depende de Fundacional, de 004 (`Serie`), de 006 (`SolicitudAsignacion`/`LineaAsignacion`) y de la transacción de 007.
- **US2 (Fase 4)**: depende de US1 y de la auditoría de 007.
- **US3 (Fase 5)**: depende de US1 y de `confirmada_en` de 007.
- **US4 (Fase 6)**: depende de US1.
- **Polish (Fase 7)**: depende de todas las historias deseadas.

### Dependencias entre historias

- **US2**, **US3** y **US4** no son funcionalidad nueva: verifican propiedades de US1. Pueden
  ejecutarse en paralelo entre sí una vez que US1 esté implementada, salvo los archivos compartidos.
- **US1** es el MVP de la feature; sin US1 no hay confirmación que probar.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar.
- Modelos y migraciones antes de servicios.
- Servicios fundacionales antes del servicio de confirmación.
- La confirmación antes de las pruebas de reversión, días en mano y auditoría.
- No se avanza con pruebas en rojo.

### Oportunidades de paralelización

- T003, T004 y T005 en Setup.
- T006–T011 en Fundacional (archivos de prueba distintos).
- T026 y T030 en US1 usan archivos distintos; las pruebas de `test_stock_confirmacion.py` se ejecutan en secuencia.
- T041 y T043 en US2 usan archivos distintos; las pruebas de `test_stock_confirmacion.py` se ejecutan en secuencia.
- T050 en US3 usa un archivo distinto; T048 y T049 se ejecutan en secuencia.
- T054–T057 en US4 comparten `test_stock_auditoria.py` y se ejecutan en secuencia.
- T061–T066 en Polish usan archivos distintos.

**Nota**: `stock/services.py` es el archivo de mayor contención; T031–T037, T045–T046 y T058 deben
secuenciarse. `asignaciones/services.py` pertenece a 007; 008 solo verifica la llamada, no la
duplica.

---

## Ejemplo de paralelización: US1

```text
# Pruebas en archivos distintos
Tarea: "CA-01 series ASIGNADA en tests/integration/test_stock_confirmacion.py"
Tarea: "CA-02 stock técnico en tests/integration/test_stock_confirmacion.py"
Tarea: "Contrato del resultado en tests/contract/test_stock_confirmacion_contrato.py"
Tarea: "Orden de bloqueo en tests/integration/test_stock_concurrencia.py"

# Implementación secuencial en stock/services.py
T031 → T032 → T033 → T034 → T035 → T036 → T037 → T038 → T039
```

## Ejemplos de paralelización: US2, US3 y US4

```text
# US2: archivos distintos
Tarea: "Reversión por auditoría en tests/integration/test_stock_auditoria.py"   # T041
Tarea: "Defensa de base en tests/integration/test_stock_concurrencia.py"        # T043
# T040, T042 y T044 comparten test_stock_confirmacion.py y van en secuencia.

# US3
Tarea: "Contrato del resultado en tests/contract/test_stock_confirmacion_contrato.py"  # T050
# T048 y T049 comparten test_stock_confirmacion.py y van en secuencia.

# US4: las pruebas comparten test_stock_auditoria.py
T054 → T055 → T056 → T057 → T058 → T059 → T060
```

## Estrategia de implementación

### MVP (Fundacional + US1)

1. Completar Setup.
2. Completar Fundacional; validar que 004 y 005 pueden consumir los servicios.
3. Completar US1.
4. **DETENERSE y VALIDAR**: CA-01, CA-02, CA-03 y CA-07 en verde.
5. Desplegar/demostrar la confirmación si 006 y 007 están listos.

### Entrega incremental

1. Fundacional → 004 y 005 pueden implementarse.
2. US1 → confirmación con movimiento de stock y series.
3. US2 → garantía de reversión total.
4. US3 → días en mano desde `confirmada_en`.
5. US4 → auditoría completa.
6. Polish → concurrencia, rendimiento, aislamiento y documentación.

---

## Trazabilidad de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US1 | T022, T039 |
| CA-02 | US1 | T023, T039 |
| CA-03 | US1 | T024, T039 |
| CA-04 | US2 | T040, T047 |
| CA-05 | US3 | T048, T053 |
| CA-06 | US4 | T054, T055, T060 |
| CA-07 | US1 | T025, T039 |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id`/`region_id` del cliente; el alcance sale de la sesión y de la solicitud.
- `StockTecnico.tenant` se copia de `tecnico.tenant` y se valida; nunca se toma del cliente.
- 008 no crea endpoints, vistas, plantillas ni tareas Celery y no cambia el estado de la solicitud.
- El rechazo y la liberación de series pertenecen a 007.
- Evitar tareas vagas y conflictos de archivo; `stock/services.py` debe secuenciarse.
