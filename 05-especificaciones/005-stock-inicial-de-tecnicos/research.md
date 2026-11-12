# Investigación y decisiones: 005 Stock Inicial de Técnicos

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/005-stock-inicial-de-tecnicos/spec.md`

Este documento resuelve las incógnitas del contexto técnico y fija las decisiones de diseño. No
queda ningún `NEEDS CLARIFICATION`. El detalle de modelos, servicios y contratos vive en
`plan.md`, `data-model.md` y `contracts/`.

## Resumen de incógnitas resueltas

| Incógnita | Decisión | Sección |
|---|---|---|
| ¿Dónde viven las series? | Registro transversal `series.Serie` de 004 | 1 |
| ¿En qué estado nacen las series del stock inicial? | `ASIGNADA` | 1 |
| ¿Quién es dueño del stock del técnico? | 008: `StockTecnico` y sus servicios | 2 |
| ¿Cómo se garantiza la carga única? | Flag del tenant + `UniqueConstraint(tenant)` + bloqueo | 3 |
| ¿Qué formato de Excel se acepta? | Solo `.xlsx`; `.xls` se rechaza | 4 |
| ¿De dónde salen lote y descripción? | Del catálogo; los del Excel son informativos | 5 |
| ¿Cómo se tratan varias filas no seriadas? | Se agrupan por técnico y material y se suman | 6 |
| ¿El formulario es uno por técnico o uno por tenant? | Una página con secciones por técnico, guardada como una sola carga | 7 |
| ¿La vista previa escribe? | No; es un fragmento HTML/HTMX y la carga revalida | 8 |
| ¿La edición es por operación o por lote? | Lote transaccional; cada operación se audita | 9 |
| ¿Se puede borrar una serie incorrecta? | Sí, físicamente y con auditoría, si sigue `ASIGNADA` y el stock alcanza | 10 |
| ¿Cómo se reinicia? | Solo comando de gestión, deshabilitado por defecto | 11 |
| ¿Quién opera? | Solo `USUARIO_TENANT`; Admin y Almacén no | 12 |
| ¿Qué se audita? | Carga, líneas, series, tenant y stock (008) | 13 |
| ¿Se usa Celery? | No; carga síncrona y transaccional | 14 |
| ¿Se aceptan técnicos desactivados en el Excel? | Sí, si existen en el tenant; el formulario solo ofrece activos | 15 |
| ¿Cómo se evita revelar el tenant de una serie? | Mensaje uniforme y consulta sin datos del propietario | 16 |
| ¿Cómo se prueba? | Una prueba por CA, PostgreSQL y casos de concurrencia | 17 |

---

## 1. Registro central de series y estado inicial

**Decisión**: 005 usa `series.Serie` y `series.services` de la spec 004. No crea otra tabla de
series ni una columna `serie` de texto. `LineaStockInicial.serie` es un `OneToOneField` a
`series.Serie`. Las series del stock inicial se crean con
`series.services.crear_serie(tenant, region, material, numero, material.lote, actor, estado=EstadoSerie.ASIGNADA)`.

**Rationale**: la constitución exige unicidad global de la serie y un solo lugar a la vez. Una
columna de texto en `LineaStockInicial` no podría imponer unicidad contra `LineaRecojo`, asignaciones,
traspasos, conciliación o logística inversa. El registro central es la única forma simple de
cumplir la invariante. El stock inicial representa material que ya está en posesión del técnico;
por eso la serie nace `ASIGNADA` y no `DISPONIBLE`: no está en el stock general ni debe poder
reservarse para una asignación.

**Alternativas consideradas**:
- Guardar la serie como texto en `LineaStockInicial`: no impone unicidad global y obliga a consultar
  varias tablas para saber si existe. Rechazada.
- Crear una tabla `SerieStockInicial`: duplica la identidad de la serie y rompe la trazabilidad.
  Rechazada.
- Crear las series `DISPONIBLE` y moverlas a `ASIGNADA`: simula una asignación que no existió, toca
  el stock general y contradice la regla “el stock inicial no pasa por el stock general”. Rechazada.

**Consecuencia documental**: `series.services.crear_serie` de 004 debe aceptar un `estado` opcional
con valor por defecto `DISPONIBLE`. 004 sigue creando `DISPONIBLE`; 005 pasa `ASIGNADA`. Se corrige
el plan de 004.

---

## 2. Propiedad del stock y servicios de 008

**Decisión**: 005 no escribe `StockTecnico` ni `StockGeneral` directamente. Llama a
`stock.services.incrementar_stock_tecnico` y `decrementar_stock_tecnico` de la spec 008. Agrupa los
deltas por `(tecnico, material)` y llama una sola vez por grupo. `StockGeneral` no se lee ni se
modifica.

**Rationale**: la constitución asigna a 008 las invariantes y la auditoría de stock. Si 005
actualizara las tablas directamente, duplicaría la lógica de bloqueo, auditoría y validación de
cantidad no negativa, y podría dejar el stock inconsistente. La excepción del stock inicial es de
*procedencia* (no pasa por el stock general), no de *propiedad* del modelo: el `StockTecnico` sigue
siendo de 008.

**Alternativas consideradas**:
- Escribir `StockTecnico` con `update()` o `F()` desde 005: evita la auditoría y el bloqueo
  centralizados; rechazada.
- Crear un `StockInicial` separado y sumarlo al consultar el stock: duplica la fuente de verdad y
  complica todos los consumidores; rechazada.
- Pasar por `StockGeneral` y luego asignar: contradice la spec y la constitución; rechazada.

**Consecuencia**: la parte fundacional de 008 (`StockTecnico`, incremento y decremento) debe existir
antes de implementar 005. La confirmación de asignaciones de 008 no es prerrequisito.

---

## 3. Carga única y concurrencia

**Decisión**: la carga única se protege en tres capas:
1. `Tenant.stock_inicial_cargado` como indicador de negocio.
2. `UniqueConstraint(fields=["tenant"], name="carga_stock_inicial_tenant_unico")` como restricción
   estructural.
3. `select_for_update` sobre el `Tenant` dentro de la transacción de carga.

**Rationale**: dos sesiones pueden validar en paralelo y ambas ver el flag en `False`. El bloqueo
serializa la decisión: la primera crea la carga y marca el flag; la segunda, al adquirir el bloqueo,
relee el estado y falla con "El stock inicial ya fue cargado para este tenant". Si la carrera supera
el flag por cualquier motivo, la restricción única produce el mismo resultado. No se usan bloqueos
de aplicación ni cachés.

**Alternativas consideradas**:
- Solo el flag: dos transacciones podrían leer `False` antes de que una escriba; rechazada.
- Solo la restricción única: funciona como backstop, pero produce un `IntegrityError` genérico si no
  se traduce; se combina con el bloqueo y la traducción.
- Un estado `EN_PROGRESO` en la carga: agrega estados intermedios y limpieza de bloqueos huérfanos;
  rechazada por simplicidad.

**Pruebas**: dos cargas concurrentes (`TransactionTestCase`) dejan una sola `CargaStockInicial`, un
solo conjunto de líneas y un solo stock; la perdedora recibe el mensaje uniforme.

---

## 4. Formato del Excel: solo `.xlsx`

**Decisión**: se acepta únicamente `.xlsx`. Un archivo `.xls` se rechaza con
"El archivo debe ser un Excel .xlsx" y se indica al usuario que lo guarde como `.xlsx`.

**Rationale**: el stack aprobado usa `openpyxl`, que lee `.xlsx`/`.xlsm` pero no el formato binario
`.xls`. Agregar `xlrd` sería una dependencia nueva no justificada. El contrato actual dice
“.xlsx o .xls”; se corrige a `.xlsx`.

**Alternativas consideradas**:
- Agregar `xlrd` o `pyexcel-xls`: dependencia extra y mantenimiento; rechazada.
- Convertir `.xls` con LibreOffice o un servicio externo: infraestructura no disponible y no
  justificada; rechazada.
- Aceptar `.xls` y fallar al leer: mensaje confuso; rechazada.

**Consecuencia documental**: `04-contratos/excel-stock-inicial.md` debe cambiar el formato y el
proceso. Los archivos históricos `.xls` se guardan como `.xlsx` antes de cargarlos.

---

## 5. Lote y descripción provienen del catálogo

**Decisión**: `LineaStockInicial.lote` se copia de `material.lote`; la descripción se toma de
`material.descripcion`. Las columnas `Lote` y `Texto breve material` del Excel se leen para validar
la estructura, pero no prevalecen ni generan error si difieren.

**Rationale**: la spec 002 define el catálogo como fuente de verdad del material y el lote como
atributo fijo e informativo. La constitución dice que el lote no separa stock. Si el Excel
prevaleciera, dos filas del mismo material podrían quedar con lotes distintos y el stock se
fragmentaría. El reporte de Lari puede traer descripciones o lotes históricos; el catálogo manda.

**Alternativas consideradas**:
- Guardar el lote del Excel en la línea: rompe la unicidad lógica del lote por material y permite
  datos inconsistentes; rechazada.
- Rechazar el archivo si el lote no coincide: bloquea migraciones legítimas por diferencias de
  formato; rechazada.
- Advertir sin bloquear: se puede mostrar en la vista previa como información, pero no cambia el
  dato guardado. Se documenta como “informativo”.

---

## 6. Agregación de materiales no seriados

**Decisión**: las filas no seriadas se agrupan por `(tecnico, material)` y se suman sus cantidades.
Se crea una sola `LineaStockInicial` por grupo. Las filas seriadas generan una línea por serie con
`cantidad=1`.

**Rationale**: el Excel puede repetir el mismo material para el mismo técnico en varias filas. Si se
creara una línea por fila, el stock del técnico tendría varias filas del mismo material, se
dificultaría la edición y la restricción de unicidad no podría aplicarse. La suma mantiene el total
y una fila canónica. Para seriados, la unidad es la serie y no se pueden sumar.

**Alternativas consideradas**:
- Una línea por fila no seriada: permite duplicados y complica la edición; rechazada.
- Rechazar filas repetidas: impide migrar archivos reales que agrupan por lote o por línea; rechazada.
- Sumar también las seriadas: viola la regla “una fila por serie, cantidad 1”; rechazada.

**Consecuencia**: la restricción `UniqueConstraint(carga, tecnico, material, condition=serie IS NULL)`
es el respaldo de base de esta decisión.

---

## 7. Formulario con secciones por técnico y carga única

**Decisión**: la carga por formulario es una sola página con secciones por técnico. Cada sección
permite elegir un técnico y agregar varias líneas (material, series o cantidad). El botón “Guardar”
envía todas las secciones como una sola carga. No hay borradores, guardados parciales ni una carga
por cada técnico.

**Rationale**: la spec dice “el formulario es por técnico (uno por técnico)” y también “el stock
inicial se carga una sola vez por tenant”. Si cada guardado por técnico fuera una carga, la primera
marcaría el tenant como cargado y las demás quedarían bloqueadas. Las secciones conservan la
organización por técnico y permiten cargar varios en una sola operación atómica.

**Alternativas consideradas**:
- Un formulario y una carga por técnico: contradice la carga única; rechazada.
- Un borrador que se completa técnico a técnico y se confirma al final: agrega estados y limpieza;
  rechazada por simplicidad.
- Un formulario plano sin secciones: pierde la agrupación por técnico que la spec pide; rechazada.

**Consecuencia**: el formulario se valida con la misma lógica que el Excel y produce las mismas
líneas agregadas.

---

## 8. Vista previa del Excel: fragmento HTMX y sin escrituras

**Decisión**: `POST /stock-inicial/validar-excel/` devuelve un fragmento HTML/HTMX con
`data-valido`, filas de error y resumen. No devuelve JSON, no escribe en la base y no crea series.
`POST /stock-inicial/cargar-excel/` recibe de nuevo el archivo y revalida todo.

**Rationale**: la interfaz es Django + HTMX, no una SPA. Un fragmento HTML evita duplicar plantillas
y mantiene la lógica de presentación en el servidor. La vista previa no puede ser autoridad: entre
la validación y la carga el estado puede cambiar (otra carga, otra serie). Revalidar en la carga
garantiza la integridad. No se guarda el archivo ni el resultado en sesión, lo que evita estados
huérfanos y problemas de tamaño.

**Alternativas consideradas**:
- Devolver JSON y renderizar en JavaScript: agrega lógica de presentación en el cliente y no es el
  patrón del proyecto; rechazada.
- Guardar el archivo validado en el servidor y cargarlo después con un token: agrega almacenamiento,
  limpieza y estados; rechazada.
- Cargar directamente sin vista previa: la spec pide errores claros y una validación previa;
  rechazada.

---

## 9. Edición por lote transaccional

**Decisión**: la edición se modela como una lista de operaciones (`AGREGAR`, `ELIMINAR`,
`MODIFICAR`) que `aplicar_edicion_stock_inicial` valida y aplica en una sola transacción. La página
de edición envía todas las modificaciones en un solo POST. Las funciones
`agregar_linea_stock_inicial`, `eliminar_linea_stock_inicial` y
`modificar_cantidad_stock_inicial` son envoltorios de un solo elemento del mismo servicio.

**Rationale**: la spec dice “la edición es transaccional: si falla una modificación, falla todo”.
Un lote cumple esa regla sin depender de que el usuario envíe una operación por vez. Además, permite
corregir una serie equivocada eliminándola y agregando la correcta en la misma transacción, sin
estados intermedios.

**Alternativas consideradas**:
- Tres endpoints independientes: cada uno sería atómico, pero el conjunto podría quedar a medias si
  el usuario hace varias operaciones; no cumple la lectura estricta de la spec. Rechazada como
  mecanismo principal.
- Una cola de cambios pendientes: agrega estados y UI compleja; rechazada.

**Consecuencia**: el formulario de edición usa un formset de líneas existentes y otro de líneas
nuevas; la vista construye `OperacionEdicion` y llama al servicio. Las pruebas pueden llamar al
servicio con un lote sin pasar por HTML.

---

## 10. Borrado físico de series incorrectas

**Decisión**: al eliminar una línea seriada del stock inicial, se elimina primero la
`LineaStockInicial` y después la `Serie`. La auditoría conserva el número, el estado, el técnico y
el material anteriores. Solo se permite si la serie sigue `ASIGNADA`, pertenece al técnico de la
línea y el stock del técnico alcanza para restar.

**Rationale**: una serie cargada por error no debería quedar ocupando la unicidad global ni
aparecer en el inventario. No existe otro flujo para corregirla antes de operar. La baja lógica
(estado “dada de baja”) la dejaría existiendo y bloquearía volver a cargar el número correcto. La
auditoría preserva la trazabilidad aunque la fila desaparezca, y la operación solo se permite
mientras la serie no haya salido del técnico.

**Alternativas consideradas**:
- Baja lógica: la serie sigue existiendo y no se puede reutilizar el número; rechazada para
  correcciones de carga inicial.
- No permitir eliminar: obliga a dejar datos incorrectos o a reiniciar todo el stock inicial;
  rechazada.
- Eliminar sin auditoría: viola el principio VI; rechazada.

**Riesgo**: el borrado físico de una serie es una excepción limitada a la carga inicial. Se
documenta en `contracts/auditoria-stock-inicial.md` y se prueba que la auditoría sobrevive. Si la
serie ya fue devuelta, traspasada o dada de baja, la operación falla.

---

## 11. Reinicio solo por comando de gestión

**Decisión**: `reiniciar_stock_inicial` es un comando de `manage.py`, no una ruta HTTP ni una acción
del Admin. Exige `settings.PERMITIR_REINICIO_STOCK_INICIAL=True`, un `--usuario` con rol
`ADMIN_PLATAFORMA` y `--confirmar`. El valor por defecto de la configuración es `False`; solo se
activa en desarrollo/pruebas o durante una implementación controlada.

**Rationale**: el reinicio borra la carga, las líneas, las series y descuenta stock. Es una
operación destructiva de implementación. Exponerla por HTTP ampliaría la superficie de ataque y
contradiría el rol del Administrador, que no opera inventario. El comando deja auditoría y exige
confirmación explícita.

**Alternativas consideradas**:
- Ruta HTTP solo para Admin: riesgo alto y contradice “el Administrador no opera inventario”;
  rechazada.
- Acción en el Admin de Django: misma objeción y difícil de probar; rechazada.
- Reinicio automático al suspender el tenant: no es lo que pide la spec; rechazada.

**Consecuencia**: el comando se documenta en `quickstart.md` y se prueba que está deshabilitado por
defecto y que falla si el stock ya fue modificado.

---

## 12. Permisos y aislamiento

**Decisión**: solo `USUARIO_TENANT` activo con tenant `ACTIVO` carga, ve y edita. `ADMIN_PLATAFORMA`
y `RESPONSABLE_ALMACEN` reciben `403`. Una carga o línea de otro tenant responde `404`. El tenant
suspendido responde `403`. El tenant y la región salen de `request.usuario`; nunca de
`tenant_id`/`region_id` del cliente.

**Rationale**: principios I y II. El Administrador no opera inventario y el Responsable de almacén
tiene alcance de región, no de tenant. La única excepción es el comando de reinicio, que exige un
actor Admin y configuración explícita, y no es una operación de inventario normal.

**Alternativas consideradas**:
- Permitir al Admin reiniciar por HTTP: amplía el alcance y contradice la constitución; rechazada.
- Permitir al Responsable de almacén cargar por el tenant: no tiene alcance de tenant; rechazada.
- Filtrar solo en la vista: el servicio revalida para que una llamada interna no evada el control;
  rechazada la validación única en vista.

---

## 13. Granularidad de la auditoría

**Decisión**: se escribe:
- un `CargaStockInicial/alta` con método, archivo, hash, región y totales;
- un `LineaStockInicial/alta` por línea;
- un `Serie/alta` por serie;
- los cambios de `Tenant.stock_inicial_cargado` y `Tenant.fecha_stock_inicial`;
- en edición, `LineaStockInicial/alta`, `LineaStockInicial/baja`, `Serie/alta`,
  `Serie/baja` y `LineaStockInicial/cantidad` según corresponda;
- en reinicio, `LineaStockInicial/baja`, `Serie/baja`, `CargaStockInicial/baja` y los cambios del
  tenant;
- el stock, en `StockTecnico/cantidad`, lo escribe 008.

**Rationale**: la spec pide “quién cargó, cuándo y qué archivo exacto” y “cada serie y cantidad
creada registra usuario, fecha y valor anterior (ninguno) y nuevo”. El resumen de la carga no basta
para reconstruir una línea o una serie. La auditoría por línea y por serie permite reconstruir la
carga incluso si una serie se elimina por edición. El hash identifica el archivo exacto sin guardar
el archivo completo.

**Alternativas consideradas**:
- Solo el resumen de la carga: no permite reconstruir el detalle si las líneas cambian; rechazada.
- Un registro por fila del Excel: confunde filas informativas con líneas agregadas y duplica
  registros; rechazada.
- Guardar el archivo completo: almacenamiento y datos personales innecesarios; el hash y el nombre
  bastan.

**Consecuencia**: la auditoría se escribe en la misma transacción y nunca contiene secretos ni
`tenant_id` separado.

---

## 14. Sin Celery para la carga

**Decisión**: la carga, la validación y la edición son síncronas. No se usa Celery ni una cola. El
progreso se muestra con `hx-indicator`/`hx-disabled-elt` mientras el POST está en curso.

**Rationale**: la operación debe ser atómica y la carga única se decide en la transacción. Una tarea
asíncrona necesitaría un estado “en progreso”, un mecanismo de reintento y una forma de comunicar
errores por fila, lo que agrega complejidad sin beneficio para el volumen esperado. La spec pide
“mostrar progreso”, no “procesar en segundo plano”; el indicador de HTMX cumple la usabilidad.

**Alternativas consideradas**:
- Tarea Celery con polling: agrega estados, Redis y manejo de fallos; rechazada.
- Barra de progreso real por filas: requiere streaming o polling y no es necesaria; rechazada.

---

## 15. Técnicos desactivados en el Excel

**Decisión**: el Excel acepta cualquier técnico que exista en el tenant, esté activo o desactivado.
El selector del formulario ofrece solo técnicos activos (`tecnicos_para_operacion`).

**Rationale**: la spec solo exige que el técnico exista en el tenant. Un técnico desactivado puede
tener materiales en su poder y el stock inicial debe reflejarlo para que la conciliación y una
eventual devolución sean posibles. El formulario es una operación nueva y ofrece solo activos, igual
que los demás selectores.

**Alternativas consideradas**:
- Exigir activo en el Excel: podría perder stock histórico y bloquear la migración; rechazada.
- Permitir desactivados en el formulario: contradice el patrón de selectores de 003; rechazada.

**Consecuencia**: se documenta en el contrato de importación y se prueba con un técnico desactivado.

---

## 16. Mensajes uniformes y no revelación

**Decisión**: el mensaje de serie existente es siempre "La serie ya está registrada en el sistema",
sin importar el tenant, la región, el recojo o el técnico de origen. La consulta
`series.services.series_existentes` devuelve solo números, no propietarios. Los errores de fila no
incluyen `tenant_id`, `region_id`, stock ni creador.

**Rationale**: principio I y IV. Revelar el tenant de una serie permite inferir información de un
competidor. La uniformidad también simplifica las pruebas y evita mensajes diferentes para la misma
causa.

**Alternativas consideradas**:
- Mensaje específico “la serie pertenece a otro tenant”: revela información; rechazada.
- Mensaje distinto para serie propia y ajena: permite enumeración; rechazada.
- Incluir el técnico o el recojo de origen: revela datos; rechazada.

---

## 17. Estrategia de pruebas

**Decisión**: una prueba por CA-01…CA-13, más pruebas de restricciones, permisos, concurrencia,
auditoría, reinicio, RLS y rendimiento. Todas sobre PostgreSQL. Las pruebas de Excel generan el
archivo con `openpyxl` en memoria. Las pruebas de concurrencia usan `TransactionTestCase` y dos
conexiones.

**Rationale**: la puerta de pruebas de la constitución exige al menos una prueba por criterio de
aceptación y no avanzar con pruebas en rojo. Las pruebas de base son necesarias porque las
restricciones son parte del diseño. Las de concurrencia validan que la carga única y la unicidad de
series no dependen solo de la aplicación.

**Alternativas consideradas**:
- Solo pruebas de vista: no cubren restricciones ni concurrencia; rechazada.
- SQLite para rapidez: prohibido por la constitución y no reproduce `select_for_update` ni las
  restricciones parciales; rechazada.
- Archivos Excel binarios en el repositorio: difíciles de mantener; se generan en la prueba.

---

## Riesgos y seguimiento

| Riesgo | Impacto | Mitigación |
|---|---|---|
| `series.services.crear_serie` no acepta `estado` | 005 no puede crear series `ASIGNADA` | Corregir 004 antes de implementar; se documenta en el plan de 004 |
| 008 no expone `StockTecnico` o los servicios de incremento/decremento | 005 no puede asignar stock | Detener la implementación y completar la parte fundacional de 008 |
| RLS no disponible en 001 | Aislamiento solo de aplicación | Registrar deuda y mantener filtrado obligatorio; no inventar RLS paralela |
| Excel `.xls` en uso | Usuarios no pueden cargar el archivo tal cual | Documentar “guardar como .xlsx” y mensaje claro |
| Archivo grande | Tiempo de carga y memoria | `read_only=True`; medir con 100+ filas; si aparece un límite, agregarlo al contrato |
| Reinicio usado fuera de implementación | Pérdida de stock y series | Configuración apagada por defecto, comando con confirmación, guard de stock/serie y auditoría |
| Borrado físico de series | Pérdida de la fila de serie | Solo para la carga inicial, con auditoría completa y guard de estado/stock |
| Serie duplicada en concurrencia | `IntegrityError` no controlado | Traducir a mensaje uniforme y probar dos conexiones |
| Técnico desactivado en Excel | Confusión del usuario | Documentar y probar; el formulario solo muestra activos |

## Decisiones que requieren seguimiento documental

1. `04-contratos/excel-stock-inicial.md`: `.xlsx` únicamente; lote y descripción del catálogo;
   `.xls` debe guardarse como `.xlsx`.
2. `05-especificaciones/008-confirmacion-y-actualizacion-de-stock/plan.md`: declarar
   `StockTecnico`, `incrementar_stock_tecnico` y `decrementar_stock_tecnico` como fundacionales para
   005.
3. `05-especificaciones/004-recojo-de-materiales/plan.md`: `crear_serie` con `estado` opcional;
   005 pasa `ASIGNADA`.
4. `05-especificaciones/004-recojo-de-materiales/research.md`: retirar el riesgo obsoleto de la
   columna `serie` de texto de 005.
5. `05-especificaciones/004-recojo-de-materiales/data-model.md`: precisar el estado inicial por
   spec.
6. `06-plan-implementacion/desglose-tareas.md`: actualizar la dependencia de 005 (series de 004 y
   núcleo de stock de 008).
7. `03-reglas-de-dominio/series.md`: agregar el stock inicial como vía de ingreso.
8. `03-reglas-de-dominio/stock.md`: mencionar el stock inicial en los incrementos del stock del
   técnico.
