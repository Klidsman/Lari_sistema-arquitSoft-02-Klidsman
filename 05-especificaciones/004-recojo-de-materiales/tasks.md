---
description: "Lista de tareas para la implementación de 004 Recojo de materiales"
---

# Tareas: 004 Recojo de materiales

**Entrada**: Documentos de diseño en `05-especificaciones/004-recojo-de-materiales/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`, `tenants.Region`,
`tenants.Almacen`, `tenants.Tenant`, `ContextoUsuarioMiddleware` y
`auditoria.RegistroCambio`/`registrar_cambio`), **spec 002 implementada** (`materiales.Material`) y
**parte fundacional de la spec 008 implementada** (`stock.StockGeneral` y
`stock.services.incrementar_stock_general`). La spec 003 (técnicos) **no** es prerrequisito. Las
tareas de 001, 002 y 008 no se repiten aquí.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige
al menos una prueba por criterio de aceptación CA-01…CA-09. Cada historia escribe primero sus
pruebas, las ve fallar y luego implementa.

**Organización**: `spec.md` no define historias de usuario propias; se derivan cuatro historias a
partir de los criterios de aceptación y de las dependencias técnicas, para permitir entregas
incrementales e independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario asociada (`US1`…`US4`)
- Todas las rutas de archivo son relativas a la raíz del repositorio

## Origen de las historias de usuario

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Alta y consulta de recojos con stock y auditoría | P1 | CA-01, CA-02, CA-09; RF-14, RF-15, RF-16; listado y detalle del contrato |
| US2 — Normalización y validación de series | P2 | CA-03, CA-04, CA-05, CA-06; RF-18 y parte de RF-19 |
| US3 — Regla todo o nada y concurrencia | P3 | CA-07; RF-19 y RNF de integridad |
| US4 — Vista previa de series en tiempo real | P4 | CA-08; RF-17 |

## Convenciones de rutas

Proyecto Django único en la raíz: las apps nuevas son `series/` y `recojos/`; las plantillas viven
en `templates/recojos/`; las pruebas en `tests/{unit,integration,contract}/`. Las apps `acceso`,
`tenants`, `auditoria` (001), `materiales` (002) y `stock` (008) son propiedad de sus specs y no se
duplican.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: crear las apps `series` y `recojos`, conectarlas al proyecto y preparar el entorno de
pruebas.

- [ ] T001 Verificar los prerrequisitos en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py`, `materiales/models.py`, `stock/models.py`, `stock/services.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware` activo, roles `ADMIN_PLATAFORMA`/`USUARIO_TENANT`/`RESPONSABLE_ALMACEN`, `materiales.Material` con `es_seriado` y `lote`, `stock.StockGeneral` con `UniqueConstraint(tenant, material)` y `stock.services.incrementar_stock_general` importable; detenerse y reportar si falta alguno
- [ ] T002 Crear la app Django `series` con `series/__init__.py`, `series/apps.py`, `series/migrations/__init__.py` y registrarla en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T003 Crear la app Django `recojos` con `recojos/__init__.py`, `recojos/apps.py`, `recojos/migrations/__init__.py` y registrarla en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T004 [P] Agregar `SERIE_LONGITUD = 12` y `SERIE_PATRON = r"^[A-Z0-9]{12}$"` en `config/settings/base.py`, con lectura opcional desde variables de entorno
- [ ] T005 [P] Incluir `recojos/urls.py` desde `config/urls.py` con el prefijo `/recojos/` (el archivo se crea en T028)
- [ ] T006 [P] Extender `conftest.py` con fixtures sobre PostgreSQL: `region`, `almacen`, `tenant`, `otro_tenant`, `tenant_suspendido`, `usuario_tenant`, `usuario_admin`, `usuario_almacen`, `material_seriado`, `material_no_seriado`, `serie_existente`, `recojo` y `registro_cambios`
- [ ] T007 [P] Agregar el enlace de navegación a Recojos en `templates/base.html`, visible solo para `USUARIO_TENANT` y con tenant activo

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelos, migraciones, normalización, validaciones base, alcance, auditoría y registro
de movimientos que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

- [ ] T008 Implementar `EstadoSerie` (`DISPONIBLE`, `RESERVADA`, `ASIGNADA`, `INSTALADA`, `INACTIVA`) y `Serie` en `series/models.py`: `numero = CharField(max_length=12, unique=True)`, `tenant = ForeignKey("tenants.Tenant", on_delete=PROTECT, related_name="series")`, `region = ForeignKey("tenants.Region", on_delete=PROTECT, related_name="series")`, `material = ForeignKey("materiales.Material", on_delete=PROTECT, related_name="series")`, `lote = CharField(max_length=50, blank=True, default="")`, `estado = CharField(max_length=10, choices=EstadoSerie.choices, default=DISPONIBLE)`, `tecnico` FK `tecnicos.Tecnico` `PROTECT` `null=True` `related_name="series"`, `asignada_en = DateTimeField(null=True, blank=True)`, `creado_por`/`actualizado_por` FK `PROTECT` a `AUTH_USER_MODEL` (`related_name="+"`), `creado_en = auto_now_add`, `actualizado_en = auto_now`; `Meta.ordering=["numero"]`, `CheckConstraint(Q(numero__regex=r"^[A-Z0-9]{12}$"), name="serie_formato")`, `CheckConstraint(Q(estado__in=["DISPONIBLE","RESERVADA","ASIGNADA","INSTALADA"]), name="serie_estado_valido")`, `CheckConstraint` de coherencia `serie_tecnico_coherente_estado`, `Index(["tenant","estado"])`, `Index(["tenant","material"])`, `Index(["tecnico","estado"])` e `Index(["tecnico","material"])`
- [ ] T009 Generar y revisar `series/migrations/0001_initial.py`, aplicar con `migrate` y no crear series ni datos maestros por migración; `tenants.Tenant`, `tenants.Region` y `materiales.Material` deben existir antes
- [ ] T010 Implementar `Recojo` en `recojos/models.py`: `tenant = ForeignKey("tenants.Tenant", on_delete=PROTECT, related_name="recojos")`, `region = ForeignKey("tenants.Region", on_delete=PROTECT, related_name="recojos")`, `fecha = DateField()`, `creado_por` FK `PROTECT` `related_name="recojos_creados"`, `creado_en = auto_now_add`; `Meta.ordering=["-fecha","-id"]` e índices `(tenant, fecha)` y `(region, fecha)`
- [ ] T011 Implementar `LineaRecojo` en `recojos/models.py`: `tenant` FK `PROTECT` `related_name="lineas_recojo"`, `recojo` FK `Recojo` `PROTECT` `related_name="lineas"`, `material` FK `"materiales.Material"` `PROTECT` `related_name="lineas_recojo"`, `lote = CharField(max_length=50, blank=True, default="")`, `serie = OneToOneField("series.Serie", null=True, blank=True, on_delete=PROTECT, related_name="linea_recojo")`, `cantidad = IntegerField(default=0)`; `CheckConstraint(Q(serie__isnull=False) | Q(cantidad__gt=0), name="linea_recojo_serie_o_cantidad")`, `CheckConstraint(Q(serie__isnull=True) | Q(cantidad=1), name="linea_recojo_serie_cantidad_uno")`, `CheckConstraint(Q(cantidad__gte=0), name="linea_recojo_cantidad_no_negativa")`, `Index(["recojo","material"])` e `Index(["tenant","material"])`
- [ ] T012 Generar y revisar `recojos/migrations/0001_initial.py`, aplicar con `migrate` y no crear recojos, líneas ni series por migración; depende de T009 y T011
- [ ] T013 Implementar en `series/services.py` las excepciones `SerieInvalida`, `SerieDuplicada` y `SerieYaExiste`, y las funciones `normalizar_numero(numero)` (elimina todos los espacios en blanco con `re.sub(r"\s+", "")` y aplica `upper()`) y `validar_numero(numero)` (usa `settings.SERIE_PATRON`; mensaje "La serie debe tener 12 caracteres alfanuméricos")
- [ ] T014 Implementar en `series/services.py` `series_existentes(numeros)` con una sola consulta `Serie.objects.filter(numero__in=numeros)` y `crear_serie(tenant, region, material, numero, lote, actor, estado=EstadoSerie.DISPONIBLE, tecnico=None, asignada_en=None)` que normaliza, valida, crea con el estado y la custodia recibidos (por defecto `DISPONIBLE` sin técnico) y no captura `IntegrityError` (la capa de recojos la traduce); 005 pasa `EstadoSerie.ASIGNADA` con `tecnico`/`asignada_en`
- [ ] T015 Implementar en `recojos/services.py` las excepciones `ValidacionRecojo`, `RecojoInvalido`, `MaterialNoValido`, `PermisoDenegado`, `NoEncontrado`, `TenantSuspendido`, `RegionIncorrecta` y `RecojoNoEncontrado`, el tipo `ResultadoValidacion`, y las funciones `validar_cuenta_tenant(actor)` (solo `USUARIO_TENANT` activo, tenant `ACTIVO`, mensajes "No tienes permiso para registrar recojos"/"El tenant está suspendido"), `validar_region_tenant(tenant)` ("La región del tenant no tiene almacén configurado") y `obtener_recojo(tenant, recojo_id)` (filtra por tenant; ajeno o inexistente → "El recojo no existe")
- [ ] T016 Implementar en `recojos/services.py` `normalizar_lineas(datos)` y `validar_recojo_previo(tenant, datos)`: al menos una línea ("El recojo debe tener al menos una línea"), material existente ("El material no existe en el catálogo"), material seriado exige series con cantidad 1, material no seriado exige `cantidad > 0` y no admite series, normalización y validación de formato con `series.services`, y expansión a una línea por serie; devuelve `ResultadoValidacion` sin escribir en la base
- [ ] T017 Implementar en `recojos/services.py` `auditar_alta_recojo(recojo, actor)` que llama a `auditoria.services.registrar_cambio` con `entidad="Recojo"`, `campo="alta"` y `valor_nuevo` con fecha ISO, región, número de líneas, número de series y suma de cantidades no seriadas; sin secretos ni `tenant_id` separado
- [ ] T018 Implementar la integración con la inmutabilidad del tipo de material: `materiales_tiene_movimientos(material)` en `recojos/services.py` (consulta `LineaRecojo`, `Serie` y `stock.StockGeneral` del material) y registrarla desde `recojos/apps.py` (`ready()`) mediante `materiales.services.registrar_verificacion_movimientos`; si la función de registro no existe, detenerse y reportar

**Checkpoint**: apps, tablas, normalización, validaciones base, alcance, auditoría y registro de movimientos listos; las historias pueden comenzar.

---

## Fase 3: US1 — Alta y consulta de recojos con stock y auditoría (P1) 🎯

**Objetivo**: la cuenta del tenant registra un recojo con varias líneas seriadas y/o no seriadas,
siempre en la región de su tenant; las series se crean `DISPONIBLE`, el stock general se incrementa
por material y el alta queda auditada en la misma transacción; el listado y el detalle muestran solo
recojos del tenant.

**Prueba independiente**: autenticado como tenant, crear un recojo con 3 series válidas de un
material seriado y 25 unidades de uno no seriado; verificar el detalle, el incremento de stock por
material, las series `DISPONIBLE` con tenant/región correctos y la auditoría; abrir el recojo desde
otro tenant y recibir `404`; entrar como Administrador y Responsable de almacén y recibir `403`;
forzar `tenant_id`/`region_id` y comprobar que se ignoran.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T019 [P] [US1] Pruebas de contrato de `GET/POST /recojos/nuevo/` en `tests/contract/test_recojo_alta_http.py`: `302` al detalle con fecha válida, serie válida y cantidad no seriada; fecha ausente `400` "La fecha es obligatoria"; sin líneas `400` "El recojo debe tener al menos una línea"; material inexistente `400`; seriado sin series `400` "Debe indicar al menos una serie"; no seriado con `cantidad<=0` `400`; `tenant_id`/`region_id` forzados ignorados; Administrador/Responsable `403`; tenant suspendido `403`; `PUT`/`PATCH`/`DELETE` `405`
- [ ] T020 [P] [US1] Pruebas de contrato de `GET /recojos/` y `GET /recojos/<id>/` en `tests/contract/test_recojo_lista_detalle_http.py`: `200` con fecha, identificador, líneas, total de series y total de cantidad; orden por fecha e id descendente; paginación de 50; detalle con tenant, región y líneas; recojo de otro tenant `404` "El recojo no existe"; Administrador/Responsable `403`; métodos no permitidos `405`
- [ ] T021 [P] [US1] Pruebas de integración del alta seriada en `tests/integration/test_recojo_alta.py`: tenant y región tomados del actor, series creadas `DISPONIBLE`, lote copiado, stock incrementado una vez por material, auditoría `Recojo/alta` con totales y `StockGeneral/cantidad`, normalización previa al guardado y ausencia de auditoría cuando falla la validación
- [ ] T022 [P] [US1] Pruebas de integración de materiales no seriados en `tests/integration/test_recojo_stock.py`: línea con `serie=NULL` y `cantidad>0`, sin series creadas, stock general incrementado por la cantidad exacta y `total_series=0` en el detalle
- [ ] T023 [P] [US1] Pruebas de integración de aislamiento y región en `tests/integration/test_recojo_aislamiento.py`: la región se fija desde `tenant.region` aunque se envíe otra; un recojo de otro tenant no se lista ni se abre (`404`); el listado no muestra series ni stock de otros tenants; Administrador/Responsable no operan

### Implementación de US1

- [ ] T024 [US1] Implementar en `recojos/forms.py` `RecojoForm` (`fecha` con valor inicial hoy) y `LineaRecojoForm`/formset con `material_id`, `series` y `cantidad`, excluyendo `tenant`, `tenant_id`, `region`, `region_id`, `almacen` y `almacen_id`; mostrar los mensajes exactos del contrato
- [ ] T025 [US1] Implementar `crear_recojo(datos, actor)` en `recojos/services.py`: valida cuenta y región, normaliza y valida líneas, crea en `transaction.atomic` el `Recojo`, las `LineaRecojo` y las `Serie` (`DISPONIBLE`), agrupa por material y llama una vez a `stock.services.incrementar_stock_general(tenant, material, cantidad, actor)` por material, y audita el alta; no acepta tenant/región del cliente
- [ ] T026 [US1] Implementar `listar_recojos(tenant)` (filtra por tenant, ordena por fecha/id descendente y anota `total_lineas`, `total_series` y `total_cantidad`), `obtener_detalle_recojo(tenant, recojo_id)` (precarga `lineas__material` y `lineas__serie`) y `totales_recojo(recojo)` en `recojos/services.py`
- [ ] T027 [US1] Implementar las vistas `lista_recojos` (50 por página), `detalle_recojo` y `crear_recojo` (`GET/POST`) en `recojos/views.py` con `@login_required`, validación de rol/tenant, `404`/`403`/`400`/`405` y los mensajes del contrato; la lógica de negocio permanece en `services.py`
- [ ] T028 [US1] Crear `recojos/urls.py` con `GET /recojos/`, `GET/POST /recojos/nuevo/` y `GET /recojos/<int:id>/`, sin rutas de edición ni borrado
- [ ] T029 [US1] Crear `templates/recojos/recojos_lista.html` (fecha, identificador, líneas, totales y enlace al detalle; paginación de 50) y `templates/recojos/recojo_form.html` (fecha, líneas dinámicas, botón Agregar línea y `hx-disabled-elt` en Guardar)
- [ ] T030 [US1] Crear `templates/recojos/recojo_detalle.html` con identificador, fecha, tenant, región, total de series, total de cantidad y tabla de líneas (material, descripción, lote, serie o cantidad), sin botones de edición ni borrado
- [ ] T031 [US1] Crear `templates/recojos/_linea_form.html` con selector de material por búsqueda HTMX sobre `/materiales/buscar/`, tipo y lote de solo lectura, campo `series` para seriados y `cantidad` para no seriados, y el contenedor de vista previa que usará US4

**Checkpoint**: US1 funcional e independiente; el tenant registra y consulta recojos, con stock y auditoría.

---

## Fase 4: US2 — Normalización y validación de series (P2)

**Objetivo**: toda serie se normaliza (mayúsculas y sin espacios) y se valida antes de escribir;
los formatos incorrectos, los duplicados dentro del recojo y las series ya existentes se informan
con los mensajes exactos, sin revelar el tenant de una serie ajena.

**Prueba independiente**: ingresar `abc123456789` y `" abc 123456789 "` y ver `ABC123456789`;
ingresar `ABC123` y ver "La serie debe tener 12 caracteres alfanuméricos"; repetir una serie en el
mismo recojo y ver "La serie está duplicada en el recojo"; usar una serie de otro tenant y ver "La
serie ya está registrada en el sistema" sin datos del propietario; verificar que nada se guarda.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T032 [P] [US2] Pruebas unitarias de normalización y reglas de línea en `tests/unit/test_recojo_validaciones.py`: `" abc 123456789 "` → `ABC123456789`; `ABC123`, `ABC12345678`, `ABC1234567890` y `ABC-12345678` inválidos; seriado con cantidad distinta de 1; no seriado sin cantidad o con series; material inexistente
- [ ] T033 [P] [US2] Pruebas unitarias de `series.services` en `tests/unit/test_series_servicios.py`: normalización idempotente, validación con `SERIE_PATRON`, `series_existentes` en una sola consulta, `crear_serie` con estado `DISPONIBLE` por defecto y sin técnico, `crear_serie` con `EstadoSerie.ASIGNADA` y custodia explícita, coherencia estado/técnico/fecha e `IntegrityError` no capturado
- [ ] T034 [P] [US2] Pruebas de restricciones de base en `tests/integration/test_restricciones_recojo.py`: formato de serie inválido falla por `CheckConstraint`; dos series con el mismo `numero` fallan por `unique`; línea sin serie ni cantidad falla; línea con serie y `cantidad!=1` falla; cantidad negativa falla
- [ ] T035 [P] [US2] Pruebas de contrato de validación en `tests/contract/test_recojo_validacion_http.py`: `400` con mensaje exacto para formato inválido, duplicado en el recojo y serie ya existente; la serie en minúsculas se guarda normalizada; el mensaje de serie existente es idéntico para serie propia y de otro tenant; no se crea `Recojo`, `LineaRecojo` ni `Serie`
- [ ] T036 [P] [US2] Pruebas de integración de series en `tests/integration/test_recojo_series.py`: duplicado dentro del mismo recojo marcado en la segunda ocurrencia; serie existente del mismo tenant y de otro tenant; `series_existentes` no filtra por tenant; el intento fallido no deja stock ni auditoría; la respuesta no revela `tenant_id`, región ni recojo de origen

### Implementación de US2

- [ ] T037 [US2] Extender `validar_recojo_previo(tenant, datos)` en `recojos/services.py`: detectar duplicados normalizados dentro del mismo recojo, consultar todas las series existentes con `series.services.series_existentes` en una sola operación, marcar estados `invalida`/`duplicada`/`ya_existe`, respetar `SERIE_LONGITUD`/`SERIE_PATRON` y devolver `ResultadoValidacion` con líneas expandidas y errores
- [ ] T038 [US2] Extender `recojos/forms.py` para normalizar y validar series antes de aceptar el formulario, mapear los errores de `validar_recojo_previo` a los mensajes exactos y conservar los valores ingresados cuando la respuesta es `400`
- [ ] T039 [US2] Actualizar `crear_recojo` en `recojos/services.py` para usar el resultado completo de `validar_recojo_previo` y lanzar `RecojoInvalido` con estados y errores antes de escribir; el mensaje de serie existente debe ser uniforme y sin datos del tenant
- [ ] T040 [US2] Actualizar las vistas de alta en `recojos/views.py` para renderizar el formulario con errores `400`, los estados por serie y los valores conservados, sin filtrar datos de otros tenants
- [ ] T041 [US2] Extraer a `recojos/services.py` el helper `clasificar_series(numeros, existentes)` (estados `valida`, `invalida`, `duplicada`, `ya_existe`) y reutilizarlo en `validar_recojo_previo` y, en US4, en la vista previa

**Checkpoint**: US2 funcional e independiente; las series se normalizan y validan con mensajes uniformes.

---

## Fase 5: US3 — Regla todo o nada y concurrencia (P3)

**Objetivo**: si una serie es inválida, duplicada o existente, o si falla el stock, no se guarda nada;
dos sesiones concurrentes que intentan la misma serie terminan con un solo recojo y un `409` uniforme
en la perdedora.

**Prueba independiente**: preparar 10 series válidas y 1 inválida y comprobar que no queda ningún
`Recojo`, `LineaRecojo`, `Serie`, cambio de stock ni auditoría; simular un fallo de
`incrementar_stock_general` y comprobar el rollback completo; guardar la misma serie nueva desde dos
sesiones y comprobar que una recibe "La serie ya está registrada en el sistema" sin guardar nada.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T042 [P] [US3] Pruebas de integración de todo o nada en `tests/integration/test_recojo_todo_o_nada.py`: una serie inválida, duplicada o existente no deja `Recojo`, `LineaRecojo`, `Serie`, stock ni auditoría; un fallo simulado de `incrementar_stock_general` revierte todo; un fallo de auditoría revierte todo
- [ ] T043 [P] [US3] Pruebas de integración de concurrencia en `tests/integration/test_recojo_concurrencia.py`: dos sesiones con la misma serie nueva dejan una sola `Serie` y un solo `Recojo`; dos recojos concurrentes del mismo tenant y material suman correctamente el stock (verifica el bloqueo/`F()` del servicio de 008); no quedan filas parciales
- [ ] T044 [P] [US3] Pruebas de contrato de conflicto en `tests/contract/test_recojo_conflicto_http.py`: conflicto de `unique` detectado durante el guardado responde `409` "La serie ya está registrada en el sistema"; un error de stock responde `400` "No se guardó el recojo; corrige los errores"; no se revela el tenant de la serie

### Implementación de US3

- [ ] T045 [US3] Endurecer `crear_recojo(datos, actor)` en `recojos/services.py`: ejecutar la validación autoritativa dentro de `transaction.atomic`, capturar `IntegrityError` de `Serie.numero` y traducirlo a `SerieYaExiste`, garantizar que recojo, líneas, series, stock y auditoría se escriban o se reviertan juntos, y no usar bloqueos de aplicación
- [ ] T046 [US3] Actualizar las vistas de alta en `recojos/views.py` para mapear `SerieYaExiste` a `409`, `RecojoInvalido` a `400` y un error de stock a `400` con el mensaje "No se guardó el recojo; corrige los errores", manteniendo el formulario y los valores cuando corresponda
- [ ] T047 [US3] Verificar y documentar en `recojos/services.py` la dependencia de concurrencia con `stock.services.incrementar_stock_general`: 004 no actualiza `StockGeneral` directamente y exige que el servicio de 008 use `select_for_update` o `F()`; agregar una prueba de integración que falle si 004 escribe stock por su cuenta

**Checkpoint**: US3 funcional e independiente; la operación es atómica y resiste concurrencia.

---

## Fase 6: US4 — Vista previa de series en tiempo real (P4)

**Objetivo**: al pegar o escanear series, el formulario muestra sin recargar una fila por serie con
su estado (`valida`, `invalida`, `duplicada`, `ya_existe`), sin escribir en la base ni revelar datos
de otros tenants.

**Prueba independiente**: pegar un bloque con series válidas, inválidas, repetidas y de otro tenant y
ver los cuatro estados con `data-serie`/`data-estado`; comprobar que no se crea ninguna fila; que
`ADMIN`/`ALMACEN` y el tenant suspendido reciben `403`; que `GET`/`DELETE` responden `405`; y que el
fragmento no contiene `tenant_id`, `region_id`, stock ni creador.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T048 [P] [US4] Pruebas de contrato de `POST /recojos/validar-series/` en `tests/contract/test_recojo_vista_previa_http.py`: `200` con atributos `data-serie` y `data-estado` para `valida`, `invalida`, `duplicada` y `ya_existe`; orden de entrada; serie normalizada; estado vacío "No se ingresaron series"; material inexistente `404`; material no seriado `400`; roles no autorizados `403`; tenant suspendido `403`; `GET`/`DELETE` `405`
- [ ] T049 [P] [US4] Pruebas de integración de la vista previa en `tests/integration/test_recojo_vista_previa.py`: `previsualizar_series` no escribe en `recojos_recojo`, `recojos_linearecojo`, `series_serie` ni `stock_stockgeneral`; usa una sola consulta de existencia; marca serie de otro tenant como `ya_existe` sin revelar tenant, región ni recojo; el guardado posterior revalida

### Implementación de US4

- [ ] T050 [US4] Implementar `previsualizar_series(tenant, material, texto_series)` en `recojos/services.py`: valida que el material exista y sea seriado, divide por líneas, ignora vacías, normaliza, detecta duplicados y consulta existentes en una sola operación con `clasificar_series`; no escribe ni revela datos ajenos
- [ ] T051 [US4] Implementar la vista `validar_series` en `recojos/views.py` (solo `POST`, `@login_required`, rol `USUARIO_TENANT`, tenant activo, CSRF, `400`/`403`/`404`/`405`) y agregar `POST /recojos/validar-series/` en `recojos/urls.py`
- [ ] T052 [US4] Crear `templates/recojos/_vista_previa_series.html` con una fila por serie y los atributos `data-serie` y `data-estado`, textos de estado exactos, estado vacío explícito y sin datos de stock, tenant, región ni creador
- [ ] T053 [US4] Conectar HTMX en `templates/recojos/_linea_form.html`: `hx-post="/recojos/validar-series/"`, `hx-trigger` al pegar/escanear/cambiar el campo de series, `hx-target` al contenedor de vista previa y `hx-include` con `material_id` y `series`; solo para materiales seriados

**Checkpoint**: US4 funcional e independiente; la vista previa cumple `contracts/validacion-series.md`.

---

## Fase 7: Pulido y asuntos transversales

**Propósito**: cerrar calidad, seguridad, rendimiento, RLS, documentación y validación extremo a extremo.

- [ ] T054 [P] Agregar `tests/contract/test_recojo_permisos_aislamiento.py` con la matriz completa de las 4 rutas para `ADMIN`/`ALMACEN` (`403`), tenant suspendido (`403`), recojo de otro tenant (`404`) y `tenant_id`/`region_id` forzados ignorados
- [ ] T055 [P] Agregar `tests/integration/test_recojo_auditoria.py`: un `RegistroCambio` `Recojo/alta` con fecha, región, líneas, series y cantidad; registros `StockGeneral/cantidad` con valor anterior y nuevo por material; ausencia de secretos y de `tenant_id` separado; la auditoría se conserva al suspender el tenant o desactivar la cuenta
- [ ] T056 [P] Agregar `tests/integration/test_recojo_rendimiento.py` con `django_assert_num_queries` para listado, detalle y vista previa: listado paginado a 50 sin N+1, detalle con precarga, vista previa con una sola consulta de existencia y sin escrituras
- [ ] T057 [P] Agregar las políticas RLS por `tenant_id` para `recojos_recojo`, `recojos_linearecojo` y `series_serie` en `recojos/migrations/` y `series/migrations/`; si la infraestructura de 001 no las soporta, registrar la deuda en `05-especificaciones/004-recojo-de-materiales/research.md`
- [ ] T058 [P] Verificar la deuda documental antes de implementar consumidores: en `05-especificaciones/005-stock-inicial-de-tecnicos/plan.md` reemplazar la columna `serie` de texto por FK a `series.Serie`; confirmar que 013 usa `materiales.Material` y corregir cualquier mención restante a `catalogo`; no cambiar alcance de 004
- [ ] T059 [P] Ejecutar los escenarios manuales 1–15 de `05-especificaciones/004-recojo-de-materiales/quickstart.md` contra PostgreSQL y registrar el resultado
- [ ] T060 Ejecutar `pytest --cov=recojos --cov=series --cov-report=term-missing` sobre PostgreSQL usando la configuración de `pytest.ini`/`pyproject.toml` y cerrar brechas en `tests/` hasta cubrir CA-01…CA-09 y los criterios de salida de `quickstart.md`
- [ ] T061 Verificar que no existe ninguna ruta de edición ni borrado en `recojos/urls.py` (`DELETE` responde `405`), que `admin.py` es de solo lectura y que no se crea ni requiere superusuario de Django

---

## Dependencias y orden de ejecución

### Dependencias de fase

- **Setup (Fase 1)**: depende de 001, 002 y la parte fundacional de 008 implementadas.
- **Fundacional (Fase 2)**: depende del Setup y **bloquea todas las historias** (apps, modelos,
  migraciones, normalización, validaciones base, alcance, auditoría y registro de movimientos).
- **Historias (Fases 3–6)**: dependen de la Fase 2.
- **Pulido (Fase 7)**: depende de todas las historias que se entreguen.

### Dependencias entre historias

- **US1 (P1)**: sin dependencias posteriores a la Fase 2; entrega el MVP.
- **US2 (P2)**: requiere US1 (alta y formulario); endurece la validación de series.
- **US3 (P3)**: requiere US1 y US2 (transacción y detección de series); completa la atomicidad y la
  concurrencia.
- **US4 (P4)**: requiere US1 y US2 (servicio `clasificar_series` y formulario); puede avanzar en
  paralelo con US3.

### Dentro de cada historia

1. Pruebas primero y en rojo.
2. Modelo/servicio → formulario → vista → ruta → plantilla.
3. El recojo, las líneas, las series, el stock y la auditoría se escriben en la misma transacción.
4. No se avanza con pruebas en rojo (constitución, puerta de pruebas).

### Oportunidades de paralelización

- Setup: T004–T007 en archivos distintos.
- Fundacional: T008–T018 comparten `series/models.py`, `recojos/models.py` y los `services.py`;
  solo las migraciones pueden prepararse en paralelo después de sus modelos.
- US1: T019–T023 en archivos distintos; T029–T031 en plantillas distintas tras las vistas.
- US2: T032–T036 en archivos distintos; el resto comparte `services.py`/`forms.py`/`views.py`.
- US3: T042–T044 en archivos distintos; T045–T047 comparten `services.py`/`views.py`.
- US4: T048–T049 en archivos distintos; T050–T053 son secuenciales por servicio, vista y plantilla.
- Pulido: T054–T059 son independientes; T060–T061 cierran al final.

---

## Ejemplo de paralelización: US1

```bash
# Escribir primero todas las pruebas de US1 (archivos distintos):
Task: "Pruebas de contrato de alta en tests/contract/test_recojo_alta_http.py"
Task: "Pruebas de contrato de listado/detalle en tests/contract/test_recojo_lista_detalle_http.py"
Task: "Pruebas de integración de alta seriada en tests/integration/test_recojo_alta.py"
Task: "Pruebas de integración de stock no seriado en tests/integration/test_recojo_stock.py"
Task: "Pruebas de integración de aislamiento en tests/integration/test_recojo_aislamiento.py"

# Implementación paralelizable tras servicios y vistas:
Task: "Plantilla de listado en templates/recojos/recojos_lista.html"
Task: "Plantilla de detalle en templates/recojos/recojo_detalle.html"
Task: "Parcial de línea en templates/recojos/_linea_form.html"
```

## Ejemplo de paralelización: US2, US3 y US4

```bash
# Con US1 y el servicio de validación listos, tres personas pueden avanzar:
Task: "Pruebas de restricciones de series/stock"                       # US2
Task: "Pruebas de todo o nada y concurrencia"                          # US3
Task: "Pruebas de contrato de la vista previa"                         # US4

# Los archivos de prueba son distintos y pueden escribirse a la vez.
```

> Las tareas de implementación de US2, US3 y US4 comparten `recojos/services.py`,
> `recojos/views.py` y `recojos/forms.py`; si se ejecutan en paralelo, coordinar esos archivos o
> serializar las tareas concretas.

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 (Setup).
2. Completar Fase 2 (Fundacional) — **crítica**.
3. Completar Fase 3 (US1).
4. **DETENERSE y VALIDAR**: alta seriada y no seriada, stock, auditoría, listado, detalle y
   aislamiento por tenant.
5. Desplegar/demostrar si está listo.

> US1 ya entrega el recojo completo con series válidas y cantidades, que es el valor central del
> módulo.

### Entrega incremental

1. Setup + Fundacional → apps, tablas y validaciones base listas.
2. US1 → alta, stock, auditoría, listado y detalle (MVP).
3. US2 → normalización, formato, duplicados y series existentes.
4. US3 → atomicidad, rollback y concurrencia.
5. US4 → vista previa HTMX en tiempo real.
6. Pulido → permisos, auditoría, rendimiento, RLS, documentación y escenarios manuales.

### Estrategia de equipo en paralelo

1. Todo el equipo completa Setup + Fundacional.
2. Al terminar la Fase 2:
   - Persona A: US1 (alta, stock, consulta).
   - Persona B: prepara las pruebas y el contrato de US2 mientras US1 se estabiliza.
   - Persona C: prepara las pruebas y el contrato de US4.
3. Con US1 listo: US2 y US4 en paralelo; US3 al estabilizar la validación.
4. Pulido al final.

---

## Notas

- `[P]` significa archivos distintos y sin dependencia de tareas incompletas.
- `[Story]` traza cada tarea a su historia y a los criterios de aceptación de `spec.md`.
- El tenant y la región salen siempre de la sesión; ninguna tarea agrega `tenant_id`, `region_id` ni
  `almacen_id` a formularios, URLs o peticiones HTMX.
- La unicidad de `Serie.numero` es global y se impone en PostgreSQL; la vista previa no es autoridad.
- No se crea ninguna ruta de edición ni borrado; `DELETE` responde `405`.
- El recojo, sus líneas, las series, el incremento de stock y la auditoría se escriben en la misma
  transacción; nunca se auditan secretos.
- La app de series es transversal y propiedad de esta spec; 005, 006, 007, 008, 010 y 011 la
  consumen y no crean otra tabla de series.
- Las tareas de 001, 002 y 008 se asumen implementadas; si falta la parte fundacional de stock,
  T001 detiene el trabajo.
- Commit tras cada tarea o grupo lógico; detenerse en cada checkpoint para validar la historia de
  forma independiente.
- Evitar: tareas vagas, conflictos en el mismo archivo y dependencias entre historias que rompan la
  independencia.
