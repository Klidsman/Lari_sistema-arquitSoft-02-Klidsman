# Investigación y decisiones técnicas: 004 Recojo de materiales

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/004-recojo-de-materiales/spec.md`

Este documento resuelve las incógnitas del plan técnico antes del diseño de datos y contratos.
No queda ningún `NEEDS CLARIFICATION` pendiente. Los supuestos que la spec deja abiertos se
adoptan explícitamente y se marcan como riesgo.

---

## 1. App `recojos`, app `series` y alcance

**Decision**: la feature agrega dos apps: `recojos` (modelos `Recojo` y `LineaRecojo`) y `series`
(modelo `Serie`). La app `stock` y su modelo `StockGeneral` pertenecen a la spec 008 y se consumen
como dependencia.

**Rationale**: `recojos` es el nombre usado por el desglose de implementación y por el plan
anterior. `series` no tiene spec dueña y ninguna otra spec la crea: 005, 006, 007, 008, 010 y 011
la referencian como transversal. 004 es el primer módulo que introduce series en el sistema, por lo
que asumir su creación evita que cinco specs posteriores dependan de una app inexistente.

**Alternativas consideradas**:
- Guardar la serie solo como cadena en `LineaRecojo`: no permite imponer la unicidad global en la
  base de datos, que la constitución exige, y obliga a consultar varias tablas para saber si una
  serie existe.
- Poner `Serie` dentro de `recojos`: rompe la separación de responsabilidades; 005/006/010/011
  necesitan la serie sin depender de un recojo.

**Estado**: resuelto. El plan de 005 ya define `LineaStockInicial.serie` como FK a `series.Serie` y
usa el registro central; no crea una columna de texto ni otra tabla de series. Se conserva como
trazabilidad de la decisión, no como deuda pendiente.

---

## 2. Registro central de series y unicidad global

**Decision**: `series.Serie.numero` es `CharField(max_length=12, unique=True)`. La unicidad global
se impone con la restricción `unique` de PostgreSQL. `LineaRecojo.serie` es un `OneToOneField` a
`Serie`, nulo para materiales no seriados.

**Rationale**: la spec exige que una serie exista una sola vez en todo el sistema, en cualquier
tenant, y la constitución exige que esa unicidad se imponga en la base de datos. Una columna
`unique` en cada tabla operativa no puede garantizar la unicidad entre tablas. El registro central
es la única forma simple y auditable de cumplirlo.

**Alternativas consideradas**:
- `unique` solo en `LineaRecojo.serie`: impide duplicados dentro de los recojos, pero no contra
  stock inicial, conciliación o logística inversa.
- Disparadores o funciones de base de datos que consulten todas las tablas: más complejos, difíciles
  de probar y de mantener; el registro central es más simple.
- Validación solo en la aplicación: no resiste concurrencia ni inserciones directas.

**Consecuencia**: 005, 010 y 011 deben crear o consultar `series.Serie`; no deben inventar otra
tabla de series ni otra columna única. La app `series` es la fuente de verdad de identidad y
estado.

---

## 3. Formato y normalización de series

**Decision**: se normaliza con `strip` + eliminación de **todos** los espacios en blanco internos
(`\s+`) + `upper()`. El formato se valida con `SERIE_PATRON` (por defecto `^[A-Z0-9]{12}$`) y
`SERIE_LONGITUD` (por defecto 12), configurables en `settings`.

**Rationale**: RF-18 dice "mayúsculas, sin espacios"; CA-03 solo muestra el cambio de mayúsculas.
Eliminar todos los espacios permite pegar o escanear series con separadores accidentales sin
obligar al usuario a limpiarlas, y es coherente con el texto de la spec. El plan anterior
conservaba los espacios internos y los rechazaba; eso contradice RF-18 y se corrige aquí.

**Alternativas consideradas**:
- Solo `strip()`: rechaza `ABC 123456789`, que la spec describe como normalizable.
- Eliminar también guiones y otros separadores: la spec solo habla de espacios; no se inventan
  reglas adicionales.

**Riesgo**: si Lari usa series con espacios significativos, la normalización las uniría. La spec y
las reglas de dominio definen 12 caracteres alfanuméricos sin separadores, por lo que el supuesto
es seguro. Si cambia el formato, se corrige primero la spec y luego `SERIE_PATRON`.

---

## 4. Representación de líneas seriadas y no seriadas

**Decision**: cada unidad seriada ocupa una fila `LineaRecojo` con `serie` no nulo y
`cantidad=1`. Un material no seriado ocupa una fila con `serie=NULL` y `cantidad>0`. La cantidad
de un material seriado nunca es distinta de 1.

**Rationale**: es la misma representación que usan las reglas de stock y series ("una fila por
serie", "el stock se mide en número de series") y la que ya adopta el plan de 005. Mantiene el
stock general y el inventario alineados sin campos redundantes.

**Alternativas consideradas**:
- Una línea seriada con una lista de series en un campo de texto: impide la unicidad por fila y
  complica la vista previa y la trazabilidad.
- Una línea seriada con cantidad agregada: pierde la identidad de cada serie, que es la unidad de
  trazabilidad del negocio.

**Consecuencia**: el formulario acepta un bloque de texto con varias series por material seriado;
el servicio lo expande a una fila por serie normalizada. La vista previa muestra una fila por
serie, aunque el usuario haya pegado un bloque.

---

## 5. Tenant, región y almacén

**Decision**: el tenant sale siempre de `request.usuario.tenant`/`actor.tenant`. La región del
recojo y de cada serie se toma de `tenant.region` y se guarda como FK `tenants.Region` en
`Recojo` y `Serie`. No se acepta `tenant_id`, `region_id`, `almacen_id` ni equivalentes desde el
formulario, la URL o la petición HTMX.

**Rationale**: el principio I prohíbe derivar el alcance del cliente y el principio II exige que
cada tenant pertenezca a una región. Guardar la región como instantánea permite consultar y
auditar sin joins, y hace explícito que la serie no cambia de región. El almacén central no se
elige: cada región tiene exactamente uno (001), por lo que la región identifica al almacén.

**Alternativas consideradas**:
- No guardar `region` y derivarla siempre de `tenant.region`: es posible porque la región del
  tenant es inmutable, pero obliga a un join en cada listado y deja la regla "la serie no cambia de
  región" solo implícita.
- Incluir un selector de almacén: la spec no lo pide y permitiría elegir otro almacén, violando
  RF-14.

**Riesgo**: `Recojo.region` y `Serie.region` son datos denormalizados; el servicio debe fijarlos
desde `tenant.region` y nunca actualizarlos. Se prueba que un `region_id` forzado no cambia el
valor guardado.

---

## 6. Dependencia del stock general (spec 008) y orden de implementación

**Decision**: 004 no crea el modelo de stock. Consume `stock.models.StockGeneral` y
`stock.services.incrementar_stock_general(tenant, material, cantidad, actor)` de la spec 008. La
parte fundacional de 008 (modelo `StockGeneral` y el servicio de incremento) es prerrequisito de
004; la confirmación de asignaciones de 008 puede completarse después de 007.

**Rationale**: la spec 008 es la dueña del servicio compartido de stock y su plan ya define el
modelo y la firma. Duplicar `StockGeneral` en 004 crearía dos fuentes de verdad y dos migraciones
incompatibles. El orden recomendado del repositorio pone 004 antes de 008, pero esa parte de 008
no depende de 007 y puede implementarse antes.

**Alternativas consideradas**:
- Que 004 cree `StockGeneral` y 008 lo reutilice: contradice el plan de 008 y deja a 008 sin su
  migración inicial.
- Calcular el stock general sumando recojos, asignaciones y devoluciones en cada consulta: no es
  un stock almacenado, complica la conciliación y contradice el modelo de 008.

**Consecuencia documental**: el plan de 008 debe leerse con esta dependencia; su parte de
confirmación de asignaciones no es requisito para 004. El desglose global de implementación debe
reflejar que la parte fundacional de 008 va antes de 004.

**Riesgo**: si 008 no está implementada, 004 no puede guardar stock. La tarea inicial de 004 debe
verificar que `stock.StockGeneral` y `incrementar_stock_general` existan y detenerse si faltan.

---

## 7. Validación previa, todo o nada y concurrencia

**Decision**: la validación se ejecuta en dos capas. Primero, una validación en memoria (formato,
duplicados del mismo recojo, tipo de material, cantidades y existencia del material) que produce un
resultado con el estado de cada serie. Después, dentro de `transaction.atomic`, se vuelve a validar,
se crea el recojo, sus líneas, las series y se incrementa el stock; la restricción `unique` de
`Serie.numero` es la fuente de verdad ante dos sesiones concurrentes.

**Rationale**: la vista previa necesita estados por fila sin escribir; el guardado necesita fallar
completo si algo cambió entre la vista previa y el `POST`. Una comprobación "leer y luego insertar"
no basta ante concurrencia; la restricción única sí.

**Alternativas consideradas**:
- Validar solo dentro de la transacción y abortar en el primer error: el usuario no ve todos los
  problemas y la vista previa no puede reutilizar la lógica.
- Validar solo en la aplicación: dos sesiones podrían insertar la misma serie.

**Consecuencia**: la validación previa se comparte entre el endpoint de vista previa y el guardado.
Si la base rechaza una serie duplicada, se traduce a "La serie ya está registrada en el sistema" y
toda la transacción se revierte.

---

## 8. Vista previa como fragmento HTML, no JSON

**Decision**: `POST /recojos/validar-series/` devuelve un fragmento HTML (`text/html`) con una fila
por serie y los atributos `data-serie` y `data-estado`. Estados: `valida`, `invalida`,
`duplicada`, `ya_existe`.

**Rationale**: el proyecto es server-rendered con HTMX y los contratos de 002 y 003 usan fragmentos
HTML con `data-*`, no una API JSON. Un fragmento permite que HTMX reemplace la vista previa sin
JavaScript adicional y mantiene un solo estilo de contrato.

**Alternativas consideradas**:
- JSON: exigiría JavaScript propio para renderizar la vista previa y rompería la convención del
  proyecto.
- Validación solo en el cliente: no es autoridad y no conoce las series existentes de otros
  tenants.

**Consecuencia**: el endpoint es de solo lectura, exige `POST` y CSRF (el texto puede ser largo y no
debe ir en la URL) y nunca revela el tenant de una serie existente.

---

## 9. Duplicados, series existentes y aislamiento

**Decision**: el mensaje de una serie ya existente es siempre "La serie ya está registrada en el
sistema", sin indicar tenant, región ni recojo de origen. El mensaje de duplicado dentro del mismo
recojo es "La serie está duplicada en el recojo". La vista previa marca `ya_existe` sin más datos.

**Rationale**: el principio I exige no revelar la existencia ni el propietario de datos ajenos. La
consulta de existencia es global porque la unicidad lo es, pero la respuesta solo devuelve un
estado uniforme.

**Alternativas consideradas**:
- Mensaje específico por tenant: revelaría información de otro tenant.
- No consultar series de otros tenants: permitiría intentar insertarlas y fallar por la restricción
  única con un error de base de datos, sin una vista previa clara.

---

## 10. Permisos

**Decision**: solo el rol `USUARIO_TENANT` (cuenta del tenant) crea, lista, consulta y previsualiza
recojos. `ADMIN_PLATAFORMA` y `RESPONSABLE_ALMACEN` reciben `403`. El tenant suspendido recibe
`403`; la cuenta inactiva no conserva la sesión.

**Rationale**: la spec identifica al tenant como único actor del recojo; la constitución prohíbe
que el Administrador opere inventario y que el Responsable de almacén actúe fuera de su región. El
recojo es una operación de inventario del tenant.

**Alternativas consideradas**:
- Permitir al Administrador consultar todos los recojos: la spec no lo pide y expondría datos de
  todos los tenants; la consulta administrativa pertenece a la auditoría de 001.
- Permitir al Responsable de almacén registrar recojos en nombre de un tenant: no está en la spec y
  rompería el alcance de una sola región.

**Consecuencia**: la autorización se valida en la vista y se revalida en el servicio. Ocultar un
botón no es autorización.

---

## 11. Auditoría

**Decision**: se registra un `auditoria.RegistroCambio` por alta de recojo con `entidad="Recojo"`,
`campo="alta"` y un resumen legible (fecha, región, número de líneas, total de series y total de
cantidad). Los incrementos de stock los audita `stock.services.incrementar_stock_general` con
`entidad="StockGeneral"`, `campo="cantidad"`. No se escribe un registro de auditoría por cada
serie.

**Rationale**: la auditoría de stock ya registra el movimiento de cantidad por material, y cada
`Serie` conserva `creado_por`, `creado_en` y su vínculo con la línea y el recojo; eso da
trazabilidad individual sin inflar el libro con miles de filas por recojo. La constitución exige
auditar movimientos y ajustes de stock, no necesariamente cada alta de serie.

**Alternativas consideradas**:
- Un `RegistroCambio` por serie: máxima granularidad, pero un recojo de 1 000 series generaría
  1 000 registros de auditoría además de las filas de serie; el vínculo `Serie → LineaRecojo →
  Recojo` ya identifica el origen.
- Auditar solo el stock y no el recojo: se perdería el resumen del documento que originó el
  movimiento.

**Consecuencia**: la auditoría del recojo y la del stock se escriben en la misma transacción. Si el
recojo falla, no se escribe ninguna. Nunca se auditan contraseñas, tokens ni secretos.

---

## 12. Inmutabilidad del recojo y ausencia de edición/borrado

**Decision**: no hay rutas de edición ni de borrado de recojos. `POST /recojos/nuevo/` crea; el
detalle y el listado son de solo lectura. `DELETE` responde `405`. `LineaRecojo.recojo` y
`LineaRecojo.serie` usan `PROTECT`.

**Rationale**: un recojo es un movimiento de stock histórico; corregirlo requiere un movimiento
nuevo, no una edición. La spec no define edición y la constitución exige trazabilidad inmutable.

**Alternativas consideradas**:
- Edición con auditoría: permitiría cambiar cantidades o series después de afectar el stock;
  exigiría reversar y reaplicar stock, una operación que la spec no contempla.
- Borrado lógico: la spec no lo pide; el recojo debe conservarse completo.

**Consecuencia**: si un recojo se registró mal, la corrección se hará con una operación de
devolución/ajuste de una spec posterior, no editando el recojo.

---

## 13. Integración con la inmutabilidad del tipo de material (spec 002)

**Decision**: 004 registra en `materiales.services` una verificación de movimientos que consulta
`LineaRecojo`/`Serie`/`StockGeneral` para el material. Mientras exista un recojo o stock del
material, `puede_cambiar_tipo` devuelve `False`.

**Rationale**: el plan de 002 expone `registrar_verificacion_movimientos(func)` precisamente para
que las specs 004–011 aporten su verificación real. Sin ella, un material seriado podría convertirse
en no seriado después de tener series en stock, corrompiendo el inventario.

**Alternativas consideradas**:
- Duplicar la regla en 004: la decisión de si el tipo puede cambiar pertenece a 002; 004 solo
  aporta la evidencia de que hay movimientos.
- No registrarla: el tipo quedaría mutable con stock, violando la regla de 002 y la constitución.

---

## 14. Rendimiento y concurrencia

**Decision**: la vista previa consulta todas las series existentes con una sola consulta
`Serie.objects.filter(numero__in=normalizadas)`; el listado se pagina a 50 filas y anota totales;
el detalle precarga líneas, materiales y series. La creación agrupa las líneas por material y llama
una vez a `incrementar_stock_general` por material.

**Rationale**: evita N+1 y mantiene la validación por debajo de un segundo por lote de series. La
agrupación por material produce una auditoría de stock legible y menos escrituras.

**Alternativas consideradas**:
- Consultar la existencia serie por serie: N consultas y riesgo de superar el objetivo de
  rendimiento.
- Llamar al servicio de stock por cada serie: muchas actualizaciones y auditorías del mismo
  registro de stock.

**Riesgo**: dos recojos concurrentes del mismo tenant y material deben sumar correctamente. El
servicio de 008 debe usar bloqueo de fila (`select_for_update`) o una expresión `F()`; 004 no
implementa su propia actualización de stock y lo verifica en pruebas de integración.

---

## 15. Fecha del recojo

**Decision**: `fecha` es un `DateField` obligatorio, con valor inicial hoy en el formulario. La
fecha de registro (`creado_en`) se guarda aparte con `auto_now_add`. No se prohíben fechas pasadas
ni futuras.

**Rationale**: la spec pide la fecha del recojo y un valor por defecto hoy; no impone límites. Un
recojo puede registrarse tarde. Prohibir fechas futuras sería una regla no especificada.

**Alternativas consideradas**:
- Usar solo `creado_en`: confunde la fecha del documento con la fecha de carga.
- Rechazar fechas futuras: no está en la spec; si el negocio lo requiere, se agrega primero.

---

## 16. RLS y aislamiento en base de datos

**Decision**: se recomienda RLS por `tenant_id` en `recojos_recojo`, `recojos_linearecojo`,
`series_serie` y `stock_stockgeneral`. `LineaRecojo` lleva una FK `tenant` denormalizada para que la
política no dependa de un join. La aplicación no depende de RLS: todas las consultas filtran por
tenant.

**Rationale**: el principio I exige aislamiento en el backend y, cuando la base lo permita, también
en ella. La FK de tenant en la línea permite una política directa y consultas de respaldo.

**Alternativas consideradas**:
- RLS solo en el padre: obliga a políticas con subconsultas y complica el mantenimiento.
- No usar RLS: la aplicación sigue siendo la fuente de verdad, pero se pierde la defensa en
  profundidad que la constitución recomienda.

**Riesgo**: la FK `tenant` de `LineaRecojo` es redundante con `Recojo.tenant`; el servicio debe
fijarla desde el recojo y nunca aceptarla del cliente. Se prueba la coherencia.

---

## 17. Resumen de incógnitas resueltas

| Incógnita del plan anterior | Resolución |
|---|---|
| Nombre y propiedad de la app de series | `series`, creada por 004; 005–011 la consumen |
| Unicidad global de series | `Serie.numero unique` en PostgreSQL; registro central |
| ¿Serie como cadena o entidad? | Entidad `Serie`; `LineaRecojo.serie` es FK uno a uno |
| ¿Se eliminan espacios internos? | Sí, todos los espacios en blanco, antes de validar |
| ¿JSON o HTML en la vista previa? | Fragmento HTML con `data-serie` y `data-estado` |
| ¿Quién es dueño del stock general? | Spec 008; 004 consume su servicio |
| ¿Se guarda la región? | Sí, en `Recojo` y `Serie`, fijada desde `tenant.region` |
| ¿Se audita cada serie? | No; se audita el recojo y el stock, y la serie queda trazada por sus filas |
| ¿Se puede editar o borrar un recojo? | No; solo alta y consulta, `DELETE` responde `405` |
| ¿004 depende de técnicos? | No; el recojo es del tenant, no de un técnico |
| ¿Cómo se bloquea el cambio de tipo? | 004 registra la verificación de movimientos en 002 |
| ¿Qué pasa si 008 no está implementada? | 004 se detiene: `StockGeneral` y el servicio son prerrequisito |

---

## Decisiones que requieren seguimiento documental

1. El plan de 008 debe indicar que su parte fundacional (`StockGeneral` e
   `incrementar_stock_general`) se implementa antes de 004; su parte de confirmación de
   asignaciones puede ir después de 007.
2. El plan de 005 ya usa `series.Serie` y el registro central; no requiere una columna de texto.
   Queda como referencia de la decisión, no como deuda.
3. El desglose global de implementación debe corregir la dependencia de 004: depende de materiales
   y del stock general, no de técnicos.
4. La app `series` debe documentarse como transversal y dueña de la identidad y el estado de las
   series; las specs 006, 007, 008, 010 y 011 agregan transiciones, no otra tabla.
