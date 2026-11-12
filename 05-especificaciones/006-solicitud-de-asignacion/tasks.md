---
description: "Lista de tareas para la implementación de 006 Solicitud de Asignación"
---

# Tareas: 006 Solicitud de Asignación

**Entrada**: Documentos de diseño en `05-especificaciones/006-solicitud-de-asignacion/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/` y `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`, `tenants.Region`,
`tenants.Almacen`, `tenants.Tenant`, `ContextoUsuarioMiddleware` y
`auditoria.RegistroCambio`/`registrar_cambio`), **spec 002 implementada**
(`materiales.Material` y `/materiales/buscar/`), **spec 003 implementada**
(`tecnicos.Tecnico` y `tecnicos.services.tecnicos_para_operacion`), **app `series` de 004
implementada** (`series.Serie` y `EstadoSerie`) y **parte fundacional de 008 implementada**
(`stock.StockGeneral`, `stock.services.obtener_stock_general` y
`stock.services.calcular_disponible`). El envío de correo y la confirmación de 007 **no** son
prerrequisitos. Las tareas de 001, 002, 003, 004 y 008 no se repiten aquí.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-11. Cada historia escribe primero sus
pruebas, las ve fallar y luego implementa.

**Organización**: `spec.md` define las historias HU-08…HU-13 sin etiqueta de prioridad explícita; se
agrupan en cuatro historias derivadas para permitir entregas incrementales e independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario asociada (`US1`…`US4`)
- Todas las rutas de archivo son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Armar solicitud con técnico, series, cantidades y validación en tiempo real | P1 | HU-08, HU-11; CA-02, CA-03, CA-04, CA-07, CA-10, CA-11; §5.1–§5.3, §5.6 |
| US2 — Enviar solicitud, reservar series/cantidades y generar el Excel | P2 | HU-08, HU-10, HU-11, HU-12; CA-01, CA-05, CA-06; §5.4, §5.5 |
| US3 — Días en mano y alerta de cupo máximo | P3 | HU-09, HU-13; CA-08, CA-09; §5.7, §5.8 |
| US4 — Consulta, cancelación, aislamiento y auditoría | P4 | §9, §10, contratos HTTP y de auditoría |

## Convenciones de rutas

Proyecto Django único en la raíz: la app nueva es `asignaciones/`; las plantillas viven en
`templates/asignaciones/`; las pruebas en `tests/{unit,integration,contract}/`. Las apps `acceso`,
`tenants`, `auditoria` (001), `materiales` (002), `tecnicos` (003), `series` (004) y `stock` (008)
son propiedad de sus specs y no se duplican. 006 **no** crea una tabla de series, **no** escribe
`stock.StockGeneral` ni `stock.StockTecnico` y **no** implementa correo, Celery, WebSocket ni la
confirmación del almacén.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: corregir los documentos contradictorios, crear la app `asignaciones`, conectarla al
proyecto y preparar el entorno de pruebas.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `series/models.py`, `stock/models.py`, `stock/services.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware` activo, roles `ADMIN_PLATAFORMA`/`USUARIO_TENANT`/`RESPONSABLE_ALMACEN`, `Almacen.centro`/`codigo_almacen`/`buzon`, `Material.es_seriado`/`lote`/`descripcion`, `tecnicos.services.tecnicos_para_operacion`, `series.Serie` con `unique(numero)`, `EstadoSerie.DISPONIBLE`/`RESERVADA`/`ASIGNADA`, `stock.StockGeneral` y `stock.services.calcular_disponible`; detenerse y reportar si falta alguno
- [ ] T002 [P] Corregir `05-especificaciones/006-solicitud-de-asignacion/spec.md` §5.5 y CA-01 para indicar que el Excel se genera al enviar (`BORRADOR`→`ENVIADA`) y que “crear” en CA-01 significa crear y enviar; corregir §11 para alertar por cada equipo seriado que supera 20 días, no por la suma de días
- [ ] T003 [P] Corregir `04-contratos/excel-asignacion.md` §2 y §8 para precisar que el Excel se genera al enviar, no al guardar el borrador, y que su descarga, envío y verificación de hash pertenecen a 007
- [ ] T004 [P] Registrar en `05-especificaciones/007-envio-y-revision-del-almacen/plan.md`, `05-especificaciones/009-traspaso-entre-tecnicos/plan.md` y `05-especificaciones/011-logistica-inversa-y-devoluciones/plan.md` las correcciones de integración: roles explícitos y `confirmada_en` en 007, y actualización de la fuente de custodia en 009/011
- [ ] T005 Crear la app Django `asignaciones` con `asignaciones/__init__.py`, `asignaciones/apps.py`, `asignaciones/migrations/__init__.py` y registrarla en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T006 [P] Agregar en `config/settings/base.py` `MOVIMIENTO_ASIGNACION="Z31"`, `DIAS_ALERTA_CUSTODIA=20` y `ASIGNACIONES_EXCEL_DIR="asignaciones"`, con lectura desde variables de entorno y esos valores por defecto
- [ ] T007 [P] Incluir `asignaciones/urls.py` desde `config/urls.py` bajo el prefijo `/asignaciones/` (el archivo se completa en T041, T064 y T098)
- [ ] T008 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region`, `almacen`, `tenant`, `otro_tenant`, `tenant_suspendido`, `usuario_tenant`, `usuario_admin`, `usuario_almacen`, `usuario_inactivo`, `tecnico_activo`, `tecnico_desactivado`, `material_seriado`, `material_no_seriado`, `serie_disponible`, `serie_reservada`, `serie_asignada`, `stock_general`, `solicitud_borrador`, `solicitud_enviada`, `solicitud_confirmada` y `registro_cambios`
- [ ] T009 [P] Agregar el enlace de navegación a Asignaciones en `templates/base.html`, visible solo para `USUARIO_TENANT` con tenant activo

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelos, migraciones, excepciones, permisos, validaciones base, disponibilidad,
selector, consultas y auditoría que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

- [ ] T010 [P] Escribir las pruebas unitarias de normalización y validación en `tests/unit/test_asignacion_validaciones.py`: material seriado con series y no seriado con cantidad; seriado sin series; no seriado con series; cantidad cero, negativa y no entera; agrupación de no seriados por material; expansión de series a líneas con `cantidad=1`; duplicado de serie dentro de la solicitud; técnico inactivo y de otro tenant; lote tomado del catálogo; y `filas_origen` conservadas para los mensajes
- [ ] T011 [P] Escribir las pruebas unitarias de disponibilidad en `tests/unit/test_asignacion_disponibilidad.py`: `Disponible = Stock General - Reservado`; el reservado solo suma solicitudes `ENVIADA`; cantidad igual al disponible se acepta y cantidad mayor se rechaza; material sin `StockGeneral` tiene disponible 0; y cálculo agregado sin una consulta por línea
- [ ] T012 [P] Escribir las pruebas unitarias de servicios y permisos en `tests/unit/test_asignacion_servicios.py`: `validar_cuenta_tenant` con los tres roles, cuenta inactiva y tenant suspendido; `obtener_solicitud` con solicitud propia, inexistente y ajena; `listar_solicitudes` filtra por tenant y estado; `totales_solicitud`; y transiciones de estado permitidas y rechazadas
- [ ] T013 [P] Escribir las pruebas de restricciones de base en `tests/integration/test_asignacion_creacion.py`: línea con serie y `cantidad != 1` falla; línea sin serie y `cantidad <= 0` falla; dos líneas con la misma serie en la solicitud fallan; dos líneas no seriadas del mismo material en la solicitud fallan; y una solicitud con `estado` fuera del conjunto falla
- [ ] T014 Implementar `SolicitudAsignacion` en `asignaciones/models.py`: `tenant` FK `"tenants.Tenant"` `on_delete=PROTECT` `related_name="solicitudes_asignacion"`, `region` FK `"tenants.Region"` `PROTECT` `related_name="solicitudes_asignacion"`, `tecnico` FK `"tecnicos.Tecnico"` `PROTECT` `related_name="solicitudes_asignacion"`, `fecha = DateField()`, `estado = CharField(max_length=20, choices=[("BORRADOR","Borrador"),("ENVIADA","Enviada"),("CONFIRMADA","Confirmada"),("RECHAZADA","Rechazada"),("CANCELADA","Cancelada")], default="BORRADOR")`, `excel_ruta = CharField(max_length=255, blank=True, default="")`, `excel_hash = CharField(max_length=64, blank=True, default="")`, `excel_generado_en = DateTimeField(null=True, blank=True)`, `enviada_en = DateTimeField(null=True, blank=True)`, `confirmada_en = DateTimeField(null=True, blank=True)`, `creado_por` FK `AUTH_USER_MODEL` `PROTECT` `related_name="solicitudes_asignacion_creadas"`, `creado_en = DateTimeField(auto_now_add=True)`, `actualizado_por` FK `AUTH_USER_MODEL` `PROTECT` `related_name="solicitudes_asignacion_actualizadas"` `null=True` `blank=True`, `actualizado_en = DateTimeField(auto_now=True)`; `Meta.ordering=["-fecha","-id"]`, `CheckConstraint(solicitud_asignacion_estado_valido, estado IN (...))` e índices `solicitud_asign_tenant_estado`, `solicitud_asign_tecnico_fecha` y `solicitud_asign_region_fecha`
- [ ] T015 Implementar `LineaAsignacion` en `asignaciones/models.py`: `tenant` FK `"tenants.Tenant"` `PROTECT` `related_name="lineas_asignacion"`, `solicitud` FK `SolicitudAsignacion` `PROTECT` `related_name="lineas"`, `material` FK `"materiales.Material"` `PROTECT` `related_name="lineas_asignacion"`, `lote = CharField(max_length=50, blank=True, default="")`, `serie` FK `"series.Serie"` `PROTECT` `related_name="lineas_asignacion"` `null=True` `blank=True`, `cantidad = IntegerField(default=0)`; restricciones `linea_asignacion_serie_o_cantidad` (`Q(serie__isnull=False) | Q(cantidad__gt=0)`), `linea_asignacion_serie_cantidad_uno` (`Q(serie__isnull=True) | Q(cantidad=1)`), `linea_asignacion_cantidad_no_negativa` (`Q(cantidad__gte=0)`), `linea_asignacion_serie_unica_en_solicitud` (`UniqueConstraint(fields=["solicitud","serie"], condition=Q(serie__isnull=False))`) y `linea_asignacion_no_seriada_unica` (`UniqueConstraint(fields=["solicitud","material"], condition=Q(serie__isnull=True))`); índices `linea_asign_solicitud_material`, `linea_asign_tenant_material` y `linea_asign_serie`
- [ ] T016 Crear `asignaciones/migrations/0001_initial.py` con T014 y T015, revisar que no cree solicitudes, líneas, series ni stock por migración y aplicar con `migrate`
- [ ] T017 Crear `asignaciones/migrations/0002_rls.py` con políticas RLS por `tenant_id` para `asignaciones_solicitudasignacion` y `asignaciones_lineaasignacion`; si la infraestructura RLS de 001 no está disponible, registrar la deuda en `05-especificaciones/006-solicitud-de-asignacion/research.md` y no inventar una infraestructura paralela
- [ ] T018 Implementar en `asignaciones/services.py` las excepciones `ValidacionAsignacion`, `PermisoDenegado`, `TenantSuspendido`, `SolicitudNoExiste`, `TecnicoNoDisponible`, `MaterialNoExiste`, `SerieNoDisponible`, `SerieDuplicada`, `CantidadInvalida`, `CantidadExcedeDisponible`, `EstadoSolicitudInvalido` y `ExcelAsignacionInvalido`, y los `dataclass` inmutables `ErrorValidacion`, `LineaValidada`, `AlertaCupo` y `ResumenValidacion`
- [ ] T019 Implementar en `asignaciones/services.py` `validar_cuenta_tenant(actor)`, `obtener_solicitud(tenant, solicitud_id)`, `listar_solicitudes(tenant, estado=None)` y `obtener_detalle_solicitud(tenant, solicitud_id)` con los mensajes exactos “No tienes permiso para crear asignaciones”, “El tenant está suspendido” y “La solicitud no existe”, filtrado siempre por el tenant de la sesión y sin aceptar `tenant_id`/`region_id` del cliente
- [ ] T020 Implementar en `asignaciones/services.py` `validar_tecnico_para_asignacion(tenant, tecnico_id)`, `normalizar_lineas_solicitud(tenant, lineas)` y `validar_lineas_solicitud(tenant, lineas)`: resolver material por `id` global, exigir tipo seriado/no seriado, expandir series a líneas con `cantidad=1`, agrupar no seriados por material sumando cantidades, copiar `lote` de `material.lote`, detectar series repetidas y usar los mensajes “La solicitud debe tener al menos una línea”, “El material no existe en el catálogo”, “Debe indicar al menos una serie”, “El material no es seriado y no admite series”, “La serie está duplicada en la solicitud”, “La serie no está disponible”, “La cantidad debe ser un número entero”, “La cantidad debe ser mayor a 0”, “El técnico no existe en este tenant” y “El técnico está desactivado”; no escribir en la base
- [ ] T021 Implementar en `asignaciones/services.py` `calcular_reservado(tenant, material)`, `calcular_disponible(tenant, material)` y `validar_cantidad_disponible(tenant, material, cantidad)`: sumar solo líneas no seriadas de solicitudes `ENVIADA`, usar `max(0, stock - reservado)`, tratar la ausencia de `StockGeneral` como 0 y lanzar “La cantidad supera el stock disponible”; sin tabla de reservas
- [ ] T022 Implementar en `asignaciones/services.py` `series_disponibles_para_asignacion(tenant, material, q="", excluir_ids=None)` y `validar_series_disponibles(tenant, material, series)`: filtrar por tenant, material y `estado=EstadoSerie.DISPONIBLE`, excluir ids ya elegidos, buscar por `numero` o por código/descripción del material, ordenar por `numero`, paginar a 20 y no revelar series de otro tenant; usar “La serie no está disponible”
- [ ] T023 Implementar en `asignaciones/services.py` `totales_solicitud(solicitud)` y las consultas de detalle con `select_related` de técnico y `prefetch_related` de `lineas__material`/`lineas__serie`; `total_lineas`, `total_series` (líneas con serie) y `total_cantidad` (suma de no seriadas) deben calcularse sin N+1
- [ ] T024 Implementar en `asignaciones/services.py` los helpers de auditoría para `SolicitudAsignacion/alta`, `LineaAsignacion/alta`, `SolicitudAsignacion/estado`, `Serie/estado` y `SolicitudAsignacion/excel`, usando `auditoria.services.registrar_cambio` en la misma transacción, sin secretos, sin contenido binario del Excel, sin `tenant_id` separado y sin duplicar la auditoría de stock de 008
- [ ] T025 Implementar en `asignaciones/services.py` las guardas de transición `BORRADOR→ENVIADA` y `BORRADOR→CANCELADA` con “Solo se pueden enviar solicitudes en borrador” y “Solo se pueden cancelar solicitudes en borrador”; `CONFIRMADA`, `RECHAZADA` y `CANCELADA` son terminales y no se acepta `estado` desde formularios

**Checkpoint**: app, tablas, migraciones, permisos, validaciones, disponibilidad, consultas y auditoría listos; las historias pueden comenzar.

---

## Fase 3: US1 — Armar solicitud con validación en tiempo real (P1) 🎯 MVP

**Objetivo**: la cuenta del tenant elige un técnico activo, arma líneas seriadas y no seriadas,
selecciona series `DISPONIBLE` y valida la disponibilidad en tiempo real; puede guardar un
`BORRADOR` sin reservar series ni cantidades y sin generar Excel. El NIF se muestra de solo lectura.

**Prueba independiente**: como `USUARIO_TENANT`, abrir `/asignaciones/nueva/`, elegir un técnico,
agregar una serie disponible y 10 unidades de un no seriado, validar que el disponible descuenta lo
reservado y guardar un borrador; verificar `302`, estado `BORRADOR`, serie aún `DISPONIBLE`, sin
Excel, `StockGeneral` intacto y NIF no editable.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T026 [P] [US1] Pruebas de contrato de `GET /asignaciones/nueva/` en `tests/contract/test_asignacion_creacion_http.py`: `200` con técnico activo, fecha de hoy, una línea vacía, NIF de solo lectura y ausencia de `tenant_id`/`region_id`/`nif` editables; `403` para Admin/Almacén y tenant suspendido; `302` sin sesión; `405` para métodos no permitidos
- [ ] T027 [P] [US1] Pruebas de contrato de `POST /asignaciones/nueva/` con `accion=borrador` en `tests/contract/test_asignacion_creacion_http.py`: `302` al detalle, estado `BORRADOR`, sin Excel, sin reserva, errores `400` por línea con los mensajes exactos, `403`, `405` y campos `tenant_id`/`region_id`/`nif`/`estado` forzados ignorados
- [ ] T028 [P] [US1] Pruebas de contrato de `GET /asignaciones/series-disponibles/` en `tests/contract/test_asignacion_series_http.py`: **CA-02** devuelve `200` `text/html` con solo series `DISPONIBLE`, atributos `data-serie-id`, `data-serie`, `data-material-id` y `data-disponible`, búsqueda por número/material, paginación de 20 y sin JSON; **CA-10** una serie `ASIGNADA` no aparece; **CA-11** una serie `RESERVADA` no aparece; `400` para material ausente/inexistente/no seriado; `403` y `405`
- [ ] T029 [P] [US1] Pruebas de contrato de `POST /asignaciones/validar-disponibilidad/` en `tests/contract/test_asignacion_validacion_http.py`: **CA-03** cantidad 60 con disponible 50 devuelve `data-valido="false"` y `data-error="La cantidad supera el stock disponible"`; **CA-04** stock 50 y reservado 20 devuelve `data-disponible="30"`; atributos `data-valido`, `data-disponible`, `data-solicitado`, `data-error` y `data-alerta-cupo`; no escribe ni reserva; `400`, `403` y `405`
- [ ] T030 [P] [US1] Pruebas de integración de **CA-02**, **CA-10** y **CA-11** en `tests/integration/test_asignacion_reserva.py`: `test_selector_solo_muestra_series_disponibles` con series `DISPONIBLE`, `RESERVADA` y `ASIGNADA` del mismo tenant y material; la consulta devuelve solo la `DISPONIBLE`, no revela series de otro tenant y respeta la paginación
- [ ] T031 [P] [US1] Pruebas de integración de **CA-03** y **CA-04** en `tests/integration/test_asignacion_reserva.py`: `test_cantidad_excede_disponible_se_rechaza` con 60 sobre 50; `test_disponible_descuenta_reservado` con 50 de stock y 20 de una solicitud `ENVIADA`; 30 se acepta y 31 se rechaza; un borrador, una cancelada y una rechazada no suman al reservado
- [ ] T032 [P] [US1] Pruebas de integración de **CA-07** en `tests/integration/test_asignacion_excel.py`: `test_nif_se_copia_del_tecnico_y_no_del_formulario` con `nif=LA9999` forzado en el `POST`; la solicitud y el Excel usan `Tecnico.nif` y el campo del formulario es de solo lectura
- [ ] T033 [P] [US1] Pruebas de integración del borrador en `tests/integration/test_asignacion_creacion.py`: `test_crear_borrador_no_reserva_ni_genera_excel`; líneas y totales correctos; serie aún `DISPONIBLE`; `StockGeneral` y `StockTecnico` sin cambios; `excel_ruta` y `excel_hash` vacíos
- [ ] T034 [P] [US1] Pruebas de integración de validaciones en `tests/integration/test_asignacion_creacion.py`: solicitud sin líneas, técnico inactivo o de otro tenant, material inexistente, seriado sin series, no seriado con series, serie duplicada, cantidad cero/negativa/no entera y lote copiado del catálogo; cada caso con su mensaje exacto y sin escritura en la base

### Implementación de US1

- [ ] T035 [US1] Implementar `crear_borrador_solicitud(tenant, tecnico_id, fecha, lineas, actor)` en `asignaciones/services.py`: validar cuenta y técnico, normalizar y validar líneas, y en `transaction.atomic` crear `SolicitudAsignacion` en `BORRADOR` con región de `tenant.region`, `creado_por=actor` y sus `LineaAsignacion` con `tenant` y lote del catálogo; auditar alta de solicitud y de cada línea; no reservar series ni cantidades y no generar Excel
- [ ] T036 [US1] Implementar `asignaciones/forms.py` con el formulario de cabecera (técnico activo del tenant, fecha por defecto hoy) y el formset de líneas (material, tipo y lote de solo lectura, series o cantidad); excluir `tenant`, `tenant_id`, `region`, `region_id`, `almacen`, `nif`, `estado`, `excel_ruta` y `excel_hash`; validar al menos una línea y los mensajes exactos de `plan.md`
- [ ] T037 [US1] Implementar en `asignaciones/views.py` `nueva_asignacion` (GET): `@login_required`, validación de rol/tenant, formulario con fecha de hoy y una línea vacía, selector de técnico con `tecnicos.services.tecnicos_para_operacion`, selector de material con `/materiales/buscar/`, NIF de solo lectura y `403`/`405` según contrato
- [ ] T038 [US1] Implementar en `asignaciones/views.py` `nueva_asignacion` (POST) para `accion=borrador`: validar CSRF, rol, tenant, formulario y líneas; llamar a `crear_borrador_solicitud`; responder `302` al detalle o `400` con errores por línea; no aceptar `tenant`/`region`/`nif`/`estado` del cliente; la lógica permanece en `services.py`
- [ ] T039 [US1] Implementar en `asignaciones/views.py` `series_disponibles`: `GET`, rol/tenant, parámetros `material_id`, `q`, `page` y `excluir`; llamar a `series_disponibles_para_asignacion`; devolver `200` `text/html` con el fragmento de `contracts/selector-series.md`; `400`/`403`/`405` según contrato
- [ ] T040 [US1] Implementar en `asignaciones/views.py` `validar_disponibilidad`: `POST`, rol/tenant, técnico y líneas; calcular disponibilidad y alerta sin escribir; devolver `200` `text/html` con `data-valido`, `data-disponible`, `data-solicitado`, `data-error` y `data-alerta-cupo` de `contracts/validacion-disponibilidad.md`; `400`/`403`/`405` según contrato
- [ ] T041 [US1] Crear `asignaciones/urls.py` con `GET /asignaciones/nueva/`, `POST /asignaciones/nueva/`, `GET /asignaciones/series-disponibles/` y `POST /asignaciones/validar-disponibilidad/` (las rutas restantes se agregan en T064 y T098)
- [ ] T042 [US1] Crear `templates/asignaciones/formulario.html` con cabecera (técnico, NIF de solo lectura, fecha), formset de líneas, botones "Guardar borrador" y "Enviar", errores generales y de línea, y datos de solo lectura del catálogo; sin campos de tenant, región, almacén ni NIF editable
- [ ] T043 [US1] Crear `templates/asignaciones/_linea_form.html` con material, tipo y lote de solo lectura, contenedor de series para seriados y cantidad para no seriados, botón de eliminar línea y errores de la línea
- [ ] T044 [US1] Crear `templates/asignaciones/_series_disponibles.html` con la tabla del selector, atributos `data-serie-id`, `data-serie`, `data-material-id`, `data-disponible`, checkboxes `lineas-<n>-serie_ids` y paginación `data-page`/`data-has-next`; escapar valores y no incluir datos de otro tenant
- [ ] T045 [US1] Crear `templates/asignaciones/_validacion_disponibilidad.html` con el contenedor `data-valido`, `data-alerta-cupo`, `data-dias-maximo` y las filas `data-material-id`, `data-disponible`, `data-solicitado`, `data-valido` y `data-error`
- [ ] T046 [US1] Conectar HTMX en `templates/asignaciones/formulario.html`: `hx-get="/asignaciones/series-disponibles/"` al elegir material seriado, `hx-post="/asignaciones/validar-disponibilidad/"` al cambiar cantidad/técnico, `hx-target` correspondiente, `hx-indicator` y `hx-disabled-elt` mientras el POST está en curso; el servidor revalida siempre
- [ ] T047 [US1] Implementar en `asignaciones/services.py` la auditoría de alta de solicitud y de cada línea dentro de la transacción de `crear_borrador_solicitud`, con actor de la sesión, NIF del técnico, material, lote, serie o cantidad, sin secretos ni `tenant_id` separado

**Checkpoint**: US1 funcional e independiente; el tenant arma y guarda borradores con validación en tiempo real, sin reservar ni generar Excel.

---

## Fase 4: US2 — Enviar, reservar y generar el Excel (P2)

**Objetivo**: al enviar, la solicitud pasa a `ENVIADA`, las series a `RESERVADA`, las cantidades
quedan reservadas lógicamente y se genera un Excel inmutable con los metadatos de la región, el NIF
del técnico y su SHA-256. El envío es transaccional y resiste concurrencia.

**Prueba independiente**: crear un borrador con una serie y 10 unidades, enviarlo y verificar
`302`, estado `ENVIADA`, serie `RESERVADA`, Excel con `Z31`/centro/almacén/NIF, hash de 64
caracteres, auditoría de envío y reserva, y `StockGeneral`/`StockTecnico` sin cambios.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T048 [P] [US2] Pruebas de integración de **CA-01** en `tests/integration/test_asignacion_creacion.py`: `test_crear_y_enviar_solicitud_valida` con series y no seriados; la solicitud queda `ENVIADA`, las series `RESERVADA`, el Excel existe con hash y no se modificó el stock
- [ ] T049 [P] [US2] Pruebas de integración de **CA-05** en `tests/integration/test_asignacion_reserva.py`: `test_series_pasan_a_reservada_al_enviar`, una por una; `test_otra_solicitud_no_puede_reservar_la_misma_serie`; y una serie de otro tenant no se reserva
- [ ] T050 [P] [US2] Pruebas unitarias de **CA-06** en `tests/unit/test_asignacion_excel.py`: metadatos `Movimiento=Z31`, `Centro=region.almacen.centro`, `Almacén=region.almacen.codigo_almacen`, `NIF`, fecha, tenant, región e ID; una fila por serial y una por material menor; hash SHA-256 estable de 64 caracteres hexadecimales; sin datos de otra solicitud ni de otro tenant; nombre de archivo seguro y ruta relativa
- [ ] T051 [P] [US2] Pruebas de integración del Excel en `tests/integration/test_asignacion_excel.py`: `test_hash_del_excel_coincide_con_el_archivo`; `test_excel_no_se_regenera_despues_de_enviar`; metadatos leídos del almacén de la región, no literales; y el archivo no se modifica al consultar el detalle
- [ ] T052 [P] [US2] Pruebas de contrato de `POST /asignaciones/<id>/enviar/` en `tests/contract/test_asignacion_creacion_http.py`: `302` al detalle desde `BORRADOR`; `409` "Solo se pueden enviar solicitudes en borrador" desde `ENVIADA`/`CONFIRMADA`/`RECHAZADA`/`CANCELADA`; `404` para solicitud ajena; `403` para Admin/Almacén y tenant suspendido; `405` para otros métodos
- [ ] T053 [P] [US2] Pruebas de concurrencia en `tests/integration/test_asignacion_concurrencia.py`: dos envíos concurrentes del mismo tenant no superan el disponible; dos envíos de la misma serie dejan una sola `RESERVADA`; y el orden de bloqueo no produce interbloqueo
- [ ] T054 [P] [US2] Pruebas de invariantes de stock en `tests/integration/test_asignacion_reserva.py`: `test_stock_general_y_tecnico_no_cambian_al_enviar`; 006 no escribe `StockGeneral` ni `StockTecnico`; solo 007/008 lo harán al confirmar
- [ ] T055 [P] [US2] Pruebas de auditoría del envío en `tests/integration/test_asignacion_auditoria.py`: un registro `SolicitudAsignacion/estado` `BORRADOR→ENVIADA` con totales y hash; un `Serie/estado` `DISPONIBLE→RESERVADA` por serie; un registro de Excel con ruta relativa y hash; sin secretos ni `tenant_id` separado
- [ ] T056 [P] [US2] Pruebas de reversión en `tests/integration/test_asignacion_concurrencia.py`: un envío fallido (Excel, serie o auditoría) revierte solicitud, líneas, reservas, archivo y auditoría; no queda serie `RESERVADA` ni archivo huérfano accesible
- [ ] T057 [P] [US2] Pruebas de validación en el envío en `tests/integration/test_asignacion_reserva.py`: cantidad sobre el disponible, serie ya no disponible, serie duplicada y solicitud sin líneas se rechazan con los mensajes exactos y no cambian el estado

### Implementación de US2

- [ ] T058 [US2] Implementar `enviar_solicitud(solicitud, actor)` en `asignaciones/services.py`: validar cuenta, exigir `BORRADOR`, y en `transaction.atomic` bloquear el `Tenant` con `select_for_update`, releer la solicitud, revalidar líneas, disponibilidad y estado de series, cambiar cada serie a `RESERVADA`, generar y guardar el Excel, fijar `excel_ruta`/`excel_hash`/`excel_generado_en`, pasar a `ENVIADA`, fijar `enviada_en`/`actualizado_por` y auditar; no tocar `StockGeneral` ni `StockTecnico`
- [ ] T059 [US2] Implementar `crear_y_enviar_solicitud(tenant, tecnico_id, fecha, lineas, actor)` en `asignaciones/services.py` como una sola `transaction.atomic` que crea el borrador y lo envía; si el envío falla no queda borrador, serie reservada ni archivo
- [ ] T060 [US2] Implementar `generar_excel_asignacion(solicitud)` en `asignaciones/excel.py` con `openpyxl`: libro nuevo sin macros ni fórmulas; metadatos `Movimiento=settings.MOVIMIENTO_ASIGNACION`, `Centro=region.almacen.centro`, `Almacén=region.almacen.codigo_almacen`, `NIF=solicitud.tecnico.nif`, `Fecha de solicitud=solicitud.fecha.isoformat()`, `Tenant=tenant.codigo`, `Región=region.codigo` e `ID de solicitud=solicitud.id`; tabla de seriales (código, descripción, lote, serie, cantidad 1) y de material menor (código, descripción, lote, cantidad); devolver `(contenido, hash)`
- [ ] T061 [US2] Implementar `guardar_excel_asignacion(solicitud, contenido, hash)` en `asignaciones/excel.py`: escribir en `MEDIA_ROOT/ASIGNACIONES_EXCEL_DIR/<tenant.codigo>/<solicitud.id>/<uuid>.xlsx`, guardar `excel_ruta` relativa a `MEDIA_ROOT` y `excel_hash`, no incluir datos personales en el nombre y marcar el archivo de solo lectura
- [ ] T062 [US2] Implementar los bloqueos de `enviar_solicitud` en `asignaciones/services.py` en orden estable: `Tenant` (una fila), `StockGeneral` de los materiales no seriados afectados por id y `Serie` seleccionadas por id; recalcular reservado dentro de la transacción y no confiar en la validación previa de la vista
- [ ] T063 [US2] Implementar en `asignaciones/views.py` `enviar_solicitud` (POST): `@login_required`, rol/tenant, CSRF, `obtener_solicitud` con `404`, llamada al servicio, `302` al detalle, `409` por estado y `403`/`405` según contrato
- [ ] T064 [US2] Agregar `POST /asignaciones/<int:solicitud_id>/enviar/` a `asignaciones/urls.py` sin ruta de edición ni de borrado
- [ ] T065 [US2] Implementar la auditoría del envío en `asignaciones/services.py`: `SolicitudAsignacion/estado` con totales y hash, `Serie/estado` por cada reserva y `SolicitudAsignacion/excel` con ruta relativa y hash, todo en la misma transacción y sin duplicar la auditoría de stock de 008
- [ ] T066 [US2] Implementar en `asignaciones/services.py`/`asignaciones/excel.py` el manejo de fallo: si la generación o escritura del Excel falla, lanzar `ExcelAsignacionInvalido` con “No se pudo generar el Excel de asignación”, revertir la transacción y eliminar el archivo escrito; no exponer rutas ni trazas
- [ ] T067 [US2] Conectar el botón "Enviar" de `templates/asignaciones/formulario.html` con `accion=enviar` y `hx-disabled-elt`; el `POST` usa `crear_y_enviar_solicitud`; si falla, se muestran los errores sin perder los valores del formulario
- [ ] T068 [US2] Asegurar que `LineaAsignacion.lote` se copia de `material.lote` en `asignaciones/services.py` y que el Excel usa ese valor, no el enviado por el cliente; agregar prueba de regresión si falta
- [ ] T069 [US2] Agregar en `asignaciones/services.py` una guarda explícita que impida llamar a servicios de `stock` para escribir; documentar con comentario que solo 007/008 actualizan stock y verificar con la prueba de T054
- [ ] T070 [US2] Revisar el detalle mínimo en `templates/asignaciones/detalle.html` para mostrar estado `ENVIADA`, ruta relativa, hash y totales; la edición y la cancelación se completan en US4

**Checkpoint**: US2 funcional; el flujo crear-y-enviar reserva series y cantidades, genera el Excel firmado y no mueve stock físico.

---

## Fase 5: US3 — Días en mano y alerta de cupo (P3)

**Objetivo**: una vez confirmada la asignación por 007, el sistema calcula los días en mano de cada
serie desde `confirmada_en` y alerta al tenant, sin bloquear, si algún equipo seriado supera 20
días. La alerta se evalúa por equipo, no por suma de días.

**Prueba independiente**: con una solicitud `CONFIRMADA` cuyo `confirmada_en` es de hace 25 días y
su serie `ASIGNADA`, abrir `/asignaciones/nueva/` y verificar el aviso “El técnico supera los 20
días en mano”, el cálculo por serie y que el botón "Enviar" sigue habilitado.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T071 [P] [US3] Pruebas de integración de **CA-08** en `tests/integration/test_asignacion_custodia.py`: `test_dias_en_mano_inician_al_confirmar` con `confirmada_en` fijado por fixture; 10 días desde la confirmación y no desde `fecha`; una solicitud `ENVIADA` o `BORRADOR` no muestra días; una serie devuelta no se cuenta
- [ ] T072 [P] [US3] Pruebas de integración de **CA-09** en `tests/integration/test_asignacion_custodia.py`: `test_alerta_cupo_maximo_se_muestra` con una serie de 25 días; `test_alerta_cupo_no_bloquea_el_envio`; 19/20 días no alertan y 21/25 sí; y la alerta identifica el equipo, no la suma de días
- [ ] T073 [P] [US3] Pruebas unitarias de días y alerta en `tests/unit/test_asignacion_disponibilidad.py`: `dias_en_mano_serie` con 0, 19, 20, 21 y 25 días; `confirmada_en` nulo devuelve `None`; `calcular_alerta_cupo` con 0, 1 y 2 equipos; y `series_en_custodia_tecnico` conserva la confirmación más reciente por serie
- [ ] T074 [P] [US3] Pruebas de contrato de la alerta en `tests/contract/test_asignacion_creacion_http.py` y `tests/contract/test_asignacion_validacion_http.py`: `GET /asignaciones/nueva/` muestra el aviso y no deshabilita "Enviar"; `validar-disponibilidad` devuelve `data-alerta-cupo="true"` y `data-dias-maximo` sin afectar `data-valido`
- [ ] T075 [P] [US3] Pruebas de aislamiento de custodia en `tests/integration/test_asignacion_custodia.py`: la alerta solo considera técnicos y series del tenant de la sesión; una serie de otro tenant no altera días ni alerta

### Implementación de US3

- [ ] T076 [US3] Implementar `dias_en_mano_serie(linea, hoy=None)` en `asignaciones/services.py`: exigir solicitud `CONFIRMADA` y `confirmada_en` no nulo; devolver `(hoy - confirmada_en.date()).days`; devolver `None` si no está confirmada; no usar `fecha` de la solicitud
- [ ] T077 [US3] Implementar `series_en_custodia_tecnico(tecnico)` en `asignaciones/services.py`: recorrer líneas seriadas de solicitudes `CONFIRMADA` del técnico con `Serie.estado=ASIGNADA`, conservar la confirmación más reciente por serie y devolver serie, material, `confirmada_en` y días en mano; filtrar por el tenant del técnico y dejar la consulta aislada para que 009/011 la extiendan
- [ ] T078 [US3] Implementar `calcular_alerta_cupo(tecnico)` en `asignaciones/services.py`: devolver `AlertaCupo` si alguna serie en custodia supera `settings.DIAS_ALERTA_CUSTODIA`, con el mensaje “El técnico supera los 20 días en mano”; no bloquear ni cambiar el estado de la solicitud; no sumar días entre equipos
- [ ] T079 [US3] Integrar la alerta en `asignaciones/views.py` `nueva_asignacion` (GET): calcular `calcular_alerta_cupo` para el técnico seleccionado o para el primero disponible y pasarla al contexto; no deshabilitar "Enviar"
- [ ] T080 [US3] Integrar la alerta en `asignaciones/views.py` `validar_disponibilidad`: incluir `data-alerta-cupo` y `data-dias-maximo` en el fragmento, sin alterar `data-valido` ni escribir en la base
- [ ] T081 [US3] Crear `templates/asignaciones/_alerta_cupo.html` con el aviso visible pero no intrusivo, el mensaje exacto y el detalle del equipo que supera el umbral; sin bloquear acciones ni exponer datos de otro tenant
- [ ] T082 [US3] Completar `templates/asignaciones/detalle.html` para mostrar, si la solicitud está `CONFIRMADA`, los días en mano por serie y la alerta de cupo; una solicitud no confirmada no muestra días ni alerta
- [ ] T083 [US3] Implementar el cálculo de días en el detalle con `series_en_custodia_tecnico` y `dias_en_mano_serie` en `asignaciones/views.py`, sin N+1 y sin consultar series de otro tenant
- [ ] T084 [US3] Extender `conftest.py` con el fixture `solicitud_confirmada` que fija `confirmada_en` y deja la serie `ASIGNADA`, sin implementar 007; usarlo en T071, T072 y T075
- [ ] T085 [US3] Documentar en `asignaciones/services.py` que `confirmada_en` lo escribe 007 y que 009/011 deben actualizar la fuente de custodia al mover o devolver series; no implementar esas transiciones en 006

**Checkpoint**: US3 funcional; el detalle y el formulario informan custodia y alerta sin bloquear la operación.

---

## Fase 6: US4 — Consulta, cancelación, aislamiento y auditoría (P4)

**Objetivo**: el tenant consulta sus solicitudes, filtra por estado, ve el detalle con totales y
hash, cancela borradores y recibe `403`/`404` correctos ante roles o tenants ajenos. Toda la
operación queda auditada y el listado no tiene N+1.

**Prueba independiente**: con dos tenants y solicitudes en distintos estados, listar y filtrar,
abrir el detalle propio, recibir `404` por el ajeno, cancelar un borrador y verificar que no se
liberan series porque no estaban reservadas; Admin y Almacén reciben `403`.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T086 [P] [US4] Pruebas de contrato de `GET /asignaciones/` en `tests/contract/test_asignacion_lista_http.py`: `200` con ID, fecha, técnico, NIF, estado, totales y enlace al detalle; filtro `estado`; paginación de 50; solo solicitudes del tenant; `403` para Admin/Almacén y tenant suspendido; `302` sin sesión; `405`
- [ ] T087 [P] [US4] Pruebas de contrato de `GET /asignaciones/<id>/` en `tests/contract/test_asignacion_creacion_http.py`: `200` con detalle, líneas agrupadas, totales y hash; `BORRADOR` sin Excel y con "Enviar"/"Cancelar"; `CONFIRMADA` con días en mano; `404` para ajena; `403`/`405`
- [ ] T088 [P] [US4] Pruebas de contrato de `POST /asignaciones/<id>/cancelar/` en `tests/contract/test_asignacion_creacion_http.py`: `302` desde `BORRADOR`; `409` "Solo se pueden cancelar solicitudes en borrador" desde otros estados; `404` para ajena; `403` para Admin/Almacén y tenant suspendido; `405`
- [ ] T089 [P] [US4] Matriz completa de permisos en `tests/contract/test_asignacion_permisos_http.py` para las 8 rutas y los perfiles `ADMIN_PLATAFORMA`, `RESPONSABLE_ALMACEN`, `USUARIO_TENANT`, tenant suspendido y anónimo; verificar `403`, `404`, `302` y `405` según `contracts/http-endpoints.md`
- [ ] T090 [P] [US4] Pruebas de aislamiento en `tests/integration/test_asignacion_aislamiento.py`: solicitud de otro tenant responde `404`; `tenant_id`/`region_id`/`nif` forzados se ignoran; el listado no muestra solicitudes ajenas; y la RLS por tenant se verifica si la infraestructura está disponible
- [ ] T091 [P] [US4] Pruebas de auditoría de alta y cancelación en `tests/integration/test_asignacion_auditoria.py`: alta de solicitud y de cada línea, cancelación `BORRADOR→CANCELADA`, ausencia de secretos y de `tenant_id` separado, y conservación de la auditoría al desactivar la cuenta o suspender el tenant
- [ ] T092 [P] [US4] Pruebas de rendimiento en `tests/integration/test_asignacion_creacion.py` con `django_assert_num_queries`: listado a 50 sin N+1; detalle con `select_related`/`prefetch_related`; validación con una consulta de stock y una de reservado; selector paginado; y envío con una consulta de series y una de stock por material, no por línea
- [ ] T093 [P] [US4] Pruebas de cancelación en `tests/integration/test_asignacion_creacion.py`: `test_cancelar_borrador_no_libera_series`; no se genera Excel; no se reserva cantidad; y no se puede cancelar una solicitud `ENVIADA`, `CONFIRMADA`, `RECHAZADA` o `CANCELADA`

### Implementación de US4

- [ ] T094 [US4] Implementar en `asignaciones/views.py` `lista_asignaciones`: `@login_required`, rol/tenant, filtro `estado`, paginación de 50, totales y enlace al detalle; orden `fecha`/`id` descendente; `403`/`405` según contrato
- [ ] T095 [US4] Implementar en `asignaciones/views.py` `detalle_asignacion`: `obtener_detalle_solicitud` con `select_related`/`prefetch_related`, `404` para solicitud ajena o inexistente, totales, hash y días en mano si está `CONFIRMADA`; `403`/`405`
- [ ] T096 [US4] Implementar `cancelar_solicitud(solicitud, actor)` en `asignaciones/services.py`: validar cuenta, exigir `BORRADOR`, en `transaction.atomic` cambiar a `CANCELADA`, fijar `actualizado_por` y auditar `BORRADOR→CANCELADA`; no liberar series ni cantidades porque el borrador no reservó
- [ ] T097 [US4] Implementar en `asignaciones/views.py` `cancelar_solicitud` (POST): rol/tenant, CSRF, `obtener_solicitud` con `404`, llamada al servicio, `302` al detalle, `409` por estado y `403`/`405`
- [ ] T098 [US4] Agregar a `asignaciones/urls.py` `GET /asignaciones/`, `GET /asignaciones/<int:solicitud_id>/` y `POST /asignaciones/<int:solicitud_id>/cancelar/`; no agregar rutas de edición ni de borrado
- [ ] T099 [US4] Crear `templates/asignaciones/lista.html` con ID, fecha, técnico, NIF, estado, totales, filtro por estado, paginación y enlace al detalle; sin datos de otro tenant ni de stock del técnico
- [ ] T100 [US4] Completar `templates/asignaciones/detalle.html` con técnico, NIF, fecha, estado, líneas agrupadas, totales, ruta y hash del Excel, botones "Enviar"/"Cancelar" solo en `BORRADOR` y días en mano si está `CONFIRMADA`; sin enlace de descarga propio de 006
- [ ] T101 [US4] Asegurar que todas las consultas de `asignaciones/views.py` y `asignaciones/services.py` filtran por `tenant=request.usuario.tenant`; no aceptar `tenant_id`/`region_id` de la URL ni del `POST`; responder `404` ante datos ajenos
- [ ] T102 [US4] Verificar en `asignaciones/services.py` que `LineaAsignacion.tenant` se fija desde `solicitud.tenant` en todos los servicios y que la auditoría no escribe un `tenant_id` separado; agregar prueba de regresión si falta
- [ ] T103 [US4] Revisar las 8 rutas contra `contracts/http-endpoints.md`: métodos permitidos, `405`, CSRF, `403`/`404`/`409`, fragmentos HTML/HTMX y ausencia de JSON; corregir desviaciones antes del cierre

**Checkpoint**: las cuatro historias funcionan; la feature queda completa y aislada por tenant.

---

## Fase 7: Polish y preocupaciones transversales

**Propósito**: verificación final, cobertura de criterios, rendimiento, documentación y limpieza.

- [ ] T104 [P] Verificar en `05-especificaciones/006-solicitud-de-asignacion/quickstart.md` que cada CA-01…CA-11 tiene al menos una prueba en `tests/unit/`, `tests/integration/` o `tests/contract/`; agregar la prueba faltante si alguna no está cubierta
- [ ] T105 [P] Ejecutar `pytest` completo de 006 desde `tests/` sobre PostgreSQL y corregir cualquier fallo; no se avanza con pruebas en rojo
- [ ] T106 [P] Ejecutar `python manage.py makemigrations --check --dry-run` sobre `asignaciones/migrations/` y `python manage.py migrate --plan`; no deben quedar migraciones pendientes
- [ ] T107 [P] Ejecutar `pytest --cov=asignaciones --cov-report=term-missing` sobre `tests/` y cubrir los caminos de error de permisos, disponibilidad, estado y Excel
- [ ] T108 [P] Revisar `asignaciones/services.py` y `asignaciones/excel.py`: sin lógica de negocio en vistas, formularios ni plantillas; sin `tenant_id` del cliente; sin escrituras a `StockGeneral`/`StockTecnico`; sin correo, Celery, WebSocket ni confirmación de almacén
- [ ] T109 [P] Revisar rendimiento con `django_assert_num_queries` en `tests/integration/test_asignacion_creacion.py` para listado, detalle, selector, validación y envío; la validación debe responder en menos de 1 segundo en el escenario de prueba
- [ ] T110 [P] Actualizar la documentación de la feature si la implementación difiere del plan; registrar cualquier deuda (RLS no disponible, limpieza de Excel huérfano, fuente de custodia de 009/011) en `research.md` y no inventar comportamiento no especificado
- [ ] T111 Ejecutar los escenarios de `quickstart.md` y marcar los criterios de salida; reportar el resultado antes de cerrar la feature

---

## Dependencias y orden de ejecución

### Dependencias de fase

- **Setup (Fase 1)**: sin dependencias; las correcciones documentales T002–T004 deben completarse antes de implementar.
- **Fundacional (Fase 2)**: depende de Setup y **bloquea** las cuatro historias.
- **US1 (Fase 3)**: depende de Fundacional; no depende de otras historias.
- **US2 (Fase 4)**: depende de Fundacional y de los servicios de borrador de US1; puede probarse con un borrador creado por servicio o fixture.
- **US3 (Fase 5)**: depende de Fundacional; usa el fixture `solicitud_confirmada` y no requiere 007 implementada.
- **US4 (Fase 6)**: depende de Fundacional; consume solicitudes de US1/US2, pero se prueba con fixtures.
- **Polish (Fase 7)**: depende de las historias que se quieran entregar.

### Dependencias entre historias

- **US1 (P1)**: arma y guarda borradores; es la base del flujo.
- **US2 (P2)**: envía, reserva y genera Excel; requiere un borrador de US1.
- **US3 (P3)**: calcula custodia y alerta; requiere solicitudes `CONFIRMADA` creadas por fixture o por 007.
- **US4 (P4)**: consulta, cancela y audita; puede avanzar en paralelo con US3 si hay capacidad.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Modelos antes que servicios; servicios antes que vistas; vistas antes que plantillas.
- La lógica de negocio permanece en `services.py` y `excel.py`.
- Una historia se completa y se valida antes de pasar a la siguiente prioridad.

## Oportunidades de paralelización

- T002, T003, T004, T005, T006, T007, T008 y T009 pueden ejecutarse en paralelo si no comparten archivos.
- T010, T011, T012 y T013 (pruebas fundacionales) pueden escribirse en paralelo.
- T014 y T015 comparten `asignaciones/models.py`: no ejecutar en paralelo entre sí.
- Las pruebas de US1 T026–T034 pueden escribirse en paralelo; la implementación T035–T047 tiene dependencias internas.
- Las pruebas de US2 T048–T057 pueden escribirse en paralelo; T058–T069 comparten `services.py`/`excel.py` y deben secuenciarse.
- Las pruebas de US3 T071–T075 y las de US4 T086–T093 pueden escribirse en paralelo entre historias.
- T104–T110 del polish pueden ejecutarse en paralelo; T105 y T111 requieren que las historias estén completas.

## Ejemplo de paralelización: US1

```text
# Pruebas de US1 en paralelo (archivos distintos):
Task: "Contrato GET /asignaciones/nueva/ en tests/contract/test_asignacion_creacion_http.py"
Task: "Contrato del selector en tests/contract/test_asignacion_series_http.py"
Task: "Contrato de validación en tests/contract/test_asignacion_validacion_http.py"
Task: "Integración CA-03/CA-04 en tests/integration/test_asignacion_reserva.py"
Task: "Integración CA-07 en tests/integration/test_asignacion_excel.py"
```

## Ejemplo de paralelización: US2

```text
# Pruebas de US2 en paralelo:
Task: "Integración CA-01 en tests/integration/test_asignacion_creacion.py"
Task: "Integración CA-05 en tests/integration/test_asignacion_reserva.py"
Task: "Unitarias CA-06 en tests/unit/test_asignacion_excel.py"
Task: "Concurrencia en tests/integration/test_asignacion_concurrencia.py"
```

## Estrategia de implementación

### MVP primero

1. Completar Setup y Fundacional.
2. Completar US1: armar y guardar borradores con validación en tiempo real.
3. Completar US2: enviar, reservar y generar el Excel.
4. **DETENERSE y VALIDAR**: el flujo crear-y-enviar funciona de extremo a extremo, con Excel y
   auditoría, sin mover stock físico. Este es el MVP real de 006; US1 sola solo guarda borradores.
5. Completar US3 y US4 para custodia, alertas, consulta y cancelación.

### Entrega incremental

1. Setup + Fundacional → base lista.
2. US1 → borradores y validación; demostrable.
3. US2 → envío, reserva y Excel; MVP del flujo de asignación.
4. US3 → custodia y alerta; valor para el control de equipos.
5. US4 → consulta, cancelación y aislamiento; cierre operativo.

### Estrategia de equipo

- Una persona completa Setup + Fundacional.
- Después, una persona puede tomar US1, otra US2 (con un borrador de fixture) y otra US3 con el
  fixture de confirmación; US4 puede esperar a que las rutas de US1/US2 existan.
- Evitar que dos personas editen `asignaciones/services.py` a la vez; dividir por archivos o
  secuenciar.

## Cobertura de criterios de aceptación

| CA | Historia | Pruebas principales |
|---|---|---|
| CA-01 | US2 | T048 `test_crear_y_enviar_solicitud_valida` |
| CA-02 | US1 | T028, T030 selector solo `DISPONIBLE` |
| CA-03 | US1 | T029, T031 cantidad sobre disponible |
| CA-04 | US1 | T029, T031 disponible descuenta reservado |
| CA-05 | US2 | T049 series pasan a `RESERVADA` |
| CA-06 | US2 | T050, T051 metadatos y hash del Excel |
| CA-07 | US1 | T032 NIF copiado del técnico, no editable |
| CA-08 | US3 | T071 días desde `confirmada_en` |
| CA-09 | US3 | T072, T074 alerta de cupo |
| CA-10 | US1 | T028, T030 serie `ASIGNADA` no aparece |
| CA-11 | US1 | T028, T030 serie `RESERVADA` no aparece |

## Notas

- [P] significa archivos distintos y sin dependencia de una tarea incompleta.
- [Story] solo aparece en las fases de historia; Setup, Fundacional y Polish no llevan etiqueta.
- Toda prueba se escribe antes de la implementación y debe fallar primero.
- No se acepta `tenant_id`, `region_id`, `nif` ni `estado` del cliente.
- 006 no escribe `StockGeneral` ni `StockTecnico`; no implementa correo, Celery, WebSocket,
  bandeja del almacén ni confirmación de 007.
- Las correcciones documentales T002–T004 son obligatorias antes de implementar (principio VIII).
- Evitar tareas vagas y conflictos de archivo; `asignaciones/services.py` es el archivo de mayor
  contención y debe secuenciarse.
