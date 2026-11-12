# Plan técnico: 002 Módulo de materiales

**Branch**: `002-materiales` | **Date**: 2026-11-12 | **Spec**: `05-especificaciones/002-materiales/spec.md`

**Input**: Spec en `05-especificaciones/002-materiales/spec.md`

## Summary

Implementar el catálogo compartido de materiales que Lari introduce en el almacén central:
alta con código de 11 dígitos único e inmutable, descripción, lote y tipo (seriado o no
seriado); edición restringida al creador o al Administrador de plataforma; búsqueda global por
código o descripción reutilizable por los módulos de recojo, stock inicial, asignación y
traspaso; y auditoría de altas y cambios. Es la **única excepción documentada** al aislamiento
multitenant: el catálogo no lleva `tenant_id` y todos los tenants ven los mismos materiales.
El diseño reutiliza el modelo de usuario, el middleware de contexto y el libro
`auditoria.RegistroCambio` de la spec 001, y no agrega dependencias al stack.

## Technical Context

**Language/Version**: Python 3.12+ (fijado por la constitución y ADR-015)

**Primary Dependencies**: Django LTS 5.x, HTMX, PostgreSQL 16+ y `pytest`/`pytest-django`
(ya fijados por la spec 001). **Sin dependencias nuevas**: la búsqueda usa `icontains` de
Django y la paginación nativa; no se requiere motor de búsqueda ni `pg_trgm` en esta versión.

**Storage**: PostgreSQL 16+ compartido. Tabla `materiales_material` sin `tenant_id` por ser
catálogo global (excepción al principio I, declarada en `spec.md` §Reglas de negocio). Tabla de
auditoría `auditoria_registrocambio` creada por la spec 001.

**Testing**: pytest + pytest-django contra PostgreSQL (sin SQLite), con pruebas de contrato
HTTP, integración de servicios y restricciones de base de datos. Un caso por criterio de
aceptación.

**Target Platform**: servidor Linux (Gunicorn + Nginx); interfaz web server-rendered con HTMX;
desarrollo local en Windows o Linux.

**Project Type**: aplicación web monolítica modular Django; esta spec agrega una app
(`materiales`) al proyecto ya planificado en 001.

**Performance Goals**: listado y búsqueda p95 < 300 ms con ~10 000 materiales; fragmento HTMX
de autocompletado p95 < 200 ms con límite de 20 resultados; listado paginado a 50 filas.

**Constraints**: código de exactamente 11 dígitos, único global e inmutable; sin eliminación
de materiales; solo creador o Administrador de plataforma editan descripción y lote; el tipo no
cambia si el material tiene stock o movimientos; toda alta y cambio se audita en la misma
transacción; el catálogo nunca se filtra por tenant.

**Scale/Scope**: ~100 tenants y un catálogo estimado de 1 000–10 000 materiales; 1 entidad
(`Material`); 4 rutas HTTP; 12 criterios de aceptación.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA con excepción documentada | El catálogo compartido es la única excepción admitida por `spec.md` §Reglas de negocio y por la propia spec 001; no hay `tenant_id` y ninguna consulta se filtra por tenant. No se expone información de qué cuenta/tenant creó un material más allá de la auditoría administrativa |
| II. Jerarquía Región → Tenant → Técnico | N/A (no contradice) | `Material` es global y no participa de la jerarquía; los consumidores lo referencian desde sus tablas operativas con `PROTECT` |
| III. Invariantes de stock | N/A | Esta spec no modifica stock; solo expone la regla de tipo inmutable cuando existan movimientos |
| IV. Identidad y unicidad de series | N/A | Esta spec no gestiona series |
| V. Integridad transaccional | PASA | Alta y edición se ejecutan en `transaction.atomic` junto con la auditoría; la restricción única resuelve el doble envío concurrente |
| VI. Auditoría inmutable y trazabilidad | PASA | Un `RegistroCambio` por campo modificado, en la misma transacción; nunca se auditan contraseñas, tokens ni secretos |
| VII. Autoridad del reporte de Lari | N/A | Esta spec no procesa conciliaciones |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada criterio de aceptación tiene prueba; no se agregan dependencias; la lógica vive en `materiales/services.py` y es testeable sin interfaz |

Sin violaciones que justificar. `Complexity Tracking` queda vacío. La excepción al principio I
no es una violación: está declarada en la spec y en las reglas de dominio.

## Project Structure

### Documentation (this feature)

```text
05-especificaciones/002-materiales/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   ├── http-endpoints.md
│   ├── busqueda-materiales.md
│   └── auditoria-material.md
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

Estructura existente planificada por la spec 001; esta spec agrega `materiales/`.

```text
manage.py
config/
├── settings/
│   ├── base.py
│   ├── dev.py
│   ├── prod.py
│   └── test.py
├── urls.py
└── celery.py

acceso/                 # spec 001: Usuario, Rol, middleware
auditoria/              # spec 001: RegistroCambio, services.registrar_cambio
tenants/                # spec 001: Region, Almacen, Tenant

materiales/             # NUEVA app de esta spec
├── models.py           # Material
├── services.py         # crear_material, actualizar_material, puede_cambiar_tipo, búsqueda
├── forms.py            # MaterialForm, MaterialEdicionForm
├── views.py            # listado, búsqueda HTMX, alta, edición
├── urls.py
├── migrations/
│   └── 0001_initial.py
└── admin.py            # registro de solo lectura (opcional, sin superusuario)

templates/
└── materiales/
    ├── materiales_lista.html
    ├── material_form.html
    └── _filas_busqueda.html

tests/
├── contract/
│   └── test_materiales_http.py
├── integration/
│   └── test_materiales.py
└── unit/
    └── test_materiales_servicios.py
```

**Structure Decision**: se conserva el monolito modular de la spec 001. La app se llama
`materiales` —no `catalogo`— para coincidir con las referencias concretas ya escritas por las
specs 004, 005, 006, 008, 009, 010 y 011 (`"materiales.Material"`) y con las rutas
`/materiales/` de esta spec. Las referencias a `catalogo.Material` en la spec 013 deben
corregirse antes de implementarla (ver `research.md` §1). Las reglas de negocio viven en
`materiales/services.py`, nunca en las vistas.

## Referencias
- Spec: `05-especificaciones/002-materiales/spec.md`
- Reglas: `03-reglas-de-dominio/catalogo-de-materiales.md` (vacío a la fecha),
  `03-reglas-de-dominio/auditoria.md`
- Specs consumidoras: 004 (recojo), 005 (stock inicial), 006 (asignación), 008 (confirmación de
  stock), 009 (traspaso), 010 (conciliación), 011 (logística inversa), 013 (registro de materiales)
- ADR: ADR-002 (esquema compartido), ADR-015 (stack), ADR-019 (usuario único)
- Constitución 1.3.0

## Módulos afectados
- App Django nueva `materiales`: modelo `Material`, servicios, formularios, vistas y búsqueda.
- App `auditoria` (spec 001): se reutiliza `RegistroCambio` y `registrar_cambio`; si la app no
  existe todavía, esta spec no la crea: 001 es su dueña.
- `config/urls.py`: inclusión de `materiales/urls.py`.
- `templates/base.html` (spec 001): se agrega el enlace de navegación a Materiales.
- No se modifican modelos de inventario, técnicos, recojos ni conciliación.

## Modelo de datos

```python
class Material(models.Model):
    codigo = models.CharField(max_length=11, unique=True)
    descripcion = models.CharField(max_length=100)
    lote = models.CharField(max_length=50, blank=True, default="")
    es_seriado = models.BooleanField()
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(codigo__regex=r"^[0-9]{11}$"),
                name="material_codigo_11_digitos",
            ),
            models.CheckConstraint(
                condition=~Q(descripcion=""),
                name="material_descripcion_obligatoria",
            ),
        ]

    @property
    def tipo(self):
        return "SERIADO" if self.es_seriado else "NO_SERIADO"
```

- Sin `tenant_id`: el catálogo es compartido (única excepción al principio I).
- `unique=True` sobre `codigo` crea el índice único global y resuelve el doble envío.
- El `CheckConstraint` con expresión regular impide códigos inválidos aunque se salte la
  validación de aplicación.
- `descripcion` se guarda normalizada (sin espacios al inicio/final ni repetidos).
- `lote` se guarda normalizado en mayúsculas y admite vacío.
- `es_seriado` es la fuente de verdad del tipo; la propiedad `tipo` expone `SERIADO` /
  `NO_SERIADO` para formularios, búsqueda, auditoría y specs consumidoras.
- No hay transiciones de estado ni borrado lógico: el material existe desde su alta y se
  conserva aunque su creador se desactive (`creado_por` con `PROTECT`).

### Auditoría

Se reutiliza `auditoria.RegistroCambio` (spec 001). Eventos propios de esta spec:

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Alta de material | `Material` | `alta` | — | `codigo`, `descripcion`, `lote`, `tipo` |
| Edición de descripción | `Material` | `descripcion` | valor anterior | valor nuevo |
| Edición de lote | `Material` | `lote` | valor anterior | valor nuevo |

- Un registro por campo modificado, en la misma `transaction.atomic` que el cambio.
- Si el cambio falla (permiso, código duplicado, tipo inmutable), no se audita.
- Nunca se auditan contraseñas, tokens, secretos ni datos sensibles.

### Migraciones
- `materiales/migrations/0001_initial.py`: `Material`, con `unique(codigo)`, los dos
  `CheckConstraint` y los índices de clave foránea.
- No se crean datos maestros ni materiales por migración.
- `AUTH_USER_MODEL = "acceso.Usuario"` ya debe existir (spec 001) antes de aplicar esta
  migración.

## Servicios (lógica de negocio)
Viven en `materiales/services.py`, no en las vistas.

- `crear_material(datos, usuario)`:
  - Verifica que `usuario` esté activo y tenga rol autenticado (cualquiera de los tres roles).
  - Normaliza `codigo` (strip), `descripcion` (strip + colapsa espacios internos) y `lote`
    (strip + colapsa espacios + mayúsculas).
  - Valida 11 dígitos exactos, descripción de 1–100, lote de hasta 50 y tipo obligatorio.
  - En `transaction.atomic`: crea el material y el registro de auditoría `alta`.
  - Captura `IntegrityError` de `codigo` y devuelve "El material ya existe".
- `actualizar_material(material, cambios, usuario)`:
  - Valida permiso con `puede_editar_material(material, usuario)`; si no, lanza
    `PermisoDenegado` con "No tienes permiso para editar este material".
  - Rechaza cualquier clave `codigo` en `cambios` con "El código no se puede cambiar".
  - Normaliza `descripcion` y `lote` con las mismas reglas del alta.
  - Si `es_seriado`/`tipo` cambia, exige `puede_cambiar_tipo(material)`.
  - En `transaction.atomic` con `select_for_update`: aplica cambios, completa
    `actualizado_por`/`actualizado_en` y registra un `RegistroCambio` por campo modificado.
- `puede_editar_material(material, usuario)`:
  - `True` si `material.creado_por_id == usuario.id` o el usuario es
    `ADMIN_PLATAFORMA` (helper de rol de la spec 001).
- `puede_cambiar_tipo(material)`:
  - Consulta el registro de verificaciones `_VERIFICACIONES_MOVIMIENTOS`; devuelve `False` si
    cualquiera reporta stock o movimientos para el material.
  - Se expone `registrar_verificacion_movimientos(func)` para que las specs 004–011 registren
    su verificación real cuando existan sus tablas. Hoy, sin verificaciones registradas,
    devuelve `True`.
  - Las pruebas registran una verificación temporal que simula movimientos y validan el
    rechazo con "El tipo no se puede cambiar: el material tiene movimientos".
- `buscar_materiales(q="")`:
  - Devuelve `Material.objects.all()` si `q` está vacío.
  - Si `q` tiene contenido, filtra por `codigo__icontains=q` **o**
    `descripcion__icontains=q`.
  - Orden estable por `codigo`; sin filtro de tenant; paginación de 50 en listado y límite de
    20 en el fragmento HTMX.
- `obtener_datos_material(material)`:
  - Devuelve `codigo`, `descripcion`, `lote`, `tipo` para el autocompletado de las specs
    004, 005, 006, 009 y 013.

## Permisos
- **Crear**: cualquier cuenta autenticada y activa (tenant, almacén o administrador). La spec
  permite que cualquier tenant registre materiales; la restricción real está en el código único.
- **Editar descripción y lote**: únicamente `creado_por == usuario` o rol
  `ADMIN_PLATAFORMA`. La vista aplica la misma comprobación y el servicio la revalida.
- **Cambiar el código**: nadie; el campo no existe en el formulario de edición y el servicio
  rechaza la clave.
- **Cambiar el tipo**: creador o Administrador, y solo si `puede_cambiar_tipo` lo permite.
- **No eliminar**: no hay ruta ni vista de borrado; `DELETE` responde `405`.
- Los permisos se validan siempre en el backend; ocultar un botón no es autorización.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/materiales/` | GET | Listado paginado con búsqueda por `q` |
| `/materiales/buscar/?q=` | GET | Fragmento HTMX con resultados para otros módulos |
| `/materiales/nuevo/` | GET / POST | Alta de material |
| `/materiales/<id>/editar/` | GET / POST | Edición de descripción y lote |

### Pantallas
- **Listado**: código, descripción, lote, tipo, creador y fecha; buscador; paginación de 50.
- **Alta**: código (11 dígitos), descripción, lote (opcional) y tipo; el botón Guardar se
  desactiva al primer clic con `hx-disabled-elt` y la restricción única evita duplicados.
- **Edición**: código, tipo y creador en solo lectura; solo descripción y lote editables; el
  formulario de tipo se muestra deshabilitado cuando `puede_cambiar_tipo` es `False`.
- **Búsqueda (fragmento)**: filas con `data-codigo`, `data-descripcion`, `data-lote` y
  `data-tipo`; estado vacío explícito.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Exactamente 11 dígitos | Formulario, servicio y `CheckConstraint` | "El código debe tener 11 dígitos" |
| Código único global | Servicio y restricción `unique` | "El material ya existe" |
| Descripción obligatoria (1–100) | Formulario y servicio | "La descripción es obligatoria" |
| Lote máximo 50 y opcional | Formulario y servicio | "El lote no puede superar los 50 caracteres" |
| Tipo obligatorio | Formulario y `BooleanField` | "El tipo es obligatorio" |
| Código inmutable | Formulario (campo ausente) y servicio | "El código no se puede cambiar" |
| Permiso de edición | Servicio y vista | "No tienes permiso para editar este material" |
| Tipo inmutable con movimientos | Servicio (`puede_cambiar_tipo`) | "El tipo no se puede cambiar: el material tiene movimientos" |

## Transacciones y concurrencia
- El alta crea el material y su auditoría en una sola transacción.
- La edición bloquea la fila (`select_for_update`), aplica cambios y audita en la misma
  transacción.
- El doble clic y las altas simultáneas del mismo código se resuelven con la restricción
  `unique` y la traducción de `IntegrityError` a "El material ya existe"; no se usan bloqueos de
  aplicación ni comprobaciones "leer y luego insertar" como fuente de verdad.
- La normalización ocurre antes de la validación, de modo que dos variantes de espaciado del
  mismo código no burlan la unicidad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos (coinciden con la spec y con
`plan.md` §Pruebas anterior):

- `test_crear_material_con_codigo_nuevo_registra_creador_y_fecha`
- `test_codigo_duplicado_se_rechaza_sin_revelar_tenant`
- `test_codigo_con_longitud_incorrecta_o_letras_se_rechaza`
- `test_material_sin_lote_se_guarda_con_lote_vacio`
- `test_lote_visible_para_otro_tenant_en_busqueda`
- `test_editar_descripcion_registra_valor_anterior_y_nuevo`
- `test_usuario_sin_permiso_no_puede_editar_descripcion_ni_lote`
- `test_codigo_no_es_editable`
- `test_cambio_de_tipo_rechazado_si_hay_movimientos`
- `test_descripcion_solo_espacios_se_rechaza`
- `test_doble_envio_no_crea_duplicado`
- `test_busqueda_por_descripcion_devuelve_material`
- `test_busqueda_por_codigo_devuelve_material`
- `test_busqueda_vacia_devuelve_listado_paginado`
- `test_lote_se_normaliza_en_mayusculas`
- `test_descripcion_se_normaliza_sin_espacios_repetidos`
- `test_codigo_con_espacios_o_guiones_se_rechaza`
- `test_material_se_conserva_si_se_desactiva_su_creador`

Pruebas de contrato HTTP (rutas, roles, códigos y mensajes) y de base de datos (inserción
directa de un código de 10 dígitos o con letras falla por `CheckConstraint`; código duplicado
falla por `unique`) viven en `tests/contract/` e `tests/integration/`.

## Decisiones y riesgos
- **App `materiales` y no `catalogo`:** siete specs consumidoras ya referencian
  `materiales.Material`; la spec 013 usa `catalogo.Material` y debe corregirse. Detalle en
  `research.md`.
- **Catálogo compartido:** cualquier cuenta activa crea materiales; un error de descripción
  afecta a todos. Mitigación: auditoría, edición restringida y unicidad del código. La
  aprobación previa de materiales está fuera de alcance.
- **Lote en mayúsculas:** la spec lo propone como supuesto; se implementa así y se documenta.
  Si Lari envía lotes que distinguen mayúsculas, se corrige la spec primero.
- **Tipo inmutable con movimientos:** hoy no existen tablas de stock; la regla se implementa
  con un registro de verificaciones para no inventar tablas ni un campo desnormalizado.
- **Doble clic:** se resuelve con la restricción única, no con estado en sesión.
- **Sin eliminación:** no hay ruta de borrado y `creado_por` usa `PROTECT`; desactivar la
  cuenta del creador no borra el material.
- **Búsqueda:** `icontains` es suficiente para el tamaño estimado. Si el catálogo supera
  ~50 000 filas, se evaluará un índice `pg_trgm` en una spec posterior.
- **Consulta de auditoría de materiales:** el registro se escribe, pero su pantalla de consulta
  pertenece a la auditoría administrativa (spec 001); esta spec no expone una ruta de auditoría.

## Complexity Tracking

> Sin violaciones a la constitución. La única excepción (catálogo compartido) está declarada en
> la spec y en el principio I. No se agregan dependencias ni patrones adicionales.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Ninguna | — | — |

## Artefactos de diseño

| Artefacto | Contenido |
|---|---|
| `research.md` | Decisiones: nombre de app, reutilización de auditoría, representación del tipo, permisos, inmutabilidad del tipo, normalización, búsqueda y concurrencia |
| `data-model.md` | Entidad `Material`, campos, restricciones, índices, reglas de normalización y eventos de auditoría |
| `contracts/http-endpoints.md` | Rutas, roles, peticiones, respuestas, códigos y mensajes |
| `contracts/busqueda-materiales.md` | Contrato del fragmento HTMX consumido por 004, 005, 006, 009 y 013 |
| `contracts/auditoria-material.md` | Eventos auditados, datos prohibidos y reglas de escritura |
| `quickstart.md` | Escenarios ejecutables de validación extremo a extremo |
