# Plan técnico: 003 Técnicos del tenant

**Branch**: `003-tecnicos` | **Date**: 2026-11-12 | **Spec**: `05-especificaciones/003-tecnicos/spec.md`

**Input**: Spec en `05-especificaciones/003-tecnicos/spec.md`

## Summary

Implementar la gestión de los técnicos de cada tenant: alta con NIF `LAXXXX` único en todo el
sistema y nombre obligatorio, edición del nombre con NIF y tenant inmutables, desactivación y
reactivación sin eliminación física, búsqueda por NIF o nombre limitada al tenant de la sesión y
un selector HTMX de técnicos activos para los módulos de stock inicial, asignación, traspaso y
registro de materiales; la conciliación resuelve el NIF por servicio dentro de su tenant. Toda
alta, cambio de nombre, desactivación y reactivación
se audita en `auditoria.RegistroCambio`, en la misma transacción. El diseño reutiliza la cuenta
única, el middleware de contexto y la auditoría de la spec 001; no agrega dependencias ni tablas
de stock, y no permite que el Administrador de plataforma ni el Responsable de almacén gestionen
técnicos.

## Technical Context

**Language/Version**: Python 3.12+ (fijado por la constitución y ADR-015)

**Primary Dependencies**: Django LTS 5.x, HTMX, PostgreSQL 16+ y `pytest`/`pytest-django`
(ya fijados por la spec 001). **Sin dependencias nuevas**: la búsqueda usa `icontains` de Django
y la paginación nativa; no se requiere motor de búsqueda ni `pg_trgm` en esta versión.

**Storage**: PostgreSQL 16+ compartido. Tabla `tecnicos_tecnico` con `tenant_id`, filtrada
siempre por el tenant de la sesión y respaldada por RLS cuando esté disponible. Tabla de
auditoría `auditoria_registrocambio` creada por la spec 001. No se agregan tablas de stock,
series, asignaciones, traspasos, conciliaciones ni registro de materiales.

**Testing**: pytest + pytest-django contra PostgreSQL (sin SQLite), con pruebas de contrato HTTP,
integración de servicios, transiciones de estado y restricciones de base de datos. Un caso por
criterio de aceptación.

**Target Platform**: servidor Linux (Gunicorn + Nginx); interfaz web server-rendered con HTMX;
desarrollo local en Windows o Linux.

**Project Type**: aplicación web monolítica modular Django; esta spec agrega una app (`tecnicos`)
al proyecto ya planificado en 001.

**Performance Goals**: listado y búsqueda p95 < 300 ms con ~5 000 técnicos; fragmento HTMX de
autocompletado p95 < 200 ms con límite de 20 resultados; listado paginado a 50 filas.

**Constraints**: NIF `LA` + 4 dígitos, único global e inmutable; nombre obligatorio de 1–100
caracteres; tenant inmutable y obtenido solo de la sesión; sin eliminación física; solo la cuenta
del tenant gestiona técnicos; los selectores de operaciones nuevas muestran solo técnicos
activos; toda alta, cambio y transición de estado se audita en la misma transacción.

**Scale/Scope**: ~100 tenants y un estimado de 50 técnicos por tenant (≈5 000 filas globales);
1 entidad (`Tecnico`); 7 rutas HTTP; 21 criterios de aceptación.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | El tenant sale de `request.usuario`/`request.tenant`, nunca de un parámetro del cliente. Toda consulta filtra por `tenant`; un técnico de otro tenant se trata como inexistente (`404`) sin revelar su existencia. La unicidad global del NIF no expone el tenant propietario: el mensaje de duplicado es uniforme |
| II. Jerarquía Región → Tenant → Técnico | PASA | `Tecnico` pertenece a exactamente un tenant y no guarda región: la región se deriva de `tenant.region`. El técnico es un actor pasivo sin cuenta ni sesión; la cuenta operativa sigue siendo única por tenant |
| III. Invariantes de stock | PASA (sin modificar stock) | Esta spec no crea ni mueve stock. La desactivación conserva el stock y el historial; las operaciones de devolución o traspaso pertenecen a las specs 009 y 011 |
| IV. Identidad y unicidad de series | N/A | Esta spec no gestiona series |
| V. Integridad transaccional | PASA | Alta, edición, desactivación y reactivación se ejecutan en `transaction.atomic` junto con su auditoría. La restricción única del NIF resuelve dos altas concurrentes |
| VI. Auditoría inmutable y trazabilidad | PASA | Se reutiliza `RegistroCambio`; un registro por campo modificado, en la misma transacción. Nunca se auditan contraseñas, tokens ni secretos. Desactivar no borra la auditoría |
| VII. Autoridad del reporte de Lari | N/A | Esta spec no procesa reportes ni conciliaciones; solo expone técnicos que las specs consumidoras resolverán dentro de su tenant |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada criterio de aceptación tiene prueba; no se agregan dependencias; la lógica vive en `tecnicos/services.py` y es testeable sin interfaz |

Sin violaciones que justificar. `Complexity Tracking` queda vacío. La unicidad global del NIF no
contradice el principio I porque es una restricción de identidad, no una consulta entre tenants,
y el mensaje de error nunca revela el tenant propietario.

**Re-evaluación tras la Fase 1**: el diseño de `data-model.md` y de los contratos mantiene el
filtro por tenant en todas las consultas, la auditoría en la misma transacción y la ausencia de
rutas de borrado. No aparecieron violaciones nuevas ni incógnitas pendientes; la puerta sigue en
verde.

## Project Structure

### Documentation (this feature)

```text
05-especificaciones/003-tecnicos/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   ├── http-endpoints.md
│   ├── busqueda-tecnicos.md
│   └── auditoria-tecnico.md
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

Estructura existente planificada por la spec 001; esta spec agrega `tecnicos/`.

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

tecnicos/               # NUEVA app de esta spec
├── models.py           # Tecnico
├── services.py         # alta, edición, estado, búsqueda y helpers de integración
├── forms.py            # TecnicoForm, TecnicoEdicionForm
├── views.py            # listado, búsqueda HTMX, alta, detalle, edición, estado
├── urls.py
├── migrations/
│   └── 0001_initial.py
└── admin.py            # registro de solo lectura (opcional, sin superusuario)

templates/
└── tecnicos/
    ├── tecnicos_lista.html
    ├── tecnico_form.html
    ├── tecnico_detalle.html
    └── _filas_busqueda.html

tests/
├── contract/
│   └── test_tecnicos_http.py
├── integration/
│   └── test_tecnicos.py
└── unit/
    └── test_tecnicos_servicios.py
```

**Structure Decision**: se conserva el monolito modular de la spec 001. La app se llama
`tecnicos` y el modelo `Tecnico`, que es la referencia ya usada por las specs consumidoras
(`"tecnicos.Tecnico"` en 005, 006, 009 y 013; `tecnicos_para_operacion` en 009;
`validar_tecnico_para_operacion` en 006). La región no se duplica en el técnico: se deriva de
`tenant.region`. Las reglas de negocio viven en `tecnicos/services.py`, nunca en las vistas.

## Referencias
- Spec: `05-especificaciones/003-tecnicos/spec.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `03-reglas-de-dominio/series.md`,
  `03-reglas-de-dominio/registro-materiales.md`, `03-reglas-de-dominio/auditoria.md`
- Specs consumidoras: 004 (recojo), 005 (stock inicial), 006 (asignación), 009 (traspaso),
  010 (conciliación), 011 (logística inversa), 013 (registro de materiales)
- ADR: ADR-003 (aislamiento multitenant), ADR-007 (auditoría), ADR-019 (cuenta única por tenant)
- Constitución 1.3.0

## Módulos afectados
- App Django nueva `tecnicos`: modelo `Tecnico`, servicios, formularios, vistas y búsqueda.
- App `auditoria` (spec 001): se reutiliza `RegistroCambio` y `registrar_cambio`; si la app no
  existe todavía, esta spec no la crea: 001 es su dueña.
- `config/urls.py`: inclusión de `tecnicos/urls.py`.
- `templates/base.html` (spec 001): se agrega el enlace de navegación a Técnicos, visible solo
  para la cuenta del tenant.
- No se modifican stock, series, asignaciones, traspasos, conciliaciones ni registro de
  materiales. Las specs consumidoras agregan sus propias FK `PROTECT` a `Tecnico`.

## Modelo de datos

```python
class Tecnico(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="tecnicos",
    )
    nif = models.CharField(max_length=6, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre", "nif"]
        constraints = [
            models.CheckConstraint(
                condition=Q(nif__regex=r"^LA[0-9]{4}$"),
                name="tecnico_nif_formato",
            ),
            models.CheckConstraint(
                condition=~Q(nombre=""),
                name="tecnico_nombre_obligatorio",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "activo"], name="tecnico_tenant_activo"),
            models.Index(fields=["tenant", "nombre"], name="tecnico_tenant_nombre"),
        ]

    def __str__(self):
        return f"{self.nif} - {self.nombre}"
```

- `nif` es único global (`unique=True`) y mide exactamente 6 caracteres cuando es válido. Se usa
  `max_length=6` —no 10— para que la longitud del campo y el `CheckConstraint` coincidan con el
  formato `LAXXXX`; una entrada más larga se rechaza antes de llegar a la base.
- `tenant` usa `PROTECT` porque un tenant no se elimina y el técnico conserva su historial. La
  relación es inmutable después del alta.
- No se guarda `region`: se obtiene desde `tenant.region`.
- `activo` no borra datos; solo controla la disponibilidad para operaciones nuevas.
- Los índices cubren el listado y la búsqueda por tenant, estado y nombre.
- La restricción `tecnico_nif_formato` protege la base de datos aunque se salte la validación de
  la aplicación.
- La restricción `tecnico_nombre_obligatorio` impide nombres vacíos por inserción directa; la
  longitud máxima la impone `varchar(100)`.
- `creado_por` y `actualizado_por` usan `PROTECT`: desactivar una cuenta no elimina sus técnicos
  ni su auditoría.

### Auditoría

Se reutiliza `auditoria.RegistroCambio` (spec 001). Eventos propios de esta spec:

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Alta de técnico | `Tecnico` | `alta` | — | `nif`, `nombre`, `estado=ACTIVO` |
| Edición de nombre | `Tecnico` | `nombre` | nombre anterior | nombre nuevo |
| Desactivación | `Tecnico` | `activo` | `ACTIVO` | `DESACTIVADO` |
| Reactivación | `Tecnico` | `activo` | `DESACTIVADO` | `ACTIVO` |

- Un registro por campo modificado, en la misma `transaction.atomic` que el cambio.
- Si el cambio falla (permiso, NIF duplicado, NIF/tenant inmutable, tenant suspendido), no se
  audita.
- Una operación idempotente (desactivar dos veces o reactivar dos veces) no cambia el estado ni
  duplica la auditoría.
- Nunca se auditan contraseñas, tokens, secretos ni datos sensibles. La auditoría no guarda un
  `tenant_id` separado: el alcance se deriva de la entidad `Tecnico` y de la cuenta autora.

### Migraciones
- `tecnicos/migrations/0001_initial.py`: `Tecnico`, con `unique(nif)`, los dos
  `CheckConstraint`, los índices y las claves foráneas.
- No se crean técnicos, cuentas ni datos maestros por migración.
- No se modifican tablas de stock, series, asignaciones, traspasos ni conciliaciones.
- `AUTH_USER_MODEL = "acceso.Usuario"` y `tenants.Tenant` ya deben existir (spec 001) antes de
  aplicar esta migración.

## Servicios (lógica de negocio)
Viven en `tecnicos/services.py`, no en las vistas.

### Excepciones
- `ValidacionTecnico`: error de formato o de nombre.
- `NifDuplicado`: conflicto de unicidad global.
- `PermisoDenegado`: rol o alcance incorrecto.
- `NoEncontrado`: técnico inexistente o de otro tenant.
- `TecnicoNoDisponible`: técnico desactivado en una operación nueva.
- `TenantSuspendido`: tenant con estado `SUSPENDIDO`.

### Alcance y permisos
- `validar_cuenta_tenant(actor, tenant=None)`:
  - Exige `actor.rol == Rol.USUARIO_TENANT`.
  - Exige que `actor.is_active` sea verdadero.
  - Exige que `actor.tenant` exista y que `actor.tenant.estado == "ACTIVO"`; si no, lanza
    `TenantSuspendido` con "El tenant está suspendido".
  - Si se recibe `tenant`, exige `actor.tenant_id == tenant.id`.
  - Cualquier otro rol o tenant lanza `PermisoDenegado` con "No tienes permiso para gestionar
    técnicos".
  - Devuelve el tenant de la sesión. No acepta un `tenant_id` externo.
- `obtener_tecnico(tenant, tecnico_id)`:
  - Busca con `Tecnico.objects.filter(tenant=tenant, id=tecnico_id)`.
  - Si no existe o pertenece a otro tenant, lanza `NoEncontrado` con "El técnico no existe".
- `validar_tecnico_para_operacion(tenant, tecnico_id)`:
  - Usa `obtener_tecnico`.
  - Exige que el tenant esté activo.
  - Exige `activo=True`; si no, lanza `TecnicoNoDisponible` con "El técnico está desactivado".
  - Devuelve el técnico. La usan asignaciones, traspasos, conciliación y registro de materiales.

### Normalización y validación
- `normalizar_nif(nif)`:
  - Elimina espacios al inicio y al final.
  - Convierte a mayúsculas.
  - No elimina guiones ni espacios internos: el formato estricto los rechaza.
- `validar_nif(nif)`:
  - Debe cumplir `^LA[0-9]{4}$`.
  - Si no, lanza `ValidacionTecnico` con "El NIF debe tener el formato LAXXXX".
- `normalizar_nombre(nombre)`:
  - Elimina espacios al inicio y al final.
  - Colapsa espacios internos repetidos.
- `validar_nombre(nombre)`:
  - No vacío; si lo es, "El nombre es obligatorio".
  - Máximo 100 caracteres; si lo supera, "El nombre no puede superar los 100 caracteres".

### Alta
- `crear_tecnico(datos, actor)`:
  - `validar_cuenta_tenant(actor)`; el tenant se toma de `actor.tenant`.
  - Normaliza y valida NIF y nombre.
  - Busca el NIF en todo el sistema. Si existe un técnico **activo**, lanza `NifDuplicado` con
    "El NIF ya está registrado". Si existe uno **desactivado del mismo tenant**, lanza
    `NifDuplicado` con "El NIF ya está registrado; reactiva el técnico existente". Si está
    desactivado en otro tenant, mantiene el mensaje uniforme "El NIF ya está registrado" para no
    revelar datos ajenos.
  - En `transaction.atomic`, crea el técnico activo y registra la auditoría de alta.
  - Si la base de datos rechaza el NIF duplicado (`IntegrityError`), traduce a "El NIF ya está
    registrado".
  - No acepta `tenant`, `tenant_id`, `region` ni `region_id` desde el formulario.

### Edición
- `actualizar_tecnico(tecnico, cambios, actor)`:
  - `validar_cuenta_tenant(actor, tecnico.tenant)`.
  - Rechaza cualquier clave `nif` con "El NIF no se puede cambiar".
  - Rechaza cualquier clave `tenant` o `tenant_id` con "El tenant del técnico no se puede
    cambiar".
  - Solo permite cambiar `nombre`.
  - Normaliza y valida el nombre.
  - En `transaction.atomic` con `select_for_update`, aplica el cambio, actualiza
    `actualizado_por`/`actualizado_en` y registra un `RegistroCambio` si el nombre cambió.
  - Si el nombre no cambió, no escribe cambios, no actualiza los metadatos y no genera auditoría
    duplicada.
  - Editar el nombre de un técnico desactivado se permite: es una corrección administrativa y no
    habilita al técnico para operaciones nuevas.

### Estado
- `desactivar_tecnico(tecnico, actor)`:
  - `validar_cuenta_tenant(actor, tecnico.tenant)`.
  - En `transaction.atomic` con `select_for_update`.
  - Si ya está desactivado, no hace cambios ni duplica auditoría.
  - Marca `activo=False`, actualiza `actualizado_por`/`actualizado_en` y audita el valor anterior
    y el nuevo.
  - No borra stock, series, asignaciones, traspasos, órdenes ni conciliaciones.
- `reactivar_tecnico(tecnico, actor)`:
  - `validar_cuenta_tenant(actor, tecnico.tenant)`.
  - En `transaction.atomic` con `select_for_update`.
  - Si ya está activo, no hace cambios ni duplica auditoría.
  - Marca `activo=True`, actualiza `actualizado_por`/`actualizado_en` y audita el valor anterior y
    el nuevo.

### Consultas
- `buscar_tecnicos(tenant, q="", solo_activos=False, estado=None)`:
  - Filtra siempre por `tenant`.
  - Si `q` tiene contenido, busca por `nif__icontains=q` **o** `nombre__icontains=q`.
  - Si `solo_activos=True`, filtra `activo=True`.
  - Si `estado` es `"activos"` o `"desactivados"`, filtra por `activo`; `"todos"` o vacío no
    filtra por estado.
  - Ordena por `nombre` y `nif`.
  - Devuelve un queryset; la paginación se aplica en la vista.
- `obtener_tecnico_por_nif(tenant, nif)`:
  - Normaliza el NIF y busca filtrando por `tenant` y `nif`.
  - Si no existe, lanza `NoEncontrado` con "El técnico no existe".
  - La spec 005 lo usa para validar la existencia del técnico en las líneas de stock inicial.
- `tecnicos_para_operacion(tenant)`:
  - Devuelve solo técnicos activos del tenant, ordenados por nombre y NIF.
  - Es la fuente de los selectores de stock inicial, asignación, traspaso, conciliación y
    registro de materiales.
- `tecnicos_para_reporte(tenant, incluir_inactivos=True)`:
  - Devuelve técnicos del tenant para reportes históricos; incluye inactivos cuando el reporte
    los necesite.
- `obtener_datos_tecnico(tecnico)`:
  - Devuelve `nif`, `nombre` y `activo` para el autocompletado y los contratos de las specs
    consumidoras.

## Permisos
- **Gestionar técnicos**: únicamente el rol `USUARIO_TENANT` (cuenta del tenant). Crear, ver,
  editar, desactivar, reactivar y buscar comparten esta regla.
- **Administrador de plataforma**: no gestiona técnicos. Aunque fuerce la URL o el `POST`, recibe
  `403` "No tienes permiso para gestionar técnicos".
- **Responsable de almacén**: no gestiona técnicos ni ve su listado completo. Recibe `403` con el
  mismo mensaje.
- Los permisos se validan en el backend, en la vista y de nuevo en el servicio. Ocultar un botón
  no es autorización.
- No se siembran grupos ni permisos de Django en migraciones; la autorización es por rol explícito
  y alcance de tenant, igual que en la spec 001. Si el proyecto adopta `Permission` de Django más
  adelante, los códigos serían `tecnicos.add_tecnico`, `tecnicos.view_tecnico`,
  `tecnicos.change_tecnico`, `tecnicos.desactivar_tecnico` y `tecnicos.reactivar_tecnico`, pero
  no son la fuente de verdad en esta versión.
- No se acepta `tenant_id` ni `region_id` desde formularios, URLs, parámetros de búsqueda o
  archivos. El tenant sale de `request.tenant`/`actor.tenant`.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/tecnicos/` | GET | Listado paginado con búsqueda y filtro por estado |
| `/tecnicos/buscar/?q=` | GET | Fragmento HTMX con técnicos activos del tenant |
| `/tecnicos/nuevo/` | GET / POST | Alta de técnico |
| `/tecnicos/<id>/` | GET | Detalle del técnico |
| `/tecnicos/<id>/editar/` | GET / POST | Edición del nombre; NIF y tenant solo lectura |
| `/tecnicos/<id>/desactivar/` | POST | Desactivar técnico |
| `/tecnicos/<id>/reactivar/` | POST | Reactivar técnico |

### Pantallas
- **Listado**: NIF, nombre, estado y acciones. Búsqueda por NIF o nombre. Filtro
  Activos/Desactivados/Todos; por defecto, Todos para poder localizar y reactivar desactivados.
  Paginación de 50.
- **Alta**: NIF y nombre. El tenant no se muestra como campo editable.
- **Edición**: NIF y tenant como solo lectura; nombre editable; el estado se cambia con acciones
  separadas.
- **Detalle**: datos del técnico, estado y acceso a su historial en los módulos que lo consumen.
- **Selectores de otros módulos**: solo técnicos activos del tenant; el NIF se completa solo y
  no es editable en el formulario consumidor.
- **Desactivación/reactivación**: acciones `POST` con confirmación; no hay botón ni ruta de
  borrado.

## Integraciones
- **Stock inicial (spec 005):** valida que el NIF exista dentro del tenant; su
  `validar_tecnico_existe` se apoya en `obtener_tecnico_por_nif` y nunca busca fuera del tenant
  de la sesión.
- **Asignaciones (spec 006):** el selector usa `tecnicos_para_operacion` y el servicio
  `validar_tecnico_para_operacion`; copia el NIF al Excel.
- **Traspasos (spec 009):** origen y destino deben ser técnicos activos del mismo tenant y
  distintos entre sí; ambos se resuelven con `tecnicos_para_operacion` y
  `validar_tecnico_para_operacion`.
- **Conciliación (spec 010):** el NIF del reporte se resuelve dentro del tenant de la sesión; un
  NIF desconocido se informa como advertencia, nunca se busca en otro tenant.
- **Registro de materiales (spec 013):** las órdenes usan un técnico activo del tenant en el
  momento del alta; las órdenes históricas conservan el técnico aunque luego se desactive
  (`PROTECT`).
- **Logística inversa (spec 011):** una devolución o baja puede referenciar un técnico
  desactivado para conservar la trazabilidad.
- **Recojo (spec 004):** su plan vigente no referencia técnicos; si una versión posterior los
  requiere, debe usar los mismos helpers y no consultar `Tecnico` sin filtro de tenant.
- Todas las integraciones usan la FK `Tecnico` y el tenant de la sesión. No se acepta un NIF
  suelto sin resolverlo contra el tenant.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| NIF con formato `LAXXXX` | Formulario, servicio y `CheckConstraint` | "El NIF debe tener el formato LAXXXX" |
| NIF único global | Servicio y restricción `unique` | "El NIF ya está registrado" |
| NIF de un desactivado del mismo tenant | Servicio | "El NIF ya está registrado; reactiva el técnico existente" |
| NIF de un desactivado de otro tenant | Servicio | "El NIF ya está registrado" (mensaje uniforme, sin revelar el tenant) |
| NIF inmutable | Formulario (campo ausente) y servicio | "El NIF no se puede cambiar" |
| Nombre obligatorio | Formulario, servicio y `CheckConstraint` | "El nombre es obligatorio" |
| Nombre máximo 100 | Formulario, servicio y `varchar(100)` | "El nombre no puede superar los 100 caracteres" |
| Tenant inmutable | Servicio | "El tenant del técnico no se puede cambiar" |
| Solo cuenta del tenant | Servicio y decorador de rol | "No tienes permiso para gestionar técnicos" |
| Técnico de otro tenant | Servicio | "El técnico no existe" |
| Técnico activo para operar | Servicio de integración | "El técnico está desactivado" |
| Tenant suspendido | Middleware y servicio | "El tenant está suspendido" |

## Transacciones y concurrencia
- El alta y su auditoría se ejecutan en una sola transacción.
- La edición del nombre y su auditoría se ejecutan en una sola transacción con
  `select_for_update`.
- La desactivación y la reactivación se ejecutan en una transacción con `select_for_update` y
  auditan el cambio; si el estado ya es el objetivo, no escriben nada.
- La restricción única de `nif` resuelve dos altas simultáneas con el mismo NIF: una gana y la
  otra recibe "El NIF ya está registrado".
- Dos sesiones que editan el mismo técnico se serializan con `select_for_update`; la auditoría
  conserva el valor anterior que leyó cada transacción.
- No se usan bloqueos de aplicación para evitar duplicados; la base de datos es la fuente de
  verdad.
- La normalización ocurre antes de validar y de escribir, de modo que `" la1234 "` y `"LA1234"`
  no burlan la unicidad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_crear_tecnico_valido_queda_activo_y_auditado`
- `test_nif_duplicado_en_el_mismo_tenant_se_rechaza`
- `test_nif_duplicado_en_otro_tenant_se_rechaza_sin_revelar_tenant`
- `test_nif_en_minusculas_o_con_espacios_externos_se_normaliza`
- `test_nif_con_formato_invalido_se_rechaza`
- `test_nombre_vacio_o_solo_espacios_se_rechaza`
- `test_nombre_de_mas_de_100_caracteres_se_rechaza`
- `test_editar_nombre_audita_valor_anterior_y_nuevo`
- `test_nif_no_se_puede_editar`
- `test_tenant_no_se_puede_cambiar`
- `test_desactivar_tecnico_lo_quita_de_selectores_activos`
- `test_tecnico_desactivado_con_historial_sigue_visible`
- `test_reactivar_tecnico_lo_habilita_y_audita`
- `test_no_se_crea_otro_tecnico_con_nif_desactivado`
- `test_nif_desactivado_de_otro_tenant_no_revela_tenant`
- `test_busqueda_solo_devuelve_tecnicos_del_tenant`
- `test_tecnico_de_otro_tenant_se_rechaza_sin_revelar_datos`
- `test_admin_plataforma_y_almacen_no_gestionan_tecnicos`
- `test_tecnico_desactivado_en_formulario_viejo_se_rechaza`
- `test_desactivar_tecnico_con_stock_conserva_stock`
- `test_altas_simultaneas_con_mismo_nif_fallan_por_restriccion_unica`
- `test_no_se_puede_eliminar_un_tecnico`
- `test_nombre_duplicado_se_permite`
- `test_desactivar_dos_veces_no_duplica_auditoria`
- `test_reactivar_dos_veces_no_duplica_auditoria`
- `test_listado_paginado_y_filtro_por_estado`
- `test_busqueda_por_nif_y_por_nombre`
- `test_fragmento_busqueda_devuelve_solo_activos_del_tenant`
- `test_tenant_suspendido_no_gestiona_tecnicos`
- `test_editar_nombre_de_tecnico_desactivado_se_permite`

Además, pruebas de base de datos:
- Insertar un NIF con formato inválido directamente debe fallar por `CheckConstraint`.
- Insertar dos técnicos con el mismo NIF directamente debe fallar por `unique`.
- Insertar un técnico con nombre vacío directamente debe fallar por `CheckConstraint`.
- Un técnico de otro tenant no aparece en `buscar_tecnicos` ni en `tecnicos_para_operacion`.

Pruebas de contrato HTTP (rutas, roles, códigos y mensajes) e integración de servicios viven en
`tests/contract/` e `tests/integration/`.

## Decisiones y riesgos
- **NIF único global:** se asume que Lari asigna un NIF único por técnico. Si el mismo NIF puede
  pertenecer a dos tenants, se cambia a `UniqueConstraint(fields=["tenant", "nif"])` y se ajusta
  la spec antes del código.
- **NIF inmutable:** se protege la trazabilidad de los Excel y reportes. Una corrección de NIF se
  resuelve desactivando el técnico y creando uno nuevo con el NIF correcto.
- **Sin eliminación:** los técnicos no se borran; se desactivan. `PROTECT` y la ausencia de rutas
  de borrado conservan stock, asignaciones, traspasos, órdenes y conciliaciones.
- **Desactivación con stock:** se permite desactivar un técnico con stock pendiente, pero no
  recibe nuevas operaciones. El stock sigue visible para devolución o traspaso; las reglas
  concretas viven en las specs 009 y 011.
- **Mensaje de NIF desactivado:** la variante "reactiva el técnico existente" solo se muestra
  cuando el técnico desactivado pertenece al tenant de la sesión. Para un NIF desactivado de otro
  tenant se mantiene el mensaje uniforme, evitando revelar su existencia.
- **Cupo máximo fuera de alcance:** la alerta de cupo de equipos sin liquidar se definirá en la
  spec de asignación o como parámetro del tenant, no en el alta del técnico.
- **NIF de 4 dígitos:** si Lari usa otra longitud, se ajusta el regex, la longitud del campo y la
  restricción de base de datos; primero se corrige la spec.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por
  módulo.
- **Búsqueda por nombre:** se indexa `tenant + nombre`; si el volumen crece, se evalúa un índice
  de texto completo.
- **Integraciones:** todos los módulos deben usar los servicios de este módulo para resolver el
  técnico; no deben consultar `Tecnico` sin filtrar por tenant.
- **Concurrencia:** la restricción única de NIF es la fuente de verdad ante dos altas simultáneas;
  `select_for_update` evita auditorías inconsistentes en ediciones y cambios de estado.
- **Edición de desactivados:** se permite corregir el nombre de un técnico desactivado; no se
  habilita para operaciones nuevas hasta reactivarlo.
- **RLS:** se recomienda como respaldo; la aplicación no depende de ella para el aislamiento.

## Complexity Tracking

> Sin violaciones a la constitución. No se agregan dependencias ni patrones adicionales.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Ninguna | — | — |

## Artefactos de diseño

| Artefacto | Contenido |
|---|---|
| `research.md` | Decisiones: app/modelo, NIF global e inmutable, estado binario, aislamiento, permisos, normalización, búsqueda, contrato para consumidores, auditoría y concurrencia |
| `data-model.md` | Entidad `Tecnico`, campos, restricciones, índices, normalización, transiciones de estado y eventos de auditoría |
| `contracts/http-endpoints.md` | Rutas, roles, peticiones, respuestas, códigos y mensajes |
| `contracts/busqueda-tecnicos.md` | Contrato del fragmento HTMX consumido por 005, 006, 009 y 013; 010 resuelve NIF por servicio |
| `contracts/auditoria-tecnico.md` | Eventos auditados, datos prohibidos y reglas de escritura |
| `quickstart.md` | Escenarios ejecutables de validación extremo a extremo |
