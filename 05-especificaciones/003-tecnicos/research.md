# Investigación y decisiones técnicas: 003 Técnicos del tenant

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/003-tecnicos/spec.md`

Este documento resuelve las incógnitas del plan técnico antes del diseño de datos y contratos.
No queda ningún `NEEDS CLARIFICATION` pendiente. Los supuestos que la spec deja "a confirmar" se
adoptan explícitamente y se marcan como riesgo.

---

## 1. App `tecnicos` y modelo `Tecnico`

**Decision**: la app se llama `tecnicos` y el modelo `tecnicos.models.Tecnico`.

**Rationale**: es la referencia que ya usan las specs consumidoras: `"tecnicos.Tecnico"` en 005,
006, 009 y 013; `validar_tecnico_para_operacion` en 006; `tecnicos_para_operacion` en 009. Las
rutas de esta spec también son `/tecnicos/`. Elegir otro nombre obligaría a corregir esas FK y
los planes ya escritos.

**Alternativas consideradas**:
- `personal` o `cuadrillas`: no corresponden al glosario de la constitución, que define
  "Técnico / NIF" como una persona identificada con código `LAxxxx`.
- `acceso.Tecnico`: mezclaría identidad de acceso con un actor pasivo que no inicia sesión.

---

## 2. NIF único global, no único por tenant

**Decision**: `nif` usa `unique=True` global.

**Rationale**: la spec lo establece como regla de negocio y como criterio de aceptación: el mismo
NIF no puede existir en dos tenants. El NIF es el identificador que viaja en los Excel de
asignación, traspaso y conciliación; permitir duplicados entre tenants haría ambiguo el reporte.
El mensaje de duplicado es uniforme y no revela el tenant propietario, por lo que la unicidad
global no contradice el aislamiento.

**Alternativas consideradas**:
- `UniqueConstraint(fields=["tenant", "nif"])`: solo si Lari confirma que el mismo NIF puede
  pertenecer a dos subcontratistas. Hoy contradice la spec; se cambiaría primero el documento.
- Unicidad solo en la aplicación: no resiste concurrencia ni inserciones directas.

**Riesgo**: si el negocio descubre que un técnico cambia de subcontratista y conserva su NIF, la
regla global impedirá registrarlo en el nuevo tenant. La salida documentada es desactivar en el
tenant actual y crear en el nuevo; si el NIF sigue existiendo, primero se corrige la spec.

---

## 3. NIF inmutable y sin historial de NIF

**Decision**: el NIF se guarda al alta y no se edita. El formulario de edición no lo incluye y el
servicio rechaza cualquier clave `nif` con "El NIF no se puede cambiar". No se crea una tabla de
historial de NIF.

**Rationale**: los Excel y reportes históricos se concilian por NIF; cambiarlo rompería la
trazabilidad. La spec indica que un NIF mal registrado se corrige desactivando el técnico y
creando uno nuevo con el NIF correcto. Un historial de NIF añadiría una entidad que la spec
declara fuera de alcance.

**Alternativas consideradas**:
- Permitir edición con auditoría: conserva el valor anterior, pero deja documentos históricos
  apuntando a un NIF que ya no identifica al mismo técnico.
- Historial de NIF: útil en un sistema de identidad completo, pero fuera de alcance y sin regla
  de negocio que lo respalde.

---

## 4. Estado modelado como `activo` booleano

**Decision**: `activo = BooleanField(default=True)`. Los estados visibles son "Activo" y
"Desactivado"; la auditoría registra los textos `ACTIVO` y `DESACTIVADO`.

**Rationale**: la spec define exactamente dos estados y un valor inicial Activo. Un booleano es
suficiente, se indexa de forma natural y evita una restricción de valores para dos opciones fijas.
La conversión a texto se hace solo en la auditoría y en la interfaz.

**Alternativas consideradas**:
- `CharField(choices=("ACTIVO", "DESACTIVADO"))`: más explícito, pero agrega una restricción y
  no aporta estados adicionales.
- Borrado lógico con `desactivado_en`: la spec no pide fecha de desactivación; la auditoría ya
  conserva el momento y el autor.

**Transiciones**: `ACTIVO → DESACTIVADO` (desactivar) y `DESACTIVADO → ACTIVO` (reactivar). No
existe transición a eliminado.

---

## 5. Aislamiento por tenant y RLS

**Decision**: el tenant se obtiene siempre de la cuenta autenticada
(`actor.tenant`/`request.tenant`). Toda consulta de `Tecnico` filtra por `tenant`. Un técnico de
otro tenant se responde como inexistente (`404`, "El técnico no existe"). No se acepta
`tenant_id` ni `region_id` desde formularios, URLs, parámetros de búsqueda ni archivos.

**Rationale**: cumple el principio I de la constitución y la regla 2 de la spec. Tratar el acceso
ajeno como inexistente evita revelar la existencia y el propietario del dato. La región no se
guarda en el técnico: se deriva de `tenant.region`, lo que evita duplicar y desincronizar la
jerarquía Región → Tenant → Técnico.

**Alternativas consideradas**:
- Guardar `region` en `Tecnico`: redundante y propenso a inconsistencias si el tenant cambia de
  región (operación que además está fuera de alcance).
- Filtrar solo en la vista: insuficiente; un servicio o una tarea de Celery podría consultar sin
  alcance. El filtro se aplica en el servicio y en el `QuerySet` base.

**RLS**: se recomienda una política de fila por `tenant_id` como respaldo, igual que en 001. La
aplicación no depende de RLS para el aislamiento; las pruebas se ejecutan con el filtro de
aplicación y, si el entorno lo permite, verifican también la política.

---

## 6. Permisos: solo la cuenta del tenant

**Decision**: únicamente `USUARIO_TENANT` puede listar, buscar, crear, ver, editar, desactivar y
reactivar técnicos. `ADMIN_PLATAFORMA` y `RESPONSABLE_ALMACEN` reciben `403` "No tienes permiso
para gestionar técnicos", incluso si fuerzan la petición.

**Rationale**: la spec es explícita: el Administrador no gestiona técnicos y el Responsable de
almacén no gestiona técnicos ni ve su listado completo. La autorización se valida en la vista y
se revalida en el servicio; ocultar un botón no autoriza. No se siembran grupos ni permisos en
migraciones: la autorización es por rol explícito y alcance de tenant, como en 001 y 002.

**Alternativas consideradas**:
- Permitir lectura al Administrador de plataforma: la spec no la necesita y ampliar el alcance
  obligaría a definir qué datos ve de cada tenant; se descarta.
- Permisos de Django sembrados por migración: agrega datos de seguridad en migraciones y no
  aporta nada frente al chequeo de rol, que ya existe en 001.

**Nota**: si más adelante se adopta `Permission` de Django, los códigos previstos son
`tecnicos.add_tecnico`, `tecnicos.view_tecnico`, `tecnicos.change_tecnico`,
`tecnicos.desactivar_tecnico` y `tecnicos.reactivar_tecnico`; hoy no son la fuente de verdad.

---

## 7. Normalización y validación de NIF y nombre

**Decision**:
- `nif`: `strip()` de espacios externos y `upper()`; se valida `^LA[0-9]{4}$` después de
  normalizar. Los espacios y guiones internos se rechazan.
- `nombre`: `strip()` y colapso de espacios internos repetidos; longitud 1–100 después de
  normalizar.
- `nif` se declara `CharField(max_length=6)`, no 10.

**Rationale**: cumple los casos borde de la spec: `" la1234 "` se guarda como `LA1234`; `LA123`,
`LA12345`, `A1234`, `LA12A4`, `LA 1234` y `LA-1234` se rechazan. Normalizar antes de validar evita
que dos variantes del mismo NIF burlen la unicidad. `max_length=6` hace que la longitud del campo
coincida con el único formato válido; el borrador anterior usaba 10, pero eso permitía almacenar
cadenas más largas que luego el `CheckConstraint` rechazaba con un error menos claro.

**Alternativas consideradas**:
- Guardar el NIF tal cual y normalizar en cada consulta: duplica la lógica y permite duplicados
  por espaciado.
- Aceptar NIF con guiones o espacios internos: la spec exige el formato estricto `LAXXXX`.
- `max_length=10`: no aporta nada y separa la restricción de aplicación de la restricción de
  base.

**Nombre**: se permiten caracteres especiales salvo que una política posterior indique lo
contrario; la spec solo exige que no esté vacío y que no supere 100 caracteres.

---

## 8. Búsqueda y selectores

**Decision**: `buscar_tecnicos(tenant, q="", solo_activos=False, estado=None)` filtra siempre por
tenant; con `q` usa `nif__icontains=q OR nombre__icontains=q`; ordena por `nombre` y `nif`. El
listado pagina a 50. El fragmento HTMX usa `solo_activos=True`, limita a 20 por defecto y 50 como
máximo.

**Rationale**: el volumen estimado (≈5 000 técnicos globales) hace innecesario un índice de texto
completo. `icontains` es portable, no agrega dependencias y satisface la búsqueda parcial por NIF
o nombre. El orden por nombre es el esperado en la interfaz; el NIF desempata. Los selectores de
operaciones nuevas solo ofrecen activos, como exige la regla 16 de la spec.

**Alternativas consideradas**:
- `SearchVector`/`pg_trgm`: mejor para volúmenes grandes, pero agrega configuración y no se
  justifica hoy.
- Coincidencia exacta por NIF y `icontains` por nombre: la búsqueda parcial por NIF es útil para
  autocompletar; se mantiene `icontains` en ambos.
- Devolver todos los estados en el fragmento y filtrar en el cliente: el servidor debe garantizar
  que un técnico desactivado no se ofrezca para una operación nueva.

**Listado**: el filtro por estado acepta `todos` (por defecto), `activos` y `desactivados`. El
valor por defecto `todos` permite localizar y reactivar desactivados; los selectores de otros
módulos no usan este listado, usan `tecnicos_para_operacion`.

---

## 9. Contrato para los módulos consumidores

**Decision**: los consumidores usan los helpers de `tecnicos/services.py` y el fragmento
`GET /tecnicos/buscar/`. El fragmento devuelve filas con `data-nif`, `data-nombre` y
`data-activo`; solo incluye técnicos activos del tenant de la sesión. El detalle está en
`contracts/busqueda-tecnicos.md`.

**Rationale**: 005 valida existencia por NIF dentro del tenant mediante
`obtener_tecnico_por_nif`; 006 y 009 necesitan elegir técnicos activos y validar que sigan activos
al guardar; 010 resuelve NIF del reporte dentro del tenant; 013 conserva la FK histórica. Un
contrato HTML con `data-*` permite que HTMX lo inserte y que el formulario consumidor complete el
NIF sin acoplar los módulos a un esquema JSON adicional. El servidor sigue siendo la autoridad: un
formulario viejo con un técnico desactivado se rechaza en el servicio del consumidor mediante
`validar_tecnico_para_operacion`.

**Alternativas consideradas**:
- Endpoint JSON: obligaría a mantener dos representaciones y un cliente JS en cada consumidor.
- Devolver el `Tecnico` completo: expone `tenant_id`, creador y fechas innecesarias.
- Permitir que cada módulo consulte `Tecnico` directamente: duplica el filtro de tenant y facilita
  fugas entre tenants.

**Garantías**: el NIF es estable e inmutable; el fragmento nunca devuelve `tenant_id`,
`region_id`, stock ni datos del creador; la misma consulta desde dos tenants devuelve solo los
técnicos de cada uno.

---

## 10. Reutilización de `auditoria.RegistroCambio`

**Decision**: no se crea un modelo de auditoría nuevo. Se reutiliza `auditoria.RegistroCambio` y
`auditoria.services.registrar_cambio` de la spec 001. El detalle está en
`contracts/auditoria-tecnico.md`.

**Rationale**: `03-reglas-de-dominio/auditoria.md` define una tabla única para todo el sistema.
Duplicarla por módulo rompería la consulta global y la inmutabilidad centralizada. La auditoría
registra un evento `alta` compuesto y un registro por campo modificado (`nombre`, `activo`).

**Alternativas consideradas**:
- Historial propio en `tecnicos`: descartado por duplicar y fragmentar la auditoría.
- `django-simple-history`: agrega dependencia y guarda versiones completas, no un registro por
  campo con valor anterior y nuevo.

**Dependencia**: si la app `auditoria` aún no existe al implementar 003, la implementación se
detiene: 001 es su dueña. No se crea una segunda tabla.

**Estado en auditoría**: `activo` se registra como `ACTIVO`/`DESACTIVADO`, no como
`True`/`False`, para que el registro sea legible por el negocio. El alta incluye `nif`, `nombre`
y `estado=ACTIVO`.

---

## 11. Sin eliminación y conservación histórica

**Decision**: no hay ruta, vista ni servicio de borrado; `DELETE` responde `405`. El técnico se
desactiva y se conserva. Las specs consumidoras usan FK `PROTECT`.

**Rationale**: la spec prohíbe la eliminación física y exige conservar stock, asignaciones,
traspasos, órdenes, conciliaciones y documentos históricos. `PROTECT` impide que una baja
accidental de usuario o de tenant arrastre técnicos.

**Alternativas consideradas**:
- `CASCADE`: destruiría historial ante la baja de un tenant o una cuenta; inaceptable.
- Borrado lógico adicional al `activo`: la desactivación ya es el borrado lógico; dos banderas
  confundirían a los consumidores.

**Edición de desactivados**: se permite corregir el nombre de un técnico desactivado. La regla de
"formulario viejo se rechaza" aplica a los formularios de operaciones nuevas (asignación,
traspaso, orden), no a la ficha administrativa del técnico. La decisión queda documentada para
que no se confunda con una reactivación implícita.

---

## 12. Concurrencia, doble envío e idempotencia

**Decision**:
- Alta: la fuente de verdad es `unique(nif)`; un `IntegrityError` se traduce a "El NIF ya está
  registrado". No se usa `get_or_create`.
- Edición: `transaction.atomic` + `select_for_update`; un `RegistroCambio` por campo realmente
  modificado; si no hay cambios, no se audita.
- Desactivación/reactivación: `transaction.atomic` + `select_for_update`; si el estado ya es el
  objetivo, no se actualiza ni se audita.
- El botón Guardar se desactiva con `hx-disabled-elt` como mejora de UX, no como garantía.

**Rationale**: dos altas simultáneas con el mismo NIF producen una sola fila y un mensaje
uniforme. `select_for_update` evita que dos ediciones lean el mismo valor anterior y escriban
auditorías contradictorias. La idempotencia de las transiciones evita auditoría duplicada por
doble clic en Desactivar o Reactivar.

**Alternativas consideradas**:
- `get_or_create`: devuelve éxito al segundo envío, ocultando el conflicto; la spec exige
  rechazar la segunda solicitud.
- Bloqueo pesimista por NIF: innecesario; la restricción única cubre dos procesos sin
  coordinación.
- Banderas en sesión para el doble clic: no cubren dos sesiones ni dos usuarios.

---

## 13. Tenant suspendido y cuenta inactiva

**Decision**: `ContextoUsuarioMiddleware` de 001 rechaza cuentas inactivas y tenants suspendidos.
Además, `validar_cuenta_tenant` revalida `actor.is_active` y `actor.tenant.estado == "ACTIVO"` y
lanza "El tenant está suspendido" cuando corresponde.

**Rationale**: la regla 19 de la spec exige que un tenant suspendido no pueda gestionar técnicos.
La revalidación en el servicio protege también procesos internos o llamadas que no pasan por el
middleware. Suspender un tenant conserva sus técnicos y su auditoría; solo bloquea la operación.

**Alternativas consideradas**:
- Confiar solo en el middleware: una tarea o un servicio invocado desde otro módulo podría operar
  sin el contexto HTTP.
- Marcar a todos los técnicos como desactivados al suspender: confunde suspensión con
  desactivación y pierde el estado operativo del técnico.

---

## 14. Códigos HTTP y mensajes

**Decision**:
- `200` lectura, detalle y fragmento HTMX.
- `302` tras `POST` exitoso (alta → listado o detalle; edición/desactivación/reactivación →
  detalle o listado).
- `400` validación de formulario o intento de cambiar NIF/tenant.
- `401` sin sesión.
- `403` rol distinto de `USUARIO_TENANT`.
- `404` técnico inexistente o de otro tenant.
- `405` método no permitido (incluye `DELETE` y `GET` en las acciones de estado).
- `409` NIF duplicado.

**Rationale**: coherencia con la convención de 001 y 002, que usan `409` para conflictos de
unicidad y `404` para recursos inexistentes. La spec 003 no fija códigos; se adoptan los de la
convención existente. Los mensajes exactos están en `contracts/http-endpoints.md`.

**Alternativas consideradas**: `400` para duplicado; se descarta porque impide distinguir
validación de conflicto y rompe la consistencia con el resto del proyecto.

---

## 15. Pruebas sobre PostgreSQL

**Decision**: `pytest` + `pytest-django` contra PostgreSQL, igual que 001 y 002. Se prueban
servicios, restricciones de base, rutas HTTP, permisos y transiciones de estado.

**Rationale**: SQLite no reproduce `CheckConstraint` con expresiones regulares, la restricción
`unique` global ni el comportamiento de concurrencia de PostgreSQL. Las pruebas de base son parte
de la puerta de calidad. Cada criterio de aceptación tiene al menos una prueba.

**Alternativas consideradas**: SQLite en pruebas unitarias: descartado por ocultar diferencias del
motor.

---

## 16. Supuestos adoptados y fuera de alcance

**Decision**: se adoptan los supuestos de la spec:
1. NIF `LA` + exactamente 4 dígitos.
2. NIF único global.
3. NIF inmutable después del alta.
4. Nombre obligatorio de 1–100 caracteres.
5. Estado binario Activo/Desactivado, inicial Activo.
6. Un desactivado puede reactivarse; no se elimina.
7. El cupo máximo de equipos sin liquidar no forma parte del alta; se definirá en la spec de
   asignación o como parámetro del tenant.
8. No se guardan datos personales adicionales.
9. El tenant sale de la sesión.
10. La auditoría usa `RegistroCambio`.

**Fuera de alcance**: cuentas de técnico, inicio de sesión, asignaciones, traspasos, devoluciones,
stock, conciliación, registro de materiales, cálculo de días en mano, alertas de custodia, carga
masiva por Excel, eliminación física, cambio de tenant o región, sincronización con Lari, datos
bancarios, nómina, turnos y jerarquías.

**Rationale**: mantener el alcance evita duplicar responsabilidades de las specs 004–013 y respeta
la puerta de alcance de la constitución.

---

## 17. Deuda documental detectada

- `05-especificaciones/003-tecnicos/plan.md` usaba `nif = CharField(max_length=10)`; se corrige a
  6 para que coincida con el formato `LAXXXX`.
- El plan anterior listaba permisos de Django como fuente de verdad; se aclara que la
  autorización es por rol explícito, coherente con 001 y 002, y que los códigos de permiso son
  solo una opción futura.
- Las referencias a `catalogo` en 013 y 001 no pertenecen a esta spec, pero siguen siendo deuda
  documental conocida; se corrigen antes de implementar 013.
- `03-reglas-de-dominio/registro-materiales.md` se referencia en la spec; esta spec no lo
  modifica. Si su contenido contradice la regla de técnicos, prevalece la constitución y se
  corrige el documento antes del código.

---

## Resumen de dependencias

| Dependencia | Estado | Uso |
|---|---|---|
| Django LTS 5.x, HTMX, PostgreSQL, pytest | Ya fijadas por constitución/001 | Base de la implementación |
| `acceso.Usuario` y helpers de rol | Planificada en 001 | Autor, permisos y sesión |
| `tenants.Tenant` y `tenant.region` | Planificada en 001 | Pertenencia, región derivada y estado del tenant |
| `auditoria.RegistroCambio` | Planificada en 001 | Auditoría de altas, cambios y estados |
| `ContextoUsuarioMiddleware` | Planificada en 001 | `request.usuario`, `request.tenant`, `request.rol` |
| Dependencias nuevas | **Ninguna** | La búsqueda y la paginación usan Django |

## Incógnitas resueltas

| Incógnita | Resolución |
|---|---|
| Nombre de app y modelo | `tecnicos.Tecnico` (§1) |
| Unicidad del NIF | Global, `unique(nif)` (§2) |
| Inmutabilidad del NIF | Formulario sin campo y servicio que rechaza la clave (§3) |
| Representación del estado | `activo` booleano, textos `ACTIVO`/`DESACTIVADO` en auditoría (§4) |
| Aislamiento | Tenant de la sesión; `404` para otro tenant; RLS como respaldo (§5) |
| Permisos | Solo `USUARIO_TENANT`; `403` para los demás roles (§6) |
| Normalización | NIF `strip`+`upper`; nombre `strip`+colapso; `max_length=6` (§7) |
| Búsqueda | `icontains` por NIF o nombre; activos en selectores; 50 en listado y 20/50 en fragmento (§8) |
| Contrato para consumidores | Helpers de servicio y fragmento con `data-nif`, `data-nombre`, `data-activo` (§9) |
| Auditoría | Reutilizar `RegistroCambio`; un registro por campo; misma transacción (§10) |
| Borrado | Sin ruta; desactivación y `PROTECT` (§11) |
| Concurrencia | `unique(nif)` + `IntegrityError`; `select_for_update`; idempotencia (§12) |
| Tenant suspendido | Middleware y servicio; no borra datos (§13) |
| Códigos HTTP | Convención de 001/002, con `409` para duplicado (§14) |
| Pruebas | PostgreSQL, un caso por criterio de aceptación (§15) |
| Alcance | Sin stock, cupo ni operaciones de otros módulos (§16) |
