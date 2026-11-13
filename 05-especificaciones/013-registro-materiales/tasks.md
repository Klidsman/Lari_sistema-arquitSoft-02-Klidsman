---
description: "Lista de tareas para la implementación de 013 Registro de Materiales"
---

# Tareas: 013 Registro de Materiales

**Entrada**: Documentos de diseño en `05-especificaciones/013-registro-materiales/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`,
`ContextoUsuarioMiddleware`, `tenants.Tenant`, roles y `auditoria.RegistroCambio` con `tenant`),
**spec 002 implementada** (`materiales.Material`), **spec 003 implementada** (`tecnicos.Tecnico` con
`nif`) y **spec 004 implementada** (`recojos.Recojo` y `recojos.LineaRecojo`). También deben estar
aplicadas las correcciones de `plan.md`: `materiales.Material` en lugar de `catalogo.Material`,
`recojos.LineaRecojo` en lugar de `RecojoLinea`, claves de orden con número y auditoría compartida.
La app `registro_materiales` se crea aquí; no se duplican tablas de materiales, técnicos, recojos,
stock ni auditoría.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación. Cada historia escribe primero sus pruebas, las ve
fallar y luego implementa. Todas las pruebas usan PostgreSQL, nunca SQLite.

**Organización**: `spec.md` declara HU-30…HU-33 sin descripción individual y una lista de criterios de
aceptación. Se agrupan en cuatro historias derivadas por área funcional, sin agregar alcance.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia asociada (`US1`…`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Catálogo habilitado y registro por orden | P1 | HU-30/HU-31; criterios de menú, catálogo, orden, cantidades e historial |
| US2 — Saldos iniciales y herencia mensual | P2 | HU-32; criterios de saldo inicial, herencia y saldo manual |
| US3 — Despachos vinculados al recojo | P3 | HU-32; criterios de despacho del tenant, ajeno y límite de línea |
| US4 — Reporte mensual y detalle por técnico | P4 | HU-33; criterios de saldo final, reporte y aislamiento |

## Convenciones de rutas

Proyecto Django único en la raíz: app nueva `registro_materiales/`, plantillas en
`templates/registro_materiales/`, pruebas en `tests/{unit,integration,contract}/`. Las apps `acceso`,
`tenants`, `auditoria`, `materiales`, `tecnicos` y `recojos` son propiedad de sus specs. 013 **no**
crea tablas de materiales, técnicos, recojos, stock ni auditoría, **no** modifica stock ni
conciliaciones, **no** exporta Excel/PDF y **no** usa permisos Django por cadena.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: verificar prerrequisitos y correcciones, crear la app, registrar rutas, preparar
fixtures y comprobar RLS.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `recojos/models.py` y `auditoria/models.py`: roles, `Material` con `codigo`/`descripcion`/`lote`, `Tecnico` con `tenant`/`nif`, `Recojo`/`LineaRecojo` con `tenant`/`material`/`cantidad` y `RegistroCambio` con `tenant`; detenerse y reportar si falta alguno
- [ ] T002 Crear el esqueleto de `registro_materiales` en `registro_materiales/__init__.py`, `apps.py`, `models.py`, `services.py`, `forms.py`, `views.py`, `urls.py` y `migrations/__init__.py`; registrar `"registro_materiales"` en `config/settings/base.py`, incluir `registro_materiales.urls` en `config/urls.py` y añadir el enlace “Registrar materiales” en `templates/base.html` solo para `USUARIO_TENANT`
- [ ] T003 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `tenant_registro`, `tenant_registro_otro`, `usuario_tenant_registro`, `usuario_otro_tenant_registro`, `tecnico_registro`, `tecnico_otro_tenant`, `material_registro`, `material_registro_otro`, `material_habilitado`, `recojo_registro`, `linea_recojo_registro`, `orden_existente`, `saldo_inicial_registro`, `despacho_registro` y `registro_cambios_registro`
- [ ] T004 [P] Comprobar si la infraestructura RLS de 001 está disponible en `config/settings/base.py` y en las migraciones de `tenants`; si no lo está, registrar la deuda en `05-especificaciones/013-registro-materiales/research.md` y no crear una infraestructura paralela
- [ ] T005 [P] Verificar en `05-especificaciones/013-registro-materiales/spec.md`, `plan.md` y `data-model.md` que estén aplicadas las correcciones: `materiales.Material`, `recojos.LineaRecojo`, unicidad `(tenant, técnico, periodo, número)`, auditoría compartida y ausencia de permisos Django/Excel; corregir antes de implementar si algo no coincide

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelos, restricciones, migraciones, RLS, excepciones, validadores y auditoría base que
todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

### Pruebas fundacionales (escribir primero, deben fallar)

- [ ] T006 [P] Escribir en `tests/unit/test_registro_validaciones.py` las pruebas de restricciones de `MaterialHabilitado`, `SaldoInicialPeriodo`, `DespachoAlmacen`, `OrdenLiquidacion` y `UsoMaterialOrden`: `unique(tenant, material)`, `unique(tenant, material, periodo)`, `unique(orden, material)`, `unique(tenant, tecnico, periodo, numero_orden)`, regex de número/periodo, cantidades `>=0`, `PROTECT`/`CASCADE` e índices
- [ ] T007 Escribir en `tests/unit/test_registro_validaciones.py` las pruebas de `periodo_de_fecha`, `validar_periodo`, `normalizar_numero_orden` y `validar_cantidad`: espacios, mayúsculas, 1–30 alfanuméricos, periodo `YYYY-MM`, vacío/0, negativos, decimales y texto
- [ ] T008 [P] Escribir en `tests/contract/test_registro_http.py` las pruebas de contrato de firmas y excepciones de `registro_materiales/services.py` según `contracts/servicios-registro-materiales.md`

### Implementación fundacional

- [ ] T009 Implementar `MaterialHabilitado` en `registro_materiales/models.py`: `tenant` FK `Tenant` `PROTECT` `related_name="materiales_habilitados"`, `material` FK `materiales.Material` `PROTECT` `related_name="habilitaciones"`, `activo=True`, `orden=0`, `creado_por`/`actualizado_por` FK `Usuario` `PROTECT`, `creado_en`/`actualizado_en`; `UniqueConstraint(tenant, material)` e índices
- [ ] T010 Implementar `SaldoInicialPeriodo` en `registro_materiales/models.py`: `tenant`, `material`, `periodo=CharField(7)` con regex `^[0-9]{4}-(0[1-9]|1[0-2])$`, `cantidad=PositiveIntegerField()`, actores y timestamps; `UniqueConstraint(tenant, material, periodo)` y `CheckConstraint(cantidad >= 0)`
- [ ] T011 Implementar `DespachoAlmacen` en `registro_materiales/models.py`: `tenant`, `material`, `recojo` FK `recojos.Recojo` `PROTECT`, `recojo_linea` FK `recojos.LineaRecojo` `PROTECT`, `fecha`, `cantidad`, actores y timestamps; `CheckConstraint(cantidad >= 0)` e índices `(tenant, fecha)`, `(tenant, material, fecha)`, `(recojo_linea)`
- [ ] T012 Implementar `OrdenLiquidacion` en `registro_materiales/models.py`: `tenant`, `tecnico` FK `Tecnico` `PROTECT`, `numero_orden=CharField(30)` con regex `^[A-Z0-9]{1,30}$`, `fecha_liquidacion`, `periodo` con regex, actores y timestamps; `UniqueConstraint(tenant, tecnico, periodo, numero_orden)` e índices
- [ ] T013 Implementar `UsoMaterialOrden` en `registro_materiales/models.py`: `tenant`, `orden` FK `CASCADE`, `tecnico` FK `PROTECT`, `material` FK `PROTECT`, `cantidad=PositiveIntegerField(default=0)`, actores y timestamps; `UniqueConstraint(orden, material)`, `CheckConstraint(cantidad >= 0)` e índices
- [ ] T014 Crear `registro_materiales/migrations/0001_initial.py` con T009–T013, revisar que no cree datos por migración y aplicar con `python manage.py migrate`
- [ ] T015 Crear `registro_materiales/migrations/0002_rls.py` con RLS por `tenant_id` en las cinco tablas; si T004 determinó que 001 no está disponible, dejar la migración inactiva y registrar la deuda
- [ ] T016 Implementar en `registro_materiales/services.py` las excepciones y mensajes exactos de `contracts/servicios-registro-materiales.md`: `PermisoDenegado`, `TecnicoNoExiste`, `MaterialNoHabilitado`, `MaterialInactivo`, `CantidadInvalida`, `NumeroOrdenInvalido`, `PeriodoInvalido`, `RecojoNoExiste`, `LineaRecojoNoExiste`, `MaterialNoCoincide`, `DespachoExcedeRecojo`, `TecnicoNoCoincide` y `NoEncontrado`
- [ ] T017 Implementar en `registro_materiales/services.py` `periodo_de_fecha`, `validar_periodo`, `normalizar_numero_orden`, `validar_cantidad`, `validar_cuenta_tenant` y `validar_tecnico`
- [ ] T018 Implementar en `registro_materiales/services.py` el helper de auditoría para `MaterialHabilitado/alta` y `/activo`, `SaldoInicialPeriodo/alta` y `/cantidad`, `OrdenLiquidacion/alta`, `/numero_orden`, `/fecha_liquidacion` y `/periodo`, `UsoMaterialOrden/alta` y `/cantidad`, y `DespachoAlmacen/alta`, `/fecha` y `/cantidad`; usar `auditoria.services.registrar_cambio` con `tenant`, sin secretos
- [ ] T019 Ejecutar `pytest tests/unit/test_registro_validaciones.py tests/contract/test_registro_http.py`; corregir hasta que la fase fundacional esté en verde

**Checkpoint**: modelos, restricciones, RLS, validadores y auditoría listos; las historias pueden
comenzar.

---

## Fase 3: US1 — Catálogo habilitado y registro por orden (P1) 🎯 MVP

**Objetivo**: el tenant habilita su catálogo, registra órdenes por técnico/mes con cantidades usadas,
reabre órdenes existentes y conserva el historial; el menú solo aparece para la cuenta del tenant.

**Prueba independiente**: habilitar dos materiales, registrar una orden con 3 usos, reabrirla con el
mismo número y comprobar que no se duplica; verificar cantidades 0, rechazos de cantidad y técnico, y
que otro técnico/mes permite la misma orden.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T020 [P] [US1] Prueba de menú/aislamiento en `tests/integration/test_registro_catalogo.py`: `test_menu_registrar_materiales_solo_para_tenant`; solo `USUARIO_TENANT` ve la opción y solo opera con técnicos/materiales de su tenant
- [ ] T021 [US1] Prueba de catálogo en `tests/integration/test_registro_catalogo.py`: habilitar, deshabilitar y reactivar; el material inactivo no se ofrece en nuevas órdenes y el historial se conserva
- [ ] T022 [P] [US1] Prueba de orden nueva en `tests/integration/test_registro_ordenes.py`: `test_orden_nueva_muestra_catalogo_habilitado`; devuelve materiales activos del tenant con cantidades en 0
- [ ] T023 [US1] Prueba de orden existente en `tests/integration/test_registro_ordenes.py`: `test_orden_duplicada_mismo_tecnico_y_mes_abre_existente`; la misma clave devuelve la orden existente, sin duplicar
- [ ] T024 [US1] Prueba de clave distinta en `tests/integration/test_registro_ordenes.py`: `test_misma_orden_en_otro_tecnico_o_mes_se_permite`
- [ ] T025 [US1] Prueba de cantidades en `tests/integration/test_registro_ordenes.py`: `test_cantidad_vacia_o_cero_no_suma_uso`; `test_cantidad_negativa_decimal_o_texto_se_rechaza`; `test_uso_con_tecnico_distinto_al_de_la_orden_se_rechaza`
- [ ] T026 [US1] Prueba de doble clic y cambio de mes en `tests/integration/test_registro_ordenes.py`: `test_doble_clic_no_crea_orden_duplicada` y `test_cambio_de_fecha_a_otro_mes_revalida_unicidad`
- [ ] T027 [P] [US1] Prueba de historial en `tests/integration/test_registro_auditoria.py`: editar una orden y sus usos produce registros con valor anterior/nuevo, sin borrar usos puestos a 0
- [ ] T028 [P] [US1] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: pantalla, contexto HTMX, guardar orden, historial y catálogo con `200/302/400/403/404/405`

### Implementación de US1

- [ ] T029 [US1] Implementar en `registro_materiales/services.py` `materiales_habilitados`, `habilitar_material` y `deshabilitar_material`, con auditoría de alta/estado y sin borrar historial
- [ ] T030 [US1] Implementar en `registro_materiales/services.py` `obtener_orden` y `guardar_orden`: normalizar número/periodo, validar técnico/materiales/cantidades, bloquear la orden existente, crear o actualizar, conservar usos en 0 y revalidar unicidad al cambiar de mes
- [ ] T031 [US1] Implementar en `registro_materiales/services.py` la creación/actualización de `UsoMaterialOrden` por diferencia, sin borrar líneas, y `historial_orden` por entidad/ID y tenant
- [ ] T032 [US1] Implementar `RegistroOrdenForm` en `registro_materiales/forms.py`: técnico del tenant, número, fecha y cantidades por material; normalizar y validar sin aceptar tenant/estado/material fuera del catálogo
- [ ] T033 [US1] Implementar en `registro_materiales/views.py` y `registro_materiales/urls.py` la pantalla de orden, el contexto HTMX, el guardado y el historial; crear `templates/registro_materiales/registro_orden.html`, `_catalogo_orden.html` y `historial.html`
- [ ] T034 [US1] Implementar en `registro_materiales/views.py` y `registro_materiales/urls.py` la pantalla de catálogo habilitado y las acciones activar/desactivar; crear `templates/registro_materiales/catalogo.html`
- [ ] T035 [US1] Ejecutar `pytest tests/integration/test_registro_catalogo.py tests/integration/test_registro_ordenes.py tests/integration/test_registro_auditoria.py tests/contract/test_registro_http.py` y corregir hasta que los criterios de US1 estén en verde

**Checkpoint**: US1 funcional; el tenant registra órdenes, reabre existentes y conserva historial.

---

## Fase 4: US2 — Saldos iniciales y herencia mensual (P2)

**Objetivo**: el tenant carga saldos iniciales manuales por material/periodo; si no hay manual, el
saldo se hereda del final del mes anterior; todo cambio se audita.

**Prueba independiente**: cargar 100, registrar despachos 20 y usos 30, y verificar saldo final 90; el
mes siguiente sin saldo manual hereda 90; un saldo manual prevalece.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T036 [P] [US2] Prueba de saldo final en `tests/integration/test_registro_saldos.py`: `test_saldo_final_es_inicial_mas_despachos_menos_usado`; 100+20−30=90
- [ ] T037 [US2] Prueba de herencia en `tests/integration/test_registro_saldos.py`: `test_mes_sin_saldo_inicial_hereda_final_anterior`; sin datos anteriores = 0
- [ ] T038 [US2] Prueba de saldo manual en `tests/integration/test_registro_saldos.py`: `test_saldo_inicial_manual_prevalece_y_se_audita`; crea/actualiza y audita valor anterior/nuevo
- [ ] T039 [P] [US2] Prueba de periodo/cantidad en `tests/unit/test_registro_saldos.py`: periodo `YYYY-MM`, cantidad entera `>=0`, material habilitado/activo y saldo negativo no bloquea
- [ ] T040 [P] [US2] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: entradas y `POST saldo-inicial/guardar/` con `302/400/403/404/405`

### Implementación de US2

- [ ] T041 [US2] Implementar en `registro_materiales/services.py` `registrar_saldo_inicial`, `saldo_inicial_efectivo` y `saldo_final`: manual prevalece, herencia iterativa desde el primer periodo con datos, caché por request y auditoría
- [ ] T042 [US2] Implementar en `registro_materiales/views.py` y `registro_materiales/urls.py` la pantalla de entradas y el guardado de saldo; crear `templates/registro_materiales/entradas.html` con periodo, materiales y saldo inicial
- [ ] T043 [US2] Ejecutar `pytest tests/integration/test_registro_saldos.py tests/unit/test_registro_saldos.py tests/contract/test_registro_http.py` y corregir hasta que los criterios de saldo de US2 estén en verde

**Checkpoint**: US2 funcional; los saldos manuales y la herencia mensual son correctos y auditables.

---

## Fase 5: US3 — Despachos vinculados al recojo (P3)

**Objetivo**: el tenant registra despachos individuales con fecha, material, cantidad y referencia al
recojo/línea del tenant; la suma no supera la línea y se puede editar con historial.

**Prueba independiente**: registrar un despacho válido, rechazar uno de otro tenant y uno que exceda la
línea; verificar que un despacho 0 se registra pero no suma y que la edición se audita.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T044 [P] [US3] Prueba de despacho válido en `tests/integration/test_registro_despachos.py`: `test_despacho_vinculado_a_recojo_del_tenant`; guarda recojo/línea/material/fecha/cantidad
- [ ] T045 [US3] Prueba de despacho ajeno en `tests/integration/test_registro_despachos.py`: `test_despacho_con_recojo_de_otro_tenant_se_rechaza`; también línea ajena y material distinto
- [ ] T046 [US3] Prueba de límite en `tests/integration/test_registro_despachos.py`: `test_despacho_mayor_a_linea_de_recojo_se_rechaza`; varios despachos no superan el total
- [ ] T047 [US3] Prueba de cantidad 0/edición en `tests/integration/test_registro_despachos.py`: cantidad 0 se registra y no suma; editar fecha/cantidad excluye el propio despacho del cálculo y audita
- [ ] T048 [P] [US3] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: entradas, `POST despachos/guardar/`, `POST despachos/<id>/editar/` y `GET recojos/buscar/` con `200/302/400/403/404/405`

### Implementación de US3

- [ ] T049 [US3] Implementar en `registro_materiales/services.py` `registrar_despacho` y `actualizar_despacho`: validar recojo/línea/material/fecha/cantidad, bloquear `Tenant` y `LineaRecojo`, sumar despachos excluyendo el editado y auditar
- [ ] T050 [US3] Implementar en `registro_materiales/services.py` `despachos_del_periodo` y `recojos_del_tenant` para entradas y selectores, con `select_related` y sin N+1
- [ ] T051 [US3] Implementar en `registro_materiales/views.py` y `registro_materiales/urls.py` el formulario/acciones de despacho y la búsqueda de recojos; completar `templates/registro_materiales/entradas.html`
- [ ] T052 [US3] Ejecutar `pytest tests/integration/test_registro_despachos.py tests/contract/test_registro_http.py` y corregir hasta que los criterios de despacho de US3 estén en verde

**Checkpoint**: US3 funcional; los despachos respetan el recojo y su línea, y se auditan.

---

## Fase 6: US4 — Reporte mensual y detalle por técnico (P4)

**Objetivo**: el tenant consulta el reporte mensual por material con saldo inicial, despachos, usado y
saldo final, y el detalle por técnico; un saldo negativo se muestra con alerta.

**Prueba independiente**: generar un reporte con dos materiales y dos técnicos; verificar totales,
detalle y alerta de saldo negativo; otro tenant no ve los datos.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T053 [P] [US4] Prueba de reporte en `tests/integration/test_registro_reporte.py`: `test_reporte_mensual_incluye_detalle_por_tecnico`; filas por material con inicial, despachos, usado y final; detalle por NIF
- [ ] T054 [US4] Prueba de saldo negativo en `tests/integration/test_registro_reporte.py`: `test_saldo_final_negativo_se_muestra_con_alerta`; no se oculta ni bloquea
- [ ] T055 [P] [US4] Prueba de aislamiento en `tests/integration/test_registro_aislamiento.py`: `test_aislamiento_entre_tenants_en_ordenes_y_reporte`; órdenes, saldos, despachos y reporte ajenos no se ven
- [ ] T056 [P] [US4] Prueba de contrato HTTP en `tests/contract/test_registro_http.py`: `GET /registro-materiales/reporte/` con `200/403/405`, filtro por periodo y sin datos de otro tenant

### Implementación de US4

- [ ] T057 [US4] Implementar en `registro_materiales/services.py` `reporte_mensual`: materiales habilitados activos más los que tengan datos, agregaciones por material/técnico, saldo final y alerta, sin N+1
- [ ] T058 [US4] Implementar en `registro_materiales/views.py` y `registro_materiales/urls.py` la pantalla de reporte y crear `templates/registro_materiales/reporte.html` con totales, detalle por técnico y alerta
- [ ] T059 [US4] Ejecutar `pytest tests/integration/test_registro_reporte.py tests/integration/test_registro_aislamiento.py tests/contract/test_registro_http.py` y corregir hasta que el reporte y el aislamiento estén en verde

**Checkpoint**: US4 funcional; el reporte muestra totales y detalle, y respeta el tenant.

---

## Fase 7: Polish y preocupaciones transversales

- [ ] T060 [P] Ejecutar `pytest -k "registro"` sobre `tests/unit`, `tests/integration` y `tests/contract` con PostgreSQL y corregir cualquier fallo
- [ ] T061 [P] Ejecutar `pytest --cov=registro_materiales tests/unit tests/integration tests/contract` y revisar que cada validación, excepción y cálculo de `registro_materiales/services.py` tenga al menos una prueba
- [ ] T062 [P] Agregar en `tests/integration/test_registro_aislamiento.py` las pruebas de concurrencia: doble clic de orden, dos despachos de la misma línea y dos ediciones de saldo, sin duplicados ni exceso
- [ ] T063 [P] Agregar en `tests/integration/test_registro_reporte.py` la prueba de rendimiento: 100 materiales y 1 000 usos en tiempo razonable, sin N+1
- [ ] T064 [P] Revisar `registro_materiales/models.py`, `services.py`, `views.py` y `forms.py`: sin escrituras a stock/series/conciliaciones, sin borrados, sin permisos Django, sin Excel/PDF y sin `tenant_id` del cliente
- [ ] T065 [P] Revisar `registro_materiales/migrations/`: RLS, restricciones únicas, regex de periodo/número, cantidades no negativas y ningún cambio a tablas de otras apps
- [ ] T066 [P] Actualizar `05-especificaciones/013-registro-materiales/quickstart.md` con los comandos y resultados reales de la suite, sin duplicar contratos ni modelos
- [ ] T067 [P] Verificar en `05-especificaciones/013-registro-materiales/spec.md`, `plan.md`, `data-model.md` y `registro_materiales/services.py` que las correcciones de 013 sigan aplicadas: `materiales.Material`, `LineaRecojo`, unicidad con número y auditoría compartida
- [ ] T068 Ejecutar `python manage.py check` y `python manage.py migrate --check`; confirmar que no hay migraciones pendientes ni errores de configuración
- [ ] T069 Recorrer los escenarios de `quickstart.md` y registrar el resultado; corregir implementación o documento antes de cerrar
- [ ] T070 Revisar `registro_materiales/services.py`, `views.py`, `config/settings/base.py` y `requirements-dev.txt`: 013 no agrega dependencias, Excel/PDF, Celery, permisos Django ni escrituras a stock/conciliaciones

---

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Setup (Fase 1)**: depende de 001–004 implementadas y de las correcciones documentales.
- **Fundacional (Fase 2)**: depende de Setup; **bloquea** las historias.
- **US1 (Fase 3)**: depende de Fundacional; entrega catálogo y órdenes.
- **US2 (Fase 4)**: depende de US1 (necesita órdenes y materiales habilitados).
- **US3 (Fase 5)**: depende de Fundacional y de US1 para el catálogo; puede ejecutarse en paralelo con
  US2.
- **US4 (Fase 6)**: depende de US2 y US3 para tener saldos y despachos.
- **Polish (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1** es el MVP: sin órdenes no hay usos ni reporte.
- **US2** y **US3** alimentan el cálculo del reporte; pueden ejecutarse en paralelo.
- **US4** consume saldos, despachos y usos.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar.
- Modelos y migraciones antes de servicios.
- Servicios antes de vistas y plantillas.
- No se avanza con pruebas en rojo.

### Oportunidades de paralelización

- T003–T005 en Setup.
- T006–T008 en Fundacional (archivos de prueba distintos; T006/T007 comparten
  `test_registro_validaciones.py` y van en secuencia).
- T020–T028 en US1: catálogo/órdenes/auditoría/contrato usan archivos distintos; las pruebas de
  órdenes van en secuencia.
- T036–T040 en US2: saldos y contrato usan archivos distintos.
- T044–T048 en US3: despachos y contrato usan archivos distintos.
- T053–T056 en US4: reporte, aislamiento y contrato usan archivos distintos.
- T060–T067 en Polish usan archivos distintos.

**Nota**: `registro_materiales/services.py` es el archivo de mayor contención; T016–T018, T029–T031,
T041, T049–T050 y T057 deben secuenciarse.

---

## Ejemplo de paralelización: US2 y US3

```text
# US2: pruebas y contrato
Tarea: "Saldos en tests/integration/test_registro_saldos.py"          # T036–T038
Tarea: "Contrato HTTP en tests/contract/test_registro_http.py"       # T040

# US3: pruebas y contrato
Tarea: "Despachos en tests/integration/test_registro_despachos.py"   # T044–T047
Tarea: "Contrato HTTP en tests/contract/test_registro_http.py"       # T048

# Implementación compartida: secuenciar services.py
T041
T049 → T050
```

## Estrategia de implementación

### MVP (Fundacional + US1)

1. Completar Setup.
2. Completar Fundacional; validar modelos, periodos y cantidades.
3. Completar US1.
4. **DETENERSE y VALIDAR**: catálogo, orden nueva/existente, cantidades e historial en verde.
5. Demostrar el registro por orden.

### Entrega incremental

1. Fundacional → modelos y validadores.
2. US1 → catálogo y órdenes.
3. US2 → saldos y herencia.
4. US3 → despachos.
5. US4 → reporte mensual.
6. Polish → concurrencia, rendimiento y documentación.

---

## Trazabilidad de criterios de aceptación

| Criterio | Historia | Pruebas principales |
|---|---|---|
| Menú solo tenant | US1 | T020 |
| Catálogo en orden nueva | US1 | T022 |
| Orden existente se abre | US1 | T023 |
| Misma orden otro técnico/mes | US1 | T024 |
| Cantidad 0 no suma | US1 | T025 |
| Cantidad inválida | US1 | T025 |
| Saldo final | US2 | T036 |
| Herencia de saldo | US2 | T037 |
| Saldo manual | US2 | T038 |
| Despacho del tenant | US3 | T044 |
| Despacho ajeno | US3 | T045 |
| Despacho excede línea | US3 | T046 |
| Técnico de línea | US1 | T025 |
| Historial | US1 | T027 |
| Aislamiento | US4 | T055 |
| Reporte detalle | US4 | T053 |
| Doble clic | US1 | T026 |
| Cambio de fecha/mes | US1 | T026 |
| Saldo negativo | US4 | T054 |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id` del cliente.
- 013 no modifica stock, series, recojos ni conciliaciones; no exporta Excel/PDF.
- No se borran órdenes, usos, saldos ni despachos.
- Evitar tareas vagas y conflictos de archivo; `registro_materiales/services.py` debe secuenciarse.
