# Plan técnico: 011 Logística Inversa y Devoluciones

**Branch**: `011-logistica-inversa-y-devoluciones` | **Date**: 2026-11-12 | **Spec**:
`05-especificaciones/011-logistica-inversa-y-devoluciones/spec.md`

**Input**: Spec en `05-especificaciones/011-logistica-inversa-y-devoluciones/spec.md`

## Summary

Implementar la logística inversa del tenant: registrar la devolución de series por parte de un
técnico, devolverlas al stock general y dejar la custodia libre; registrar equipos recuperados o de
baja con causa (avería, migración u otro), sacándolos del stock disponible sin eliminar la serie; y
generar automáticamente el acta de entrega de devoluciones a Lari, con hash SHA-256 y descarga
verificada.

La devolución mueve stock del técnico al stock general y deja la serie `DISPONIBLE`. La baja saca la
serie del stock donde esté (técnico o general), la deja `INACTIVA` y no vuelve a asignarse. Ninguna de
las dos operaciones toca series de otro tenant ni elimina filas. El acta se genera al registrar la
devolución, dentro de la misma transacción, y se guarda inmutable.

## Technical Context

| Aspecto | Decisión |
|---|---|
| Lenguaje | Python 3.12+ |
| Framework | Django LTS 5.x |
| Base de datos | PostgreSQL 16+; sin SQLite, tampoco en pruebas |
| Interfaz | Django + HTMX; devoluciones, bajas, detalle y descarga de acta |
| App nueva | `logistica_inversa` |
| Serie | `series.Serie`; nuevo estado terminal `INACTIVA` |
| Devolución | `ASIGNADA → DISPONIBLE`; stock técnico → stock general |
| Baja | `ASIGNADA`/`DISPONIBLE → INACTIVA`; sale del stock técnico o general |
| Acta | `openpyxl`; una hoja; generada al registrar; SHA-256 |
| Stock | Servicios de 008; el total del tenant no cambia en devolución |
| Transacciones | Devolución y baja atómicas; acta dentro de la transacción |
| Bloqueos | `select_for_update` en orden estable |
| Auditoría | `auditoria.RegistroCambio` en la misma transacción |
| Correo/Celery | Fuera de alcance; el tenant descarga y envía el acta |
| Dependencias nuevas | Ninguna |
| Pruebas | `pytest` + `pytest-django` sobre PostgreSQL |

### Prerrequisitos bloqueantes

- **001**: `AUTH_USER_MODEL`, `ContextoUsuarioMiddleware`, `Tenant`, `Region`, roles y auditoría.
- **002**: `Material` con `codigo`, `descripcion`, `lote` y `es_seriado`.
- **003**: `Tecnico` con `tenant`, `nif`, `nombre` y `activo`.
- **004**: `series.Serie` con `numero`, `tenant`, `region`, `material`, `estado`, `tecnico` y
  `asignada_en`; `EstadoSerie` con `DISPONIBLE`, `RESERVADA`, `ASIGNADA`, `INSTALADA` e `INACTIVA`.
- **005/008**: `StockTecnico`, `StockGeneral`, `incrementar_stock_tecnico`,
  `decrementar_stock_tecnico`, `incrementar_stock_general` y `decrementar_stock_general`.
- **009**: custodia de series y bloqueo de series reservadas en traspasos `ENVIADA`.
- **010**: estado `INSTALADA` y conciliación; 011 no modifica conciliaciones.
- **Infraestructura**: PostgreSQL con rol sin `SUPERUSER` ni `BYPASSRLS`.

Si falta cualquiera, la implementación se detiene y se reporta.

### Orden de implementación

1. Correcciones documentales de 004/009 y migración de `Serie.estado=INACTIVA`.
2. App `logistica_inversa`: modelos, migraciones y servicios de devolución.
3. Acta automática y descarga verificada.
4. Servicio de baja y pantallas.
5. 012 consume `INACTIVA`/`INSTALADA` sin duplicar la logística inversa.

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | `Devolucion`, `LineaDevolucion` y `BajaEquipo` llevan `tenant`; la devolución lleva `region`. El tenant sale de la sesión; series, técnicos y stock de otro tenant se rechazan o no se exponen. RLS como respaldo. |
| II. Jerarquía Región → Tenant → Técnico | PASA | El técnico pertenece al tenant; la región se fija desde `tenant.region`; el Administrador no registra devoluciones ni bajas. |
| III. Invariantes de stock | PASA | Devolución: baja stock técnico y sube stock general por el mismo total; el total del tenant no cambia. Baja: saca la serie del stock técnico o general, sin tocar el otro. No se deja stock negativo. |
| IV. Identidad y unicidad de series | PASA | Se usa `series.Serie`; no se crea otra tabla. La devolución deja `DISPONIBLE` y la baja `INACTIVA`; no se elimina ni se duplica. |
| V. Integridad transaccional | PASA | Devolución, serie, stock, acta y auditoría ocurren en una transacción. La baja es igual. Cualquier fallo revierte todo. |
| VI. Auditoría inmutable y trazabilidad | PASA | `Devolucion/alta`, `BajaEquipo/alta`, `Serie/estado`, `Serie/tecnico`, `Serie/asignada_en`, `Devolucion/acta` y `StockTecnico`/`StockGeneral/cantidad` con valor anterior y nuevo. Sin secretos ni binarios. |
| VII. Autoridad del reporte de Lari y aprobación humana | PASA | 011 no procesa reportes de Lari ni aprueba conciliaciones; solo registra devoluciones y bajas humanas. |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada CA-01…CA-06 tiene prueba. Solo se usa `openpyxl`; no se agregan dependencias, correo ni Celery. La lógica vive en `logistica_inversa/services.py`. |

**Post-design re-check**: PASA. El diseño corrige el estado terminal, usa FK a `Serie`, no elimina
series, no toca el stock equivocado en la baja y genera el acta de forma atómica.

## Project Structure

```text
logistica_inversa/
├── __init__.py
├── apps.py
├── models.py
├── services.py
├── acta.py
├── forms.py
├── views.py
├── urls.py
├── migrations/
│   ├── 0001_initial.py
│   └── 0002_rls.py

series/
└── migrations/
    └── 0005_serie_inactiva.py

templates/
└── logistica_inversa/
    ├── devoluciones_listado.html
    ├── devolucion_formulario.html
    ├── devolucion_detalle.html
    ├── bajas_listado.html
    └── baja_formulario.html

tests/
├── unit/
│   ├── test_logistica_inversa_servicios.py
│   └── test_logistica_inversa_acta.py
├── integration/
│   ├── test_devolucion_registro.py
│   ├── test_devolucion_stock.py
│   ├── test_baja_registro.py
│   ├── test_baja_stock.py
│   ├── test_logistica_inversa_concurrencia.py
│   └── test_logistica_inversa_auditoria.py
└── contract/
    └── test_logistica_inversa_http.py
```

También se modifican:

- `config/settings/base.py`: registrar `logistica_inversa` y `ACTAS_DIR`.
- `config/urls.py`: incluir `logistica_inversa.urls`.
- `templates/base.html`: enlaces a devoluciones y bajas para `USUARIO_TENANT`.
- `series/models.py` y `series/migrations/`: estado `INACTIVA` y coherencia de custodia.
- `05-especificaciones/011-logistica-inversa-y-devoluciones/plan.md`: este documento.
- No se crean tareas Celery ni se modifica `StockGeneral` fuera de los servicios de 008.

## Modelo de datos

### `logistica_inversa.Devolucion`

```python
class Devolucion(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT,
                               related_name="devoluciones")
    region = models.ForeignKey("tenants.Region", on_delete=models.PROTECT,
                               related_name="devoluciones")
    tecnico = models.ForeignKey("tecnicos.Tecnico", on_delete=models.PROTECT,
                                related_name="devoluciones")
    fecha = models.DateField()
    observaciones = models.TextField(blank=True, default="")
    acta_ruta = models.CharField(max_length=255, blank=True, default="")
    acta_hash = models.CharField(max_length=64, blank=True, default="")
    acta_generada_en = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="devoluciones_creadas")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="devolucion_tenant_fecha"),
            models.Index(fields=["region", "fecha"], name="devolucion_region_fecha"),
            models.Index(fields=["tecnico", "fecha"], name="devolucion_tecnico_fecha"),
        ]
```

- `tenant` y `region` salen de la sesión y de `tenant.region`.
- `tecnico` pertenece al tenant y a la región.
- `fecha` no puede ser futura.
- `acta_ruta` es relativa; `acta_hash` es SHA-256; el acta es inmutable.
- No se elimina; se conserva con sus líneas y su acta.

### `logistica_inversa.LineaDevolucion`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT`; copiado de la devolución |
| `devolucion` | FK `Devolucion` | `CASCADE`, `related_name="lineas"` |
| `serie` | FK `series.Serie` | `PROTECT`, `related_name="lineas_devolucion"` |
| `material` | FK `Material` | `PROTECT`; copiado de `serie.material` |
| `descripcion` | `CharField(255)` | Copia de `material.descripcion` para el acta |
| `lote` | `CharField(50)` | Copia de `serie.lote` |

- `UniqueConstraint(devolucion, serie)` para no repetir una serie en la misma devolución.
- Índices `(devolucion, serie)`, `(tenant, material)` y `(serie)`.
- No se edita ni se borra; es parte del documento histórico.
- La serie debe estar `ASIGNADA` al técnico al registrar.

### `logistica_inversa.BajaEquipo`

| Campo | Tipo | Regla |
|---|---|---|
| `tenant` | FK `Tenant` | `PROTECT` |
| `region` | FK `Region` | `PROTECT`; copiado de `tenant.region` |
| `serie` | `OneToOneField(series.Serie)` | `PROTECT`, `related_name="baja"`; una baja por serie |
| `material` | FK `Material` | `PROTECT`; copiado de la serie |
| `causa` | `CharField(20)` | `AVERIA`, `MIGRACION`, `OTRO` |
| `observaciones` | `TextField` | `blank=True, default=""` |
| `creado_por` | FK `Usuario` | `PROTECT` |
| `creado_en` | `DateTimeField` | `auto_now_add` |

- `UniqueConstraint(serie)` implícita por `OneToOneField`; una serie no se da de baja dos veces.
- Índices `(tenant, causa)`, `(region, creado_en)` y `(serie)`.
- La causa es obligatoria; `OTRO` no exige texto adicional, pero se permite observación.
- No se elimina; conserva la trazabilidad de la baja.

### `series.Serie` (estado terminal)

| Aspecto | Cambio |
|---|---|
| `EstadoSerie` | Añade `INACTIVA` |
| `CheckConstraint(serie_estado_valido)` | `DISPONIBLE`, `RESERVADA`, `ASIGNADA`, `INSTALADA`, `INACTIVA` |
| Coherencia de custodia | `INACTIVA` exige `tecnico=None` y `asignada_en=None` |
| Transición | `ASIGNADA`/`DISPONIBLE → INACTIVA` al registrar la baja |
| Reversión | No vuelve al stock disponible; no se reasigna |

- `INACTIVA` es terminal y distinta de `INSTALADA`: `INSTALADA` es liquidación por conciliación;
  `INACTIVA` es recuperación/baja por avería o migración.
- 012 puede contar ambas según su regla de reportes.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 011 |
|---|---|---|
| `series.Serie` | 004 | Estado y custodia; 011 cambia estado y limpia técnico/fecha. |
| `stock.StockTecnico` | 008 | Devolución y baja de series en custodia. |
| `stock.StockGeneral` | 008 | Devolución suma; baja de serie disponible resta. |
| `tecnicos.Tecnico` | 003 | Técnico que devuelve; tenant y NIF. |
| `materiales.Material` | 002 | Código, descripción y lote para el acta. |
| `tenants.Tenant` / `Region` | 001 | Alcance, RLS y metadatos. |
| `auditoria.RegistroCambio` | 001 | Auditoría compartida. |

## Migraciones

1. `series/migrations/0005_serie_inactiva.py`: añade `INACTIVA` a choices/check y amplía la coherencia
   de custodia; no reescribe series existentes.
2. `logistica_inversa/migrations/0001_initial.py`: `Devolucion`, `LineaDevolucion` y `BajaEquipo` con
   restricciones e índices.
3. `logistica_inversa/migrations/0002_rls.py`: RLS por `tenant_id`/`region_id` en devoluciones y
   bajas, y por `tenant_id` en líneas; si 001 no está disponible, deuda.
4. No se modifican tablas de stock, asignaciones, recojos, traspasos ni conciliaciones.

## Servicios (lógica de negocio)

Viven en `logistica_inversa/services.py`; las vistas solo orquestan.

### Excepciones

- `PermisoDenegado`: “No tienes permiso para registrar devoluciones”.
- `SerieNoEnTecnico`: “La serie no está asignada al técnico”.
- `SerieNoDisponible`: “La serie no está disponible para la baja”.
- `SerieReservada`: “La serie está reservada en otro traspaso”.
- `SerieYaInactiva`: “La serie ya fue dada de baja”.
- `SerieInstalada`: “La serie está instalada y no puede devolverse ni darse de baja”.
- `SerieFueraTenant`: “La serie no pertenece a este tenant”.
- `TecnicoNoExiste`: “El técnico no existe o no pertenece al tenant”.
- `CausaRequerida`: “Debe indicar la causa de la baja”.
- `CausaInvalida`: “La causa de la baja no es válida”.
- `FechaInvalida`: “La fecha de devolución no es válida”.
- `SinSeries`: “Debe seleccionar al menos una serie”.
- `NoEncontrado`: “La devolución no existe”.
- `ArchivoNoDisponible` / `HashNoCoincide`: “El acta no está disponible” / “El acta fue modificada,
  descarga bloqueada”.

### Alcance y validaciones

- `validar_cuenta_tenant(actor, tenant)`: `USUARIO_TENANT`, cuenta activa, tenant activo y
  `actor.tenant_id == tenant.id`.
- `validar_tecnico(tenant, tecnico)`: existe, pertenece al tenant y a la región.
- `validar_serie_para_devolucion(serie, tecnico)`:
  - Mismo tenant que el técnico.
  - `estado=ASIGNADA`, `serie.tecnico_id == tecnico.id`.
  - No referenciada por una `LineaTraspaso` de solicitud `ENVIADA` (reservada).
  - No `INSTALADA` ni `INACTIVA`.
- `validar_serie_para_baja(serie, tenant)`:
  - Mismo tenant.
  - `estado=ASIGNADA` o `DISPONIBLE`; no `RESERVADA`, `INSTALADA` ni `INACTIVA`.
  - Si `ASIGNADA`, debe tener `tecnico` y `asignada_en`.
  - Si `DISPONIBLE`, no debe tener técnico.
- `validar_fecha_devolucion(fecha)`: no futura.

### Devolución

- `registrar_devolucion(tenant, tecnico, fecha, series, observaciones, actor)`:
  1. Valida cuenta, técnico, fecha, al menos una serie y cada serie.
  2. En `transaction.atomic`:
     - Bloquear `Tenant`, `StockGeneral` por `material_id`, `StockTecnico` del técnico por
       `material_id` y series por `id`.
     - Revalidar estado/custodia/reserva dentro del bloqueo.
     - Crear `Devolucion` con región de la sesión.
     - Crear `LineaDevolucion` por serie con `tenant`, material, descripción y lote.
     - Por cada serie: `estado=DISPONIBLE`, `tecnico=None`, `asignada_en=None`; auditar
       `Serie/estado`, `Serie/tecnico` y `Serie/asignada_en`.
     - Por material: `decrementar_stock_tecnico(tecnico, material, n, actor)` e
       `incrementar_stock_general(tenant, material, n, actor)`; los servicios de 008 auditan el
       stock.
     - Generar el acta, guardar ruta/hash y auditar `Devolucion/acta`.
     - Auditar `Devolucion/alta` y `LineaDevolucion/alta`.
  3. Si falla el acta, se revierte la devolución y se elimina el archivo parcial.
  4. Devuelve la devolución.

### Baja

- `registrar_baja_equipo(tenant, serie, causa, observaciones, actor)`:
  1. Valida cuenta, existencia de la serie en el tenant, estado, causa y que no tenga baja previa.
  2. En `transaction.atomic`:
     - Bloquear `Tenant`, la fila de stock correspondiente (`StockGeneral` o `StockTecnico`) y la
       serie.
     - Revalidar estado, custodia y stock suficiente.
     - Crear `BajaEquipo` con región, material, causa y observaciones.
     - Si la serie estaba `ASIGNADA`: `decrementar_stock_tecnico(tecnico, material, 1, actor)`.
     - Si estaba `DISPONIBLE`: `decrementar_stock_general(tenant, material, 1, actor)`.
     - Cambiar la serie a `INACTIVA` y limpiar `tecnico`/`asignada_en`; auditar `Serie/estado`,
       `Serie/tecnico` y `Serie/asignada_en`.
     - Auditar `BajaEquipo/alta` con causa.
  3. No toca el stock que no corresponde ni el stock de otro tenant.
  4. Devuelve la baja.

### Acta

- `generar_acta_devolucion(devolucion)`:
  - Genera un `.xlsx` de una hoja con metadatos: tenant, región, fecha de generación e ID.
  - Tabla: NIF, material, descripción, serie y fecha de devolución.
  - Guarda en `ACTAS_DIR`/`MEDIA_ROOT` con nombre relativo seguro y hash SHA-256.
  - Se ejecuta al registrar la devolución, dentro de la transacción.
  - No se regenera después; es inmutable.
- `verificar_hash_acta(devolucion, contenido)`:
  - Recalcula SHA-256 y compara con `hmac.compare_digest`.
  - Si no coincide, `HashNoCoincide`.

### Consultas

- `listar_devoluciones(tenant, fecha_desde=None, fecha_hasta=None)`.
- `obtener_devolucion(tenant, devolucion_id)`.
- `detalle_devolucion(devolucion)`.
- `listar_bajas(tenant, causa=None)`.
- `obtener_baja(tenant, baja_id)`.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/logistica-inversa/devoluciones/` | GET | Listado paginado con filtro por fecha |
| `/logistica-inversa/devoluciones/nueva/` | GET/POST | Registrar devolución |
| `/logistica-inversa/devoluciones/<id>/` | GET | Detalle y series |
| `/logistica-inversa/devoluciones/<id>/acta/` | GET | Descargar acta verificando hash |
| `/logistica-inversa/bajas/` | GET | Listado de bajas |
| `/logistica-inversa/bajas/nueva/` | GET/POST | Registrar baja |
| `/logistica-inversa/bajas/<id>/` | GET | Detalle de baja |

- No hay `POST` para generar el acta: se genera automáticamente al registrar la devolución.
- No hay `GET` para acciones de escritura.
- Un recurso ajeno devuelve `404`; un rol incorrecto, `403`; un estado inválido, `409`.
- No se aceptan `tenant_id`, `region_id`, estado, material ni NIF del cliente.
- El formulario de devolución solo ofrece técnicos del tenant y series `ASIGNADA` de ese técnico, no
  reservadas.
- El formulario de baja recibe la serie y la causa; el material se obtiene de la serie.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Cuenta del tenant | Servicio | “No tienes permiso para registrar devoluciones” |
| Técnico del tenant/región | Servicio | “El técnico no existe o no pertenece al tenant” |
| Serie del tenant | Servicio | “La serie no pertenece a este tenant” |
| Serie asignada al técnico | Servicio | “La serie no está asignada al técnico” |
| Serie no reservada | Servicio | “La serie está reservada en otro traspaso” |
| Serie no instalada/inactiva | Servicio | “La serie está instalada y no puede devolverse ni darse de baja” / “La serie ya fue dada de baja” |
| Serie disponible/asignada para baja | Servicio | “La serie no está disponible para la baja” |
| Causa obligatoria/válida | Servicio y formulario | “Debe indicar la causa de la baja” / “La causa de la baja no es válida” |
| Fecha no futura | Servicio | “La fecha de devolución no es válida” |
| Al menos una serie | Servicio | “Debe seleccionar al menos una serie” |
| Una serie por devolución | `UniqueConstraint` | Violación de restricción de base |
| Una baja por serie | `OneToOneField` | Violación de restricción de base |

## Transacciones y concurrencia

- Orden de bloqueo: `Tenant` → `StockGeneral` por `material_id` → `StockTecnico` por `material_id` →
  `Serie` por `id`.
- Es compatible con 008: 008 bloquea `Tenant → StockGeneral → StockTecnico → Serie`.
- Devolución y baja son una sola transacción; cualquier fallo revierte series, stock, acta y
  auditoría.
- Dos devoluciones simultáneas de la misma serie: solo una pasa; la segunda detecta que ya no está
  `ASIGNADA`.
- Dos bajas simultáneas de la misma serie: el `OneToOneField` y el bloqueo dejan una sola.
- Devolución y traspaso simultáneos: si la serie está reservada en un traspaso `ENVIADA`, la
  devolución falla con `SerieReservada`.
- No se usan decrementos con `F()` ciego; se usan los servicios de 008.

## Acta de entrega

- Formato según `04-contratos/acta-devoluciones.md`: una hoja, metadatos y tabla NIF/material/
  descripción/serie/fecha.
- Se genera automáticamente al registrar la devolución, no a demanda.
- Se guarda con nombre relativo seguro y hash SHA-256; el binario no se guarda en base ni se audita.
- La descarga verifica el hash antes de servir; si no coincide, `409` “El acta fue modificada,
  descarga bloqueada”.
- No se envía por correo desde el sistema; el tenant la descarga y la envía a Lari.
- Las bajas no generan acta en 011; su trazabilidad está en `BajaEquipo` y la auditoría.

## Auditoría y RLS

- Eventos:
  - `Devolucion/alta`: tenant, región, técnico, fecha, total de series, actor.
  - `LineaDevolucion/alta`: serie, material, lote.
  - `Devolucion/acta`: ruta relativa y hash.
  - `BajaEquipo/alta`: serie, material, causa, observaciones, actor.
  - `Serie/estado`: `ASIGNADA→DISPONIBLE` o `ASIGNADA/DISPONIBLE→INACTIVA`.
  - `Serie/tecnico` y `Serie/asignada_en`: limpieza de custodia.
  - `StockTecnico/cantidad` y `StockGeneral/cantidad`: los escribe 008.
- Cada ajuste registra valor anterior y nuevo.
- No se auditan secretos, binarios, rutas absolutas ni datos de otro tenant.
- RLS:
  - `logistica_inversa_devolucion`: por `tenant_id` y `region_id`.
  - `logistica_inversa_lineadevolucion`: por `tenant_id`.
  - `logistica_inversa_bajaequipo`: por `tenant_id` y `region_id`.
  - Si 001 no está disponible, deuda registrada y filtrado ORM.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Pruebas

Un caso por criterio de aceptación, más servicios, acta, concurrencia, auditoría y aislamiento.

| CA | Prueba principal |
|---|---|
| CA-01 | `test_devolucion_libera_custodia` |
| CA-02 | `test_series_devueltas_pueden_reasignarse` |
| CA-03 | `test_recuperacion_con_causa` |
| CA-04 | `test_baja_por_migracion` |
| CA-05 | `test_generacion_acta` |
| CA-06 | `test_auditoria_devoluciones` |

Además:

- **Devolución**: serie no en técnico, serie reservada, serie instalada/inactiva, serie de otro
  tenant, fecha futura, sin series, duplicada, acta fallida, stock insuficiente.
- **Baja**: serie reservada, serie instalada/inactiva, serie de otro tenant, causa inválida,
  serie en stock técnico, serie en stock general, serie inexistente, doble baja.
- **Acta**: una hoja, metadatos, tabla, hash estable, descarga, hash alterado, ruta segura, sin
  binarios en base.
- **Concurrencia**: dos devoluciones, dos bajas, devolución vs traspaso, bloqueo sin interbloqueo.
- **Auditoría**: todos los eventos, valores anterior/nuevo, actor correcto, sin secretos.
- **Aislamiento**: tenant A no ve devoluciones/bajas de B; región ajena `404`; series de otro tenant
  no se consultan.
- **Rendimiento**: devolución de 100 series en menos de 2 segundos, sin N+1.

## Correcciones documentales necesarias

| Documento | Corrección |
|---|---|
| `011-logistica-inversa-y-devoluciones/plan.md` | Sustituir `LineaDevolucion.serie`/`BajaEquipo.serie` por FK a `Serie`, añadir `tenant`/`region`, corregir stock de baja y acta automática. |
| `004-recojo-de-materiales/data-model.md`, `plan.md` y `tasks.md` | Añadir `INACTIVA` a `EstadoSerie`, choices y check; ampliar la coherencia de custodia. |
| `009-traspaso-entre-tecnicos/data-model.md` | Ampliar `serie_tecnico_coherente_estado` para admitir `INACTIVA` sin custodia. |
| `012-reportes-mensuales/plan.md` | Distinguir `INSTALADA` (conciliación) e `INACTIVA` (baja) si el reporte las cuenta por separado. |
| `04-contratos/acta-devoluciones.md` | Confirmar que el acta se genera al registrar y que el envío lo hace el tenant, no el sistema. |

## Decisiones y riesgos

- **Devolución mueve stock al general**: el total del tenant no cambia; la serie queda `DISPONIBLE` y
  puede reasignarse. Alternativa descartada: dejar la serie `ASIGNADA` sin técnico (inconsistente).
- **Baja saca del stock donde está**: técnico o general, no ambos. Alternativa descartada: decrementar
  ambos (descuadra el total).
- **`INACTIVA` distinta de `INSTALADA`**: una es baja/recuperación, la otra liquidación por reporte.
  Ambas son terminales y no se eliminan.
- **Acta automática e inmutable**: cumple el contrato y evita actas desincronizadas. Alternativa
  descartada: generarla a demanda y permitir que el contenido cambie.
- **Sin correo del sistema**: el tenant descarga y envía; la spec no define correo propio.
- **Series reservadas**: no se devuelven ni se dan de baja hasta liberar el traspaso.
- **Riesgo de bajas masivas**: se monitorea el stock; no hay operación masiva en esta versión.
- **Riesgo de acta huérfana**: se genera dentro de la transacción y se limpia si falla.

## Complexity Tracking

| Decisión | Por qué no viola la constitución |
|---|---|
| Estado terminal `INACTIVA` | No elimina la serie ni duplica identidad; conserva la trazabilidad de la baja. |
| FK a `Serie` en líneas y bajas | Usa el registro central y la unicidad global; no crea otra tabla de series. |
| Acta dentro de la transacción | Mantiene el todo o nada; el archivo parcial se elimina si falla. |
| Sin correo/Celery | La spec no lo pide; el tenant descarga y envía. |

## Criterios de salida

- `research.md`, `data-model.md`, `contracts/` y `quickstart.md` creados y coherentes con este plan.
- Plan sin series eliminadas, sin doble decremento en la baja, sin correo/Celery y sin permisos
  Django.
- Correcciones de 011/004/009/012 y del contrato del acta registradas y aplicadas antes de
  implementar.
- `tasks.md` derivado de este plan cubre CA-01…CA-06 con al menos una prueba por criterio.
- No se implementa código en esta fase.
