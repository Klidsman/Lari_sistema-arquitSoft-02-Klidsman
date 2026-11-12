# Plan técnico: 004 Recojo de materiales

**Branch**: `004-recojo-de-materiales` | **Date**: 2026-11-12 | **Spec**: `05-especificaciones/004-recojo-de-materiales/spec.md`

**Input**: Spec en `05-especificaciones/004-recojo-de-materiales/spec.md`

## Summary

Implementar el registro de recojos de materiales del almacén central de la región del tenant:
formulario con varias líneas, materiales seriados y no seriados, normalización y validación de
series en tiempo real, rechazo de series inválidas, duplicadas o ya existentes, y aplicación todo o
nada que incrementa el stock general del tenant. El diseño crea la app `recojos` (`Recojo`,
`LineaRecojo`) y la app transversal `series` (`Serie`, registro central con unicidad global en
PostgreSQL), consume el catálogo de la spec 002 y el servicio de stock general de la spec 008, y
audita el alta del recojo y cada movimiento de stock en `auditoria.RegistroCambio`, en la misma
transacción. No usa Excel, no permite editar ni borrar recojos y no acepta `tenant_id`, `region_id`
ni `almacen_id` desde el cliente.

## Technical Context

**Language/Version**: Python 3.12+ (fijado por la constitución y ADR-015)

**Primary Dependencies**: Django LTS 5.x, HTMX, PostgreSQL 16+ y `pytest`/`pytest-django` (ya
fijados por la spec 001). **Sin dependencias nuevas**: la vista previa usa HTMX y una consulta
`__in`; no se requiere motor de búsqueda, `pg_trgm`, JavaScript de framework ni Excel.

**Storage**: PostgreSQL 16+ compartido. Tablas nuevas `recojos_recojo`, `recojos_linearecojo` y
`series_serie`; tablas existentes `materiales_material` (002), `tenants_tenant`/`tenants_region`
(001), `stock_stockgeneral` (008) y `auditoria_registrocambio` (001). `LineaRecojo` lleva `tenant`
denormalizado para RLS y consultas de respaldo. No se crean tablas de asignaciones, traspasos,
conciliaciones, logística inversa ni stock por técnico.

**Testing**: pytest + pytest-django contra PostgreSQL (sin SQLite), con pruebas de contrato HTTP,
integración de servicios, restricciones de base de datos, concurrencia y rendimiento. Un caso por
criterio de aceptación.

**Target Platform**: servidor Linux (Gunicorn + Nginx); interfaz web server-rendered con HTMX;
desarrollo local en Windows o Linux.

**Project Type**: aplicación web monolítica modular Django; esta spec agrega dos apps (`recojos` y
`series`) al proyecto ya planificado en 001 y consume 002 y la parte fundacional de 008.

**Performance Goals**: vista previa de hasta 500 series p95 < 300 ms (una sola consulta de
existencia); listado y detalle p95 < 300 ms con ~5 000 recojos por tenant; listado paginado a 50
filas; sin N+1 en listado ni detalle.

**Constraints**: tenant y región salen solo de la sesión; la serie tiene 12 caracteres alfanuméricos
(configurable), es única global y se normaliza antes de validar; una línea seriada tiene
`cantidad=1` y una no seriada `cantidad>0`; todo o nada; sin Excel; sin edición ni borrado de
recojos; solo la cuenta del tenant registra y consulta; el tipo de material con movimientos no se
puede cambiar (integración con 002); toda alta y movimiento de stock se audita en la misma
transacción.

**Scale/Scope**: ~100 tenants, 1 000–10 000 series por tenant al año y recojos de 1–500 series; 2
entidades nuevas (`Recojo`, `LineaRecojo`) y 1 transversal (`Serie`); 4 rutas HTTP; 9 criterios de
aceptación.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | El tenant sale de `request.usuario`/`actor.tenant`; la región, de `tenant.region`. Toda consulta filtra por tenant; un recojo de otro tenant se trata como inexistente (`404`). La consulta global de series solo devuelve un estado uniforme `ya_existe`, sin revelar tenant, región ni recojo de origen |
| II. Jerarquía Región → Tenant → Técnico | PASA | `Recojo` y `Serie` pertenecen a un tenant y guardan la región de ese tenant como instantánea inmutable. El recojo no referencia técnicos: es una operación del tenant. El almacén se identifica por la región, que tiene exactamente uno |
| III. Invariantes de stock | PASA | El stock general solo sube con recojos registrados; las líneas seriadas generan Cantidad 1 y las no seriadas la cantidad digitada; el lote es informativo y no separa stock. El incremento se delega en `stock.services.incrementar_stock_general` de 008, que audita valor anterior y nuevo |
| IV. Identidad y unicidad de series | PASA | `series.Serie.numero` es único global en la base de datos; se normaliza antes de validar; cada serie pertenece a un tenant y a su región y no cambia de región. Los estados son Disponible, Reservada y Asignada; 004 solo crea Disponible |
| V. Integridad transaccional | PASA | La validación autoritativa de las series, la creación del recojo, las líneas, el stock y la auditoría se ejecutan en una sola `transaction.atomic`; cualquier error revierte todo. La restricción única resuelve dos altas concurrentes |
| VI. Auditoría inmutable y trazabilidad | PASA | Un `RegistroCambio` de alta de `Recojo` y los registros de `StockGeneral` que escribe 008, en la misma transacción. Cada `Serie` conserva autor, fecha y vínculo con su línea y recojo. No se auditan secretos |
| VII. Autoridad del reporte de Lari | N/A | Esta spec no procesa reportes ni conciliaciones; las series creadas serán insumo de 010 |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada criterio de aceptación tiene prueba; no se agregan dependencias; la lógica vive en `recojos/services.py` y `series/services.py` y es testeable sin interfaz; el registro central de series es la solución más simple a la unicidad global exigida |

Sin violaciones que justificar. `Complexity Tracking` registra la única complejidad adicional
(registro central de series) y su alternativa rechazada.

**Re-evaluación tras la Fase 1**: `data-model.md` y los contratos mantienen el filtro por tenant, la
región derivada de la sesión, la unicidad global en la base, la auditoría en la misma transacción y
la ausencia de rutas de edición o borrado. No aparecieron violaciones nuevas ni incógnitas
pendientes; la puerta sigue en verde.

## Project Structure

### Documentation (this feature)

```text
05-especificaciones/004-recojo-de-materiales/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   ├── http-endpoints.md
│   ├── validacion-series.md
│   └── auditoria-recojo.md
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

Estructura existente planificada por 001, 002 y la parte fundacional de 008; esta spec agrega
`recojos/` y `series/`.

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
materiales/             # spec 002: Material, búsqueda
stock/                  # spec 008: StockGeneral, incrementar_stock_general

recojos/                # NUEVA app de esta spec
├── models.py           # Recojo, LineaRecojo
├── services.py         # validación, vista previa, alta, consultas
├── forms.py            # RecojoForm, LineaRecojoForm, formset
├── views.py            # listado, detalle, alta, validación HTMX
├── urls.py
├── apps.py             # registro de la verificación de movimientos en 002
├── migrations/
│   └── 0001_initial.py
└── admin.py            # registro de solo lectura (opcional, sin superusuario)

series/                 # NUEVA app transversal de esta spec
├── models.py           # Serie, EstadoSerie
├── services.py         # normalización, validación, creación y consulta
├── apps.py
├── migrations/
│   └── 0001_initial.py
└── admin.py            # registro de solo lectura (opcional)

templates/
├── recojos/
│   ├── recojos_lista.html
│   ├── recojo_form.html
│   ├── recojo_detalle.html
│   ├── _linea_form.html
│   └── _vista_previa_series.html
└── base.html           # enlace a Recojos para la cuenta del tenant

tests/
├── contract/
│   ├── test_recojo_alta_http.py
│   ├── test_recojo_lista_detalle_http.py
│   └── test_recojo_vista_previa_http.py
├── integration/
│   ├── test_recojo_alta.py
│   ├── test_recojo_series.py
│   ├── test_recojo_stock.py
│   ├── test_recojo_auditoria.py
│   └── test_restricciones_recojo.py
└── unit/
    ├── test_recojo_validaciones.py
    └── test_series_servicios.py
```

**Structure Decision**: se conserva el monolito modular de la spec 001. La app `recojos` contiene el
documento y sus líneas; la app `series` es la fuente de verdad transversal de identidad y estado de
las series, creada por 004 porque es el primer módulo que las introduce. La app `stock` pertenece a
008 y no se duplica. La región se guarda como instantánea en `Recojo` y `Serie`, fijada desde
`tenant.region`; no se acepta del cliente. Las reglas de negocio viven en los `services.py`, nunca
en las vistas.

## Referencias

- Spec: `05-especificaciones/004-recojo-de-materiales/spec.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `03-reglas-de-dominio/series.md`,
  `03-reglas-de-dominio/registro-materiales.md`, `03-reglas-de-dominio/auditoria.md`
- Specs relacionadas: 001 (cuenta, tenant, región, middleware, auditoría), 002 (catálogo y búsqueda
  de materiales), 003 (técnicos, no consumido por esta spec), 008 (stock general), 010
  (conciliación) y 011 (logística inversa)
- Contratos consumidos: `05-especificaciones/002-materiales/contracts/busqueda-materiales.md`
- ADR: ADR-002 (esquema compartido), ADR-003 (aislamiento multitenant), ADR-007 (auditoría),
  ADR-012 (conciliación), ADR-015 (stack)
- Constitución 1.3.0

## Módulos afectados

- App Django nueva `recojos`: modelos `Recojo` y `LineaRecojo`, servicios, formularios, vistas y
  rutas.
- App Django nueva `series`: modelo `Serie`, normalización, validación, creación y consultas.
- App `materiales` (002): se consulta el catálogo y se registra una verificación de movimientos para
  impedir el cambio de tipo de un material con recojos o stock.
- App `stock` (008): se usa `StockGeneral` e `incrementar_stock_general`; no se modifica su modelo.
- App `auditoria` (001): se reutiliza `RegistroCambio` y `registrar_cambio`.
- `config/urls.py`: inclusión de `recojos/urls.py`.
- `templates/base.html` (001): enlace a Recojos visible solo para `USUARIO_TENANT`.
- No se modifican asignaciones, traspasos, conciliaciones, técnicos ni stock por técnico.

## Modelo de datos

```python
class Recojo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="recojos",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="recojos",
    )
    fecha = models.DateField()
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recojos_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="recojo_tenant_fecha"),
            models.Index(fields=["region", "fecha"], name="recojo_region_fecha"),
        ]

    def __str__(self):
        return f"Recojo {self.id} - {self.tenant} - {self.fecha}"


class LineaRecojo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="lineas_recojo",
    )
    recojo = models.ForeignKey(
        Recojo,
        on_delete=models.PROTECT,
        related_name="lineas",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_recojo",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    serie = models.OneToOneField(
        "series.Serie",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="linea_recojo",
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_recojo_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=Q(serie__isnull=True) | Q(cantidad=1),
                name="linea_recojo_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gte=0),
                name="linea_recojo_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["recojo", "material"], name="linea_recojo_recojo_material"),
            models.Index(fields=["tenant", "material"], name="linea_recojo_tenant_material"),
        ]

    def __str__(self):
        if self.serie_id:
            return f"{self.material.codigo} - {self.serie.numero}"
        return f"{self.material.codigo} - {self.cantidad}"


class EstadoSerie(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    RESERVADA = "RESERVADA", "Reservada"
    ASIGNADA = "ASIGNADA", "Asignada"


class Serie(models.Model):
    numero = models.CharField(max_length=12, unique=True)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="series",
    )
    region = models.ForeignKey(
        "tenants.Region",
        on_delete=models.PROTECT,
        related_name="series",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="series",
    )
    lote = models.CharField(max_length=50, blank=True, default="")
    estado = models.CharField(
        max_length=10,
        choices=EstadoSerie.choices,
        default=EstadoSerie.DISPONIBLE,
    )
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
        ordering = ["numero"]
        constraints = [
            models.CheckConstraint(
                condition=Q(numero__regex=r"^[A-Z0-9]{12}$"),
                name="serie_formato",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["DISPONIBLE", "RESERVADA", "ASIGNADA"]),
                name="serie_estado_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "estado"], name="serie_tenant_estado"),
            models.Index(fields=["tenant", "material"], name="serie_tenant_material"),
        ]

    def __str__(self):
        return self.numero
```

- `Recojo` representa el documento completo; `LineaRecojo`, cada unidad o cantidad recibida.
- `Recojo.region` y `Serie.region` son instantáneas de `tenant.region`; el servicio las fija y
  nunca las actualiza. La región del tenant es inmutable (001).
- `LineaRecojo.tenant` es una FK denormalizada para RLS y consultas de respaldo; el servicio la fija
  desde el recojo y nunca la acepta del cliente.
- `LineaRecojo.serie` es uno a uno: una serie pertenece a una sola línea de recojo. Es nulo para
  materiales no seriados.
- `Serie.numero` es único global en PostgreSQL; la restricción es la fuente de verdad ante altas
  concurrentes. El patrón de aplicación es configurable (`SERIE_PATRON`); la restricción de base usa
  el valor vigente de 12 caracteres como respaldo y se actualiza con una migración si el negocio
  cambia el formato.
- `Serie.estado` nace en `DISPONIBLE` cuando lo crea 004; 005 crea `ASIGNADA` pasando el estado
  explícito a `crear_serie`. 006, 007, 008 y 011 agregan las demás transiciones. 004 no expone
  cambio de estado.
- `Serie.material`, `Serie.tenant` y `Serie.region` son inmutables después del alta.
- El lote se copia del catálogo al crear la línea y la serie; es informativo y no separa stock.

### Dependencia de stock (spec 008)

004 no define `StockGeneral`. Usa el modelo y el servicio de 008:

```python
# stock/models.py (spec 008)
class StockGeneral(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="stock_general")
    material = models.ForeignKey("materiales.Material", on_delete=models.PROTECT, related_name="stock_general")
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "material"], name="stock_general_tenant_material_unico"),
            models.CheckConstraint(condition=Q(cantidad__gte=0), name="stock_general_cantidad_no_negativa"),
        ]
```

- `incrementar_stock_general(tenant, material, cantidad, actor)` valida `cantidad > 0`, obtiene o
  crea la fila y suma, en una transacción y con auditoría de valor anterior y nuevo.
- La parte fundacional de 008 (modelo y servicio de incremento) debe existir antes de implementar
  004; la confirmación de asignaciones de 008 puede completarse después de 007.

### Auditoría

Se reutiliza `auditoria.RegistroCambio` (001). Eventos propios de esta spec:

| Evento | `entidad` | `campo` | `valor_anterior` | `valor_nuevo` |
|---|---|---|---|---|
| Alta de recojo | `Recojo` | `alta` | — | `fecha`, `region`, `lineas`, `series`, `cantidad` |
| Incremento de stock general | `StockGeneral` | `cantidad` | cantidad anterior | cantidad nueva (lo escribe 008) |

- El alta del recojo y los incrementos de stock se escriben en la misma transacción que el cambio.
- Si el recojo falla, no se escribe ninguna auditoría de recojo ni de stock.
- No se escribe un registro por cada serie: la trazabilidad individual la dan `Serie.creado_por`,
  `Serie.creado_en` y su vínculo `LineaRecojo → Recojo`.
- Nunca se auditan contraseñas, tokens, secretos ni datos sensibles.

### Migraciones

- `series/migrations/0001_initial.py`: `Serie`, con `unique(numero)`, los dos `CheckConstraint` y
  los índices.
- `recojos/migrations/0001_initial.py`: `Recojo` y `LineaRecojo`, con la FK a `series.Serie`, las
  restricciones y los índices.
- No se crean recojos, series ni datos maestros por migración.
- No se modifican tablas de materiales, stock, asignaciones, traspasos ni conciliaciones.
- `AUTH_USER_MODEL = "acceso.Usuario"`, `tenants.Tenant`, `tenants.Region`,
  `materiales.Material` y `stock.StockGeneral` deben existir antes de aplicar estas migraciones.

## Servicios (lógica de negocio)

Viven en `recojos/services.py` y `series/services.py`, no en las vistas.

### Excepciones

- `ValidacionRecojo`: fecha, líneas, material o cantidad inválidos.
- `SerieInvalida`: formato incorrecto.
- `SerieDuplicada`: la serie se repite dentro del mismo recojo.
- `SerieYaExiste`: la base rechazó una serie ya registrada durante el guardado concurrente; la
  vista responde `409` con el mensaje uniforme. La serie existente detectada en la validación previa
  se informa como estado `ya_existe` dentro de `RecojoInvalido` (`400`).
- `MaterialNoValido`: material inexistente o tipo incompatible con la línea.
- `RecojoInvalido`: el resultado de la validación contiene errores.
- `PermisoDenegado`: rol o alcance incorrecto.
- `NoEncontrado`: recojo inexistente o de otro tenant.
- `TenantSuspendido`: tenant con estado `SUSPENDIDO`.
- `RegionIncorrecta`: la región del tenant no tiene almacén configurado.

### Alcance y permisos

- `validar_cuenta_tenant(actor)`:
  - Exige `actor.rol == Rol.USUARIO_TENANT`.
  - Exige `actor.is_active`.
  - Exige `actor.tenant` y `actor.tenant.estado == "ACTIVO"`; si no, `TenantSuspendido` con "El
    tenant está suspendido".
  - Cualquier otro rol lanza `PermisoDenegado` con "No tienes permiso para registrar recojos".
  - Devuelve el tenant de la sesión. No acepta un `tenant_id` externo.
- `validar_region_tenant(tenant)`:
  - Exige `tenant.region` y que `tenant.region.almacen` exista; si no, `RegionIncorrecta` con "La
    región del tenant no tiene almacén configurado".
  - Devuelve la región. No acepta una región del cliente.
- `obtener_recojo(tenant, recojo_id)`:
  - Busca con `Recojo.objects.filter(tenant=tenant, id=recojo_id)`.
  - Si no existe o pertenece a otro tenant, lanza `NoEncontrado` con "El recojo no existe".

### Series

- `normalizar_numero(numero)`:
  - Elimina todos los espacios en blanco (`\s+`).
  - Convierte a mayúsculas.
  - No elimina guiones ni otros caracteres: el formato los rechaza.
- `validar_numero(numero)`:
  - Debe cumplir `settings.SERIE_PATRON` (por defecto `^[A-Z0-9]{12}$`).
  - Si no, `SerieInvalida` con "La serie debe tener 12 caracteres alfanuméricos".
- `series_existentes(numeros)`:
  - Consulta `Serie.objects.filter(numero__in=numeros)` una sola vez.
  - Devuelve el conjunto de números existentes.
- `crear_serie(tenant, region, material, numero, lote, actor, estado=EstadoSerie.DISPONIBLE)`:
  - Normaliza y valida el número.
  - Crea `Serie` con el `estado` recibido (por defecto `DISPONIBLE`), tenant, región, material,
    lote y autor.
  - 004 usa el valor por defecto; 005 pasa `EstadoSerie.ASIGNADA` porque el stock inicial ya está
    en posesión del técnico.
  - No captura `IntegrityError`: la capa que crea el recojo la traduce.
  - No cambia de estado ni de región después del alta.

### Validación previa

- `normalizar_lineas(datos)`:
  - Recibe una lista de líneas con `material_id`, `series` (texto) y `cantidad`.
  - Normaliza la fecha, el material, las series y la cantidad.
  - Agrupa las series de cada material seriado; cada serie normalizada será una línea.
- `validar_recojo_previo(tenant, datos)`:
  - `validar_cuenta_tenant` y `validar_region_tenant` se ejecutan en el alta, no en la vista previa.
  - Debe existir al menos una línea; si no, "El recojo debe tener al menos una línea".
  - Para cada línea:
    - El material debe existir; si no, "El material no existe en el catálogo".
    - Si es seriado: exige al menos una serie; cada serie se normaliza, se valida el formato y se
      detectan duplicados dentro del mismo recojo. La cantidad debe ser 1 si se envía.
    - Si es no seriado: exige `cantidad > 0`; no admite series.
  - Consulta todas las series existentes en una sola operación y marca `ya_existe`.
  - Devuelve un `ResultadoValidacion` con las líneas expandidas, los estados por serie y la lista de
    errores; `valido` es verdadero solo si no hay errores.
  - No escribe en la base de datos.
- `previsualizar_series(tenant, material, texto_series)`:
  - Normaliza y valida el material; exige que sea seriado.
  - Divide el texto por líneas, normaliza cada serie, detecta duplicados y consulta las existentes.
  - Devuelve una lista de `{numero, estado}` con estados `valida`, `invalida`, `duplicada`,
    `ya_existe`.
  - No revela tenant, región ni recojo de origen.

### Alta

- `crear_recojo(datos, actor)`:
  - `validar_cuenta_tenant(actor)`; el tenant se toma de `actor.tenant`.
  - `validar_region_tenant(tenant)`.
  - En `transaction.atomic`:
    - Ejecuta `validar_recojo_previo`; si no es válido, lanza `RecojoInvalido` con los estados y
      errores. La transacción no escribe nada.
    - Crea `Recojo` con tenant, región, fecha y autor.
    - Crea cada `LineaRecojo` con tenant, recojo, material, lote y serie o cantidad.
    - Crea cada `Serie` con estado `DISPONIBLE`, tenant, región, material, lote y autor.
    - Agrupa las líneas por material y llama una vez a
      `stock.services.incrementar_stock_general(tenant, material, cantidad, actor)` por material.
    - Registra la auditoría de alta del recojo.
  - Captura `IntegrityError` de `Serie.numero` y traduce a `SerieYaExiste` con "La serie ya está
    registrada en el sistema"; la transacción se revierte completa.
  - No acepta `tenant`, `tenant_id`, `region`, `region_id`, `almacen` ni `almacen_id`; si llegan,
    se ignoran y el alcance sigue saliendo de la sesión.
  - Devuelve el `Recojo` creado.

### Consultas

- `listar_recojos(tenant)`:
  - Filtra siempre por `tenant`.
  - Ordena por `fecha` descendente e `id` descendente.
  - Anota `total_lineas`, `total_series` (líneas con serie) y `total_cantidad` (suma de líneas no
    seriadas) para evitar N+1.
  - Devuelve un queryset; la paginación de 50 se aplica en la vista.
- `obtener_detalle_recojo(tenant, recojo_id)`:
  - Usa `obtener_recojo` y precarga `lineas__material` y `lineas__serie`.
  - Devuelve el recojo con sus líneas ordenadas por material y serie.
- `totales_recojo(recojo)`:
  - Devuelve `total_series`, `total_cantidad` y `total_lineas` a partir de las líneas precargadas.

## Permisos

- **Registrar, listar, ver y previsualizar**: únicamente el rol `USUARIO_TENANT` (cuenta del
  tenant).
- **Administrador de plataforma**: no registra ni consulta recojos; recibe `403` "No tienes permiso
  para registrar recojos". La consulta administrativa pertenece a la auditoría de 001.
- **Responsable de almacén**: no registra ni consulta recojos; recibe `403` con el mismo mensaje.
- **Tenant suspendido**: `403` "El tenant está suspendido".
- **Recojo de otro tenant**: `404` "El recojo no existe".
- Los permisos se validan en la vista y se revalidan en el servicio. Ocultar un botón no es
  autorización.
- No se acepta `tenant_id`, `region_id` ni `almacen_id` desde formularios, URLs, parámetros de
  búsqueda o peticiones HTMX. El tenant sale de `request.tenant`/`actor.tenant`.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/recojos/` | GET | Listado paginado de recojos del tenant |
| `/recojos/nuevo/` | GET / POST | Formulario de recojo con varias líneas |
| `/recojos/<id>/` | GET | Detalle y confirmación del recojo |
| `/recojos/validar-series/` | POST | Vista previa HTMX de series pegadas o escaneadas |

### Pantallas

- **Listado**: fecha, identificador, número de líneas, total de series, total de cantidad y enlace
  al detalle. Paginación de 50. Sin filtros por fecha: la spec no los pide.
- **Alta**: fecha (precompletada con hoy, editable); líneas dinámicas con selector de material por
  búsqueda HTMX sobre `/materiales/buscar/`, tipo y lote de solo lectura, series para seriados o
  cantidad para no seriados. Botón "Agregar línea" para clonar una fila vacía. Botón "Guardar" con
  `hx-disabled-elt` para evitar el doble envío.
- **Vista previa**: por cada línea seriada, una tabla de series con la serie normalizada y su estado
  (Válida, Inválida, Duplicada, Ya existe), actualizada con HTMX al pegar, escanear o cambiar el
  texto.
- **Detalle**: identificador, fecha, tenant, región, total de series, total de cantidad y tabla de
  líneas con material, descripción, lote, serie o cantidad. Es la confirmación del recojo.
- **Sin edición ni borrado**: no hay botón ni ruta de edición o borrado; `DELETE` responde `405`.

## Integraciones

- **Materiales (spec 002):** el selector usa `GET /materiales/buscar/?q=`, que devuelve
  `data-codigo`, `data-descripcion`, `data-lote` y `data-tipo`. El formulario copia lote y tipo como
  solo lectura; el servicio revalida el material y su tipo. 004 registra en
  `materiales.services.registrar_verificacion_movimientos` una verificación que impide cambiar
  `es_seriado` si el material tiene líneas de recojo, series o stock.
- **Stock general (spec 008):** `StockGeneral` e `incrementar_stock_general` son la única vía de
  incremento. 004 agrupa por material y llama una vez por material. El servicio de 008 debe usar
  bloqueo de fila o `F()` para sumas concurrentes y audita valor anterior y nuevo.
- **Series (transversal):** `series.Serie` es la fuente de identidad y estado. 004 crea series
  `DISPONIBLE`; 006/007/008/010/011 agregan transiciones y deben usar el registro central, no otra
  tabla ni otra columna única.
- **Conciliación (spec 010):** las series del recojo estarán disponibles para comparar contra el
  reporte de Lari. 004 no procesa el reporte.
- **Logística inversa (spec 011):** una serie dada de baja no vuelve al stock disponible; esa regla
  pertenece a 011 y no se implementa aquí.
- **Registro de materiales (spec 013):** los despachos se respaldan en el recojo y sus líneas; 004
  expone las líneas del tenant para ese consumo.
- **Técnicos (spec 003):** 004 no referencia técnicos. El recojo es del tenant; si una versión
  posterior lo requiere, debe usar los helpers de 003 y filtrar por tenant.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Solo la cuenta del tenant | Servicio y vista | "No tienes permiso para registrar recojos" |
| Tenant activo | Servicio y middleware | "El tenant está suspendido" |
| Región con almacén | Servicio | "La región del tenant no tiene almacén configurado" |
| Al menos una línea | Servicio y formulario | "El recojo debe tener al menos una línea" |
| Fecha obligatoria y válida | Formulario y servicio | "La fecha es obligatoria" / "La fecha no es válida" |
| Material existe en el catálogo | Servicio | "El material no existe en el catálogo" |
| Serie con formato de 12 caracteres | Formulario, servicio y `CheckConstraint` | "La serie debe tener 12 caracteres alfanuméricos" |
| Serie única en el sistema | Servicio y `unique(numero)` | "La serie ya está registrada en el sistema" |
| Serie no duplicada en el recojo | Servicio y vista previa | "La serie está duplicada en el recojo" |
| Serie obligatoria para material seriado | Formulario y servicio | "Debe indicar al menos una serie" |
| Cantidad 1 para material seriado | Servicio y `CheckConstraint` | "Para un material seriado la cantidad debe ser 1" |
| Cantidad > 0 para no seriado | Formulario, servicio y `CheckConstraint` | "La cantidad debe ser mayor a 0" |
| Material no seriado sin series | Servicio | "Un material no seriado no admite series" |
| Recojo de otro tenant | Servicio | "El recojo no existe" |
| Todo o nada | Servicio y transacción | "No se guardó el recojo; corrige los errores" |
| Sin edición ni borrado | Rutas y vistas | `405` |

## Transacciones y concurrencia

- La validación autoritativa de todas las series, la creación del recojo, sus líneas, las series, el
  incremento de stock y la auditoría se ejecutan dentro de la misma `transaction.atomic`. Cualquier
  error revierte todo. La vista previa ejecuta la misma validación en modo lectura, fuera de la
  transacción, para dar retroalimentación rápida; no es la fuente de verdad.
- La restricción `unique` de `Serie.numero` resuelve dos sesiones que intentan registrar la misma
  serie: una gana y la otra recibe "La serie ya está registrada en el sistema" sin revelar el
  tenant. El recojo de la perdedora no se guarda.
- El servicio de stock de 008 debe bloquear la fila (`select_for_update`) o usar una expresión `F()`
  para que dos recojos concurrentes del mismo tenant y material sumen correctamente. 004 no
  implementa su propia actualización de stock.
- La normalización ocurre antes de validar y de escribir, de modo que `" abc 123456789 "` y
  `"ABC123456789"` no burlan la unicidad.
- No se usan bloqueos de aplicación para evitar duplicados; la base de datos es la fuente de
  verdad.

## Pruebas

Un caso por criterio de aceptación. Nombres propuestos:

- `test_crear_recojo_seriado_valido_incrementa_stock_y_audita` (CA-02)
- `test_serie_se_normaliza_a_mayusculas_y_sin_espacios` (CA-03)
- `test_serie_con_formato_invalido_se_rechaza` (CA-04)
- `test_serie_duplicada_en_el_mismo_recojo_se_marca` (CA-05)
- `test_serie_ya_existente_se_rechaza_sin_revelar_tenant` (CA-06)
- `test_recojo_con_una_serie_invalida_no_se_guarda_completo` (CA-07)
- `test_vista_previa_actualiza_estado_por_serie` (CA-08)
- `test_recojo_no_seriado_suma_cantidad_al_stock` (CA-09)
- `test_recojo_solo_usa_la_region_del_tenant` (CA-01)
- `test_recojo_con_varias_lineas_se_guarda_completo`
- `test_incremento_stock_general_agrupado_por_material`
- `test_series_creadas_quedan_disponibles_con_tenant_y_region`
- `test_recojo_sin_lineas_se_rechaza`
- `test_recojo_de_otro_tenant_se_trata_como_inexistente`
- `test_admin_y_almacen_no_registran_recojos`
- `test_tenant_suspendido_no_registra_recojos`
- `test_listado_solo_muestra_recojos_del_tenant`
- `test_listado_pagina_50_y_anota_totales_sin_n_plus_uno`
- `test_detalle_precarga_lineas_y_no_filtra_otro_tenant`
- `test_no_se_puede_editar_ni_borrar_un_recojo`
- `test_tipo_de_material_con_recojo_no_se_puede_cambiar`
- `test_series_simultaneas_solo_crean_un_recojo`
- `test_fallo_de_stock_revierte_recojo_lineas_series_y_auditoria`
- `test_auditoria_de_recojo_y_stock_sin_secretos`
- `test_previsualizacion_no_escribe_en_base`
- `test_previsualizacion_no_revela_tenant_de_serie_existente`
- `test_normalizacion_de_series_elimina_espacios_internos`
- `test_cantidad_invalida_en_material_seriado_se_rechaza`
- `test_material_no_seriado_con_series_se_rechaza`
- `test_serie_existente_de_otro_tenant_se_marca_ya_existe`

Además, pruebas de base de datos:
- Insertar una serie con formato inválido directamente debe fallar por `CheckConstraint`.
- Insertar dos series con el mismo `numero` directamente debe fallar por `unique`.
- Insertar una línea sin serie ni cantidad debe fallar por `CheckConstraint`.
- Insertar una línea con serie y `cantidad != 1` debe fallar por `CheckConstraint`.
- Insertar una línea con cantidad negativa debe fallar por `CheckConstraint`.
- Insertar un recojo con un `tenant` distinto al de la línea debe ser detectable por la prueba de
  coherencia del servicio (no hay restricción cruzada en la base).

Pruebas de contrato HTTP (rutas, roles, códigos y mensajes) e integración de servicios viven en
`tests/contract/` e `tests/integration/`.

## Decisiones y riesgos

- **Registro central de series:** `series.Serie` con `unique(numero)` es la única forma simple de
  imponer la unicidad global en la base. 005, 010 y 011 deben usarlo y no duplicar la cadena.
- **Dependencia de 008:** el modelo `StockGeneral` y el servicio de incremento son prerrequisito de
  004. Si 008 no está implementada, 004 se detiene; no se duplica el stock. La parte de confirmación
  de asignaciones de 008 puede ir después de 007.
- **Vista previa HTML:** se mantiene el estilo HTMX del proyecto; no se agrega una API JSON ni
  JavaScript de framework. El endpoint es de solo lectura y no es la autoridad de validación.
- **Normalización de espacios:** se eliminan todos los espacios en blanco, no solo los externos,
  para cumplir RF-18 y facilitar el pegado/escaneo. Si el negocio distingue espacios internos, se
  corrige la spec primero.
- **Todo o nada:** la vista previa no escribe; el guardado revalida y crea el recojo completo o nada
  dentro de una transacción. La restricción única de serie resuelve la concurrencia.
- **Auditoría sin una fila por serie:** el recojo y el stock se auditan; la serie queda trazada por
  su fila, autor, fecha y vínculo con la línea. Evita inflar el libro con miles de registros.
- **Sin edición ni borrado:** un recojo es un movimiento histórico; una corrección se hará con una
  operación de ajuste/devolución posterior, no editando el documento.
- **Tipo de material inmutable:** 004 registra la verificación de movimientos en 002; sin ella, un
  material con series podría cambiar de tipo y corromper el inventario.
- **Lote informativo:** se copia del catálogo y no separa stock; el stock general es por tenant y
  material.
- **Rendimiento:** una consulta `__in` para todas las series y anotaciones para los totales. Si el
  volumen de series crece mucho, se evalúa un índice adicional o particionamiento en una spec
  posterior.
- **RLS:** se recomienda como respaldo; la aplicación no depende de ella para el aislamiento.
- **Técnicos fuera de alcance:** 004 no referencia técnicos; el desglose global que decía lo
  contrario se corrige en la documentación.

## Complexity Tracking

> Sin violaciones a la constitución. La única complejidad adicional es el registro central de
> series, exigido por la unicidad global en la base de datos.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Ninguna (complejidad adicional: `series.Serie`) | La constitución exige unicidad global de series impuesta en la base de datos; una columna única por tabla no puede garantizarla entre recojos, stock inicial, conciliación y logística inversa | Guardar la serie como cadena en cada tabla operativa obligaría a consultar todas las tablas y a validar solo en la aplicación; no resiste concurrencia ni inserciones directas |

## Artefactos de diseño

| Artefacto | Contenido |
|---|---|
| `research.md` | Decisiones: apps, registro central de series, normalización, representación de líneas, región/tenant, dependencia de stock, validación todo o nada, vista previa HTML, permisos, auditoría, inmutabilidad, integración con 002, rendimiento, concurrencia y RLS |
| `data-model.md` | Entidades `Recojo`, `LineaRecojo` y `Serie`, dependencia `StockGeneral`, campos, restricciones, índices, normalización, estados y eventos de auditoría |
| `contracts/http-endpoints.md` | Rutas, roles, peticiones, respuestas, códigos y mensajes |
| `contracts/validacion-series.md` | Contrato del fragmento HTMX de vista previa, estados y garantías de aislamiento |
| `contracts/auditoria-recojo.md` | Eventos auditados, datos prohibidos y reglas de escritura |
| `quickstart.md` | Escenarios ejecutables de validación extremo a extremo |
