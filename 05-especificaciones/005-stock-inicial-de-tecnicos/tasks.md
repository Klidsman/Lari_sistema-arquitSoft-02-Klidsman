---
description: "Lista de tareas para la implementación de 005 Stock Inicial de Técnicos"
---

# Tareas: 005 Stock Inicial de Técnicos

**Entrada**: Documentos de diseño en `05-especificaciones/005-stock-inicial-de-tecnicos/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`, `tenants.Region`,
`tenants.Tenant`, `ContextoUsuarioMiddleware` y `auditoria.RegistroCambio`/`registrar_cambio`),
**spec 002 implementada** (`materiales.Material`), **spec 003 implementada**
(`tecnicos.Tecnico` y sus servicios), **app `series` de 004 implementada**
(`series.Serie`, `EstadoSerie` y `series.services.crear_serie`/`series_existentes`) y **parte
fundacional de 008 implementada** (`stock.StockTecnico`,
`stock.services.incrementar_stock_tecnico` y `stock.services.decrementar_stock_tecnico`). La
confirmación de asignaciones de 008 **no** es prerrequisito. Las tareas de 001, 002, 003, 004 y 008
no se repiten aquí.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-13. Cada historia escribe primero sus
pruebas, las ve fallar y luego implementa.

**Organización**: `spec.md` no define historias de usuario propias; se derivan cinco historias a
partir de los criterios de aceptación y de las dependencias técnicas, para permitir entregas
incrementales e independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario asociada (`US1`…`US5`)
- Todas las rutas de archivo son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Carga por Excel con asignación directa y auditoría | P1 | CA-01, CA-08, CA-09; RF-20 §5.1, §5.10 y §5.11 |
| US2 — Validación y rechazo de datos inválidos | P2 | CA-03, CA-04, CA-05, CA-06; §5.5–§5.8 |
| US3 — Carga por formulario | P3 | CA-02; §5.2 |
| US4 — Carga única, transaccionalidad, concurrencia y acceso | P4 | CA-07, CA-10; §5.3, §5.9 y §6.3 |
| US5 — Edición transaccional del stock inicial | P5 | CA-11, CA-12, CA-13; §5.4 |

## Convenciones de rutas

Proyecto Django único en la raíz: la app nueva es `stock_inicial/`; las plantillas viven en
`templates/stock_inicial/`; las pruebas en `tests/{unit,integration,contract}/`. Las apps `acceso`,
`tenants`, `auditoria` (001), `materiales` (002), `tecnicos` (003), `series` (004) y `stock` (008)
son propiedad de sus specs y no se duplican. 005 **no** crea una tabla de series ni escribe
`stock.StockGeneral`.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: crear la app `stock_inicial`, conectarla al proyecto y preparar el entorno de pruebas.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `tecnicos/models.py`, `series/models.py`, `series/services.py`, `stock/models.py`, `stock/services.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware` activo, roles `ADMIN_PLATAFORMA`/`USUARIO_TENANT`/`RESPONSABLE_ALMACEN`, `materiales.Material.es_seriado`/`lote`/`descripcion`, `tecnicos.services.validar_nif`/`normalizar_nif`, `series.Serie` con `unique(numero)` y campos `tecnico`/`asignada_en`, `series.services.crear_serie(..., estado=..., tecnico=..., asignada_en=...)`, `stock.StockTecnico` y los servicios `incrementar_stock_tecnico`/`decrementar_stock_tecnico`; detenerse y reportar si falta alguno
- [ ] T002 Crear la app Django `stock_inicial` con `stock_inicial/__init__.py`, `stock_inicial/apps.py`, `stock_inicial/migrations/__init__.py` y registrarla en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T003 [P] Agregar `PERMITIR_REINICIO_STOCK_INICIAL = False` en `config/settings/base.py`, con lectura desde variable de entorno y valor por defecto `False`
- [ ] T004 [P] Incluir `stock_inicial/urls.py` desde `config/urls.py` bajo el prefijo `/stock-inicial/` (el archivo se completa en T034)
- [ ] T005 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region`, `tenant`, `otro_tenant`, `tenant_suspendido`, `usuario_tenant`, `usuario_admin`, `usuario_almacen`, `usuario_inactivo`, `tecnico_activo`, `tecnico_desactivado`, `material_seriado`, `material_no_seriado`, `serie_existente`, `carga_stock_inicial` y `registro_cambios`
- [ ] T006 [P] Agregar el enlace de navegación a Stock inicial en `templates/base.html`, visible solo para `USUARIO_TENANT` con tenant activo

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelos, migraciones, lectura de Excel, normalización, validaciones base, permisos,
carga transaccional, consultas y auditoría que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

- [ ] T007 [P] Escribir las pruebas unitarias de normalización y validación en `tests/unit/test_stock_inicial_validaciones.py`: NIF `LAXXXX`, material con `strip()`, serie sin espacios y en mayúsculas, agrupación de no seriados por `(tecnico, material)`, duplicados de serie dentro de la carga, serie existente con mensaje uniforme, cantidad cero/negativa/no numérica, material seriado sin serie, material no seriado con serie y `LineaValidada.lote` tomado del catálogo
- [ ] T008 [P] Escribir las pruebas unitarias de Excel en `tests/unit/test_stock_inicial_excel.py`: lectura de `.xlsx` generado con `openpyxl`, rechazo de `.xls` con "El archivo debe ser un Excel .xlsx", columna faltante, archivo vacío, hoja sin filas, archivo corrupto, hash SHA-256 estable, nombre base y uso de `read_only=True`/`data_only=True` sin escrituras
- [ ] T009 [P] Escribir las pruebas unitarias de servicios en `tests/unit/test_stock_inicial_servicios.py`: `validar_cuenta_tenant` con los tres roles, cuenta inactiva y tenant suspendido; `validar_puede_cargar_stock_inicial` y `validar_puede_editar_stock_inicial`; `obtener_carga`/`obtener_linea` con datos ajenos; y `totales_carga`
- [ ] T010 Agregar `stock_inicial_cargado = models.BooleanField(default=False)` y `fecha_stock_inicial = models.DateTimeField(null=True, blank=True)` a `tenants/models.py`; se actualizan junto con `actualizado_por`/`actualizado_en` y nunca se aceptan desde formularios, URLs ni archivos
- [ ] T011 Crear `tenants/migrations/0002_stock_inicial_fields.py` con los campos de T010, sin modificar datos existentes, y aplicarla con `migrate`
- [ ] T012 Implementar `CargaStockInicial` en `stock_inicial/models.py`: `tenant` FK `"tenants.Tenant"` `on_delete=PROTECT` `related_name="cargas_stock_inicial"`, `region` FK `"tenants.Region"` `PROTECT` `related_name="cargas_stock_inicial"`, `fecha = DateTimeField(auto_now_add=True)`, `metodo = CharField(max_length=10, choices=[("EXCEL","Excel"),("FORMULARIO","Formulario")])`, `archivo_nombre = CharField(max_length=255, blank=True, default="")`, `archivo_hash = CharField(max_length=64, blank=True, default="")`, `creado_por` FK `AUTH_USER_MODEL` `PROTECT` `related_name="cargas_stock_inicial_creadas"`; `Meta.ordering=["-fecha","-id"]`, `UniqueConstraint(fields=["tenant"], name="carga_stock_inicial_tenant_unico")` e `Index(fields=["tenant","fecha"], name="carga_stock_tenant_fecha")`
- [ ] T013 Implementar `LineaStockInicial` en `stock_inicial/models.py`: `tenant` FK `"tenants.Tenant"` `PROTECT` `related_name="lineas_stock_inicial"`, `carga` FK `CargaStockInicial` `CASCADE` `related_name="lineas"`, `tecnico` FK `"tecnicos.Tecnico"` `PROTECT` `related_name="lineas_stock_inicial"`, `material` FK `"materiales.Material"` `PROTECT` `related_name="lineas_stock_inicial"`, `lote = CharField(max_length=50, blank=True, default="")`, `serie = OneToOneField("series.Serie", null=True, blank=True, on_delete=PROTECT, related_name="linea_stock_inicial")`, `cantidad = IntegerField(default=0)`; restricciones `linea_stock_inicial_serie_o_cantidad` (`Q(serie__isnull=False) | Q(cantidad__gt=0)`), `linea_stock_inicial_serie_cantidad_uno` (`Q(serie__isnull=True) | Q(cantidad=1)`), `linea_stock_inicial_cantidad_no_negativa` (`Q(cantidad__gte=0)`) y `linea_stock_inicial_no_seriada_unica` (`UniqueConstraint(fields=["carga","tecnico","material"], condition=Q(serie__isnull=True))`); índices `linea_stock_tenant_tecnico`, `linea_stock_carga_tecnico` y `linea_stock_tenant_material`
- [ ] T014 Crear `stock_inicial/migrations/0001_initial.py` con T012 y T013, revisar que no cree cargas, líneas, series, técnicos ni materiales por migración y aplicar con `migrate`
- [ ] T015 [P] Escribir las pruebas de restricciones de base en `tests/integration/test_stock_inicial_carga.py`: dos cargas del mismo tenant fallan; línea con serie y `cantidad != 1` falla; línea sin serie y `cantidad <= 0` falla; cantidad negativa falla; dos líneas no seriadas con el mismo `(carga, tecnico, material)` fallan; y dos `series.Serie` con el mismo `numero` fallan
- [ ] T016 Crear `stock_inicial/migrations/0002_rls.py` con políticas RLS por `tenant_id` para `stock_inicial_cargastockinicial` y `stock_inicial_lineastockinicial`; si la infraestructura RLS de 001 no está disponible, registrar la deuda en `05-especificaciones/005-stock-inicial-de-tecnicos/research.md` y no inventar una infraestructura paralela
- [ ] T017 Implementar en `stock_inicial/services.py` las excepciones `ValidacionStockInicial`, `StockInicialYaCargado`, `StockInicialNoCargado`, `StockInicialNoExiste`, `PermisoDenegado`, `TenantSuspendido`, `TecnicoNoExiste`, `MaterialNoExiste`, `SerieDuplicada`, `SerieYaExiste`, `FormatoExcelInvalido`, `CantidadInvalida`, `LineaNoEditable`, `EdicionInvalida` y `ReinicioDeshabilitado`, y los `dataclass` inmutables `ErrorValidacion` (`fila`, `campo`, `mensaje`, `valor`), `FilaExcel`, `LineaValidada`, `ResumenValidacion`, `ResultadoValidacionStockInicial` y `OperacionEdicion` (`tipo`, `linea_id`, `tecnico`, `material`, `series`, `cantidad`)
- [ ] T018 Implementar `leer_excel_stock_inicial(archivo)` en `stock_inicial/excel.py`: exigir `.xlsx` sin distinguir mayúsculas, leer los bytes una sola vez, calcular SHA-256, abrir con `openpyxl.load_workbook(BytesIO(contenido), read_only=True, data_only=True)`, usar la primera hoja, normalizar cabeceras con `strip()`/`casefold()`, exigir `Material`, `Lote`, `Libre utilización`, `Número de serie`, `Nº ident.fis.1` y `Texto breve material`, ignorar filas vacías y devolver `(filas, archivo_nombre, archivo_hash)` sin escribir en la base
- [ ] T019 Implementar en `stock_inicial/services.py` `normalizar_filas_stock_inicial(filas)` y `validar_filas_stock_inicial(tenant, filas)`: cargar técnicos por NIF, materiales por código y `series_existentes` en bloque (sin consultas por fila); normalizar NIF, material y serie; validar `^LA[0-9]{4}$`, existencia del técnico en el tenant, existencia del material, tipo seriado/no seriado, formato de serie, duplicados internos, series existentes con mensaje uniforme, cantidades enteras `> 0`; agrupar no seriados por `(tecnico_id, material_id)` sumando cantidades; generar una `LineaValidada` por serie válida con `cantidad=1`; usar `material.lote` y `material.descripcion`; no escribir en la base
- [ ] T020 Implementar en `stock_inicial/services.py` `validar_excel_stock_inicial(tenant, archivo)` y `validar_formulario_stock_inicial(tenant, datos)`: combinar lectura + validación común, resolver técnico por `id` y tenant, material por `id` global, series separadas por saltos de línea, comas o espacios, y rechazar `tenant_id`/`region_id` de la entrada
- [ ] T021 Implementar `cargar_stock_inicial(tenant, resultado, metodo, actor, archivo_nombre="", archivo_hash="")` en `stock_inicial/services.py`: validar cuenta y carga única; exigir resultado válido y al menos una línea; en `transaction.atomic` bloquear el `Tenant` con `select_for_update` y revalidar flag/inexistencia de carga; crear `CargaStockInicial` con región de la sesión; crear series `ASIGNADA` con `series.services.crear_serie(..., estado=EstadoSerie.ASIGNADA, tecnico=tecnico, asignada_en=ahora)`; crear líneas con `tenant` y lote del catálogo; incrementar `StockTecnico` una vez por `(tecnico, material)` con `stock.services.incrementar_stock_tecnico`; marcar `stock_inicial_cargado`/`fecha_stock_inicial`; auditar carga, líneas, series y cambios del tenant; traducir `IntegrityError` de `CargaStockInicial.tenant` a `StockInicialYaCargado` y el de `Serie.numero` a `SerieYaExiste`; **nunca** escribir `StockGeneral`
- [ ] T022 Implementar en `stock_inicial/services.py` `cargar_desde_excel(tenant, archivo, actor)` y `cargar_desde_formulario(tenant, datos, actor)` con método `EXCEL`/`FORMULARIO`, nombre y hash solo para Excel, validación previa antes de la transacción y revalidación dentro de ella
- [ ] T023 Implementar en `stock_inicial/services.py` `validar_cuenta_tenant(actor)`, `validar_cuenta_admin(actor)`, `validar_puede_cargar_stock_inicial(tenant)`, `validar_puede_editar_stock_inicial(tenant)`, `obtener_carga(tenant, carga_id)`, `obtener_linea(carga, linea_id)`, `obtener_detalle_carga(tenant, carga_id)`, `listar_lineas_agrupadas(carga)`, `totales_carga(carga)` y `estado_stock_inicial(tenant)` con los mensajes exactos del contrato y filtrado por el tenant de la sesión
- [ ] T024 Implementar en `stock_inicial/services.py` los helpers de auditoría para `CargaStockInicial/alta`, `LineaStockInicial/alta`, `Serie/alta`, `Tenant/stock_inicial_cargado` y `Tenant/fecha_stock_inicial`, usando `auditoria.services.registrar_cambio` en la misma transacción, sin secretos, sin `tenant_id` separado y sin duplicar la auditoría de stock de 008

**Checkpoint**: apps, tablas, migraciones, lectura de Excel, validaciones base, permisos, carga transaccional, consultas y auditoría listos; las historias pueden comenzar.

---

## Fase 3: US1 — Carga por Excel con asignación directa y auditoría (P1) 🎯 MVP

**Objetivo**: la cuenta del tenant carga un `.xlsx` válido, el sistema crea la carga y sus líneas,
las series nacen `ASIGNADA`, el stock se suma directamente al técnico sin tocar el stock general y
todo queda auditado; el detalle muestra totales y líneas agrupadas por técnico.

**Prueba independiente**: autenticado como tenant, cargar un `.xlsx` con una serie del material
seriado para `LA0001`, 10 unidades del no seriado para `LA0001` y 5 para `LA0002`; verificar el
`302` al detalle, la carga con nombre y hash, 2 técnicos/3 líneas/1 serie/15 de cantidad, el stock
del técnico y la serie `ASIGNADA`; comprobar que `StockGeneral` no cambió, que la auditoría contiene
usuario/fecha/archivo/hash y que otro tenant recibe `404`.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T025 [P] [US1] Pruebas de contrato de `GET /stock-inicial/` en `tests/contract/test_stock_inicial_estado_http.py`: `200` sin carga con las dos opciones y aviso de carga única; `200` con carga con fecha, método, totales y enlaces a detalle/edición; `403` para Admin/Almacén y tenant suspendido; `302` sin sesión; `405` para métodos no permitidos
- [ ] T026 [P] [US1] Pruebas de contrato de `POST /stock-inicial/validar-excel/` en `tests/contract/test_stock_inicial_validacion_http.py`: `200` con `data-valido`, `data-filas-validas`, `data-filas-error`, `data-total-tecnicos`, `data-total-series`, `data-total-cantidad`, tabla de errores y resumen de líneas; `400` para archivo ausente, no `.xlsx`, columna faltante, sin filas y corrupto; `403`; `405`; y conteos de tablas sin cambios
- [ ] T027 [P] [US1] Pruebas de contrato de `POST /stock-inicial/cargar-excel/` en `tests/contract/test_stock_inicial_carga_http.py`: `302` a `/stock-inicial/<id>/` con archivo válido; `400` con errores por fila y valores conservados; `403`; `405`; y revalidación del archivo aunque la vista previa haya sido válida
- [ ] T028 [P] [US1] Pruebas de integración de **CA-01** en `tests/integration/test_stock_inicial_carga.py`: `test_carga_excel_exitosa_marca_tenant_y_crea_carga` con carga, líneas, totales, `Tenant.stock_inicial_cargado=True`, `fecha_stock_inicial` y redirección
- [ ] T029 [P] [US1] Pruebas de integración de **CA-08** en `tests/integration/test_stock_inicial_stock.py`: `test_asignacion_directa_stock_tecnico_sin_stock_general`, incremento una sola vez por material, series `ASIGNADA`, lote del catálogo y `StockGeneral` sin cambios en carga y edición
- [ ] T030 [P] [US1] Pruebas de integración de **CA-09** en `tests/integration/test_stock_inicial_auditoria.py`: `test_auditoria_carga_registra_usuario_fecha_archivo_y_hash`, un `LineaStockInicial/alta` por línea, un `Serie/alta` por serie, dos registros de `Tenant`, registros de `StockTecnico/cantidad`, ausencia de secretos y de `tenant_id` separado

### Implementación de US1

- [ ] T031 [US1] Implementar `CargaExcelForm` en `stock_inicial/forms.py` con `archivo = FileField()` obligatorio, `accept=".xlsx"`, mensaje "Debes seleccionar un archivo Excel" y exclusión de `tenant`, `tenant_id`, `region`, `region_id`, `almacen_id`, `lote`, `descripcion` y `es_seriado`
- [ ] T032 [US1] Implementar en `stock_inicial/views.py` `estado_stock_inicial`, `validar_excel` y `cargar_excel` con `@login_required`, validación de rol/tenant, CSRF, `200`/`302`/`400`/`403`/`405` y los mensajes de `contracts/http-endpoints.md`; la lógica de negocio permanece en `services.py`
- [ ] T033 [US1] Implementar en `stock_inicial/views.py` `detalle_stock_inicial` con `obtener_detalle_carga`, precarga `lineas__tecnico`, `lineas__material` y `lineas__serie`, respuesta `404` para carga propia inexistente o de otro tenant, y `403`/`405` según contrato
- [ ] T034 [US1] Crear `stock_inicial/urls.py` con `GET /stock-inicial/`, `POST /stock-inicial/validar-excel/`, `POST /stock-inicial/cargar-excel/` y `GET /stock-inicial/<int:carga_id>/`, sin rutas de borrado ni de reinicio por HTTP
- [ ] T035 [US1] Crear `templates/stock_inicial/estado.html` y `templates/stock_inicial/carga_excel.html` con aviso de carga única, opciones Excel/formulario, formulario `multipart/form-data`, errores claros y estados cargado/no cargado
- [ ] T036 [US1] Crear `templates/stock_inicial/_resultado_validacion.html` y `templates/stock_inicial/_resumen_carga.html` con los atributos `data-*`, tabla de errores, resumen de líneas válidas, escape de valores y sin datos de otros tenants
- [ ] T037 [US1] Crear `templates/stock_inicial/detalle.html` con fecha, método, región, nombre y hash del archivo, totales y líneas agrupadas por técnico (NIF, nombre, material, descripción, lote, serie o cantidad) y enlace a edición
- [ ] T038 [US1] Conectar HTMX en `templates/stock_inicial/carga_excel.html`: `hx-post="/stock-inicial/validar-excel/"`, `hx-target="#resultado-validacion"`, `hx-encoding="multipart/form-data"`, `hx-indicator` y `hx-disabled-elt` mientras el POST está en curso; habilitar "Cargar" solo con `data-valido="true"`

**Checkpoint**: US1 funcional e independiente; el tenant carga y consulta el stock inicial por Excel con stock y auditoría.

---

## Fase 4: US2 — Validación y rechazo de datos inválidos (P2)

**Objetivo**: todo técnico, material, serie y cantidad se valida antes de escribir; los datos
inválidos se rechazan con los mensajes exactos, la serie existente no revela el tenant y la vista
previa muestra todos los errores por fila sin escribir nada.

**Prueba independiente**: validar y cargar un Excel con `LA9999` y ver "El técnico no existe en este
tenant"; repetir con un material inexistente; repetir con la misma serie dos veces y ver "La serie
está duplicada en la carga"; usar una serie de otro tenant y ver "La serie ya está registrada en el
sistema" sin datos del propietario; comprobar que no se crea ninguna carga, línea, serie, stock ni
auditoría.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T039 [P] [US2] Pruebas de integración de **CA-03** en `tests/integration/test_stock_inicial_carga.py`: `test_tecnico_no_existe_rechaza_carga` con `LA9999`, NIF con formato inválido y técnico de otro tenant; no se crea nada
- [ ] T040 [P] [US2] Pruebas de integración de **CA-04** en `tests/integration/test_stock_inicial_carga.py`: `test_material_no_existe_rechaza_carga` con código inexistente, material con espacios y material de otro tenant; no se crea nada
- [ ] T041 [P] [US2] Pruebas de integración de **CA-05** en `tests/integration/test_stock_inicial_carga.py`: `test_serie_duplicada_en_carga_rechaza` marcando la segunda y posteriores ocurrencias y sin crear líneas ni series
- [ ] T042 [P] [US2] Pruebas de integración de **CA-06** en `tests/integration/test_stock_inicial_carga.py`: `test_serie_ya_existe_rechaza_sin_revelar_tenant` con serie propia y de otro tenant, mensaje idéntico y sin datos del propietario
- [ ] T043 [P] [US2] Pruebas de contrato de errores por fila en `tests/contract/test_stock_inicial_validacion_http.py`: `data-fila` correcto desde 2, `data-campo` correcto (`tecnico`, `material`, `serie`, `cantidad`, `tipo`, `archivo`), `data-mensaje` exacto, varios errores por fila, errores de archivo con `data-fila="0"` y respuesta sin `tenant_id`, `region_id`, stock ni creador
- [ ] T044 [P] [US2] Pruebas unitarias de mensajes exactos en `tests/unit/test_stock_inicial_validaciones.py`: seriado sin serie, no seriado con serie, cantidad no numérica, cantidad `<= 0`, NIF inválido, material inexistente y serie con formato inválido

### Implementación de US2

- [ ] T045 [US2] Extender `normalizar_filas_stock_inicial` y `validar_filas_stock_inicial` en `stock_inicial/services.py`: conservar el número de fila del Excel, marcar la segunda y posteriores ocurrencias de una serie duplicada, usar `series.services.series_existentes` en una sola consulta, uniformar el mensaje de serie existente, ignorar filas vacías y devolver todos los errores encontrados sin escribir en la base
- [ ] T046 [US2] Extender `leer_excel_stock_inicial` en `stock_inicial/excel.py` para reportar errores de archivo con `data-fila=0` y `data-campo="archivo"`, y `validar_excel_stock_inicial` en `stock_inicial/services.py` para conservar filas de origen y errores parciales
- [ ] T047 [US2] Actualizar `validar_excel` y `cargar_excel` en `stock_inicial/views.py` para renderizar `400` con todos los errores por fila, valores conservados y el resumen exacto, sin revelar datos internos ni de otros tenants
- [ ] T048 [US2] Actualizar `CargaExcelForm` y `templates/stock_inicial/_resultado_validacion.html` en `stock_inicial/forms.py` y `templates/stock_inicial/` para mapear los errores de validación a los mensajes exactos y escapar los valores de celda

**Checkpoint**: US2 funcional e independiente; los datos inválidos se rechazan con mensajes exactos y sin escrituras.

---

## Fase 5: US3 — Carga por formulario (P3)

**Objetivo**: el tenant carga el stock inicial mediante un formulario con secciones por técnico;
varias secciones y líneas se guardan como una sola carga, con las mismas validaciones, stock directo
y auditoría que el Excel.

**Prueba independiente**: abrir `/stock-inicial/formulario/`, cargar una serie para `LA0001`, 7
unidades no seriadas para `LA0001` y 3 para `LA0002`, guardar y comprobar una sola carga
`FORMULARIO` sin nombre ni hash, series `ASIGNADA`, stock del técnico correcto, stock general sin
cambios y tenant marcado como cargado.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T049 [P] [US3] Pruebas de contrato de `GET/POST /stock-inicial/formulario/` en `tests/contract/test_stock_inicial_carga_http.py`: `200` con secciones por técnico y selectores; `302` al detalle con formulario válido; `400` con errores y valores conservados; `409` si ya está cargado; `403`; `405`; y rechazo de `tenant_id`/`region_id`/`lote`/`descripcion`/`es_seriado` enviados por el cliente
- [ ] T050 [P] [US3] Pruebas de integración de **CA-02** en `tests/integration/test_stock_inicial_carga.py`: `test_carga_formulario_exitosa` con `metodo=FORMULARIO`, `archivo_nombre=""`, `archivo_hash=""`, series `ASIGNADA`, stock del técnico y tenant marcado
- [ ] T051 [P] [US3] Pruebas de integración de varias secciones en `tests/integration/test_stock_inicial_carga.py`: `test_carga_formulario_con_varios_tecnicos_es_una_sola_carga`, una sola `CargaStockInicial`, líneas por técnico y totales correctos
- [ ] T052 [P] [US3] Pruebas unitarias del formulario en `tests/unit/test_stock_inicial_servicios.py`: secciones sin técnico, sin líneas, material seriado sin series, no seriado con series, series separadas por saltos/comas/espacios y cantidades inválidas

### Implementación de US3

- [ ] T053 [US3] Implementar en `stock_inicial/forms.py` `StockInicialForm`, `SeccionTecnicoForm` y el formset de líneas con `tecnico_id`, `material_id`, `series` y `cantidad`; excluir `tenant`, `region`, `almacen`, `lote`, `descripcion`, `es_seriado` y `creado_por`
- [ ] T054 [US3] Extender `validar_formulario_stock_inicial` en `stock_inicial/services.py` para convertir secciones y líneas en `FilaExcel` lógicas con `numero_fila=None`, resolver técnico por `id` y tenant, material por `id` global, dividir series por saltos/comas/espacios y aplicar la misma validación y agrupación que el Excel
- [ ] T055 [US3] Implementar en `stock_inicial/views.py` `formulario_stock_inicial` (`GET/POST`) con `@login_required`, rol/tenant, `302` al detalle, `400`/`403`/`409`/`405` y conservación de valores; agregar `GET/POST /stock-inicial/formulario/` en `stock_inicial/urls.py`
- [ ] T056 [US3] Crear `templates/stock_inicial/carga_formulario.html` y `templates/stock_inicial/_linea_form.html` con secciones por técnico, selector de técnico activo, selector de material, tipo y lote de solo lectura, campo `series` para seriados, campo `cantidad` para no seriados, botones Agregar/Quitar línea y aviso de carga única
- [ ] T057 [US3] Conectar el selector de material a la búsqueda HTMX existente de 002 (`/materiales/buscar/`) en `templates/stock_inicial/_linea_form.html`, sin aceptar `tenant_id` ni `region_id`, y mostrar el progreso con `hx-indicator`/`hx-disabled-elt` al guardar

**Checkpoint**: US3 funcional e independiente; Excel y formulario producen el mismo tipo de carga.

---

## Fase 6: US4 — Carga única, transaccionalidad, concurrencia y acceso (P4)

**Objetivo**: el stock inicial se carga una sola vez por tenant; un error en cualquier fila revierte
todo; dos cargas concurrentes dejan una sola carga; y solo `USUARIO_TENANT` con tenant activo opera,
mientras Admin/Almacén reciben `403` y otro tenant recibe `404`.

**Prueba independiente**: completar una carga y comprobar que el segundo intento responde `409` con
"El stock inicial ya fue cargado para este tenant" sin crear nada; preparar 100 filas válidas y 1 con
técnico inexistente y comprobar que no queda ninguna carga, línea, serie, stock ni auditoría; lanzar
dos cargas concurrentes del mismo tenant y verificar una sola; y probar la matriz de permisos y
aislamiento en todas las rutas existentes.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T058 [P] [US4] Pruebas de integración de **CA-07** en `tests/integration/test_stock_inicial_carga.py`: `test_segunda_carga_rechazada_por_flag_y_por_restriccion`, con flag `True` y con `CargaStockInicial` existente, respuesta `409` y sin cambios de stock ni auditoría
- [ ] T059 [P] [US4] Pruebas de integración de **CA-10** en `tests/integration/test_stock_inicial_carga.py`: `test_error_en_una_fila_no_carga_nada` con 100 filas válidas y 1 inválida, y fallo simulado de auditoría/stock que revierte carga, líneas, series, stock, tenant y auditoría
- [ ] T060 [P] [US4] Pruebas de integración de concurrencia en `tests/integration/test_stock_inicial_concurrencia.py`: dos cargas concurrentes del mismo tenant crean una sola; dos series concurrentes crean una sola y la perdedora recibe el mensaje uniforme; la edición concurrente no deja saldos parciales
- [ ] T061 [P] [US4] Pruebas de integración de aislamiento y RLS en `tests/integration/test_stock_inicial_aislamiento.py`: carga/líneas de otro tenant responden `404`; Admin y Almacén reciben `403`; tenant suspendido recibe `403`; `tenant_id`/`region_id` forzados se ignoran; y, si la infraestructura RLS de 001 existe, las políticas impiden leer filas de otro tenant
- [ ] T062 [P] [US4] Pruebas de contrato de la matriz de permisos en `tests/contract/test_stock_inicial_permisos_http.py`: todas las rutas de estado, validación, carga y formulario para `ADMIN_PLATAFORMA`, `RESPONSABLE_ALMACEN`, `USUARIO_TENANT`, tenant suspendido y anónimo; `403`/`404`/`302`/`405` según contrato y sin filtraciones de datos

### Implementación de US4

- [ ] T063 [US4] Endurecer `cargar_stock_inicial` en `stock_inicial/services.py`: bloqueo de `Tenant` con `select_for_update`, relectura del flag y de la carga dentro de la transacción, traducción de `IntegrityError` de `CargaStockInicial.tenant` a `StockInicialYaCargado` y de `Serie.numero` a `SerieYaExiste`, y rollback completo ante cualquier fallo de fila, serie, stock o auditoría
- [ ] T064 [US4] Endurecer las vistas de `stock_inicial/views.py` para validar rol y tenant antes de llamar al servicio, mapear `StockInicialYaCargado` a `409`, `PermisoDenegado` a `403`, `TenantSuspendido` a `403` y `StockInicialNoExiste` a `404`, sin revelar el propietario y con `405` para métodos no permitidos
- [ ] T065 [US4] Verificar y blindar en `stock_inicial/forms.py` y `stock_inicial/views.py` que `tenant_id`, `region_id`, `almacen_id`, `creado_por`, `lote`, `descripcion` y `es_seriado` enviados por el cliente se ignoran y que el tenant/región salen solo de `request.usuario` y `tenant.region`
- [ ] T066 [US4] Confirmar en `stock_inicial/services.py` que 005 no escribe `stock.StockGeneral` y que todo cambio de `StockTecnico` pasa por `stock.services.incrementar_stock_tecnico`/`decrementar_stock_tecnico` de 008; si el servicio de 008 no bloquea o no audita, detenerse y reportar la dependencia

**Checkpoint**: US4 funcional e independiente; la carga es única, atómica, resistente a concurrencia y correctamente autorizada.

---

## Fase 7: US5 — Edición transaccional del stock inicial (P5)

**Objetivo**: después de la carga, el tenant corrige el stock inicial agregando series o cantidades,
eliminando líneas incorrectas y modificando cantidades no seriadas; todo el lote se aplica o se
revierte junto, ajusta el stock del técnico y deja auditoría completa.

**Prueba independiente**: completar una carga y abrir la edición; agregar `GHI123456789` para
`LA0001` y comprobar serie `ASIGNADA`, línea y stock +1; eliminar `ABC123456789` y comprobar baja de
línea/serie y stock −1 conservando la auditoría; cambiar una cantidad no seriada de 10 a 12 y
comprobar stock +2 y auditoría con 10/12; enviar un lote con una operación inválida y comprobar que
no se aplica ninguna.

### Pruebas de US5 (escribir primero, deben fallar)

- [ ] T067 [P] [US5] Pruebas de contrato de `GET/POST /stock-inicial/<id>/editar/` en `tests/contract/test_stock_inicial_edicion_http.py`: `200` con líneas agrupadas, cantidades editables solo en no seriadas y casilla eliminar; `302` al detalle con lote válido; `400` con rollback; `409` sin carga o serie creada en paralelo; `404` carga o línea ajena; `403`; `405`
- [ ] T068 [P] [US5] Pruebas de integración de **CA-11** en `tests/integration/test_stock_inicial_edicion.py`: `test_editar_agrega_serie_y_audita` con serie `ASIGNADA`, línea nueva, stock +1, lote del catálogo y auditoría `Serie/alta`/`LineaStockInicial/alta`
- [ ] T069 [P] [US5] Pruebas de integración de **CA-12** en `tests/integration/test_stock_inicial_edicion.py`: `test_editar_elimina_serie_y_audita` con baja de línea/serie, stock −1, auditoría que conserva los valores y `StockGeneral` sin cambios
- [ ] T070 [P] [US5] Pruebas de integración de **CA-13** en `tests/integration/test_stock_inicial_edicion.py`: `test_editar_modifica_cantidad_y_audita` con cantidad anterior/nueva, ajuste de stock por diferencia y rechazo de modificar una línea seriada
- [ ] T071 [P] [US5] Pruebas de integración de edición por lote en `tests/integration/test_stock_inicial_edicion.py`: `test_edicion_por_lote_es_todo_o_nada`, agregar no seriado sobre línea existente suma cantidad, serie que ya salió del técnico no se elimina, stock insuficiente no deja saldo negativo, lote vacío `400` y edición sin carga `409`
- [ ] T072 [P] [US5] Pruebas de auditoría de edición en `tests/integration/test_stock_inicial_auditoria.py`: `LineaStockInicial/alta`, `baja` y `cantidad`, `Serie/alta`/`baja`, `StockTecnico/cantidad` de 008, conservación de la auditoría tras borrar línea/serie y ausencia de secretos o `tenant_id` separado

### Implementación de US5

- [ ] T073 [US5] Implementar `aplicar_edicion_stock_inicial(carga, operaciones, actor)` en `stock_inicial/services.py`: validar cuenta y carga, exigir al menos una operación, bloquear `Tenant`, `CargaStockInicial` y líneas con `select_for_update` en orden de id, validar sin escribir `AGREGAR`/`ELIMINAR`/`MODIFICAR`, agrupar deltas por `(tecnico, material)`, aplicar stock con 008, crear/eliminar/modificar líneas y series, auditar cada cambio y revertir todo si falla una operación
- [ ] T074 [US5] Implementar en `stock_inicial/services.py` los envoltorios `agregar_linea_stock_inicial`, `eliminar_linea_stock_inicial` y `modificar_cantidad_stock_inicial`, cada uno como un lote de una operación; prohibir cambiar técnico, material, lote o serie de una línea existente
- [ ] T075 [US5] Implementar en `stock_inicial/forms.py` `EdicionStockInicialForm` y los formsets de líneas existentes/nuevas con `linea_id`, `eliminar`, `cantidad`, `tecnico_id`, `material_id`, `series` y `cantidad`; excluir `tenant`, `region`, `almacen`, `lote`, `descripcion`, `es_seriado` y `creado_por`
- [ ] T076 [US5] Implementar en `stock_inicial/views.py` `editar_stock_inicial` (`GET/POST`) con `@login_required`, rol/tenant, construcción del lote `AGREGAR`/`ELIMINAR`/`MODIFICAR`, `302` al detalle, `400`/`403`/`404`/`409`/`405` y conservación de valores
- [ ] T077 [US5] Agregar `GET/POST /stock-inicial/<int:carga_id>/editar/` en `stock_inicial/urls.py`, sin ruta de borrado de la carga ni del stock inicial
- [ ] T078 [US5] Crear `templates/stock_inicial/editar.html` con líneas agrupadas por técnico, cantidad editable solo en no seriadas, casilla eliminar, formulario de líneas nuevas por técnico, un solo botón "Guardar cambios" y aviso de que el lote es todo o nada

**Checkpoint**: US5 funcional e independiente; la edición es transaccional, ajusta stock y conserva auditoría.

---

## Fase 8: Reinicio controlado y pulido

**Propósito**: cerrar el reinicio de implementación, rendimiento, RLS, seguridad, documentación y
validación extremo a extremo.

- [ ] T079 [P] Escribir las pruebas de integración del reinicio en `tests/integration/test_stock_inicial_reinicio.py`: deshabilitado por defecto, solo `ADMIN_PLATAFORMA`, `--confirmar` obligatorio, borra carga/líneas/series y descuenta stock, conserva auditoría, falla si el stock o las series ya cambiaron y no tiene ruta HTTP
- [ ] T080 [P] Escribir las pruebas de rendimiento en `tests/integration/test_stock_inicial_rendimiento.py` con `django_assert_num_queries`: validación de 100 filas con una consulta de técnicos, una de materiales y una de series existentes; carga sin consultas por fila; detalle sin N+1; vista previa sin escrituras ni consultas por fila
- [ ] T081 Implementar `reiniciar_stock_inicial(tenant, actor)` en `stock_inicial/services.py`: exigir `settings.PERMITIR_REINICIO_STOCK_INICIAL is True`, actor `ADMIN_PLATAFORMA`, bloqueo de tenant/carga, validación de series `ASIGNADA` y stock suficiente, descuento con `decrementar_stock_tecnico`, auditoría de bajas/carga/tenant y limpieza de `stock_inicial_cargado`/`fecha_stock_inicial`
- [ ] T082 Crear `stock_inicial/management/commands/reiniciar_stock_inicial.py` con argumentos `--tenant`, `--usuario` y `--confirmar`, que sin `--confirmar` no ejecute nada y muestre la advertencia, y que no se registre en rutas HTTP ni en el Admin de Django
- [ ] T083 [P] Revisar y corregir las referencias documentales que contradigan 005 antes de cerrar: `04-contratos/excel-stock-inicial.md` (solo `.xlsx`, lote/descripción del catálogo), `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/plan.md`, `05-especificaciones/004-recojo-de-materiales/plan.md`, `research.md` y `data-model.md`, `06-plan-implementacion/desglose-tareas.md`, `03-reglas-de-dominio/series.md` y `03-reglas-de-dominio/stock.md`
- [ ] T084 [P] Verificar que no existe ninguna ruta de borrado ni de reinicio por HTTP en `stock_inicial/urls.py`, que `DELETE`/`PUT`/`PATCH` responden `405`, que no se crea superusuario de Django y que no se escriben contraseñas, tokens ni secretos en `auditoria.RegistroCambio`
- [ ] T085 Ejecutar `python manage.py makemigrations --check --dry-run` y `python manage.py migrate` sobre PostgreSQL; corregir cualquier migración pendiente en `tenants/migrations/` o `stock_inicial/migrations/`
- [ ] T086 Ejecutar la suite completa de `tests/unit/`, `tests/integration/` y `tests/contract/` sobre PostgreSQL con `pytest --cov=stock_inicial --cov-report=term-missing` y cerrar brechas hasta cubrir CA-01…CA-13 y los criterios de salida de `quickstart.md`
- [ ] T087 Ejecutar los escenarios manuales 1–20 de `05-especificaciones/005-stock-inicial-de-tecnicos/quickstart.md` contra PostgreSQL y registrar el resultado

---

## Dependencias y orden de ejecución

### Dependencias de fase

- **Setup (Fase 1)**: depende de 001, 002, 003, la app `series` de 004 y la parte fundacional de 008 implementadas.
- **Fundacional (Fase 2)**: depende del Setup y **bloquea todas las historias** (modelos, migraciones, lectura de Excel, validaciones base, permisos, carga transaccional, consultas y auditoría).
- **Historias (Fases 3–7)**: dependen de la Fase 2.
- **Reinicio y pulido (Fase 8)**: depende de todas las historias que se entreguen.

### Dependencias entre historias

- **US1 (P1)**: sin dependencias posteriores a la Fase 2; entrega el MVP.
- **US2 (P2)**: requiere US1 (vista previa y carga por Excel); endurece las validaciones y los mensajes.
- **US3 (P3)**: requiere US1 y US2 (validación común y renderizado de errores); reutiliza la misma lógica.
- **US4 (P4)**: requiere US1, US2 y US3 (rutas de carga y formulario para probar la matriz completa).
- **US5 (P5)**: requiere US1 y US2; comparte servicios y auditoría con US1–US4 y puede avanzar en paralelo con US4 si se coordinan `services.py`, `views.py` y `forms.py`.

### Dentro de cada historia

1. Pruebas primero y en rojo.
2. Servicio → formulario → vista → ruta → plantilla.
3. La carga, la edición y el reinicio se escriben en una sola transacción.
4. No se avanza con pruebas en rojo (constitución, puerta de pruebas).

### Oportunidades de paralelización

- Setup: T003–T006 en archivos distintos.
- Fundacional: T007–T009 y T015 son pruebas en archivos distintos; T010–T014 comparten modelos/migraciones y son secuenciales; T017–T024 comparten `stock_inicial/services.py` y deben serializarse.
- US1: T025–T030 son pruebas en archivos distintos; T035–T038 son plantillas distintas tras T032–T034.
- US2: T039–T044 son pruebas en archivos distintos; T045–T048 comparten `services.py`/`views.py`/`forms.py`/plantillas.
- US3: T049–T052 son pruebas en archivos distintos; T053–T057 comparten formulario, servicio, vista, ruta y plantilla.
- US4: T058–T062 son pruebas en archivos distintos; T063–T066 comparten `services.py`/`views.py`/`forms.py`.
- US5: T067–T072 son pruebas en archivos distintos; T073–T078 comparten `services.py`/`forms.py`/`views.py`/`urls.py`/plantilla.
- Reinicio y pulido: T079–T080 y T083–T084 son independientes; T081–T082 y T085–T087 cierran al final.

---

## Ejemplo de paralelización: US1

```bash
# Escribir primero todas las pruebas de US1 (archivos distintos):
Task: "Pruebas de contrato del estado en tests/contract/test_stock_inicial_estado_http.py"
Task: "Pruebas de contrato de la vista previa en tests/contract/test_stock_inicial_validacion_http.py"
Task: "Pruebas de contrato de la carga en tests/contract/test_stock_inicial_carga_http.py"
Task: "Pruebas de integración de CA-01 en tests/integration/test_stock_inicial_carga.py"
Task: "Pruebas de integración de CA-08 en tests/integration/test_stock_inicial_stock.py"
Task: "Pruebas de integración de CA-09 en tests/integration/test_stock_inicial_auditoria.py"

# Implementación paralelizable tras las vistas:
Task: "Plantilla de estado y carga en templates/stock_inicial/estado.html y carga_excel.html"
Task: "Parciales de validación y resumen en templates/stock_inicial/"
Task: "Plantilla de detalle en templates/stock_inicial/detalle.html"
```

## Ejemplo de paralelización: US2, US3, US4 y US5

```bash
# Con US1 y los servicios base listos, cuatro personas pueden avanzar:
Task: "Pruebas de CA-03…CA-06 y mensajes exactos"                     # US2
Task: "Pruebas de CA-02 y formulario por secciones"                    # US3
Task: "Pruebas de CA-07/CA-10, concurrencia y permisos"                # US4
Task: "Pruebas de CA-11…CA-13 y edición por lote"                      # US5

# Los archivos de prueba son distintos y pueden escribirse a la vez.
```

> Las tareas de implementación de US2–US5 comparten `stock_inicial/services.py`,
> `stock_inicial/views.py` y `stock_inicial/forms.py`; si se ejecutan en paralelo, coordinar esos
> archivos o serializar las tareas concretas.

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 (Setup).
2. Completar Fase 2 (Fundacional) — **crítica**.
3. Completar Fase 3 (US1).
4. **DETENERSE y VALIDAR**: carga por Excel, stock directo al técnico, series `ASIGNADA`,
   auditoría, detalle, `StockGeneral` sin cambios y aislamiento por tenant.
5. Desplegar/demostrar si está listo.

> US1 ya entrega el valor central: el tenant puede cargar una sola vez el stock inicial de sus
> técnicos desde el formato Excel de Lari, con stock y auditoría.

### Entrega incremental

1. Setup + Fundacional → app, tablas, lectura de Excel, validaciones base, permisos y auditoría.
2. US1 → carga por Excel, stock directo, auditoría y detalle (MVP).
3. US2 → validación de técnicos, materiales, series y cantidades con mensajes exactos.
4. US3 → formulario con secciones por técnico como alternativa al Excel.
5. US4 → carga única, atomicidad, concurrencia, permisos y aislamiento.
6. US5 → edición transaccional por lote con auditoría.
7. Reinicio y pulido → comando de implementación, rendimiento, RLS, documentación y escenarios.

### Estrategia de equipo en paralelo

1. Todo el equipo completa Setup + Fundacional.
2. Al terminar la Fase 2:
   - Persona A: US1 (MVP).
   - Persona B: prepara pruebas de US2 y US3.
3. Tras US1:
   - Persona A: US2.
   - Persona B: US3.
   - Persona C: US5 (edición) con coordinación en servicios.
4. US4 cierra la matriz de permisos, concurrencia y carga única cuando las rutas de US3 existan.
5. La Fase 8 se ejecuta al final, con la suite completa en verde.

---

## Notas

- [P] tasks = archivos distintos, sin dependencias pendientes.
- [Story] label mapea cada tarea a su historia para trazabilidad.
- Cada historia es independiente y testeable; US1 es el MVP.
- Verificar que las pruebas fallan antes de implementar.
- Commit después de cada tarea o grupo lógico.
- Detenerse en cualquier checkpoint para validar la historia de forma independiente.
- Evitar tareas vagas, conflictos en el mismo archivo y dependencias entre historias que rompan la independencia.
- 005 no crea una tabla de series, no escribe `StockGeneral`, no expone el reinicio por HTTP y no crea superusuario de Django.
