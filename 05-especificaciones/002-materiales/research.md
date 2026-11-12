# Investigación y decisiones técnicas: 002 Módulo de materiales

**Fase**: 0 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/002-materiales/spec.md`

Este documento resuelve las incógnitas del plan técnico antes del diseño de datos y
contratos. No queda ningún `NEEDS CLARIFICATION` pendiente. Las suposiciones que la spec deja
"a confirmar" se adoptan explícitamente y se marcan como riesgo.

---

## 1. Nombre de la app: `materiales`, no `catalogo`

**Decision**: la app se llama `materiales` (`materiales.models.Material`).

**Rationale**: las referencias concretas de las specs consumidoras ya escritas usan
`"materiales.Material"`: 004 (recojo), 005 (stock inicial), 006 (asignación), 008
(confirmación de stock), 009 (traspaso), 010 (conciliación) y 011 (logística inversa). Las
rutas de esta spec también son `/materiales/`. Elegir `catalogo` obligaría a corregir siete
planes y sus `ForeignKey`.

**Alternativas consideradas**:
- `catalogo` (nombre del plan anterior de 002 y de la regla de dominio): solo lo usa la spec
  013; se corrige ese documento antes de implementarlo.
- `catalogo` con alias `materiales`: agrega indirección sin valor y confunde migraciones.

**Seguimiento documental**: actualizar `05-especificaciones/013-registro-materiales/plan.md`
(`catalogo.Material` → `materiales.Material`) y la frase de `001-tenants-y-acceso/plan.md` que
menciona `catalogo` como app futura. No se modifican esos documentos en esta tarea porque
pertenecen a otras specs; queda registrado como deuda de documentación.

---

## 2. Reutilización de `auditoria.RegistroCambio`

**Decision**: no se crea un modelo de auditoría nuevo. Se reutiliza
`auditoria.RegistroCambio` y `auditoria.services.registrar_cambio` de la spec 001.

**Rationale**: la regla `03-reglas-de-dominio/auditoria.md` define una tabla única para todo el
sistema. Duplicarla por módulo rompería la consulta global y la inmutabilidad centralizada.

**Alternativas consideradas**:
- Historial propio en `materiales`: descartado por duplicar y fragmentar la auditoría.
- `django-simple-history`: agrega dependencia y guarda versiones completas, no un registro por
  campo con valor anterior y nuevo.

**Dependencia**: si la app `auditoria` aún no existe al implementar 002, la implementación se
detiene: 001 es su dueña. No se crea una segunda tabla.

---

## 3. Representación del tipo: `es_seriado` + propiedad `tipo`

**Decision**: se guarda `es_seriado = BooleanField()` y se expone una propiedad de solo
lectura `tipo` que devuelve `"SERIADO"` o `"NO_SERIADO"`.

**Rationale**: el plan anterior ya fijó `es_seriado`; un booleano es suficiente para una
decisión binaria y se indexa y filtra de forma natural. Las specs consumidoras y los contratos
de búsqueda hablan de "tipo" (`codigo, descripcion, lote, tipo`), por lo que la propiedad evita
que cada consumidor traduzca el booleano. La auditoría registra el texto `SERIADO` /
`NO_SERIADO`, legible para el negocio.

**Alternativas consideradas**:
- `CharField(choices=("SERIADO","NO_SERIADO"))`: más explícito en la base, pero agrega una
  restricción de valores y no aporta nada que el booleano no cubra para dos estados fijos.
- Solo `es_seriado` y que cada consumidor lo interprete: duplica la traducción en 6 módulos.

**Compatibilidad**: cualquier consumidor puede usar `material.tipo` o `material.es_seriado`.
El formulario acepta `tipo` y lo convierte a `es_seriado` en `clean()`.

---

## 4. Permisos: creación abierta a cuentas activas y edición restringida

**Decision**:
- Crear: cualquier cuenta autenticada y activa, de cualquiera de los tres roles.
- Editar descripción y lote: el creador o el rol `ADMIN_PLATAFORMA`.
- El código no es editable por nadie.
- No existe permiso de borrado.

**Rationale**: el criterio de aceptación "cuando **cualquier tenant** intenta registrarlo de
nuevo" presupone que los tenants crean materiales; la spec 001 asigna al tenant la gestión de
materiales. La spec restringe la edición a creador o administrador, no la creación. Usar el
sistema de permisos de Django para el alta obligaría a sembrar grupos/permisos en migraciones
de datos, algo que la constitución pide evitar ("no se crean credenciales ni administradores
por migración"); un chequeo de rol explícito en el servicio es más simple y testeable.

**Alternativas consideradas**:
- Permiso `materiales.add_material` para todos: requiere asignación por grupos y no aporta
  seguridad adicional si todos los roles lo tienen.
- Solo el Administrador crea materiales: contradice el criterio de aceptación que habla de
  cualquier tenant.

**Nota**: la vista aplica la comprobación para la UX, pero el servicio la revalida; ocultar un
botón no autoriza.

---

## 5. Inmutabilidad del tipo con stock o movimientos

**Decision**: `puede_cambiar_tipo(material)` consulta un registro de verificaciones
(`_VERIFICACIONES_MOVIMIENTOS`) y devuelve `False` si alguna reporta stock o movimientos.
Se expone `registrar_verificacion_movimientos(func)` para que las specs 004–011 registren su
consulta real cuando existan sus tablas. Sin verificaciones registradas devuelve `True`.

**Rationale**: en esta spec todavía no existen tablas de stock ni de movimientos; inventar un
campo desnormalizado `tiene_movimientos` crearía una fuente de verdad paralela que las specs
futuras podrían olvidar actualizar. Un registro de verificaciones permite implementar y probar
la regla hoy (con una verificación de prueba) y conectar la consulta real después sin cambiar
la firma ni el mensaje.

**Alternativas consideradas**:
- Campo `tiene_movimientos` en `Material`: simple, pero se desincroniza y duplica el estado del
  inventario.
- Consultar modelos por nombre con `apps.get_model`: frágil, depende del orden de arranque y de
  que la app exista.
- Posponer la regla a la spec 004: incumple el criterio de aceptación de 002.

**Prueba**: se registra una verificación temporal en la prueba que devuelve `True` y se verifica
el rechazo con "El tipo no se puede cambiar: el material tiene movimientos". El registro debe
limpiarse al finalizar la prueba para no contaminar otras.

---

## 6. Normalización de código, descripción y lote

**Decision**:
- `codigo`: `strip()` de espacios externos; no se eliminan espacios ni guiones internos; se
  valida `^[0-9]{11}$` después del `strip`.
- `descripcion`: `strip()` y colapso de espacios internos repetidos a uno; longitud 1–100
  después de normalizar.
- `lote`: `strip()`, colapso de espacios internos y `upper()`; vacío permitido; máximo 50
  después de normalizar.

**Rationale**: cumple los casos borde de la spec (espacios al inicio/final/repetidos, lote en
minúsculas, código con espacios o guiones internos). Normalizar antes de validar evita que dos
variantes del mismo valor burlen la unicidad o la búsqueda.

**Alternativas consideradas**:
- Guardar tal cual y comparar normalizado en cada consulta: duplica la lógica y permite
  duplicados por espaciado.
- Eliminar espacios y guiones internos del código: aceptaría entradas ambiguas; la spec exige
  exactamente 11 dígitos y los casos borde piden rechazarlas.

**Riesgo**: la spec marca el lote en mayúsculas como supuesto "a confirmar". Se implementa así
y se documenta; si Lari distingue mayúsculas, se corrige primero la spec.

---

## 7. Búsqueda y paginación

**Decision**: `buscar_materiales(q="")` usa `codigo__icontains=q OR descripcion__icontains=q`
con `order_by("codigo")`. Sin `q` devuelve el catálogo completo. Listado paginado a 50; el
fragmento HTMX limita a 20 resultados.

**Rationale**: el catálogo estimado (1 000–10 000 filas) hace innecesario un índice de texto
completo. `icontains` es portable, no agrega dependencias y satisface "ROSETA" en mayúsculas y
minúsculas. El orden por código es estable y coincide con el identificador de negocio.

**Alternativas consideradas**:
- `SearchVector`/`pg_trgm`: mejor para catálogos grandes, pero agrega configuración de índice y
  no se justifica con el volumen actual.
- Coincidencia exacta por código y `icontains` por descripción: la búsqueda por código parcial
  es útil para autocompletar; se mantiene `icontains` en ambos.

**Nota**: si un material no tuviera descripción (imposible por restricción) igual aparecería
por código. La búsqueda vacía no filtra y devuelve la primera página.

---

## 8. Doble envío y concurrencia

**Decision**: la fuente de verdad es `unique(codigo)` más la traducción de `IntegrityError` a
"El material ya existe". No se usan bloqueos de aplicación ni banderas en sesión.

**Rationale**: el doble clic y dos usuarios simultáneos con el mismo código producen el mismo
resultado: una sola fila y un mensaje uniforme. Es el patrón ya usado en la spec 001.

**Alternativas consideradas**:
- `get_or_create`: devuelve éxito al segundo envío, ocultando el conflicto; la spec exige
  rechazar la segunda petición.
- Bloqueo pesimista por código: innecesario y no cubre dos procesos sin coordinación.

**Adicional**: `hx-disabled-elt` en el botón Guardar reduce el doble clic en la interfaz, pero no
es la garantía; la base lo es.

---

## 9. Sin eliminación y conservación del material

**Decision**: no hay ruta, vista ni servicio de borrado; `creado_por` y `actualizado_por` usan
`PROTECT`; `DELETE` sobre `/materiales/<id>/editar/` responde `405`.

**Rationale**: la spec prohíbe borrar materiales y exige conservarlos aunque el creador se
desactive. `PROTECT` impide que una baja accidental de usuario arrastre materiales.

**Alternativas consideradas**:
- Borrado lógico (`activo=False`): agrega un estado que la spec no pide y complica los
  selectores de las specs consumidoras.
- `CASCADE`: destruiría catálogo compartido ante una baja de cuenta; inaceptable.

---

## 10. Contrato de búsqueda para las specs consumidoras

**Decision**: `GET /materiales/buscar/?q=&limit=` devuelve un fragmento HTML con filas que
exponen `data-codigo`, `data-descripcion`, `data-lote` y `data-tipo`. Requiere sesión
autenticada; no filtra por tenant; limita a 20 por defecto y 50 como máximo.

**Rationale**: las specs 004, 005, 006, 009 y 013 solo necesitan elegir un material y
autocompletar descripción, lote y tipo. Un fragmento HTML con atributos `data-*` permite que
HTMX lo inserte y que el JavaScript del formulario consumidor lea los valores sin acoplar los
módulos a un esquema JSON adicional. El contrato se documenta en
`contracts/busqueda-materiales.md`.

**Alternativas consideradas**:
- Endpoint JSON: obligaría a mantener dos representaciones y un cliente JS en cada consumidor.
- Devolver el `Material` completo: expone campos internos (creador, fechas) innecesarios.

---

## 11. Consulta de auditoría de materiales

**Decision**: esta spec solo **escribe** auditoría. La consulta de registros de `Material` se
resolverá en la pantalla de auditoría administrativa (spec 001 / futura spec de auditoría); no
se agrega una ruta nueva en 002.

**Rationale**: la spec 002 no define pantalla de auditoría y la spec 001 ya define
`/auditoria/acceso/` con alcance por rol. Agregar una ruta aquí ampliaría el alcance sin regla
de visibilidad para un catálogo global (no hay tenant al que atribuir el registro, solo el
usuario autor).

**Alternativas consideradas**:
- `/materiales/<id>/historial/`: útil, pero fuera de la spec; puede agregarse cuando se defina
  la visibilidad (el catálogo es global y el autor pertenece a un tenant).

**Seguimiento**: al implementar la auditoría administrativa, definir que los registros con
`entidad="Material"` son visibles para el Administrador de plataforma y, para el autor, solo
los suyos.

---

## 12. Regla de dominio ausente

**Decision**: `03-reglas-de-dominio/catalogo-de-materiales.md` está vacío (0 bytes) a la fecha.
La fuente de verdad para esta spec es `05-especificaciones/002-materiales/spec.md`.

**Rationale**: la constitución exige que las specs referencien reglas de dominio, pero no se
puede implementar un documento vacío. No se inventan reglas adicionales: se documentan solo las
de la spec. Se registra la carencia para que el responsable del proyecto complete la regla.

**Seguimiento documental**: completar `03-reglas-de-dominio/catalogo-de-materiales.md` con las
reglas de esta spec y las que agreguen las specs consumidoras. Si el documento completo llega a
contradecir la spec, prevalece la constitución y se corrige el artefacto antes del código
(principio VIII).

---

## 13. Pruebas sobre PostgreSQL

**Decision**: `pytest` + `pytest-django` contra PostgreSQL, igual que la spec 001. Se prueban
tanto el servicio como las restricciones de base (regex de 11 dígitos, unicidad) y las rutas
HTTP.

**Rationale**: SQLite no reproduce `CheckConstraint` con expresiones regulares ni el
comportamiento de concurrencia de PostgreSQL; las pruebas de base son parte de la puerta de
calidad.

**Alternativas consideradas**: SQLite en pruebas unitarias: descartado por ocultar diferencias
del motor.

---

## 14. Códigos HTTP y mensajes

**Decision**:
- `200` lectura y fragmento HTMX.
- `302` tras `POST` exitoso (alta → listado o detalle; edición → listado).
- `400` validación de formulario.
- `401` sin sesión.
- `403` sin permiso de edición.
- `404` material inexistente.
- `405` métodos distintos de `GET`/`POST` (incluido `DELETE`).
- `409` código duplicado ("El material ya existe").

**Rationale**: coherencia con el contrato de la spec 001, que ya usa `409` para conflictos de
unicidad y `404` para recursos inexistentes. La spec 002 no fija códigos; se adoptan los de la
convención existente.

**Alternativas consideradas**: `400` para duplicado; se descarta porque impide distinguir
validación de conflicto y rompe la consistencia con 001.

---

## Resumen de dependencias

| Dependencia | Estado | Uso |
|---|---|---|
| Django LTS 5.x, HTMX, PostgreSQL, pytest | Ya fijadas por constitución/001 | Base de la implementación |
| `acceso.Usuario` y helpers de rol | Planificada en 001 | `creado_por`, permisos y sesión |
| `auditoria.RegistroCambio` | Planificada en 001 | Auditoría de altas y cambios |
| `ContextoUsuarioMiddleware` | Planificada en 001 | Autenticación y `request.usuario` |
| Dependencias nuevas | **Ninguna** | La búsqueda y la paginación usan Django |

## Incógnitas resueltas

| Incógnita | Resolución |
|---|---|
| Nombre de la app | `materiales` (§1) |
| Auditoría | Reutilizar `auditoria.RegistroCambio` (§2) |
| Tipo | `es_seriado` + propiedad `tipo` (§3) |
| Quién crea y quién edita | Cualquier cuenta activa crea; creador o admin edita (§4) |
| Tipo inmutable sin tablas de stock | Registro de verificaciones (§5) |
| Normalización | Código strip; descripción sin espacios repetidos; lote mayúsculas (§6) |
| Búsqueda | `icontains` por código y descripción, orden por código (§7) |
| Doble envío | Restricción única + `IntegrityError` (§8) |
| Borrado | Sin ruta; `PROTECT` (§9) |
| Contrato para otros módulos | Fragmento HTML con `data-*` (§10) |
| Consulta de auditoría | Fuera de alcance de 002 (§11) |
| Regla de dominio vacía | Spec como fuente; seguimiento documental (§12) |
| Pruebas | PostgreSQL, un caso por criterio (§13) |
| Códigos HTTP | Convención de 001 (§14) |
