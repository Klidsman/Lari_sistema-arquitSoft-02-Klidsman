---
description: "Lista de tareas para la implementación de 003 Técnicos del tenant"
---

# Tareas: 003 Técnicos del tenant

**Entrada**: Documentos de diseño en `05-especificaciones/003-tecnicos/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`, `tenants.Tenant`, `ContextoUsuarioMiddleware`, `auditoria.RegistroCambio` y `auditoria.services.registrar_cambio`). Las tareas de 001 no se repiten aquí.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige al menos una prueba por criterio de aceptación, y `plan.md` §Pruebas enumera los nombres propuestos. Cada historia escribe primero sus pruebas, las ve fallar y luego implementa.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario asociada (`US1`…`US4`)
- Todas las rutas de archivo son relativas a la raíz del repositorio

## Origen de las historias de usuario

`spec.md` no numera historias propias; declara trazabilidad a HU-02 y describe reglas y criterios de aceptación. Las historias siguientes se derivan de esos criterios y del orden de dependencia técnica.

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Alta y consulta básica del técnico | P1 | Alta, formato y normalización del NIF, unicidad global, nombre obligatorio, tenant de la sesión, auditoría y listado/detalle |
| US2 — Edición con NIF y tenant inmutables | P2 | Edición del nombre, auditoría por campo, rechazo de cambio de NIF/tenant y permisos |
| US3 — Desactivación, conservación y reactivación | P3 | Desactivación, exclusión de selectores, conservación de historial/stock, reactivación, NIF no reutilizable e idempotencia |
| US4 — Búsqueda y selector para módulos consumidores | P4 | Búsqueda por NIF/nombre dentro del tenant, filtro por estado, fragmento HTMX y contrato para 005/006/009/013 |

## Convenciones de rutas

Proyecto Django único en la raíz: la app nueva es `tecnicos/`; las plantillas viven en `templates/tecnicos/`; las pruebas en `tests/{unit,integration,contract}/`. La app `auditoria`, `acceso` y `tenants` son propiedad de la spec 001.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: crear la app `tecnicos` y conectarla al proyecto existente de la spec 001.

- [ ] T001 Verificar los prerrequisitos de la spec 001 en `config/settings/base.py`, `acceso/models.py`, `tenants/models.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware` activo, roles `ADMIN_PLATAFORMA`/`USUARIO_TENANT`/`RESPONSABLE_ALMACEN` y `registrar_cambio()` importable; detenerse y reportar si falta alguno
- [ ] T002 Crear la app Django `tecnicos` con `tecnicos/__init__.py`, `tecnicos/apps.py`, `tecnicos/migrations/__init__.py` y registrarla en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T003 Incluir `tecnicos/urls.py` desde `config/urls.py` con el prefijo `/tecnicos/` (el archivo de rutas se crea en T021)
- [ ] T004 [P] Extender `conftest.py` con las fixtures `tenant`, `otro_tenant`, `usuario_tenant`, `usuario_admin`, `usuario_almacen`, `tecnico`, `tecnico_desactivado`, `tecnico_otro_tenant` y `registro_cambios` sobre PostgreSQL
- [ ] T005 [P] Agregar el enlace de navegación a Técnicos en `templates/base.html`, visible solo para la cuenta del tenant (`USUARIO_TENANT`)

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelo, migración, normalización, alcance y auditoría que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

- [ ] T006 Implementar `Tecnico` en `tecnicos/models.py` con `tenant = ForeignKey("tenants.Tenant", on_delete=PROTECT, related_name="tecnicos")`, `nif = CharField(max_length=6, unique=True)`, `nombre = CharField(max_length=100)`, `activo = BooleanField(default=True)`, `creado_por` FK `PROTECT` `related_name="+"`, `creado_en = auto_now_add`, `actualizado_por` FK `PROTECT` nullable `related_name="+"`, `actualizado_en = auto_now`; agregar `Meta.ordering = ["nombre", "nif"]`, `CheckConstraint(Q(nif__regex=r"^LA[0-9]{4}$"), name="tecnico_nif_formato")`, `CheckConstraint(~Q(nombre=""), name="tecnico_nombre_obligatorio")`, `Index(fields=["tenant", "activo"], name="tecnico_tenant_activo")` e `Index(fields=["tenant", "nombre"], name="tecnico_tenant_nombre")`
- [ ] T007 Generar y revisar `tecnicos/migrations/0001_initial.py`, aplicar con `migrate` y no crear técnicos, cuentas ni datos maestros por migración; `acceso.Usuario` y `tenants.Tenant` deben existir antes
- [ ] T008 Implementar en `tecnicos/services.py` las excepciones `ValidacionTecnico`, `NifDuplicado`, `PermisoDenegado`, `NoEncontrado`, `TecnicoNoDisponible` y `TenantSuspendido`, y las funciones `normalizar_nif()` (strip + `upper()`, sin quitar separadores internos), `validar_nif()` (`^LA[0-9]{4}$`), `normalizar_nombre()` (strip + colapsar espacios internos) y `validar_nombre()` (1–100 caracteres), con los mensajes exactos del contrato
- [ ] T009 Implementar en `tecnicos/services.py` `validar_cuenta_tenant(actor, tenant=None)`, `obtener_tecnico(tenant, tecnico_id)`, `obtener_tecnico_por_nif(tenant, nif)` y `validar_tecnico_para_operacion(tenant, tecnico_id)`: rol `USUARIO_TENANT`, cuenta activa, tenant activo, filtro por tenant, `404`/`NoEncontrado` para técnicos ajenos y `TecnicoNoDisponible` para desactivados
- [ ] T010 Implementar en `tecnicos/services.py` los helpers `auditar_alta_tecnico(tecnico, actor)` y `auditar_cambio_tecnico(tecnico, cambios, actor)` que llaman a `auditoria.services.registrar_cambio` con `entidad="Tecnico"`, un registro por campo y los valores `ACTIVO`/`DESACTIVADO` para `activo`, sin secretos ni `tenant_id` separado
- [ ] T011 Implementar en `tecnicos/services.py` `tecnicos_para_operacion(tenant)` (solo activos, ordenados por nombre y NIF) y `tecnicos_para_reporte(tenant, incluir_inactivos=True)` (incluye desactivados para documentos históricos)

**Checkpoint**: app, tabla, validaciones, alcance y auditoría listos; las historias pueden comenzar.

---

## Fase 3: US1 — Alta y consulta básica del técnico (P1) 🎯

**Objetivo**: la cuenta del tenant registra un técnico con NIF `LAXXXX` único y nombre válido, queda activo en su tenant y con el alta auditada; el listado y el detalle muestran solo técnicos del tenant.

**Prueba independiente**: autenticado como tenant, crear `LA1234 / Juan Pérez` y verlo activo en `/tecnicos/` y `/tecnicos/<id>/` con auditoría; repetir el NIF y recibir "El NIF ya está registrado"; probar formatos inválidos, nombre vacío/101, doble envío, NIF de otro tenant y accesos forzados de Administrador/Responsable.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T012 [P] [US1] Pruebas de contrato de `GET/POST /tecnicos/nuevo/` en `tests/contract/test_tecnico_alta_http.py`: alta `302`, formatos `LA123`/`LA12345`/`A1234`/`LA12A4`/`LA 1234`/`LA-1234` `400` "El NIF debe tener el formato LAXXXX", duplicado `409` "El NIF ya está registrado", nombre vacío/solo espacios `400` "El nombre es obligatorio", nombre > 100 `400`, `tenant_id` forzado ignorado, Administrador/Responsable `403`, tenant suspendido `403` y `DELETE` `405`
- [ ] T013 [P] [US1] Pruebas de contrato de `GET /tecnicos/` y `GET /tecnicos/<id>/` en `tests/contract/test_tecnico_lista_detalle_http.py`: `200` con NIF, nombre y estado; orden por nombre y NIF; paginación de 50; detalle `200`; técnico de otro tenant `404` "El técnico no existe"; Administrador/Responsable `403`; métodos no permitidos `405`
- [ ] T014 [P] [US1] Pruebas de integración de `crear_tecnico` en `tests/integration/test_tecnico_alta.py`: tenant tomado del actor, estado activo, auditoría `alta` con NIF/nombre/estado, normalización de NIF y nombre, duplicado en el mismo y en otro tenant, NIF de un desactivado del mismo tenant con mensaje de reactivación, NIF de un desactivado de otro tenant con mensaje uniforme, nombre duplicado permitido, `IntegrityError` traducido, tenant suspendido y ausencia de auditoría en fallos
- [ ] T015 [P] [US1] Pruebas de base de datos en `tests/integration/test_restricciones_tecnico.py`: NIF de 3/5 caracteres o con letras/espacios internos falla por `CheckConstraint`; dos técnicos con el mismo NIF fallan por `unique`; nombre vacío falla por `CheckConstraint`; dos altas simultáneas del mismo NIF dejan una sola fila
- [ ] T016 [P] [US1] Pruebas unitarias de normalización/validación en `tests/unit/test_tecnico_validaciones.py`: `" la1234 "` → `LA1234`; `LA 1234` y `LA-1234` se rechazan; nombre con espacios externos/repetidos se colapsa; 100 caracteres se aceptan y 101 se rechazan; nombre vacío/solo espacios se rechaza

### Implementación de US1

- [ ] T017 [US1] Implementar `TecnicoForm` en `tecnicos/forms.py` con `nif` (`max_length=6`, formato `LAXXXX`) y `nombre` (1–100), excluyendo `tenant`, `tenant_id`, `region`, `region_id` y `activo`; mostrar los mensajes exactos del contrato
- [ ] T018 [US1] Implementar `crear_tecnico(datos, actor)` en `tecnicos/services.py`: valida la cuenta, normaliza antes de validar, resuelve el NIF duplicado (activo, desactivado del mismo tenant o desactivado de otro tenant), crea en `transaction.atomic` con auditoría `alta` y traduce `IntegrityError` a "El NIF ya está registrado"
- [ ] T019 [US1] Implementar `listar_tecnicos(tenant, estado="todos")` en `tecnicos/services.py`: filtra siempre por tenant, aplica `activos`/`desactivados`/`todos` y ordena por nombre y NIF
- [ ] T020 [US1] Implementar las vistas `listar_tecnicos` (50 por página), `detalle_tecnico` y `crear_tecnico` (`GET/POST`) en `tecnicos/views.py` con `@login_required`, validación de rol/tenant, `404`/`403`/`400`/`405` y los mensajes del contrato
- [ ] T021 [US1] Crear `tecnicos/urls.py` con `GET /tecnicos/`, `GET/POST /tecnicos/nuevo/` y `GET /tecnicos/<int:id>/`, sin rutas de borrado
- [ ] T022 [US1] Crear `templates/tecnicos/tecnicos_lista.html` (tabla con NIF, nombre, estado y acciones; paginación) y `templates/tecnicos/tecnico_form.html` (alta con `hx-disabled-elt` en Guardar), mostrando los errores con los textos exactos
- [ ] T023 [US1] Crear `templates/tecnicos/tecnico_detalle.html` con NIF, nombre, estado, creador/fecha y última actualización, sin datos de stock ni de otros tenants

**Checkpoint**: US1 funcional e independiente; el técnico puede crearse y consultarse, con auditoría.

---

## Fase 4: US2 — Edición con NIF y tenant inmutables (P2)

**Objetivo**: la cuenta del tenant edita el nombre; el NIF y el tenant se muestran como solo lectura y el servidor rechaza cualquier intento de cambiarlos; cada cambio de nombre queda auditado y una edición sin cambios no duplica auditoría.

**Prueba independiente**: cambiar el nombre y ver el valor anterior/nuevo en auditoría; forzar `nif` y `tenant_id` y recibir `400`; abrir un técnico de otro tenant y recibir `404`; editar el nombre de un desactivado sin reactivarlo; enviar `DELETE` y recibir `405`.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T024 [P] [US2] Pruebas de contrato de `GET/POST /tecnicos/<id>/editar/` en `tests/contract/test_tecnico_edicion_http.py`: cambio de nombre `302`; `nif` forzado `400` "El NIF no se puede cambiar"; `tenant`/`tenant_id` forzado `400` "El tenant del técnico no se puede cambiar"; nombre vacío/101 `400`; técnico de otro tenant `404`; Administrador/Responsable `403`; edición de desactivado permitida; `DELETE` `405`
- [ ] T025 [P] [US2] Pruebas de integración de `actualizar_tecnico` en `tests/integration/test_tecnico_edicion.py`: solo cambia `nombre`; un `RegistroCambio` por campo modificado con valor anterior/nuevo; edición sin cambios no audita ni actualiza metadatos; actualiza `actualizado_por`/`actualizado_en`; rechaza `nif`/`tenant`; no audita intentos rechazados; usa `select_for_update`

### Implementación de US2

- [ ] T026 [US2] Implementar `actualizar_tecnico(tecnico, cambios, actor)` en `tecnicos/services.py`: valida cuenta/tenant, rechaza `nif` y `tenant`/`tenant_id`, normaliza y valida el nombre, y en `transaction.atomic` con `select_for_update` actualiza y audita solo si el nombre cambió
- [ ] T027 [US2] Implementar `TecnicoEdicionForm` en `tecnicos/forms.py` con solo `nombre`; excluir `nif`, `tenant`, `activo`, `creado_por` y `creado_en`
- [ ] T028 [US2] Implementar `editar_tecnico` (`GET/POST`) en `tecnicos/views.py` con `@login_required`, `404` si no existe o es de otro tenant, `403` por rol, `400` para NIF/tenant forzados y `405` para otros métodos
- [ ] T029 [US2] Agregar `GET/POST /tecnicos/<int:id>/editar/` en `tecnicos/urls.py`
- [ ] T030 [US2] Crear la variante de edición de `templates/tecnicos/tecnico_form.html`: NIF y tenant en solo lectura, solo nombre editable, sin acciones de borrado y con los mensajes exactos

**Checkpoint**: US2 funcional e independiente; la edición respeta la inmutabilidad y la auditoría.

---

## Fase 5: US3 — Desactivación, conservación y reactivación (P3)

**Objetivo**: la cuenta del tenant desactiva un técnico sin eliminarlo, deja de ofrecerlo en operaciones nuevas y conserva su historial/stock; puede reactivarlo y el NIF no se reutiliza; las transiciones son idempotentes.

**Prueba independiente**: desactivar y comprobar que no aparece en `tecnicos_para_operacion`; abrir su detalle y ver historial; reactivar y comprobar que vuelve a los selectores; repetir ambas acciones y verificar que no se duplica auditoría; intentar crear otro técnico con el NIF desactivado; enviar `DELETE` y recibir `405`; usar un formulario viejo con un desactivado y recibir "El técnico está desactivado".

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T031 [P] [US3] Pruebas de contrato de `POST /tecnicos/<id>/desactivar/` y `POST /tecnicos/<id>/reactivar/` en `tests/contract/test_tecnico_estado_http.py`: `302` en éxito; segunda llamada `302` sin cambio ni auditoría; técnico de otro tenant `404`; Administrador/Responsable `403`; `GET`/`DELETE` `405`
- [ ] T032 [P] [US3] Pruebas de integración de `desactivar_tecnico`/`reactivar_tecnico` en `tests/integration/test_tecnico_estado.py`: cambio de `activo`, auditoría `ACTIVO`↔`DESACTIVADO`, idempotencia sin auditoría duplicada, exclusión de `tecnicos_para_operacion`, historial visible con `tecnicos_para_reporte`, conservación de stock con un doble de prueba que verifica que no se ejecuta `delete()` y tenant suspendido
- [ ] T033 [P] [US3] Pruebas de integración en `tests/integration/test_tecnico_nif_desactivado.py`: crear con el NIF de un desactivado del mismo tenant devuelve "El NIF ya está registrado; reactiva el técnico existente"; con el de otro tenant devuelve "El NIF ya está registrado"; `validar_tecnico_para_operacion` rechaza un desactivado usado en un formulario viejo con "El técnico está desactivado"
- [ ] T034 [P] [US3] Pruebas de contrato en `tests/contract/test_tecnico_sin_borrado.py`: no existe URL de borrado en `tecnicos/urls.py`; `DELETE` sobre detalle y edición responde `405`; desactivar conserva la fila y la auditoría

### Implementación de US3

- [ ] T035 [US3] Implementar `desactivar_tecnico(tecnico, actor)` y `reactivar_tecnico(tecnico, actor)` en `tecnicos/services.py`: validan cuenta/tenant, usan `transaction.atomic` + `select_for_update`, son idempotentes, actualizan metadatos y auditan solo el cambio real, sin borrar stock, series, asignaciones, traspasos, órdenes ni conciliaciones
- [ ] T036 [US3] Implementar las vistas `desactivar_tecnico` y `reactivar_tecnico` en `tecnicos/views.py` como `POST` únicamente, con `@login_required`, `404`/`403`/`405` y redirección `302` al detalle o listado
- [ ] T037 [US3] Agregar `POST /tecnicos/<int:id>/desactivar/` y `POST /tecnicos/<int:id>/reactivar/` en `tecnicos/urls.py`, sin aceptar `GET`
- [ ] T038 [US3] Agregar a `templates/tecnicos/tecnico_detalle.html` y `templates/tecnicos/tecnicos_lista.html` los formularios `POST` de desactivar/reactivar con confirmación, sin botón ni enlace de borrado

**Checkpoint**: US3 funcional e independiente; el técnico se conserva y puede reactivarse.

---

## Fase 6: US4 — Búsqueda y selector para módulos consumidores (P4)

**Objetivo**: buscar por NIF o nombre dentro del tenant, filtrar por estado y exponer un fragmento HTMX con solo técnicos activos para las specs 005, 006, 009 y 013, sin revelar datos de otros tenants.

**Prueba independiente**: con técnicos de dos tenants, buscar el mismo NIF desde ambas sesiones y obtener solo el técnico propio; `q` vacío devuelve el listado paginado; el fragmento respeta `limit` (20 por defecto, 50 máximo), solo muestra activos y no incluye `tenant_id`, `region_id`, stock ni creador.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T039 [P] [US4] Pruebas de contrato de búsqueda en el listado en `tests/contract/test_tecnico_busqueda_http.py`: `?q=` por NIF y por nombre, `q` vacío sin filtrar, filtro `estado=activos|desactivados|todos`, orden por nombre/NIF, paginación de 50, aislamiento entre dos tenants y `403` para Administrador/Responsable
- [ ] T040 [P] [US4] Pruebas de contrato del fragmento `GET /tecnicos/buscar/` en `tests/contract/test_tecnico_fragmento_http.py`: atributos `data-nif`, `data-nombre`, `data-activo`; solo activos; `limit` por defecto 20 y máximo 50; estado vacío "No se encontraron técnicos"; ausencia de `tenant_id`, `region_id`, stock y datos del creador; `405` para métodos distintos de `GET`; `403` para roles no autorizados; aislamiento entre tenants
- [ ] T041 [P] [US4] Pruebas de integración de `buscar_tecnicos` y `tecnicos_para_operacion` en `tests/integration/test_tecnico_busqueda.py`: `nif__icontains` OR `nombre__icontains`, filtro por tenant, orden por nombre/NIF, `q=""`, filtros de estado, solo activos en operación y ningún resultado de otro tenant

### Implementación de US4

- [ ] T042 [US4] Implementar `buscar_tecnicos(tenant, q="", solo_activos=False, estado=None)` en `tecnicos/services.py` con `Q(nif__icontains=q) | Q(nombre__icontains=q)`, filtro por tenant, filtros de estado y orden por nombre/NIF
- [ ] T043 [US4] Implementar `obtener_datos_tecnico(tecnico)` en `tecnicos/services.py` devolviendo `nif`, `nombre` y `activo` para el contrato de los módulos consumidores
- [ ] T044 [US4] Extender `listar_tecnicos` en `tecnicos/views.py` para aceptar `q`, `estado` y `page`, usar `buscar_tecnicos` y paginar a 50 filas manteniendo el orden
- [ ] T045 [US4] Implementar `buscar_tecnicos_htmx` en `tecnicos/views.py`: exige sesión y rol de tenant, fuerza `solo_activos=True`, acota `limit` entre 1 y 50 con 20 por defecto y responde solo el fragmento
- [ ] T046 [US4] Agregar `GET /tecnicos/buscar/` en `tecnicos/urls.py` y verificar que no acepta `tenant_id` ni `region_id`
- [ ] T047 [US4] Crear `templates/tecnicos/_filas_busqueda.html` con una fila por técnico y los atributos `data-nif`, `data-nombre`, `data-activo`, estado vacío explícito, y agregar el buscador y el contenedor HTMX a `templates/tecnicos/tecnicos_lista.html`

**Checkpoint**: US4 funcional e independiente; el fragmento cumple `contracts/busqueda-tecnicos.md`.

---

## Fase 7: Pulido y asuntos transversales

**Propósito**: cerrar calidad, seguridad, rendimiento, documentación y validación extremo a extremo.

- [ ] T048 [P] Agregar `tests/contract/test_tecnico_permisos_aislamiento.py` con la matriz completa de las 7 rutas para `ADMIN`/`ALMACEN` (`403`), tenant suspendido y cuenta inactiva (`403`/redirección), y para técnicos de otro tenant (`404`), incluido el intento de forzar `tenant_id`
- [ ] T049 [P] Agregar `tests/integration/test_tecnico_auditoria.py` que verifique eventos `alta`/`nombre`/`activo`, misma transacción, ausencia de secretos y de `tenant_id`, y conservación de la auditoría al desactivar la cuenta o suspender el tenant
- [ ] T050 [P] Agregar `tests/integration/test_tecnico_rendimiento.py` con `django_assert_num_queries` para listado, búsqueda y fragmento, evitando N+1 en `tecnicos/views.py`
- [ ] T051 [P] Ejecutar `pytest --cov=tecnicos` y cerrar brechas hasta cubrir cada criterio de aceptación de `spec.md`
- [ ] T052 [P] Verificar la política RLS de `tecnicos_tecnico` por `tenant_id`; si la spec 001 ya la implementa, agregar la migración correspondiente en `tecnicos/migrations/`; si no, registrar la deuda en `05-especificaciones/003-tecnicos/research.md`
- [ ] T053 [P] Revisar y corregir las referencias documentales de las specs consumidoras (`005`, `006`, `009`, `010`, `013`) para que usen `tecnicos.Tecnico`, `tecnicos_para_operacion`, `obtener_tecnico_por_nif` y `validar_tecnico_para_operacion`; corregir los textos desalineados antes de implementar
- [ ] T054 [P] Ejecutar los escenarios manuales 1–16 de `05-especificaciones/003-tecnicos/quickstart.md` contra PostgreSQL y registrar el resultado
- [ ] T055 Ejecutar la suite completa (`pytest`) sobre PostgreSQL y confirmar los criterios de salida de `quickstart.md`, incluida la ausencia de secretos en auditoría y la ausencia de rutas de borrado

---

## Dependencias y orden de ejecución

### Dependencias de fase

- **Setup (Fase 1)**: depende de que la spec 001 esté implementada.
- **Fundacional (Fase 2)**: depende del Setup y **bloquea todas las historias** (modelo, migración, normalización, alcance, auditoría y helpers de consulta).
- **Historias (Fases 3–6)**: dependen de la Fase 2.
- **Pulido (Fase 7)**: depende de todas las historias que se entreguen.

### Dependencias entre historias

- **US1 (P1)**: sin dependencias posteriores a la Fase 2.
- **US2 (P2)**: requiere US1 (técnico existente y vistas base).
- **US3 (P3)**: requiere US1 (técnico creado y auditado); usa `tecnicos_para_operacion` de la Fase 2.
- **US4 (P4)**: requiere US1 (listado y rutas base); puede avanzar en paralelo con US2 y US3 una vez completada US1.

### Dentro de cada historia

1. Pruebas primero y en rojo.
2. Modelo/servicio → formulario → vista → ruta → plantilla.
3. La auditoría se escribe dentro de la misma transacción que el cambio.
4. No se avanza con pruebas en rojo (constitución, puerta de pruebas).

### Oportunidades de paralelización

- Setup: T004 y T005 en archivos distintos.
- US1: las cinco pruebas T012–T016 en archivos distintos; las plantillas T022 y T023 en paralelo tras las vistas.
- US2: T024 y T025 en paralelo; el resto comparte `services.py`/`views.py` y es secuencial.
- US3: T031–T034 en paralelo; el resto comparte `services.py`/`views.py` y es secuencial.
- US4: T039–T041 en paralelo; el resto comparte `services.py`/`views.py` y es secuencial.
- Pulido: T048–T054 son independientes.

---

## Ejemplo de paralelización: US1

```bash
# Escribir primero todas las pruebas de US1 (archivos distintos):
Task: "Pruebas de contrato de alta en tests/contract/test_tecnico_alta_http.py"
Task: "Pruebas de contrato de listado/detalle en tests/contract/test_tecnico_lista_detalle_http.py"
Task: "Pruebas de integración de alta en tests/integration/test_tecnico_alta.py"
Task: "Pruebas de restricciones de base en tests/integration/test_restricciones_tecnico.py"
Task: "Pruebas unitarias de validaciones en tests/unit/test_tecnico_validaciones.py"

# Implementación paralelizable:
Task: "Implementar TecnicoForm en tecnicos/forms.py"
Task: "Crear plantilla de listado en templates/tecnicos/tecnicos_lista.html"
```

## Ejemplo de paralelización: US2, US3 y US4

```bash
# Con US1 completo, tres personas pueden avanzar en paralelo:
Task: "Implementar actualizar_tecnico en tecnicos/services.py"       # US2
Task: "Implementar desactivar_tecnico/reactivar_tecnico en el mismo archivo"  # US3, coordinar archivo
Task: "Implementar buscar_tecnicos en tecnicos/services.py"          # US4, coordinar archivo

# Las pruebas viven en archivos distintos y pueden escribirse a la vez:
Task: "tests/contract/test_tecnico_edicion_http.py"                  # US2
Task: "tests/contract/test_tecnico_estado_http.py"                   # US3
Task: "tests/contract/test_tecnico_fragmento_http.py"                # US4
```

> Las tareas de implementación de US2, US3 y US4 comparten `tecnicos/services.py` y
> `tecnicos/views.py`; si se ejecutan en paralelo, coordinar esos archivos o serializar esas
> tareas concretas.

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 (Setup).
2. Completar Fase 2 (Fundacional) — **crítica**.
3. Completar Fase 3 (US1).
4. **DETENERSE y VALIDAR**: alta, validaciones, unicidad, normalización, auditoría, listado y
   detalle.
5. Desplegar/demostrar si está listo.

> US1 ya entrega valor: el tenant puede registrar y consultar sus técnicos. US2 completa la
> edición, US3 la conservación/reactivación y US4 la búsqueda y el consumo por otros módulos.

### Entrega incremental

1. Setup + Fundacional → app, tabla y helpers listos.
2. US1 → alta, listado y detalle (MVP).
3. US2 → edición con NIF/tenant inmutables y auditoría.
4. US3 → desactivación, conservación y reactivación.
5. US4 → búsqueda y fragmento para 005/006/009/013.
6. Pulido → cobertura, rendimiento, RLS, documentación y escenarios manuales.

### Estrategia de equipo en paralelo

1. Todo el equipo completa Setup + Fundacional.
2. Al terminar la Fase 2:
   - Persona A: US1 (alta, listado, detalle).
   - Persona B: prepara las pruebas y el contrato de US2 mientras US1 se estabiliza.
   - Persona C: prepara las pruebas y el contrato de US3/US4.
3. Con US1 listo: US2, US3 y US4 en paralelo, coordinando `services.py` y `views.py`.
4. Pulido al final.

---

## Notas

- `[P]` significa archivos distintos y sin dependencia de tareas incompletas.
- `[Story]` traza cada tarea a su historia y a los criterios de aceptación de `spec.md`.
- El tenant sale siempre de la sesión; ninguna tarea agrega `tenant_id` ni `region_id` a formularios, URLs o búsquedas.
- El NIF es único global e inmutable; el tenant es inmutable.
- No se crea ninguna ruta de borrado; `DELETE` responde `405`.
- Toda alta, cambio de nombre, desactivación y reactivación se audita en la misma transacción; nunca se auditan secretos.
- La app se llama `tecnicos`; el modelo es `Tecnico` y la región se deriva de `tenant.region`.
- Las tareas de la spec 001 (`acceso`, `tenants`, `auditoria`, `config/settings`) se asumen implementadas; si faltan, T001 detiene el trabajo.
- Commit tras cada tarea o grupo lógico; detenerse en cada checkpoint para validar la historia de forma independiente.
- Evitar: tareas vagas, conflictos en el mismo archivo y dependencias entre historias que rompan la independencia.
