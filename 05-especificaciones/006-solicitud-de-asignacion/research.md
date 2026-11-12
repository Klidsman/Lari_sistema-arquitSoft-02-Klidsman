# Investigación y decisiones: 006 Solicitud de Asignación

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

Este documento resuelve las incógnitas del contexto técnico y fija las decisiones de diseño. No
queda ningún `NEEDS CLARIFICATION`. El detalle de modelos, servicios, contratos y validación vive
en `plan.md`, `data-model.md` y `contracts/`.

## Resumen de incógnitas resueltas

| Incógnita | Decisión | Sección |
|---|---|---|
| ¿Qué significa “crear” en CA-01? | Crear y enviar en una operación; el borrador no genera Excel | 1 |
| ¿Existe una tabla de reservas? | No; el reservado se deriva de solicitudes `ENVIADA` y del estado `RESERVADA` | 2 |
| ¿Dónde viven las series? | Registro transversal `series.Serie` de 004; `LineaAsignacion.serie` es FK | 3 |
| ¿Quién mueve el stock físico? | 007/008 al confirmar; 006 solo lee `StockGeneral` | 4 |
| ¿Cuándo se genera el Excel? | En la transición `BORRADOR`→`ENVIADA`, nunca al guardar borrador | 5 |
| ¿Cómo se evita sobreasignar con envíos concurrentes? | `transaction.atomic` + `select_for_update` sobre tenant, stock y series en orden de id | 6 |
| ¿Desde cuándo se cuentan los días en mano? | Desde `SolicitudAsignacion.confirmada_en`, fijado por 007 | 7 |
| ¿La alerta suma días de todos los equipos? | No; se evalúa por equipo seriado y se alerta si alguno supera 20 días | 8 |
| ¿Cómo se valida en tiempo real? | Fragmentos HTML/HTMX, sin JSON ni API REST | 9 |
| ¿Qué permisos se usan? | Roles explícitos; solo `USUARIO_TENANT` activo con tenant activo | 10 |
| ¿Se usa Celery o correo en 006? | No; el correo, la bandeja y las notificaciones son de 007 | 11 |
| ¿Se puede editar un borrador? | No; se cancela y se crea otro. La spec no pide edición | 12 |
| ¿Cómo se audita? | Altas, cambios de estado y reservas de series en la misma transacción | 13 |
| ¿Cómo se prueban los CA que dependen de 007? | Con `confirmada_en` fijado por fixture, sin implementar 007 en 006 | 14 |
| ¿Cómo se comporta el sistema si RLS no está listo? | Filtrado de aplicación obligatorio y deuda registrada | 15 |

---

## 1. Semántica de borrador y envío

**Decisión**: 006 distingue `BORRADOR` de `ENVIADA`. Guardar borrador crea la solicitud y sus
líneas, sin reservar series, sin reservar cantidades y sin generar Excel. El botón “Enviar” ejecuta
`crear_y_enviar_solicitud`, que crea y envía en una sola transacción, o `enviar_solicitud` sobre una
solicitud creada como borrador. **CA-01 se satisface con la operación crear-y-enviar**: la solicitud
queda `ENVIADA`, las series `RESERVADA` y el Excel existe.

**Rationale**: la spec describe “crear” como el acto que produce el documento y reserva las series
(CA-01, CA-05). Un borrador que reservara series dejaría inventario bloqueado por una solicitud que
nunca se envió, y un borrador con Excel firmado obligaría a regenerarlo y refirmarlo. Separar
borrador y envío conserva la usabilidad de guardar a medias sin romper la integridad documental.

**Alternativas consideradas**:
- Reservar y generar Excel al guardar borrador: bloquea inventario sin compromiso y produce un
  documento que puede quedar obsoleto. Rechazada.
- Eliminar el estado `BORRADOR` y crear siempre `ENVIADA`: impide guardar a medias y contradice el
  conjunto de estados de la spec (§9). Rechazada.

**Consecuencia documental**: se corrige `spec.md` §5.5 y CA-01 para decir explícitamente que el
Excel se genera al enviar y que “crear” en CA-01 significa crear y enviar.

---

## 2. Reserva calculada, sin tabla de reservas

**Decisión**: no se crea una tabla `ReservaStock`. Para materiales no seriados, el reservado es la
suma de `LineaAsignacion.cantidad` de líneas no seriadas cuyas solicitudes estén `ENVIADA`. Para
series, el reservado es el estado `Serie.estado = RESERVADA`. `Disponible = StockGeneral.cantidad -
Reservado`.

**Rationale**: una tabla de reservas duplicaría el estado que ya expresan la solicitud y la serie,
y obligaría a sincronizarla en cada transición (envío, confirmación, rechazo, cancelación). Derivar
el reservado de una única fuente de verdad evita reservas huérfanas. El estado `ENVIADA` ya es
exactamente el período en que la solicitud compromete inventario.

**Alternativas consideradas**:
- `ReservaStock(tenant, material, cantidad, solicitud)` con borrado al confirmar/rechazar: agrega
  una tabla y un ciclo de vida paralelo al de la solicitud. Rechazada.
- Descontar `StockGeneral` al enviar y devolverlo al rechazar: mueve stock físico sin confirmación
  del almacén y contradice la constitución. Rechazada.

**Consecuencia**: la consulta de reservado debe ser agregada (una por material o una para todo el
formulario) y usar índice por `(tenant, material)` en `LineaAsignacion`.

---

## 3. Registro central de series y FK desde la línea

**Decisión**: `LineaAsignacion.serie` es `ForeignKey` a `series.Serie`, nulable, con
`on_delete=PROTECT`. No se guarda el número como texto ni se crea otra tabla de series. La
unicidad dentro de una solicitud se impone con `UniqueConstraint(solicitud, serie)` parcial; la
disponibilidad global la impone `Serie.estado`.

**Rationale**: la constitución exige unicidad global de la serie y un solo lugar a la vez. Un FK
permite que una serie rechazada o devuelta vuelva a asignarse, algo que un `OneToOneField` impediría
sin borrar historia. El número, el material y el tenant ya viven en `Serie`; duplicarlos abriría
inconsistencias.

**Alternativas consideradas**:
- `OneToOneField`: impediría reutilizar la serie tras un rechazo sin borrar o reescribir la línea.
  Rechazada.
- Columna `serie_numero` de texto: no impone la unicidad global y obliga a cruzar tablas para
  validar. Rechazada.

**Consecuencia**: 006 no crea series; solo lee `DISPONIBLE` y cambia a `RESERVADA`. Los cambios a
`ASIGNADA`/`DISPONIBLE` al confirmar o rechazar son de 007/008.

---

## 4. Propiedad del stock y límites de 006

**Decisión**: 006 solo lee `stock.StockGeneral` para calcular disponibilidad. No escribe
`StockGeneral` ni `StockTecnico`, no llama a servicios de incremento/decremento y no audita
movimientos de stock. La actualización física ocurre en la confirmación (007) mediante los servicios
de 008.

**Rationale**: la constitución asigna a 008 las invariantes y la auditoría de stock. Si 006
descontara stock al enviar, un rechazo posterior exigiría revertir cantidades y podría descuadrar el
stock si el proceso falla. Reservar lógicamente y mover stock solo al confirmar mantiene una sola
transacción de stock por operación real.

**Alternativas consideradas**:
- Descontar `StockGeneral` al enviar y reflejar el reservado en una columna `reservado`: duplica la
  fuente de verdad y complica la conciliación. Rechazada.
- Crear `StockTecnico` al enviar: adelanta la confirmación del almacén. Rechazada.

---

## 5. Generación del Excel al enviar

**Decisión**: el Excel se genera dentro de la transacción de envío, con `openpyxl`, en memoria. Se
calcula `sha256` del contenido, se escribe el archivo en
`MEDIA_ROOT/ASIGNACIONES_EXCEL_DIR/<tenant.codigo>/<solicitud.id>/<uuid>.xlsx`, se guarda la ruta
relativa en `excel_ruta` y el hash hexadecimal en `excel_hash`. El archivo no se regenera ni se
edita después. 006 no lo envía por correo ni expone su descarga.

**Rationale**: el documento debe corresponder exactamente a lo reservado y auditado. Generarlo en
el mismo instante en que se reservan series y cantidades garantiza esa correspondencia. Guardar la
ruta relativa evita acoplar la base a `MEDIA_ROOT` y el hash hexadecimal de 64 caracteres es el
formato natural de SHA-256.

**Alternativas consideradas**:
- Generar el Excel al mostrar el formulario y regenerarlo al enviar: dos archivos y dos hashes, con
  riesgo de enviar el equivocado. Rechazada.
- Guardar el binario en la base: encarece las consultas y la copia de seguridad. Rechazada.

**Consecuencia documental**: se corrige `04-contratos/excel-asignacion.md` §2 y §8 para precisar
que la generación ocurre al enviar y que la descarga/verificación pertenece a 007.

---

## 6. Concurrencia y bloqueos

**Decisión**: el envío se ejecuta en `transaction.atomic` y bloquea, en este orden:
`Tenant` (una fila), `StockGeneral` de los materiales no seriados afectados (orden de id) y
`Serie` seleccionadas (orden de id). Dentro del bloqueo se releen estado, disponibilidad y series, y
luego se escribe. El orden de bloqueo es siempre el mismo para evitar interbloqueos.

**Rationale**: la validación previa (formulario o HTMX) no es autoridad; entre la vista y el
guardado otra solicitud puede reservar el mismo material. Bloquear el tenant serializa los envíos
del mismo tenant, que es el alcance de la competencia por stock. Bloquear series y stock impide
sobreasignación aun si dos solicitudes del mismo tenant se envían a la vez. La unicidad global de
`Serie.numero` sigue siendo el respaldo de base.

**Alternativas consideradas**:
- Confiar solo en la validación de la vista: permite sobreasignación por carrera. Rechazada.
- Bloqueos de aplicación (caché, lock en memoria): no funcionan con varios procesos. Rechazada.
- Aislamiento `SERIALIZABLE` global: mayor contención y reintentos en toda la aplicación. Rechazada.

---

## 7. Días en mano desde la custodia actual

**Decisión**: `dias_en_mano_serie(serie, hoy=None)` exige `Serie.estado=ASIGNADA` y
`Serie.asignada_en` no nulo, y devuelve `(hoy - serie.asignada_en.date()).days`. 008 fija
`Serie.asignada_en` al confirmar una asignación, 009 la reinicia al traspasar y 011 la limpia al
devolver. Si una serie histórica no tiene `asignada_en`, se usa
`SolicitudAsignacion.confirmada_en` solo como respaldo y se registra la deuda.

**Rationale**: la spec y RF-61 dicen que el conteo inicia al aceptar el almacén, pero debe reiniciarse
cuando la serie cambia de técnico (RF-62, CA-09 de 009). `confirmada_en` de la asignación original no
sirve después de un traspaso; `Serie.asignada_en` es la única marca de la custodia actual.

**Alternativas consideradas**:
- Usar `fecha` de la solicitud: arranca antes de la aceptación. Rechazada.
- Seguir usando `confirmada_en`: no se reinicia con los traspasos. Rechazada.
- Agregar un contador `dias_en_mano`: se desincroniza. Rechazada.

**Consecuencia**: 006 lee `Serie.asignada_en` y deja `confirmada_en` como respaldo histórico; las
pruebas de 006 fijan ambos con fixtures. La corrección se coordina con 004/005/008/009/011.

---

## 8. Alerta de cupo por equipo

**Decisión**: `calcular_alerta_cupo(tecnico)` evalúa cada serie en custodia (`ASIGNADA`) con su
`confirmada_en` y alerta si **alguna** supera `settings.DIAS_ALERTA_CUSTODIA` (20). El mensaje es
“El técnico supera los 20 días en mano”. No bloquea la creación ni el envío. La alerta se muestra al
abrir el formulario y en la validación HTMX.

**Rationale**: la política de custodia busca identificar equipos retenidos demasiado tiempo. Sumar
días de todos los equipos dispara la alerta con dos equipos de 11 días sin que ninguno esté en
riesgo, y no dice qué equipo revisar. Evaluar por equipo coincide con RF-63 y con la corrección ya
adoptada en la spec.

**Alternativas consideradas**:
- Sumar días de todos los seriados: falsos positivos y sin equipo accionable. Rechazada.
- Alertar solo al enviar: oculta la información mientras el tenant arma la solicitud. Rechazada.

**Consecuencia documental**: se corrige `spec.md` §11 (“sumando días” → “revisando cada equipo”).

---

## 9. HTMX sin JSON

**Decisión**: los endpoints `series-disponibles` y `validar-disponibilidad` devuelven fragmentos
HTML (`text/html`) con atributos `data-*` estables; no devuelven JSON ni crean una API REST.

**Rationale**: el proyecto es Django + HTMX con plantillas (ADR-008/ADR-015). Los fragmentos
permiten reutilizar las plantillas y mantener un solo camino de renderizado. Los `data-*` son el
contrato verificable por pruebas sin acoplar clases CSS.

**Alternativas consideradas**:
- Endpoints JSON consumidos por JavaScript: duplica el renderizado y agrega un contrato que la
  constitución no pide. Rechazada.

---

## 10. Permisos por rol explícito

**Decisión**: la autorización es por rol y alcance de tenant, validada en vista y servicio:
`USUARIO_TENANT` activo con tenant `ACTIVO` puede; `ADMIN_PLATAFORMA` y `RESPONSABLE_ALMACEN`
reciben `403`. No se usan permisos Django (`asignaciones.add_*`) ni grupos sembrados en migraciones.
Una solicitud de otro tenant responde `404`.

**Rationale**: replica el patrón ya fijado en 001, 004 y 005. Los permisos Django requerirían
sembrar grupos y podrían desincronizarse con los roles reales. El `404` evita revelar la existencia
de datos ajenos.

**Alternativas consideradas**:
- Grupos y permisos Django: más configuración y riesgo de que un permiso conceda acceso a otro
  tenant. Rechazada.

---

## 11. Sin Celery ni correo en 006

**Decisión**: 006 no usa Celery, no envía correo, no crea `EnvioCorreo`, no implementa bandeja ni
WebSocket. El Excel se genera de forma síncrona y transaccional. El envío al buzón del almacén y su
reintento pertenecen a 007.

**Rationale**: la spec 007 es la dueña del envío y del registro de destinatario/fecha/archivo.
Adelantarlo en 006 duplicaría el modelo de envío y la cola. La generación síncrona es barata y debe
ocurrir en la misma transacción que la reserva para no dejar un Excel sin solicitud.

**Alternativas consideradas**:
- Encolar la generación en Celery: rompe la atomicidad y puede dejar la solicitud `ENVIADA` sin
  Excel. Rechazada.

---

## 12. Sin edición de borrador

**Decisión**: no existe ruta ni servicio de edición. Un borrador solo puede enviarse o cancelarse.
Para corregirlo se cancela y se crea otro. No se implementa borrado físico.

**Rationale**: la spec no pide edición y la constitución prohíbe eliminar registros. Editar un
borrador obligaría a decidir si se revalida todo, si se conserva el mismo id y cómo se audita; al no
ser requisito, se evita esa complejidad.

**Alternativas consideradas**:
- Edición completa del borrador: alcance no solicitado y más casos de auditoría. Rechazada.
- Borrado físico del borrador: contradice la prohibición de eliminar. Rechazada.

---

## 13. Auditoría en la misma transacción

**Decisión**: se auditan el alta de la solicitud y de cada línea, el envío, la reserva de cada serie,
la generación del Excel y la cancelación. Cada registro se escribe con
`auditoria.services.registrar_cambio` dentro de la misma transacción del cambio. No se auditan
secretos ni el contenido binario del Excel; solo ruta y hash.

**Rationale**: la constitución exige trazabilidad inmutable y atomicidad. Auditar fuera de la
transacción podría dejar un cambio sin registro o un registro sin cambio. La ruta y el hash son
suficientes para verificar el documento sin almacenar su contenido.

**Alternativas consideradas**:
- Auditoría asíncrona o por señal `post_save`: puede ejecutarse fuera de la transacción y duplicar
  registros. Rechazada.
- Guardar el Excel en la auditoría: expone contenido y engorda la tabla. Rechazada.

---

## 14. Pruebas de los CA dependientes de 007

**Decisión**: las pruebas de CA-08 y CA-09 usan un fixture que crea una `SolicitudAsignacion`
`CONFIRMADA` con `confirmada_en` y series `ASIGNADA`, sin implementar 007. Las pruebas de CA-01 y
CA-05 usan la operación crear-y-enviar de 006.

**Rationale**: 006 debe poder validarse antes de implementar 007. Fijar `confirmada_en` por fixture
prueba exactamente el contrato que 007 cumplirá (escribir la marca) sin acoplar la suite a una
feature posterior.

**Alternativas consideradas**:
- Depender de 007 implementada: bloquea la validación de 006. Rechazada.
- Simular la confirmación con `UPDATE` directo en el test: equivalente al fixture, pero menos claro;
  se prefiere el fixture explícito. Rechazada.

---

## 15. RLS y filtrado de aplicación

**Decisión**: `asignaciones_solicitudasignacion` y `asignaciones_lineaasignacion` llevan `tenant_id`
y política RLS por tenant si la infraestructura de 001 está disponible. En todos los casos, el
filtrado de aplicación (`tenant=request.usuario.tenant`) es obligatorio.

**Rationale**: la constitución exige aislamiento multitenant no negociable. RLS es un respaldo, no
un sustituto del filtro de aplicación. Si la infraestructura de 001 aún no existe al implementar 006,
la deuda se registra y no se inventa una RLS paralela.

**Alternativas consideradas**:
- Solo RLS: depende de una infraestructura que puede no estar lista y deja sin defensa las consultas
  que olviden el filtro. Rechazada.
- Solo filtrado de aplicación: pierde el respaldo de base. Rechazada.

---

## Riesgos y deudas documentales

| Riesgo / deuda | Impacto | Mitigación |
|---|---|---|
| Excel huérfano si el proceso muere entre la escritura y el commit | Archivo sin solicitud | Limpieza por mantenimiento documentada; no se degrada la transacción por un fallo de disco |
| 009/011 mueven series sin actualizar la fuente de custodia | Días en mano incorrectos | Corrección documental en los planes de 009 y 011 |
| RLS de 001 no disponible | Aislamiento solo de aplicación | Se registra y se mantiene el filtro obligatorio |
| 007 no implementada al validar 006 | CA-08/CA-09 sin flujo real | Fixture de confirmación y contrato explícito en `plan.md` |
| Redacción de `spec.md` §5.5, §11 y CA-01 | Ambigüedad de generación y alerta | Correcciones documentales listadas en `plan.md` |
| `04-contratos/excel-asignacion.md` dice “al crear” | Contradice el borrador | Corrección de §2 y §8 antes de implementar |

No queda ningún `NEEDS CLARIFICATION`.
