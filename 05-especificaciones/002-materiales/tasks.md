---

description: "Lista de tareas para la implementación de 002 Módulo de materiales"
---

# Tareas: 002 Módulo de materiales

**Entrada**: Documentos de diseño en `05-especificaciones/002-materiales/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`; **spec 001 implementada** (`acceso.Usuario`, `acceso.models.Rol`, `ContextoUsuarioMiddleware`, `auditoria.RegistroCambio` y `auditoria.services.registrar_cambio`). Las tareas de 001 no se repiten aquí.

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige al menos una prueba por criterio de aceptación, y `plan.md` §Pruebas enumera los nombres propuestos. Cada historia escribe primero sus pruebas, las ve fallar y luego implementa.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario asociada (`US1`…`US4`)
- Todas las rutas de archivo son relativas a la raíz del repositorio

## Origen de las historias de usuario

`spec.md` no numera historias propias; declara trazabilidad a HU/RF pendientes de completar y describe reglas y criterios de aceptación. Las historias siguientes se derivan de esos criterios y del orden de dependencia técnica.

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Alta y consulta básica del catálogo | P1 | Criterios de alta, código de 11 dígitos, duplicado, sin lote, doble clic; reglas de creador/fecha |
| US2 — Búsqueda global y fragmento para otros módulos | P2 | Búsqueda por código/descripción, «ROSETA», búsqueda vacía, catálogo compartido |
| US3 — Edición restringida con auditoría | P3 | Edición de descripción/lote, solo creador o admin, código no editable, conservación |
| US4 — Tipo inmutable con stock o movimientos | P4 | Cambio de tipo rechazado con movimientos, mensaje exacto |

## Convenciones de rutas

Proyecto Django único en la raíz: la app nueva es `materiales/`; las plantillas viven en `templates/materiales/`; las pruebas en `tests/{unit,integration,contract}/`. La app `auditoria` y el paquete `acceso` son propiedad de la spec 001.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: crear la app `materiales` y conectarla al proyecto existente de la spec 001.

- [ ] T001 Verificar los prerrequisitos de la spec 001 en `config/settings/base.py`, `acceso/models.py` y `auditoria/services.py`: `AUTH_USER_MODEL="acceso.Usuario"`, `ContextoUsuarioMiddleware` activo, rol `ADMIN_PLATAFORMA` y `registrar_cambio()` importable; detenerse y reportar si falta alguno
- [ ] T002 Crear la app Django `materiales` con `materiales/__init__.py`, `materiales/apps.py`, `materiales/migrations/__init__.py` y registrarla en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T003 Incluir `materiales/urls.py` desde `config/urls.py` con el prefijo `/materiales/` (el archivo de rutas se crea en T018)
- [ ] T004 [P] Extender `conftest.py` con las fixtures `material`, `usuario_otro_tenant` y `verificacion_movimientos` (registro y limpieza del hook de la US4) sobre PostgreSQL
- [ ] T005 [P] Agregar el enlace de navegación a Materiales en `templates/base.html`, visible para las tres cuentas autenticadas

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelo, migración, normalización y adaptador de auditoría que todas las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase.

- [ ] T006 Implementar `Material` en `materiales/models.py` con `codigo = CharField(max_length=11, unique=True)`, `descripcion = CharField(max_length=100)`, `lote = CharField(max_length=50, blank=True, default="")`, `es_seriado = BooleanField()`, `creado_por` FK `PROTECT` `related_name="+"`, `creado_en = auto_now_add`, `actualizado_por` FK `PROTECT` nullable `related_name="+"`, `actualizado_en = auto_now`; agregar `CheckConstraint(material_codigo_11_digitos)` con `Q(codigo__regex=r"^[0-9]{11}$")`, `CheckConstraint(material_descripcion_obligatoria)` con `~Q(descripcion="")`, `Meta.ordering = ["codigo"]` y la propiedad `tipo` que devuelve `"SERIADO"` o `"NO_SERIADO"`
- [ ] T007 Generar y revisar `materiales/migrations/0001_initial.py` y aplicarla con `migrate`; no crear datos maestros ni materiales por migración
- [ ] T008 Implementar en `materiales/services.py` las excepciones `ValidacionMaterial`, `MaterialDuplicado` y `PermisoDenegado`, y las funciones `normalizar_codigo()` (strip, sin quitar separadores internos), `normalizar_descripcion()` (strip + colapsar espacios internos), `normalizar_lote()` (strip + colapsar espacios + `upper()`, vacío permitido) y `validar_datos_material()` con los mensajes exactos del contrato
- [ ] T009 Implementar en `materiales/services.py` los helpers `auditar_alta_material(material, usuario)` y `auditar_cambios_material(material, cambios, usuario)` que llaman a `auditoria.services.registrar_cambio` con `entidad="Material"` y un registro por campo, sin secretos ni `tenant_id`

**Checkpoint**: app, tabla y utilidades listas; las historias pueden comenzar.

---

## Fase 3: US1 — Alta y consulta básica del catálogo (P1) 🎯

**Objetivo**: cualquier cuenta activa registra un material con código de 11 dígitos único, descripción, lote y tipo; el alta queda auditada con creador y fecha; el catálogo se muestra listado y paginado.

**Prueba independiente**: autenticado como tenant, crear `10402520279 / ROSETA / FIBERHOME / Seriado` y verlo en `/materiales/` con creador y fecha; repetir el código y recibir "El material ya existe"; probar 10/12 dígitos, letras, descripción solo espacios y doble envío.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T010 [P] [US1] Pruebas de contrato de `GET/POST /materiales/nuevo/` en `tests/contract/test_material_alta_http.py`: alta `302`, código inválido `400` "El código debe tener 11 dígitos", duplicado `409` "El material ya existe", descripción vacía/solo espacios `400` "La descripción es obligatoria", lote > 50 `400`, tipo ausente `400` "El tipo es obligatorio" y método `DELETE` `405`
- [ ] T011 [P] [US1] Pruebas de contrato de `GET /materiales/` en `tests/contract/test_material_lista_http.py`: `200` con código, descripción, lote, tipo, creador y fecha; orden por `codigo`; paginación de 50; `401`/redirección sin sesión
- [ ] T012 [P] [US1] Pruebas de integración en `tests/integration/test_material_alta.py`: `crear_material` registra creador y fecha; auditoría `alta` con código, descripción, lote y tipo; normalización de descripción y lote; material sin lote con `lote=""`; doble envío no crea duplicado; código duplicado producido por `IntegrityError` se traduce sin revelar cuenta ni tenant
- [ ] T013 [P] [US1] Pruebas de base de datos en `tests/integration/test_restricciones_material.py`: inserción directa con código de 10 dígitos, de 12 o con letras falla por `CheckConstraint`; descripción vacía falla; dos materiales con el mismo código fallan por `unique`

### Implementación de US1

- [ ] T014 [P] [US1] Implementar `MaterialForm` en `materiales/forms.py`: `codigo` de exactamente 11 dígitos, `descripcion` obligatoria de 1–100, `lote` opcional de hasta 50, `tipo` con choices `SERIADO`/`NO_SERIADO` convertido a `es_seriado` en `clean()`
- [ ] T015 [US1] Implementar `crear_material(datos, usuario)` en `materiales/services.py`: exige cuenta activa, normaliza antes de validar, escribe material y auditoría en `transaction.atomic` y traduce `IntegrityError` a "El material ya existe"
- [ ] T016 [US1] Implementar `listar_materiales()` en `materiales/services.py` con `Material.objects.order_by("codigo")`, sin filtro de tenant
- [ ] T017 [US1] Implementar las vistas `listar_materiales` (50 por página) y `crear_material` (`GET/POST`) en `materiales/views.py` con `@login_required`, mensajes del contrato y `405` por método; devolver `409` para duplicado
- [ ] T018 [US1] Crear `materiales/urls.py` con `/materiales/` y `/materiales/nuevo/`, sin rutas de borrado
- [ ] T019 [US1] Crear `templates/materiales/material_form.html` (alta con `hx-disabled-elt` en Guardar) y `templates/materiales/materiales_lista.html` (tabla con creador y fecha), mostrando los errores con los textos exactos

**Checkpoint**: US1 funcional e independiente; el catálogo ya puede poblarse y consultarse.

---

## Fase 4: US2 — Búsqueda global y fragmento para otros módulos (P2)

**Objetivo**: buscar por código o descripción en todo el catálogo, sin filtro de tenant, y exponer un fragmento HTMX con `data-codigo`, `data-descripcion`, `data-lote` y `data-tipo` para las specs 004, 005, 006, 009 y 013.

**Prueba independiente**: con materiales de dos tenants distintos, buscar `ROSETA` y `1040252` y obtener los mismos resultados en ambas sesiones; `q` vacío devuelve el listado paginado; el fragmento respeta `limit` (20 por defecto, 50 máximo) y no incluye datos de tenant, stock ni creador.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T020 [P] [US2] Pruebas de contrato de búsqueda en el listado en `tests/contract/test_material_busqueda_http.py`: `?q=` por descripción y por código, `q` vacío sin filtrar, orden por `codigo`, paginación de 50 y mismos resultados para dos tenants
- [ ] T021 [P] [US2] Pruebas de contrato del fragmento `GET /materiales/buscar/` en `tests/contract/test_material_fragmento_http.py`: atributos `data-codigo`, `data-descripcion`, `data-lote`, `data-tipo`; `limit` por defecto 20 y máximo 50; estado vacío "No se encontraron materiales"; ausencia de `tenant_id`, `region_id`, stock y datos del creador; `405` para métodos distintos de `GET`
- [ ] T022 [P] [US2] Pruebas de integración en `tests/integration/test_material_busqueda.py`: `buscar_materiales` usa `codigo__icontains` OR `descripcion__icontains`, ordena por código, no filtra por tenant y devuelve todo con `q=""`

### Implementación de US2

- [ ] T023 [US2] Implementar `buscar_materiales(q="")` y `obtener_datos_material(material)` en `materiales/services.py`, con `Q(codigo__icontains=q) | Q(descripcion__icontains=q)` y orden por `codigo`
- [ ] T024 [US2] Extender `listar_materiales` en `materiales/views.py` para aceptar `q` y paginar el resultado de `buscar_materiales` a 50 filas, manteniendo el orden
- [ ] T025 [US2] Implementar `buscar_materiales_htmx` en `materiales/views.py`: exige sesión activa, acota `limit` entre 1 y 50 con 20 por defecto y responde solo el fragmento
- [ ] T026 [US2] Agregar la ruta `/materiales/buscar/` en `materiales/urls.py` y verificar que no acepta `tenant_id` ni `region_id`
- [ ] T027 [US2] Crear `templates/materiales/_filas_busqueda.html` con una fila por material y los cuatro atributos `data-*`, estado vacío explícito, y agregar el buscador y el contenedor HTMX a `templates/materiales/materiales_lista.html`

**Checkpoint**: US2 funcional e independiente; el fragmento cumple `contracts/busqueda-materiales.md`.

---

## Fase 5: US3 — Edición restringida con auditoría (P3)

**Objetivo**: el creador o el Administrador de plataforma editan descripción y lote; el código nunca cambia; cada campo modificado queda auditado con valor anterior y nuevo; el material se conserva aunque el creador se desactive.

**Prueba independiente**: como creador, cambiar la descripción y ver el valor anterior/nuevo en auditoría; con otra cuenta, recibir `403` al forzar la URL; como Administrador, editar correctamente; forzar `codigo` y recibir `400`; enviar `DELETE` y recibir `405`; desactivar al creador y comprobar que el material persiste.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T028 [P] [US3] Pruebas de contrato de `GET/POST /materiales/<id>/editar/` en `tests/contract/test_material_edicion_http.py`: creador y `ADMIN` editan `302`; otra cuenta `403` "No tienes permiso para editar este material"; inexistente `404`; `codigo` forzado `400` "El código no se puede cambiar"; descripción solo espacios `400` "La descripción es obligatoria"; `DELETE` `405`
- [ ] T029 [P] [US3] Pruebas de integración de `actualizar_material` en `tests/integration/test_material_edicion.py`: permiso de creador y de `ADMIN`; un `RegistroCambio` por campo modificado con valor anterior y nuevo; una edición sin cambios no audita; se actualizan `actualizado_por` y `actualizado_en`; se rechaza cualquier clave `codigo`
- [ ] T030 [P] [US3] Pruebas de integración en `tests/integration/test_material_conservacion.py`: desactivar la cuenta creadora conserva el material y su auditoría; un `ADMIN` puede seguir editándolo; no existe ruta de borrado y `DELETE` responde `405`

### Implementación de US3

- [ ] T031 [US3] Implementar `puede_editar_material(material, usuario)` y `actualizar_material(material, cambios, usuario)` en `materiales/services.py`: creador o `ADMIN`, `select_for_update`, `transaction.atomic`, rechazo de `codigo`, normalización previa, auditoría por campo y actualización de `actualizado_por`/`actualizado_en`
- [ ] T032 [US3] Implementar `MaterialEdicionForm` en `materiales/forms.py` con solo `descripcion`, `lote` y el `tipo` condicionado por `puede_cambiar_tipo`; excluir `codigo`, `creado_por` y `creado_en`
- [ ] T033 [US3] Implementar `editar_material` (`GET/POST`) en `materiales/views.py` con `@login_required`, `404` si no existe, `403` si no es creador ni admin y `405` para otros métodos
- [ ] T034 [US3] Agregar la ruta `/materiales/<int:id>/editar/` en `materiales/urls.py`
- [ ] T035 [US3] Crear la variante de edición de `templates/materiales/material_form.html`: código, creador y fecha en solo lectura, solo descripción y lote editables, sin acciones de borrado
- [ ] T036 [US3] Verificar en `materiales/services.py` que un intento rechazado (permiso, `codigo`, validación) no escribe auditoría y que los textos de error coinciden con `contracts/http-endpoints.md`

**Checkpoint**: US3 funcional e independiente; la auditoría refleja cada cambio.

---

## Fase 6: US4 — Tipo inmutable con stock o movimientos (P4)

**Objetivo**: permitir el cambio de tipo solo cuando ninguna verificación reporte stock o movimientos; en caso contrario rechazarlo con "El tipo no se puede cambiar: el material tiene movimientos" y no auditar el intento.

**Prueba independiente**: sin verificaciones registradas, cambiar de Seriado a No seriado se permite y se audita; registrar una verificación de prueba que simule movimientos y comprobar el `400` con el mensaje exacto, sin cambio de tipo ni auditoría; limpiar el registro al final.

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T037 [P] [US4] Pruebas unitarias del registro en `tests/unit/test_material_tipo.py`: sin verificaciones `puede_cambiar_tipo` es `True`; con una verificación que devuelve `True` es `False`; `registrar_verificacion_movimientos` agrega y permite limpiar el registro; orden de evaluación y fallo seguro
- [ ] T038 [P] [US4] Pruebas de integración y contrato en `tests/integration/test_material_tipo.py`: cambio permitido audita `tipo` con valor anterior y nuevo; con movimientos simulados la petición responde `400` "El tipo no se puede cambiar: el material tiene movimientos", el tipo no cambia y no se escribe auditoría

### Implementación de US4

- [ ] T039 [US4] Implementar en `materiales/services.py` el registro `_VERIFICACIONES_MOVIMIENTOS`, `registrar_verificacion_movimientos(func)` (con posibilidad de desregistrar) y `puede_cambiar_tipo(material)` que devuelve `False` si alguna verificación reporta stock o movimientos
- [ ] T040 [US4] Integrar la verificación en `actualizar_material` dentro de la transacción: si cambia `tipo` y `puede_cambiar_tipo` es `False`, lanzar `ValidacionMaterial` con el mensaje exacto sin escribir cambios ni auditoría; si se permite, auditar `tipo`
- [ ] T041 [US4] Exponer `puede_cambiar_tipo` en el contexto de `editar_material` y deshabilitar el campo tipo en la variante de edición de `templates/materiales/material_form.html` cuando sea `False`

**Checkpoint**: las cuatro historias son independientes y verificables; el catálogo queda completo.

---

## Fase 7: Pulido y asuntos transversales

**Propósito**: cerrar calidad, rendimiento, documentación y validación extremo a extremo.

- [ ] T042 [P] Agregar `tests/contract/test_material_sin_borrado.py`: ninguna ruta de materiales acepta `DELETE` (todas `405`) y no existe URL de borrado en `materiales/urls.py`
- [ ] T043 [P] Agregar `tests/integration/test_material_rendimiento.py` con `django_assert_num_queries` para el listado, la búsqueda y el fragmento, evitando N+1 en `materiales/views.py`
- [ ] T044 [P] Ejecutar `pytest --cov=materiales` y cerrar brechas hasta cubrir cada criterio de aceptación de `spec.md`
- [ ] T045 [P] Verificar que `05-especificaciones/013-registro-materiales/` use `materiales.Material` y corregir cualquier mención restante a `catalogo`; revisar también la mención de `catalogo` en `05-especificaciones/001-tenants-y-acceso/plan.md`
- [ ] T046 [P] Completar `03-reglas-de-dominio/catalogo-de-materiales.md` con las reglas vigentes de `05-especificaciones/002-materiales/spec.md` (hoy está vacío)
- [ ] T047 Ejecutar los escenarios manuales 1–11 de `05-especificaciones/002-materiales/quickstart.md` contra PostgreSQL y registrar el resultado
- [ ] T048 Ejecutar la suite completa (`pytest`) sobre PostgreSQL y confirmar los criterios de salida de `quickstart.md`, incluida la ausencia de secretos en auditoría y la ausencia de rutas de borrado

---

## Dependencias y orden de ejecución

### Dependencias de fase

- **Setup (Fase 1)**: depende de que la spec 001 esté implementada.
- **Fundacional (Fase 2)**: depende del Setup y **bloquea todas las historias** (modelo, migración, normalización y auditoría).
- **Historias (Fases 3–6)**: dependen de la Fase 2.
- **Pulido (Fase 7)**: depende de todas las historias que se entreguen.

### Dependencias entre historias

- **US1 (P1)**: sin dependencias posteriores a la Fase 2.
- **US2 (P2)**: requiere US1 (listado y datos existentes); reutiliza el modelo y la vista de listado.
- **US3 (P3)**: requiere US1 (material creado y auditado).
- **US4 (P4)**: requiere US3 (flujo de edición y auditoría de campos).

### Dentro de cada historia

1. Pruebas primero y en rojo.
2. Modelo → utilidades → formulario → servicio → vista → ruta → plantilla.
3. La auditoría se escribe dentro de la misma transacción que el cambio.
4. No se avanza con pruebas en rojo (constitución, puerta de pruebas).

### Oportunidades de paralelización

- Setup y Fundacional: `[P]` en archivos distintos (fixtures, navegación).
- US1: las cuatro pruebas `[P]` se escriben en paralelo; el formulario puede ir en paralelo con las pruebas.
- US2 y US3 pueden iniciarse en paralelo una vez completada US1, si hay capacidad.
- US4 depende de US3, pero sus pruebas unitarias (`[P]`) pueden escribirse antes.
- Pulido: tareas `[P]` independientes.

---

## Ejemplo de paralelización: US1

```bash
# Escribir primero todas las pruebas de US1 (archivos distintos):
Task: "Pruebas de contrato de alta en tests/contract/test_material_alta_http.py"
Task: "Pruebas de contrato de listado en tests/contract/test_material_lista_http.py"
Task: "Pruebas de integración de alta y auditoría en tests/integration/test_material_alta.py"
Task: "Pruebas de restricciones de base en tests/integration/test_restricciones_material.py"

# Implementación paralelizable:
Task: "Implementar MaterialForm en materiales/forms.py"
Task: "Implementar listar_materiales en materiales/services.py"
```

## Ejemplo de paralelización: US2 y US3

```bash
# Con US1 completo, dos personas pueden avanzar en paralelo:
Task: "Implementar buscar_materiales y obtener_datos_material en materiales/services.py"  # US2
Task: "Implementar actualizar_material y puede_editar_material en materiales/services.py" # US3

# Las pruebas de ambas historias viven en archivos distintos y pueden escribirse a la vez:
Task: "tests/contract/test_material_busqueda_http.py y test_material_fragmento_http.py"   # US2
Task: "tests/contract/test_material_edicion_http.py"                                      # US3
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 (Setup).
2. Completar Fase 2 (Fundacional) — **crítica**.
3. Completar Fase 3 (US1).
4. **DETENERSE y VALIDAR**: alta, validaciones, duplicado, auditoría y listado básico.
5. Desplegar/demostrar si está listo.

> US1 ya entrega valor: el catálogo puede poblarse y consultarse. US2 lo hace utilizable por los
> demás módulos; US3 y US4 completan la trazabilidad y la integridad del tipo.

### Entrega incremental

1. Setup + Fundacional → app y tabla listas.
2. US1 → alta y listado (MVP).
3. US2 → búsqueda global y fragmento para 004/005/006/009/013.
4. US3 → edición con permisos y auditoría por campo.
5. US4 → inmutabilidad del tipo con movimientos.
6. Pulido → cobertura, rendimiento, documentación y escenarios manuales.

### Estrategia de equipo en paralelo

1. Todo el equipo completa Setup + Fundacional.
2. Al terminar la Fase 2:
   - Persona A: US1 (alta y listado).
   - Persona B: prepara las pruebas y el contrato de US2 mientras US1 se estabiliza.
   - Persona C: prepara la matriz de permisos y auditoría de US3.
3. Con US1 listo: US2 y US3 en paralelo (archivos de servicios y pruebas distintos).
4. US4 después de US3; pulido al final.

---

## Notas

- `[P]` significa archivos distintos y sin dependencia de tareas incompletas.
- `[Story]` traza cada tarea a su historia y a los criterios de aceptación de `spec.md`.
- El catálogo es global: ninguna tarea agrega `tenant_id` ni filtros por tenant.
- El código nunca se edita: ni el formulario ni el servicio lo permiten.
- No se crea ninguna ruta de borrado; `DELETE` responde `405`.
- Toda alta y todo cambio se auditan en la misma transacción; nunca se auditan secretos.
- La app se llama `materiales` (no `catalogo`); la deuda documental se corrige en T045/T046.
- Las tareas de la spec 001 (`acceso`, `auditoria`, `config/settings`) se asumen implementadas; si faltan, T001 detiene el trabajo.
- Commit tras cada tarea o grupo lógico; detenerse en cada checkpoint para validar la historia de forma independiente.
- Evitar: tareas vagas, conflictos en el mismo archivo y dependencias entre historias que rompan la independencia.
