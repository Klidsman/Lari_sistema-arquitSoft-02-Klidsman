# Notas de descubrimiento: Sistema de gestión de materiales de Lari

Versión: 3.1 · Fecha: [fecha]
Propósito: fuente única para extraer el análisis del sistema (actores, historias, requisitos, restricciones y drivers arquitectónicos). No es una spec ni reemplaza la constitución (`00-principios.md`).

Cambios respecto a la versión 3.0: el sistema tiene cuatro actores (Tenant, Administrador de plataforma, Almacén y Técnico); Lari queda como sistema externo; la cuenta de Responsable de almacén es el usuario con el que opera el actor Almacén; la pregunta 10 queda resuelta; y RNF-20 se redacta sin tecnología específica, en línea con la regla 5.

## Reglas para quien extrae el análisis

1. Extrae solo ítems con estado **Confirmado** o **Supuesto**. Los **Pendiente** van a la sección 10 como preguntas, nunca como requisitos.
2. Usa los IDs de este documento: ACT-, HU-, RF-, RNF-, RES-, DRV-. No inventes IDs. Si falta algo, repórtalo como hueco.
3. Conserva el ID y el estado de cada ítem al extraerlo.
4. La sección 12 (ideas no confirmadas) no se extrae como requisito.
5. Este documento no define tecnología. El stack vive en la constitución y en los ADR.
6. Usa los nombres de rol de este documento: Operador, Aprobador, Responsable del tenant, Responsable de almacén, Administrador de plataforma. No uses "administrador" para los roles de tenant ni de almacén.

**Convención de estados:** Confirmado = lo dijo explícitamente el usuario. Supuesto = propuesta de diseño que hay que validar. Pendiente = aún no decidido.

---

## 1. Contexto y alcance

Lari es una empresa de telefonía que trabaja con subcontratistas (tenants). Cada subcontratista controla los materiales que recibe del almacén central de su región, los asigna a sus técnicos, los traspasa entre ellos y cuadra su stock con los reportes de Lari.

**Dentro del alcance:** tenants y regiones, cuentas de acceso, catálogo de materiales, técnicos, recojo, stock inicial, asignación, traspaso, conciliación y auditoría.

**Fuera del alcance:** traspasos entre tenants; cambio de región de una serie; generación de reportes por parte de Lari; devoluciones de técnico al tenant (pendiente, ver sección 10); carga masiva de materiales por Excel.

**Sistema externo:** Lari envía reportes de conciliación en Excel por región y recibe por correo los Excel de asignación y traspaso. Lari no es actor del sistema: no opera la plataforma. **[Confirmado]**

Volúmenes de referencia: 100 tenants, 10 a 20 técnicos por tenant, 1.000 a 2.000 técnicos en total. **[Supuesto]**

Organización: cada región tiene un almacén central. Un tenant pertenece a una sola región. **[Confirmado]**

---

## 2. Actores

| ID | Actor | Alcance | Hace | No hace | Estado |
|---|---|---|---|---|---|
| ACT-01 | Tenant (usuario del subcontratista) | Tenant | Según su rol (ver tabla siguiente): registra recojos, crea asignaciones y traspasos, carga reportes, aprueba o rechaza conciliaciones, gestiona técnicos y usuarios de su tenant | Ver datos de otro tenant; responder solicitudes del almacén | Supuesto (actor) |
| ACT-02 | Administrador de plataforma (superusuario) | Global | Crea regiones, almacenes, tenants y las cuentas de Responsable del tenant y de Responsable de almacén. Gestiona el catálogo compartido | Registrar recojos, asignar, traspasar, aprobar conciliaciones | Supuesto (actor y alcance) |
| ACT-03 | Almacén | Región | Confirma o rechaza solicitudes y traspasos de su región | Ver solicitudes de otras regiones; operar inventario de tenants | Supuesto (actor) |
| ACT-04 | Técnico (LAxxxx) | Tenant | Recibe materiales | Usar el sistema (actor pasivo, no genera HU) | Confirmado |

**Almacén (ACT-03)** es la entidad que recibe y responde las solicitudes de su región. Quien la opera en el sistema es la cuenta de Responsable de almacén, que crea ACT-02 (RF-53, RES-19). Esa cuenta no tiene rol de tenant.

### Roles dentro del tenant (ACT-01)

Son permisos dentro del tenant, no actores separados. Cada usuario del tenant tiene un solo rol. **[Supuesto, pregunta 14]**

| Rol | Puede | No puede |
|---|---|---|
| Operador | Registrar recojos, crear asignaciones y traspasos, cargar reportes | Aprobar conciliaciones, crear usuarios |
| Aprobador | Aprobar o rechazar conciliaciones completas | Crear asignaciones, registrar recojos |
| Responsable del tenant | Crear técnicos y las cuentas de Operador y Aprobador de su tenant | Aprobar conciliaciones, operar inventario, crear cuentas de otros tenants, de Almacén o de plataforma |

### Cuentas de administración

Las cuentas de Responsable del tenant y de Responsable de almacén las crea ACT-02. Son cuentas de acceso para administrar personal, no para controlar el sistema completo. **[Supuesto]**

---

## 3. Historias de usuario

| ID | Historia | RF relacionados | Estado |
|---|---|---|---|
| HU-01 | Como ACT-02 quiero registrar regiones y su almacén con Centro, Almacén y buzón, para que cada región tenga su punto de entrega | RF-01, RF-02, RF-51 | Supuesto |
| HU-02 | Como Responsable del tenant (ACT-01) quiero registrar a mis técnicos con su NIF, para poder asignarles materiales | RF-12, RF-13 | Confirmado |
| HU-03 | Como Responsable del tenant (ACT-01) quiero crear Operadores y Aprobadores de mi tenant, para que cada persona haga solo lo que le corresponde | RF-05, RF-55 | Supuesto |
| HU-04 | Como Responsable de almacén (ACT-03) quiero ver solo las solicitudes de mi región, para responderlas | RF-04 | Supuesto |
| HU-05 | Como Operador (ACT-01) quiero registrar un material nuevo con código, descripción, lote y tipo, para usarlo en recojos y asignaciones | RF-06, RF-11 | Confirmado |
| HU-06 | Como Operador (ACT-01) quiero buscar materiales por código o descripción, para elegirlos en los formularios | RF-07, RF-08 | Confirmado |
| HU-07 | Como creador del material o ACT-02 quiero editar su descripción o lote, para corregir datos de Lari | RF-09, RF-10 | Supuesto |
| HU-08 | Como Operador (ACT-01) quiero registrar los materiales que recogí del almacén de mi región, para sumarlos a mi stock general | RF-14, RF-15, RF-16 | Confirmado |
| HU-09 | Como Operador (ACT-01) quiero pegar o escanear series y verlas fila por fila antes de guardar, para no digitarlas una a una | RF-17, RF-18, RF-19 | Confirmado |
| HU-10 | Como Responsable del tenant (ACT-01) quiero cargar una sola vez el stock inicial de cada técnico, para partir de lo que ya tienen | RF-20 | Confirmado |
| HU-11 | Como Operador (ACT-01) quiero crear una solicitud de asignación para un técnico, eligiendo materiales y series disponibles, para enviarla al almacén | RF-21, RF-22, RF-23, RF-24, RF-26 | Confirmado |
| HU-12 | Como Operador (ACT-01) quiero que el sistema genere el Excel de asignación con los códigos fijos y los datos del catálogo, para no digitarlo | RF-22, RF-25 | Confirmado |
| HU-13 | Como Operador (ACT-01) quiero que el Excel se envíe desde el sistema al buzón del almacén de mi región, para no hacerlo a mano | RF-27, RF-28 | Confirmado |
| HU-14 | Como Responsable de almacén (ACT-03) quiero confirmar o rechazar una solicitud, para controlar lo que se entrega | RF-29, RF-31 | Confirmado |
| HU-15 | Como Operador (ACT-01) quiero ver el estado de mis solicitudes, para saber cuáles faltan por responder | RF-30 | Supuesto |
| HU-16 | Como Operador (ACT-01) quiero que una solicitud confirmada actualice el stock del técnico, para tener el inventario real | RF-32 | Confirmado |
| HU-17 | Como Operador (ACT-01) quiero trasladar materiales de un técnico a otro del mismo tenant con un Excel de dos hojas, para reasignar sin pasar por el stock general | RF-33, RF-34, RF-35, RF-36, RF-38 | Confirmado |
| HU-18 | Como Responsable de almacén (ACT-03) quiero aceptar o rechazar un traspaso completo, para validar el movimiento | RF-37 | Confirmado (decisión), Supuesto (efecto) |
| HU-19 | Como Operador (ACT-01) quiero cargar el reporte de Lari de mi región sin que cambie el stock, para revisarlo antes | RF-39, RF-40, RF-48 | Confirmado |
| HU-20 | Como Aprobador (ACT-01) quiero aprobar o rechazar la conciliación completa, para que el stock cambie solo con mi aprobación | RF-43, RF-44, RF-45, RF-46, RF-47 | Confirmado |
| HU-21 | Como Operador (ACT-01) quiero ver las diferencias por técnico y material, y las series alertadas con su listado, para decidir | RF-41, RF-42 | Confirmado |
| HU-22 | Como Responsable del tenant (ACT-01) quiero consultar quién cambió el stock y cuándo, para revisar diferencias | RF-49, RF-50 | Supuesto |
| HU-23 | Como ACT-02 quiero registrar un tenant asignado a una región, para ubicar sus técnicos y solicitudes | RF-01, RF-51 | Supuesto |
| HU-24 | Como ACT-02 quiero crear la cuenta de Responsable del tenant, para que pueda empezar a operar | RF-52, RF-54 | Supuesto |
| HU-25 | Como ACT-02 quiero crear las cuentas de Responsable de almacén de cada región, limitadas a esa región, para que respondan sus solicitudes | RF-53, RF-54 | Supuesto |
| HU-26 | Como ACT-02 quiero desactivar cuentas y tenants, para retirar el acceso de forma inmediata | RF-56, RF-57 | Supuesto |
| HU-27 | Como ACT-02 quiero consultar el registro de altas, cambios de rol y desactivaciones, para auditar los accesos | RF-59 | Supuesto |

---

## 4. Requisitos funcionales

Cada RF indica la spec donde se implementa.

### Acceso, regiones y cuentas (spec 001)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-01 | Cada tenant pertenece a exactamente una región | Confirmado | 001 |
| RF-02 | Cada región tiene un almacén con Centro, Almacén y buzón de correo | Confirmado | 001 |
| RF-03 | Un usuario de tenant solo ve y opera datos de su tenant | Confirmado | 001 |
| RF-04 | La cuenta de Responsable de almacén ve y responde solo las solicitudes de su región | Supuesto | 001 |
| RF-05 | El Responsable del tenant gestiona los usuarios de su tenant (ver RF-55) | Supuesto | 001 |
| RF-51 | Solo ACT-02 crea regiones, almacenes, tenants y cuentas de Responsable del tenant y de Responsable de almacén | Supuesto | 001 |
| RF-52 | Un tenant no opera hasta que tenga una cuenta de Responsable del tenant activa | Supuesto | 001 |
| RF-53 | Una cuenta de Responsable de almacén pertenece a una sola región y no ve ni responde solicitudes de otra | Supuesto | 001 |
| RF-54 | Al crear una cuenta, el sistema envía una invitación al correo del usuario para definir su contraseña | Supuesto | 001 |
| RF-55 | El Responsable del tenant crea solo Operadores y Aprobadores de su tenant. No crea cuentas de otros tenants, de Almacén ni de plataforma | Supuesto | 001 |
| RF-56 | Desactivar una cuenta retira su acceso de inmediato y conserva su historial | Supuesto | 001 |
| RF-57 | Desactivar un tenant suspende sus operaciones. Sus datos y su stock se conservan sin cambios | Supuesto | 001 |
| RF-58 | ACT-02 no registra recojos, asignaciones ni traspasos, y no aprueba conciliaciones | Supuesto | 001 |
| RF-59 | Toda alta de región, tenant o cuenta, cambio de rol y desactivación queda registrada con usuario, fecha y valores | Supuesto | 001 |
| RF-60 | Una cuenta pertenece a un solo tenant (roles de tenant) o a una sola región (Responsable de almacén). Las cuentas de ACT-02 no pertenecen a ninguno | Supuesto | 001 |

### Catálogo de materiales (spec 002)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-06 | Registrar material con código (11 dígitos), descripción, lote y tipo (seriado o no seriado) | Confirmado | 002 |
| RF-07 | Al elegir un material en cualquier formulario, descripción y lote se completan solos y no son editables ahí | Confirmado | 002 |
| RF-08 | Buscar materiales por código o descripción en el catálogo completo | Confirmado | 002 |
| RF-09 | Editar descripción y lote solo el creador del material o ACT-02. El código no se edita | Supuesto | 002 |
| RF-10 | El tipo no se puede cambiar si el material tiene movimientos en cualquier tenant | Supuesto | 002 |
| RF-11 | Registrar quién creó o modificó cada material y cuándo | Confirmado | 002 |

### Técnicos (spec 003)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-12 | Registrar técnicos del tenant con su NIF (LAxxxx) | Confirmado | 003 |
| RF-13 | Un técnico pertenece a un solo tenant | Supuesto | 003 |

### Recojo de materiales (spec 004)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-14 | Un tenant recoge solo en el almacén de su región | Confirmado | 004 |
| RF-15 | Una serie pertenece a un tenant y no cambia de región | Confirmado | 004 |
| RF-16 | El recojo se registra por formulario con varias líneas. Cada línea suma al stock general del tenant | Confirmado | 004 |
| RF-17 | Las series se ingresan pegando texto o escaneando una por una, con vista previa por fila y su estado | Confirmado | 004 |
| RF-18 | Cada serie se normaliza (mayúsculas, sin espacios) y debe tener 12 caracteres alfanuméricos | Confirmado | 004 |
| RF-19 | Si alguna serie es inválida, duplicada o ya existe, no se guarda ningún recojo | Confirmado | 004 |

### Stock inicial de técnicos (spec 005)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-20 | Cargar una sola vez el stock inicial de cada técnico el día de implementación. La forma de carga (Excel o formulario) está pendiente | Confirmado (carga única), Pendiente (forma) | 005 |

### Solicitud de asignación (spec 006)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-21 | Crear una solicitud de asignación por técnico, con líneas de material | Confirmado | 006 |
| RF-22 | En seriados, el tenant elige series Disponibles de su inventario. Cada serie es una fila con cantidad 1 | Confirmado | 006 |
| RF-23 | En no seriados, la cantidad es un entero mayor que 0 y no supera el disponible, descontando lo reservado | Confirmado | 006 |
| RF-24 | Al enviar la solicitud, sus series y cantidades pasan a Reservada | Confirmado | 006 |
| RF-25 | El sistema genera el Excel de asignación con Movimiento Z31, Centro PR05 y Almacén BE03 autocompletados | Confirmado | 006 |
| RF-26 | El NIF se completa desde el técnico elegido y no es editable | Confirmado | 006 |

### Envío y revisión del almacén (spec 007)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-27 | El Excel se envía por correo al buzón del almacén de la región, con reintentos si falla | Confirmado (envío), Supuesto (reintentos) | 007 |
| RF-28 | Registrar cada envío: destinatario, fecha y archivo exacto enviado | Supuesto | 007 |
| RF-29 | El Responsable de almacén confirma o rechaza la solicitud dentro del sistema con un comentario del error si se rechaza | Confirmado | 007 |
| RF-30 | Estados de la solicitud: Borrador, Enviada, Confirmada, Rechazada, Cancelada | Supuesto | 007 |
| RF-31 | Al rechazar, las series vuelven a Disponible | Confirmado | 007 |

### Confirmación y actualización de stock (spec 008)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-32 | Al confirmar, las series pasan a Asignada al técnico, el stock del técnico sube y el stock general baja | Confirmado | 008 |

### Traspaso entre técnicos (spec 009)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-33 | Un traspaso mueve materiales entre técnicos del mismo tenant, con un Excel de dos hojas: Desasignación (Z32) y Asignación (Z31) | Confirmado | 009 |
| RF-34 | El técnico origen y el destino no pueden ser el mismo | Supuesto | 009 |
| RF-35 | El origen solo puede ceder materiales y series que tiene asignados, descontando lo reservado | Supuesto | 009 |
| RF-36 | Lo que sale debe cuadrar con lo que entra, por material y por serie. Si no cuadra, se rechaza todo | Supuesto | 009 |
| RF-37 | El Responsable de almacén acepta o rechaza el traspaso. Al aceptar, las series cambian de técnico. Al rechazar, no cambia nada | Confirmado (acepta o rechaza), Supuesto (efecto) | 009 |
| RF-38 | Un traspaso no modifica el stock general del tenant | Confirmado | 009 |

### Conciliación con el reporte de Lari (spec 010)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-39 | Cargar el reporte de Lari crea una conciliación "En revisión" con las diferencias, sin cambiar el stock | Confirmado | 010 |
| RF-40 | Solo puede haber una conciliación en revisión por tenant a la vez | Supuesto | 010 |
| RF-41 | Reglas de ausencia: un técnico que no aparece en el reporte se ignora. Un material que falta a un técnico presente se asume en 0 | Confirmado | 010 |
| RF-42 | Las diferencias de series se muestran en dos grupos, con el listado de cada serie: "en reporte, no en sistema" y "en sistema, no en reporte" | Confirmado | 010 |
| RF-43 | La aprobación bloquea si hay materiales del reporte que no existen en el catálogo | Supuesto | 010 |
| RF-44 | El Aprobador aprueba o rechaza la conciliación completa (todo o nada) | Confirmado | 010 |
| RF-45 | Al aprobar, las series del reporte que no existen en el sistema se crean en el técnico, y las que el sistema tiene y el reporte no traen se retiran | Supuesto | 010 |
| RF-46 | Al aprobar, cada ajuste registra valor anterior y valor nuevo | Confirmado | 010 |
| RF-47 | Si el stock de un técnico cambió entre la carga y la aprobación, el sistema recalcula y exige revisar de nuevo | Supuesto | 010 |
| RF-48 | Se rechaza el archivo completo si contiene técnicos que no pertenecen al tenant o a la región del reporte | Supuesto | 010 |

### Auditoría (transversal)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| RF-49 | Todo movimiento y ajuste de stock registra usuario, fecha, valor anterior y valor nuevo | Confirmado | Transversal |
| RF-50 | No se borran movimientos. Una corrección se hace con un movimiento nuevo | Confirmado | Transversal |

---

## 5. Requisitos no funcionales

Categorías según ISO/IEC 25010. Las medidas marcadas como pendientes deben definirse antes de cerrar el análisis.

| ID | Categoría | Requisito | Medida | Estado |
|---|---|---|---|---|
| RNF-01 | Seguridad | Un tenant nunca ve ni modifica datos de otro tenant, con excepción del catálogo | Prueba de aislamiento en cada spec que toque datos de tenant | Confirmado |
| RNF-02 | Seguridad | El tenant_id nunca se acepta desde el cliente (formulario, URL o Excel); sale de la identidad autenticada | Prueba: un tenant_id ajeno en la petición no cambia el tenant de la operación | Confirmado |
| RNF-03 | Seguridad | La base de datos refuerza el aislamiento por tenant con seguridad por fila | Prueba: una consulta sin tenant definido no devuelve filas | Supuesto |
| RNF-04 | Integridad | Toda operación de stock se aplica completa o no se aplica | Prueba de fallo a mitad de operación: no queda estado parcial | Confirmado |
| RNF-05 | Integridad | Cada serie existe una sola vez en todo el sistema. El mensaje de duplicado no revela tenant ni región | Restricción única global; mensaje idéntico en todos los casos | Confirmado |
| RNF-06 | Integridad | Ninguna operación deja stock negativo, ni una serie en dos estados a la vez | Restricciones en base de datos y pruebas de concurrencia | Confirmado |
| RNF-07 | Auditabilidad | El 100% de movimientos y ajustes queda registrado con usuario, fecha y valores | Verificación de registros por operación | Confirmado |
| RNF-08 | Trazabilidad | Se guarda el Excel original de cada envío y carga, con su huella (hash) para detectar duplicados | Un archivo guardado por envío y carga | Supuesto |
| RNF-09 | Rendimiento | Las conciliaciones de los 100 tenants en la franja nocturna no afectan la operación diaria | Medida pendiente: tiempo máximo y franja | Pendiente (medida) |
| RNF-10 | Rendimiento | La vista previa de series responde con fluidez aunque se peguen miles de filas | Medida pendiente: tiempo máximo de respuesta | Pendiente (medida) |
| RNF-11 | Escalabilidad | Soportar 100 tenants, 1.000 a 2.000 técnicos y unos 3 a 4 millones de movimientos al año | Volumen de referencia de la sección 1 | Supuesto |
| RNF-12 | Fiabilidad | Un Excel enviado al almacén no se pierde aunque el correo falle; se reintenta | Ninguna solicitud enviada queda sin registro de envío | Supuesto |
| RNF-13 | Mantenibilidad | Las reglas de negocio se pueden probar sin depender del Excel ni del correo | Pruebas de reglas sin infraestructura | Supuesto |
| RNF-14 | Capacidad de prueba | Cada criterio de aceptación de una spec tiene al menos una prueba automatizada | Una prueba por criterio | Confirmado |
| RNF-15 | Configurabilidad | Códigos Z31, Z32, PR05, BE03, longitud de serie y parámetros de región son configuración, no constantes | Cambio sin modificar código | Confirmado |
| RNF-16 | Compatibilidad | Columnas y formato de los Excel idénticos a los de Lari | Validación contra el ejemplo real | Confirmado |
| RNF-17 | Usabilidad | El ingreso de series no exige digitarlas una a una, y los errores se muestran por fila antes de guardar | Ver RF-17 y RF-19 | Confirmado |
| RNF-18 | Usabilidad | Los datos del catálogo y del técnico se completan solos en los formularios | Ver RF-07 y RF-26 | Confirmado |
| RNF-19 | Idioma | Interfaz y documentación en español | — | Confirmado |
| RNF-20 | Seguridad | Los privilegios de ACT-02 son un rol con alcance explícito y limitado. Ningún mecanismo técnico que omita los permisos (superusuario de base de datos o de framework) puede usarse para operar datos de tenants | Prueba: la cuenta de ACT-02 no puede registrar recojos, asignar ni aprobar conciliaciones, aunque se fuerce la petición | Supuesto |
| RNF-21 | Seguridad | Las cuentas de ACT-02 y de Responsable de almacén requieren autenticación de dos factores | Prueba de inicio de sesión sin segundo factor | Supuesto |

---

## 6. Restricciones

| ID | Restricción | Estado |
|---|---|---|
| RES-01 | Serie de 12 caracteres alfanuméricos. La longitud es fija; los caracteres pueden variar en equipos nuevos | Confirmado |
| RES-02 | Código de material de 11 dígitos | Confirmado |
| RES-03 | Movimientos fijos del formato Lari: Z31 (asignación) y Z32 (desasignación) | Confirmado |
| RES-04 | Centro PR05 y Almacén BE03 son iguales en todas las regiones por ahora | Confirmado |
| RES-05 | Un tenant recoge solo en el almacén de su región | Confirmado |
| RES-06 | No existen traspasos entre tenants | Confirmado |
| RES-07 | Una serie no cambia de región | Confirmado |
| RES-08 | El recojo se registra por formulario, no por Excel | Confirmado |
| RES-09 | La entrega al almacén se hace por Excel enviado por correo al buzón regional | Confirmado |
| RES-10 | Lari envía los reportes de conciliación por región, en Excel | Confirmado (formato pendiente, ver sección 10) |
| RES-11 | El catálogo de materiales es compartido por todos los tenants y su código es único global | Confirmado |
| RES-12 | El lote es un atributo fijo del material y es informativo; no separa el stock | Confirmado |
| RES-13 | Los formularios no permiten editar NIF, Movimiento, Centro, Almacén, lote ni descripción | Confirmado |
| RES-14 | Los movimientos y ajustes no se borran | Confirmado |
| RES-15 | No hay integración directa con los sistemas de Lari; el intercambio es por Excel y correo | Supuesto |
| RES-16 | El stock inicial de técnicos se carga una sola vez, el día de implementación | Confirmado |
| RES-17 | Los materiales no se borran en esta versión | Supuesto |
| RES-18 | Solo ACT-02 crea cuentas de Responsable del tenant y de Responsable de almacén | Confirmado |
| RES-19 | Una cuenta de Responsable de almacén tiene alcance de una sola región | Supuesto |

---

## 7. Drivers arquitectónicos

Son las necesidades de negocio y de calidad que más condicionan la arquitectura. Cada driver indica los RNF y RES que lo sostienen.

| ID | Driver | Efecto en la arquitectura | Sostenido por |
|---|---|---|---|
| DRV-01 | Aislamiento multitenant con una excepción (catálogo compartido) | Modelo con tenant_id en las tablas operativas, aislamiento en varias capas, pruebas obligatorias | RNF-01, RNF-02, RNF-03, RNF-20, RES-11 |
| DRV-02 | Consistencia transaccional del stock | Operaciones de stock atómicas; estructura modular con reglas de negocio en el núcleo | RNF-04, RNF-06 |
| DRV-03 | Unicidad global de series sin revelar el tenant | Restricción única global; validación que devuelve siempre el mismo mensaje | RNF-05, RES-01 |
| DRV-04 | Auditoría inmutable | Libro de movimientos de solo inserción; las correcciones son movimientos nuevos | RNF-07, RES-14 |
| DRV-05 | Picos nocturnos de conciliación para 100 tenants | Procesos de trabajo separados de la web, con cola y límites de concurrencia por tenant | RNF-09, RNF-11 |
| DRV-06 | Entrega fiable al almacén por correo | Registro del envío en la misma operación que la solicitud, y envío con reintentos | RNF-12, RES-09 |
| DRV-07 | Jerarquía región → tenant → técnico | Parámetros por región (Centro, Almacén, buzón); permisos por región para Responsable de almacén; alta de cuentas centralizada | RF-01, RF-02, RF-04, RF-53, RES-05 |
| DRV-08 | Formatos externos fijos de Lari | Adaptadores de entrada y salida separados del dominio; contratos de Excel versionados | RNF-15, RNF-16, RES-03, RES-10 |
| DRV-09 | Operación en campo y de digitación intensiva | Formularios con autocompletado y validación por fila; ingreso de series por pegado | RNF-17, RNF-18, RES-08 |
| DRV-10 | Volumen y crecimiento de 100 tenants | Índices compuestos que empiezan por tenant; esquema compartido | RNF-11 |
| DRV-11 | Administración centralizada de accesos y separación de funciones | Rol de plataforma separado del dominio operativo; flujo de invitación; auditoría de la administración | RF-51, RF-55, RF-58, RF-59, RNF-20, RNF-21, RES-18 |

---

## 8. Trazabilidad hacia las specs

| Spec | HU | RF | RNF | RES | DRV |
|---|---|---|---|---|---|
| 001 Tenants, regiones y acceso | 01, 03, 04, 23–27 | 01–05, 51–60 | 01, 02, 03, 20, 21 | 05, 18, 19 | 01, 07, 11 |
| 002 Materiales | 05, 06, 07 | 06–11 | 05, 14, 18 | 02, 11, 12, 13 | 01 |
| 003 Técnicos | 02 | 12, 13 | 01 | — | 01 |
| 004 Recojo | 08, 09 | 14–19 | 04, 05, 17 | 01, 05, 07, 08 | 02, 03 |
| 005 Stock inicial | 10 | 20 | 04, 07 | 16 | 02 |
| 006 Solicitud de asignación | 11, 12 | 21–26 | 04, 06, 16 | 03, 04, 13 | 02, 08 |
| 007 Envío y revisión | 13, 14, 15 | 27–31 | 12, 07 | 09 | 06 |
| 008 Confirmación y stock | 16 | 32 | 04, 06, 07 | — | 02, 04 |
| 009 Traspaso | 17, 18 | 33–38 | 04, 06, 07 | 06, 13 | 02, 04 |
| 010 Conciliación | 19, 20, 21 | 39–48 | 04, 05, 06, 07, 08, 09 | 10 | 03, 05 |
| Auditoría transversal | 22 | 49, 50 | 07 | 14 | 04 |

---

## 9. Glosario

El glosario completo está en la sección 7 de `00-principios.md`. Los términos nuevos de este documento son:

- **Región:** agrupación de tenants que comparten un almacén central.
- **Solicitud:** formulario de asignación o traspaso enviado al almacén.
- **Conciliación:** cuadre del stock del sistema contra el reporte de Lari, con aprobación del tenant.
- **Responsable del tenant:** usuario del tenant que gestiona técnicos y cuentas de Operador y Aprobador. No controla el sistema completo.
- **Responsable de almacén:** usuario de la región que confirma o rechaza solicitudes y traspasos de su almacén.
- **Administrador de plataforma (superusuario):** actor ACT-02. Crea regiones, almacenes, tenants y cuentas de Responsable. No opera inventario.

---

## 11. Fuentes

- Conversación de diseño con el usuario (decisiones de las secciones 2 a 10).
- Excel de asignación de ejemplo, con materiales seriados y no seriados, y las filas Z32 de LA6790 y LA8749.
- Excel con las columnas de movimiento (Z31 y Z32), centro y almacén.

---

## 12. Ideas no confirmadas (no extraer como requisitos)

- Historial por serie (kardex).
- Devoluciones de técnico al tenant.
- Panel de control.
- Reportes exportables.
- Captura de series con la cámara del celular.
- Validación previa del administrador para materiales nuevos.
- Detección de descripciones parecidas con códigos distintos.
