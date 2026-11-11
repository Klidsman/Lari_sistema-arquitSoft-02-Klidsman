<!--
Sync Impact Report
==================
Change type: materialización del scaffold de Spec Kit con la constitución vigente del proyecto.
Version change: scaffold sin versión (marcadores sin completar) → 1.3.0
  (continúa la serie 1.x de `00-constitucion.md` v1.2; incremento MINOR por estructura
  ampliada y principios consolidados)
Modified principles:
  - Marcadores PRINCIPLE_1_NAME … PRINCIPLE_5_NAME → I. Aislamiento multitenant (NO NEGOCIABLE)
  - (nuevo) → II. Jerarquía Región → Tenant → Técnico
  - (nuevo) → III. Invariantes de Stock
  - (nuevo) → IV. Identidad y Unicidad de Series
  - (nuevo) → V. Integridad Transaccional (Todo o Nada)
  - (nuevo) → VI. Auditoría Inmutable y Trazabilidad
  - (nuevo) → VII. Autoridad del Reporte de Lari y Aprobación Humana
  - (nuevo) → VIII. Spec-Driven, Pruebas y Simplicidad Técnica
Added sections:
  - Restricciones Técnicas y de Dominio (incluye glosario)
  - Método de Trabajo y Puertas de Calidad
  - Governance desarrollado (procedimiento de enmienda, versionado y cumplimiento)
Removed sections: ninguno.
Excluded as non-applicable source content:
  - Los principios sueltos de "Python 3.12+ solo biblioteca estándar / JSON local / CLI"
    de `00-constitucion.md` (líneas 113-124), incompatibles con la arquitectura y el stack
    documentados (Django, PostgreSQL, Celery).
  - Duplicados de stack e idioma en `00-constitucion.md` (líneas 128-131), consolidados aquí.
Follow-up TODOs:
  - TODO(RATIFICATION_DATE): no consta la fecha original de adopción; `00-constitucion.md`
    solo registra la última modificación (2026-10-22). Completar manualmente.
  - Reconciliar la descripción SPA/REST/JWT de `docs/02-arquitectura-software/arquitectura.md`
    con las ADR-008 y ADR-015 (Django + HTMX + cookie de sesión). Es trabajo documental,
    no parte de esta enmienda.
-->

# Constitución del Sistema de Control de Materiales de Lari

## Core Principles

### I. Aislamiento Multitenant (NO NEGOCIABLE)

Todo dato y toda operación de un tenant DEBE filtrarse por el tenant obtenido de la sesión
autenticada, nunca de un parámetro enviado por el cliente. El aislamiento se aplica en el
backend y, cuando la base de datos lo permita, también en ella mediante seguridad por fila.
Un tenant NUNCA DEBE ver ni modificar datos de otro. El catálogo de materiales es la única
entidad compartida y su código es único global. Un intento de acceso a un dato ajeno DEBE
tratarse como dato inexistente, sin revelar su existencia ni su propietario. Suspender un
tenant DEBE bloquear su cuenta y sus operaciones, conservando sus datos y su stock.

**Rationale**: la plataforma aloja subcontratistas competidores sobre una base compartida;
una fuga entre tenants destruye la confianza del negocio y no es recuperable.

### II. Jerarquía Región → Tenant → Técnico

Cada tenant DEBE pertenecer a exactamente una región y operar con exactamente una cuenta
operativa. Cada región DEBE tener un almacén central, y Centro, Almacén y buzón DEBEN ser
parámetros de la región, no constantes del código. El Responsable de almacén DEBE tener
alcance de una sola región; el Administrador de plataforma tiene alcance global pero NUNCA
DEBE operar inventario, recojos, asignaciones, traspasos ni conciliaciones. Una serie
NUNCA DEBE cambiar de región durante su vida. El técnico es un actor pasivo: recibe
materiales y no inicia sesión.

**Rationale**: la operación real de Lari se organiza por región y almacén; el modelo de
permisos debe reflejar esa jerarquía para evitar cruces de alcance.

### III. Invariantes de Stock

Existen exactamente dos niveles de stock: el stock general del tenant y el stock por
técnico. Un material pasa del stock general al de un técnico solo mediante una asignación
confirmada por el almacén central. El stock general solo cambia por operaciones registradas
y auditadas, como recojos y devoluciones confirmadas; los traspasos NUNCA modifican el
stock general ni el total del tenant. NO SE DEBE asignar más de lo disponible, descontando
lo reservado en asignaciones pendientes. Los materiales seriados generan una fila por serie
con Cantidad 1; los no seriados generan una fila con la cantidad digitada por el tenant. El
lote es un atributo fijo e informativo del material y NO separa el stock. El stock inicial
de técnicos se carga una sola vez, el día de implementación, sin pasar por el stock general.
Un equipo dado de baja sale del stock disponible y NO se reasigna.

**Rationale**: estas invariantes son la definición misma del inventario; cualquier
excepción produce descuadres que la conciliación no puede explicar.

### IV. Identidad y Unicidad de Series

Cada serie DEBE tener 12 caracteres alfanuméricos (A-Z, 0-9), existir una sola vez en todo
el sistema y estar en un solo lugar a la vez. Sus estados operativos son Disponible,
Reservada y Asignada; una serie dada de baja NO vuelve al stock disponible. Solo se pueden
seleccionar series Disponibles del inventario general, nunca escribirlas manualmente en el
formulario de asignación. La unicidad global DEBE imponerse en la base de datos y el mensaje
de error DEBE ser idéntico en todos los casos para no revelar a qué tenant pertenece una
serie. La longitud y el formato de la serie son configurables, no constantes del código.

**Rationale**: la serie es la unidad de trazabilidad física del negocio; duplicarla o
revelar su ubicación rompe tanto el inventario como el aislamiento.

### V. Integridad Transaccional (Todo o Nada)

Toda operación que modifica stock DEBE ser transaccional. Formularios, traspasos y cargas
de Excel DEBEN aplicarse completos o no aplicarse; NUNCA DEBEN quedar a medias. La
solicitud de asignación, la reserva de series y el registro de envío DEBEN confirmarse en
la misma transacción. La aprobación de una conciliación DEBE aplicar todos sus ajustes en
una sola transacción y recalcular si el stock cambió desde la carga. Un error en cualquier
fila DEBE invalidar la operación completa.

**Rationale**: el stock no admite estados intermedios; una aplicación parcial obliga a
correcciones manuales no auditadas.

### VI. Auditoría Inmutable y Trazabilidad

Nada cambia el stock sin dejar rastro. Todo movimiento y ajuste DEBE registrar usuario,
fecha, valor anterior y valor nuevo. El libro de movimientos es de solo inserción: NO SE
DEBEN borrar movimientos ni ajustes, y toda corrección DEBE hacerse con un movimiento
nuevo. También DEBEN auditarse las altas y cambios de región, almacén, tenant, cuenta y rol,
así como las desactivaciones y suspensiones. La auditoría NUNCA DEBE almacenar contraseñas,
tokens ni secretos de segundo factor. Toda serie DEBE ser trazable durante toda su vida en
el sistema.

**Rationale**: la conciliación y las auditorías de Lari dependen de reconstruir qué pasó,
quién lo hizo y con qué valores.

### VII. Autoridad del Reporte de Lari y Aprobación Humana

En una conciliación aprobada, el reporte de Lari prevalece sobre el stock del sistema.
Cargar un reporte NO DEBE modificar stock; la conciliación se aprueba o rechaza completa y
requiere aprobación humana. Un técnico ausente del reporte DEBE ignorarse; un material
ausente de un técnico presente DEBE asumirse en 0. Las discrepancias de series DEBEN
mostrarse listando cada serie afectada, nunca ocultarse. El consumo de fungibles se calcula
solo con el remanente reportado por Lari; el sistema no mide consumo propio. No existe
integración directa con los sistemas de Lari: el intercambio es por Excel y correo.

**Rationale**: el reporte de Lari es la fuente contractual de verdad; el sistema es un
instrumento de control y conciliación, no un sustituto de esa fuente.

### VIII. Spec-Driven, Pruebas y Simplicidad Técnica

No se implementa ningún comportamiento que no esté en una spec aprobada; si falta una
decisión, se detiene el trabajo y se pregunta. `spec.md` describe qué y cómo se valida, sin
mencionar tecnología; `plan.md` describe cómo, dentro de la arquitectura definida. Las specs
referencian las reglas de dominio y no las repiten. Cada criterio de aceptación DEBE tener al
menos una prueba y cada tarea termina solo con sus pruebas en verde; está prohibido avanzar
con pruebas en rojo. Si al implementar se descubre que la spec o la arquitectura están mal,
se corrige el documento primero y luego el código. La simplicidad es obligatoria: Python
3.12+, Django LTS, PostgreSQL, Celery con Redis, openpyxl, HTMX y pytest; toda dependencia
adicional DEBE justificarse. La lógica de negocio vive en el backend y el núcleo debe ser
testeable sin la interfaz.

**Rationale**: el proyecto es académico y de alcance acotado; el exceso de tecnología y la
implementación sin spec son los principales riesgos de entrega.

## Restricciones Técnicas y de Dominio

- **Arquitectura**: monolito modular en capas, un solo despliegue de backend con worker
  separado, una sola base PostgreSQL y una transacción por operación de stock. Multitenencia
  con base y esquema compartidos; toda tabla operativa lleva `tenant_id` y cada tabla nueva
  declara si es de tenant o global. Las ADR aceptadas en
  `docs/01-analisis_de_sistema/07-decisiones_arquitectonicas.md` prevalecen sobre
  descripciones narrativas desactualizadas.
- **Acceso**: no existe autoregistro; el correo electrónico es único y es el identificador
  de inicio de sesión. Toda cuenta nueva se crea inactiva y recibe una invitación de un solo
  uso, con vencimiento. Una cuenta desactivada no puede iniciar sesión ni conservar una
  sesión activa. El Administrador de plataforma y el Responsable de almacén requieren
  segundo factor. Cada tenant tiene exactamente una cuenta y no crea subcuentas. El tenant y
  la región se obtienen de la sesión autenticada, nunca de un parámetro del cliente.
- **Formularios**: cada formulario de asignación o traspaso pertenece a un solo técnico (en
  el traspaso, un origen y un destino). El NIF se completa desde la lista de técnicos del
  tenant y no se escribe. Las series se eligen del inventario general del tenant (solo
  Disponibles). Descripción y lote se completan desde el catálogo al elegir el material.
  Movimiento, Centro y Almacén son fijos y se autorrellenan: Z31 para asignación, Z32 para
  desasignación; Centro y Almacén son parámetros de la región. El recojo se registra por
  formulario, no por Excel.
- **Contratos y configuración**: los formatos de Excel se definen en `04-contratos/`, no en
  el código. Son configuración, no constantes: la longitud y el formato de serie, los
  códigos Z31 y Z32, y los parámetros de región Centro, Almacén y buzón.
- **Idioma**: interfaz, documentación y nombres de código en español.
- **Operación**: los materiales no se borran en esta versión; se dan de baja o se
  desactivan. No se eliminan cuentas, tenants ni regiones. Las reglas de detalle viven en
  `03-reglas-de-dominio/` y las specs las referencian.

### Glosario del Dominio

| Término | Significado |
|---|---|
| Región | Agrupación de tenants que comparten un almacén central |
| Almacén central | Almacén de una región, de donde sus tenants recogen material |
| Tenant | Subcontratista que usa el sistema, perteneciente a una región |
| Técnico / NIF | Persona identificada con código LAxxxx |
| Seriado | Material cuyas unidades tienen serie individual de 12 caracteres |
| Recojo | Registro de materiales retirados del almacén central |
| Asignación | Entrega de materiales del stock del tenant a un técnico (Z31) |
| Desasignación | Cesión de materiales por parte de un técnico (Z32) |
| Traspaso | Movimiento de materiales de un técnico a otro del mismo tenant |
| Conciliación | Cuadre del stock contra el reporte de Lari, por región |
| Serie Disponible / Reservada / Asignada | Estados de una serie en el flujo de asignación |

## Método de Trabajo y Puertas de Calidad

- **Ciclo por funcionalidad**: spec → plan → tareas → implementación → validación.
- **Trazabilidad**: cada spec declara sus historias, requisitos y atributos de calidad, y
  referencia las reglas de dominio que aplica.
- **Puerta de pruebas**: cada criterio de aceptación tiene al menos una prueba; una tarea no
  se cierra con pruebas en rojo y no se avanza a la siguiente sin la validación completa.
- **Puerta de alcance**: no se implementa nada fuera de una spec aprobada ni se agregan
  funcionalidades "por si acaso". Si falta una decisión, se detiene el trabajo y se pregunta.
- **Documento primero**: si la implementación revela un error en la spec o en la
  arquitectura, se corrige el documento y luego el código.
- **Revisión de cumplimiento**: toda revisión DEBE verificar el aislamiento multitenant, las
  invariantes de stock, la auditoría y las pruebas. La complejidad adicional DEBE
  justificarse explícitamente.

## Governance

Esta constitución prevalece sobre cualquier otra práctica del proyecto. Las reglas de
dominio, los contratos y las ADR DEBEN ser compatibles con ella; ante conflicto, prevalece
este documento y se corrige el artefacto afectado.

**Procedimiento de enmienda**

1. Toda enmienda DEBE proponerse con motivación, texto concreto y análisis de impacto sobre
   las specs, las reglas de dominio, los contratos y las ADR existentes.
2. La enmienda DEBE revisarse y aprobarse antes de aplicar cambios en el código.
3. Aprobada la enmienda, se actualizan la versión y la fecha de última modificación, y se
   registran los cambios en el informe de impacto o en el historial del repositorio.
4. Los artefactos dependientes DEBEN actualizarse en la misma iniciativa; no se deja una
   spec o un plan contradiciendo la constitución vigente.

**Política de versionado**

- **MAJOR**: eliminación o redefinición incompatible de un principio o regla de gobierno.
- **MINOR**: nuevo principio, nueva sección o expansión material de la guía existente.
- **PATCH**: aclaraciones, correcciones de redacción o refinamientos no semánticos.

**Cumplimiento**

- Toda pull request y revisión DEBE verificar el cumplimiento de esta constitución.
- Una violación no justificada BLOQUEA la integración.
- La complejidad y las dependencias adicionales DEBEN justificarse en el plan.
- La guía operativa de detalle vive en `03-reglas-de-dominio/`, `04-contratos/` y las ADR;
  este documento fija los límites que esas fuentes no pueden contradecir.

**Version**: 1.3.0 | **Ratified**: TODO(RATIFICATION_DATE) | **Last Amended**: 2026-11-11
