# Modelo de datos: 009 Traspaso entre Técnicos

**Fase**: 1 | **Fecha**: 2026-11-21 | **Spec**:
`05-especificaciones/009-traspaso-entre-tecnicos/spec.md`

Describe las entidades del traspaso multi-técnico (1→N / N→1), la custodia de series, las reservas
derivadas, el cuadre, las transiciones y la trazabilidad. El detalle de servicios está en `plan.md`;
los contratos en `contracts/`.

## Diagrama de relaciones

```mermaid
erDiagram
    TENANT ||--o{ SOLICITUD_TRASPASO : "posee"
    REGION ||--o{ SOLICITUD_TRASPASO : "agrupa"
    SOLICITUD_TRASPASO ||--o{ LINEA_TRASPASO : "contiene"
    TECNICO ||--o{ LINEA_TRASPASO : "origen"
    TECNICO ||--o{ LINEA_TRASPASO : "destino"
    MATERIAL ||--o{ LINEA_TRASPASO : "se mueve"
    SERIE ||--o{ LINEA_TRASPASO : "se mueve"
    TENANT ||--o{ SERIE : "posee"
    TECNICO ||--o{ SERIE : "custodia"
    TECNICO ||--o{ STOCK_TECNICO : "posee"
    MATERIAL ||--o{ STOCK_TECNICO : "acumula"
    SOLICITUD_TRASPASO ||--o{ REGISTRO_CAMBIO : "se audita"
```

- `SOLICITUD_TRASPASO`, `LINEA_TRASPASO` son nuevas.
- `SERIE`, `STOCK_TECNICO`, `TECNICO` y `MATERIAL` son externas; 009 solo cambia la custodia de
  `SERIE` y usa los servicios de `STOCK_TECNICO`.
- `STOCK_GENERAL` no aparece: 009 no lo lee ni lo escribe.
- No hay tabla de reservas: se derivan de `SOLICITUD_TRASPASO.estado=ENVIADA`.
- El técnico origen y el destino viven en la **línea**; la solicitud agrupa varias líneas.

## Entidades

### `traspasos.SolicitudTraspaso`

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `tenant` | FK `tenants.Tenant` | No | `PROTECT`, `related_name="solicitudes_traspaso"`; inmutable |
| `region` | FK `tenants.Region` | No | `PROTECT`, `related_name="solicitudes_traspaso"`; copiada de `tenant.region`; inmutable |
| `fecha` | `DateField` | No | Fecha del traspaso; por defecto hoy |
| `estado` | `CharField(20)` | No | `BORRADOR`, `ENVIADA`, `CONFIRMADA`, `RECHAZADA`, `CANCELADA`; default `BORRADOR` |
| `motivo_rechazo` | `TextField` | No | `blank=True, default=""`; solo al rechazar; máximo 1000 |
| `excel_ruta` | `CharField(255)` | No | `blank=True, default=""`; ruta relativa |
| `excel_hash` | `CharField(64)` | No | `blank=True, default=""`; SHA-256 |
| `creado_por` | FK `acceso.Usuario` | No | `PROTECT`, `related_name="traspasos_creados"` |
| `creado_en` | `DateTimeField` | No | `auto_now_add` |
| `enviada_en` | `DateTimeField` | Sí | Se fija al enviar |
| `confirmada_en` | `DateTimeField` | Sí | Se fija al confirmar |
| `rechazada_en` | `DateTimeField` | Sí | Se fija al rechazar |
| `cancelada_en` | `DateTimeField` | Sí | Se fija al cancelar |
| `actualizado_por` | FK `acceso.Usuario` | Sí | `PROTECT`, `related_name="+"` |
| `actualizado_en` | `DateTimeField` | No | `auto_now` |

**Restricciones**

- `CheckConstraint(estado__in=[...], name="solicitud_traspaso_estado_valido")`.
- La coherencia estado/fecha (`ENVIADA` exige `enviada_en`, etc.) se valida en el servicio y se
  prueba; no se impone con una restricción condicional múltiple para no duplicar la máquina de
  estados.
- La pertenencia de los técnicos al `tenant` se valida en el servicio; no se puede expresar con un
  `CheckConstraint` entre tablas.

**Índices**

- `(tenant, estado)`, `(region, estado)`, `(tenant, fecha)`.

**Propiedades derivadas**

- `origenes`: técnicos distintos con líneas como origen.
- `destinos`: técnicos distintos con líneas como destino.
- `tecnicos`: unión de orígenes y destinos.
- `forma`: `1→N`, `N→1` o `INVALIDA`, calculada a partir de las líneas.

**Reglas**

- `tenant` y `region` salen de la sesión y de `tenant.region`; nunca del cliente.
- La solicitud no guarda un único origen/destino; se derivan de las líneas.
- Debe haber al menos dos técnicos distintos y forma 1→N o N→1.
- Solo `BORRADOR` se edita, envía o cancela; solo `ENVIADA` se confirma o rechaza.
- No se elimina; se conserva con su estado terminal.

### `traspasos.LineaTraspaso`

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `tenant` | FK `tenants.Tenant` | No | `PROTECT`, `related_name="lineas_traspaso"`; copiado de la solicitud |
| `solicitud` | FK `SolicitudTraspaso` | No | `CASCADE`, `related_name="lineas"` |
| `tecnico_origen` | FK `tecnicos.Tecnico` | No | `PROTECT`, `related_name="lineas_traspaso_origen"`; inmutable |
| `tecnico_destino` | FK `tecnicos.Tecnico` | No | `PROTECT`, `related_name="lineas_traspaso_destino"`; inmutable |
| `material` | FK `materiales.Material` | No | `PROTECT`, `related_name="lineas_traspaso"`; inmutable |
| `lote` | `CharField(50)` | No | `blank=True, default=""`; copia de `material.lote` |
| `serie` | FK `series.Serie` | Sí | `PROTECT`, `related_name="lineas_traspaso"`; nullable para no seriados |
| `cantidad` | `IntegerField` | No | `default=0`; `>0` para no seriados, `1` para seriados |

**Restricciones**

- `CheckConstraint(~Q(tecnico_origen=F("tecnico_destino")), name="linea_traspaso_origen_destino_distintos")`.
- `CheckConstraint(Q(serie__isnull=False) | Q(cantidad__gt=0), name="linea_traspaso_serie_o_cantidad")`.
- `CheckConstraint(Q(serie__isnull=True) | Q(cantidad=1), name="linea_traspaso_serie_cantidad_uno")`.
- `CheckConstraint(Q(cantidad__gte=0), name="linea_traspaso_cantidad_no_negativa")`.
- `UniqueConstraint(fields=["solicitud","serie"], condition=Q(serie__isnull=False), name="linea_traspaso_serie_unica")`.
- `UniqueConstraint(fields=["solicitud","tecnico_origen","tecnico_destino","material"], condition=Q(serie__isnull=True), name="linea_traspaso_no_seriada_unica")`.

**Índices**

- `(solicitud, material)`, `(tenant, material)`, `(tecnico_origen, material)`,
  `(tecnico_destino, material)`, `(serie)`.

**Reglas**

- `tenant` se copia de `solicitud.tenant`; no se acepta del cliente.
- `tecnico_origen` y `tecnico_destino` son del mismo tenant y distintos entre sí.
- Para seriados, `serie` no es nula y `cantidad=1`; la serie debe estar `ASIGNADA` al origen.
- Para no seriados, `serie` es nula y `cantidad>0`; varias filas del mismo origen, destino y material
  se agregan en una sola línea.
- Cada línea tiene una dirección explícita origen → destino.
- La estructura global de la solicitud debe ser 1→N o N→1.
- No se edita una línea fuera de `BORRADOR`.
- No se elimina una línea confirmada; el histórico permanece.

### `series.Serie` (campos añadidos)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `tecnico` | FK `tecnicos.Tecnico` | Sí | `PROTECT`, `related_name="series"`; custodio actual |
| `asignada_en` | `DateTimeField` | Sí | Inicio de la custodia actual; se reinicia al traspasar |

**Restricciones**

- `CheckConstraint(Q(estado="ASIGNADA", tecnico__isnull=False, asignada_en__isnull=False) | (Q(estado__in=["DISPONIBLE","RESERVADA","INSTALADA","INACTIVA"]) & Q(tecnico__isnull=True) & Q(asignada_en__isnull=True)), name="serie_tecnico_coherente_estado")`; `INSTALADA` la agrega 010 e `INACTIVA` 011.
- `tecnico.tenant_id == serie.tenant_id` se valida en el servicio.
- `Index(tecnico, estado)` y `Index(tecnico, material)`.

**Reglas**

- 004 crea `DISPONIBLE` con ambos nulos.
- 005 crea `ASIGNADA` con `tecnico` y `asignada_en` de la línea de stock inicial.
- 008 confirma una asignación y fija `tecnico`/`asignada_en`.
- 009 confirma un traspaso, cambia `tecnico` al destino de la línea y reinicia `asignada_en`; el
  estado sigue `ASIGNADA`.
- 011 devuelve a `DISPONIBLE` y limpia ambos.
- No cambia tenant, región ni material.

### Entidades externas consumidas

| Entidad | Dueña | Uso en 009 |
|---|---|---|
| `series.Serie` | 004 | Identidad, estado y custodia; 009 cambia `tecnico`/`asignada_en`. |
| `stock.StockTecnico` | 008 | Disponibilidad por técnico origen y actualización de stock por línea. |
| `stock.StockGeneral` | 008 | **No se lee ni se escribe.** |
| `tecnicos.Tecnico` | 003 | Origen/destino por línea, tenant y estado activo. |
| `materiales.Material` | 002 | Catálogo, lote y tipo seriado. |
| `asignaciones.SolicitudAsignacion` | 006/007 | Historial de asignaciones; no se modifica. |
| `auditoria.RegistroCambio` | 001 | Auditoría compartida. |

## Cálculos

### Disponibilidad del técnico

```text
Reservado(tecnico, material) =
    cantidad de líneas seriadas ENVIADA con tecnico_origen = tecnico y material
  + suma de cantidad de líneas no seriadas ENVIADA con tecnico_origen = tecnico y material

Disponible(tecnico, material) = max(0, StockTecnico.cantidad - Reservado(tecnico, material))
```

- Solo cuenta `ENVIADA`; `BORRADOR`, `CONFIRMADA`, `RECHAZADA` y `CANCELADA` no reservan.
- Para seriados, además de la cantidad, se valida serie por serie que esté `ASIGNADA` al origen y que
  no esté referenciada por otra solicitud `ENVIADA`.
- Material sin `StockTecnico` devuelve `0`.
- Varias líneas del mismo origen y material se suman antes de comparar.

### Cuadre

```text
Salida(linea)  = (material, lote, serie o cantidad, origen, destino)
Entrada(linea) = la misma tupla

Por serie:
    cada serie aparece exactamente una vez y con el mismo material/lote/origen/destino

Por material no seriado:
    la cantidad de cada línea es la misma que entra en su destino

Agregado:
    suma de cantidades que salen por material == suma de cantidades que entran por material
```

- La lista canónica es la única fuente; las proyecciones se comparan antes de generar el Excel y al
  confirmar.
- Una serie que sale y no entra, una cantidad distinta, un material o lote distinto, una línea extra o
  faltante produce `CuadreIncorrecto`.
- La estructura 1→N / N→1 se valida aparte; el cuadre no la sustituye.

### Ejemplo 1→N

Solicitud del técnico A a los técnicos B y C:

| Línea | Origen | Destino | Material | Cantidad | Stock origen antes | Stock destino antes | Después |
|---|---|---|---|---|---|---|---|
| 1 | A | B | X (no seriado) | 20 | 50 | 10 | A=30, B=30 |
| 2 | A | C | Y (seriado) | 3 series | 10 | 5 | A=7, C=8 |

Stock general: sin cambio.

### Ejemplo N→1

Solicitud de los técnicos A y B al técnico C:

| Línea | Origen | Destino | Material | Cantidad | Stock origen antes | Stock destino antes | Después |
|---|---|---|---|---|---|---|---|
| 1 | A | C | X (no seriado) | 20 | 50 | 0 | A=30, C=20 |
| 2 | B | C | X (no seriado) | 5 | 10 | 20 | B=5, C=25 |

Stock general: sin cambio.

## Transiciones de estado

### Solicitud de traspaso

```text
BORRADOR ── enviar ──▶ ENVIADA ── confirmar ──▶ CONFIRMADA
   │                       └──── rechazar ────▶ RECHAZADA
   └── cancelar ─────────────────────────────▶ CANCELADA
```

- `BORRADOR`: se puede editar, enviar o cancelar; no reserva ni genera Excel.
- `ENVIADA`: reserva derivada activa; se puede confirmar o rechazar.
- `CONFIRMADA`: series en el destino de su línea, stock técnico movido, `asignada_en` reiniciado;
  terminal.
- `RECHAZADA`: sin cambios de custodia ni stock; motivo obligatorio; terminal.
- `CANCELADA`: solo desde `BORRADOR`; sin cambios; terminal.

### Serie

```text
DISPONIBLE ── reserva 006 ──▶ RESERVADA ── confirmación 008 ──▶ ASIGNADA (tecnico, asignada_en)
ASIGNADA ── traspaso 009 ──▶ ASIGNADA (nuevo tecnico, asignada_en reiniciado)
ASIGNADA ── devolución 011 ──▶ DISPONIBLE (tecnico=null, asignada_en=null)
```

- 009 nunca cambia el estado de la serie; solo su custodio y la fecha de inicio de custodia.
- Una serie solo se traspasa si está `ASIGNADA` al origen de su línea.

## Consultas y bloqueos

### Creación o edición de borrador

1. Validar rol, tenant y técnicos de cada línea.
2. Validar que la estructura sea 1→N o N→1 y que haya al menos dos técnicos distintos.
3. Cargar líneas y materiales.
4. Validar disponibilidad por origen y cuadre.
5. `transaction.atomic`: crear/actualizar solicitud y líneas; auditar.
6. No bloquear series ni stock: el borrador no reserva.

### Envío

1. Bloquear la solicitud con `select_for_update`.
2. Bloquear el `Tenant`.
3. Bloquear `StockTecnico` de todos los técnicos implicados por `(material_id, tecnico_id)`
   ascendente.
4. Bloquear las series afectadas por `id` ascendente.
5. Revalidar estructura, series, disponibilidad y cuadre dentro del bloqueo.
6. Cambiar a `ENVIADA`, generar Excel, guardar ruta/hash y auditar.

### Confirmación

1. Bloquear la solicitud.
2. Bloquear el `Tenant`.
3. Bloquear `StockTecnico` de todos los técnicos implicados por `(material_id, tecnico_id)`.
4. Bloquear las series por `id`.
5. Revalidar que cada serie siga `ASIGNADA` al origen de su línea.
6. Cambiar `tecnico`/`asignada_en` de cada serie al destino de su línea.
7. Agrupar por `(origen, destino, material)` y decrementar/incrementar `StockTecnico` con 008.
8. Cambiar a `CONFIRMADA` y auditar.

### Rechazo y cancelación

1. Bloquear la solicitud.
2. Validar estado y motivo.
3. Cambiar estado y auditar; no tocar series ni stock.

### Consultas de lectura

- `listar_traspasos` filtra por tenant y ordena por fecha descendente.
- `obtener_traspaso` filtra por tenant; `obtener_traspaso_almacen` por región.
- `series_disponibles_para_traspaso` filtra por técnico origen, material, estado y exclusión de
  reservas.
- `stock_tecnico_para_traspaso` devuelve el stock actual de un técnico del tenant, solo lectura.
- Las consultas no crean ni bloquean.

## Excel

- Dos hojas: `Desasignación` (Z32) y `Asignación` (Z31).
- Cada hoja agrupa las líneas por técnico; cada grupo tiene su propio bloque de metadatos con NIF.
- Metadatos: movimiento, Centro, Almacén, NIF, fecha, tenant, región e ID.
- Tabla de seriales: código, descripción, lote, serie y cantidad 1.
- Tabla de material menor: código, descripción, lote y cantidad agregada.
- Generado al enviar; almacenado con ruta relativa y hash SHA-256.
- Descarga verificando hash; si no coincide, `HashNoCoincide`.
- No se guarda el binario en la base ni se audita su contenido.

## Auditoría

| Evento | Entidad / campo | Cuándo | Contenido |
|---|---|---|---|
| Alta de traspaso | `SolicitudTraspaso/alta` | Crear | Tenant, técnicos derivados, fecha, actor |
| Alta de línea | `LineaTraspaso/alta` | Crear/editar | Origen, destino, material, serie o cantidad |
| Baja de línea | `LineaTraspaso/baja` | Editar borrador | Línea eliminada |
| Envío | `SolicitudTraspaso/estado` | Enviar | `BORRADOR→ENVIADA` |
| Excel | `SolicitudTraspaso/excel` | Enviar | Ruta relativa y hash |
| Confirmación | `SolicitudTraspaso/estado` | Confirmar | `ENVIADA→CONFIRMADA` |
| Serie | `Serie/tecnico` | Confirmar | Técnico origen y destino de la línea |
| Días en mano | `Serie/asignada_en` | Confirmar | Fecha anterior y nueva |
| Stock origen | `StockTecnico/cantidad` | Confirmar | Lo escribe 008 |
| Stock destino | `StockTecnico/cantidad` | Confirmar | Lo escribe 008 |
| Rechazo | `SolicitudTraspaso/estado` | Rechazar | `ENVIADA→RECHAZADA` |
| Motivo | `SolicitudTraspaso/motivo_rechazo` | Rechazar | Motivo |
| Cancelación | `SolicitudTraspaso/estado` | Cancelar | `BORRADOR→CANCELADA` |

- Todo en la misma transacción; si falla, se revierte.
- Actor de la sesión; nunca inventado.
- Sin secretos, binarios, rutas absolutas ni datos de otro tenant.

## RLS y aislamiento

- `traspasos_solicitudtraspaso`: por `tenant_id` y `region_id`.
- `traspasos_lineatraspaso`: por `tenant_id`.
- `series_serie`: ya tiene RLS por `tenant_id` en 004; 009 no la duplica.
- Si la infraestructura de 001 no está disponible, se registra la deuda y el ORM filtra por
  tenant/región.
- El rol de aplicación no es superusuario ni `BYPASSRLS`.

## Trazabilidad de criterios de aceptación

| CA | Entidad / servicio | Evidencia |
|---|---|---|
| CA-01 | `SolicitudTraspaso` + Excel | Dos hojas generadas para técnicos del mismo tenant |
| CA-02 | `validar_estructura_tecnicos` + `CheckConstraint` | Mismo técnico o estructura inválida se rechaza |
| CA-03 | `calcular_disponible_tecnico` | 15 sobre 10 se rechaza por insuficiente |
| CA-04 | `validar_cuadre_traspaso` | Serie que sale y no entra se rechaza |
| CA-05 | `validar_cuadre_traspaso` | 50 que salen y 40 que entran se rechaza |
| CA-06 | `Serie.tecnico` | Tras confirmar, cada serie apunta al destino de su línea |
| CA-07 | `rechazar_traspaso` | Tras rechazar, las series siguen en el origen |
| CA-08 | `StockGeneral` | Sin cambios en todo el ciclo |
| CA-09 | `Serie.asignada_en` | Se reinicia al confirmar el traspaso |
| CA-10 | `validar_estructura_tecnicos` | Una solicitud con un origen y dos destinos se acepta |
| CA-11 | `validar_estructura_tecnicos` | Una solicitud con dos orígenes y un destino se acepta |
| CA-12 | `stock_tecnico_para_traspaso` | La interfaz lista el stock del técnico sin modificarlo |
