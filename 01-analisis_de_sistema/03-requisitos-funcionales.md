# 03 - Requisitos Funcionales

Cada RF indica la spec donde se implementa. Los estados siguen la convención del documento de descubrimiento v3.1: **Confirmado** = lo dijo explícitamente el usuario. **Supuesto** = propuesta de diseño que hay que validar. **Pendiente** = aún no decidido.

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-01** | Cada tenant pertenece a exactamente una región | Confirmado | 001 |
| **RF-02** | Cada región tiene un almacén con Centro, Almacén y buzón de correo | Confirmado | 001 |
| **RF-03** | Un usuario de tenant solo ve y opera datos de su tenant | Confirmado | 001 |
| **RF-04** | La cuenta de Responsable de almacén ve y responde solo las solicitudes de su región | Supuesto | 001 |
| **RF-05** | El Responsable del tenant gestiona los usuarios de su tenant (ver RF-55) | Supuesto | 001 |
| **RF-51** | Solo ACT-02 crea regiones, almacenes, tenants y cuentas de Responsable del tenant y de Responsable de almacén | Supuesto | 001 |
| **RF-52** | Un tenant no opera hasta que tenga una cuenta de Responsable del tenant activa | Supuesto | 001 |
| **RF-53** | Una cuenta de Responsable de almacén pertenece a una sola región y no ve ni responde solicitudes de otra | Supuesto | 001 |
| **RF-54** | Al crear una cuenta, el sistema envía una invitación al correo del usuario para definir su contraseña | Supuesto | 001 |
| **RF-55** | El Responsable del tenant crea solo Operadores y Aprobadores de su tenant. No crea cuentas de otros tenants, de Almacén ni de plataforma | Supuesto | 001 |
| **RF-56** | Desactivar una cuenta retira su acceso de inmediato y conserva su historial | Supuesto | 001 |
| **RF-57** | Desactivar un tenant suspende sus operaciones. Sus datos y su stock se conservan sin cambios | Supuesto | 001 |
| **RF-58** | ACT-02 no registra recojos, asignaciones ni traspasos, y no aprueba conciliaciones | Supuesto | 001 |
| **RF-59** | Toda alta de región, tenant o cuenta, cambio de rol y desactivación queda registrada con usuario, fecha y valores | Supuesto | 001 |
| **RF-60** | Una cuenta pertenece a un solo tenant (roles de tenant) o a una sola región (Responsable de almacén). Las cuentas de ACT-02 no pertenecen a ninguno | Supuesto | 001 |

### Catálogo de materiales (spec 002)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-06** | Registrar material con código (11 dígitos), descripción, lote y tipo (seriado o no seriado) | Confirmado | 002 |
| **RF-07** | Al elegir un material en cualquier formulario, descripción y lote se completan solos y no son editables ahí | Confirmado | 002 |
| **RF-08** | Buscar materiales por código o descripción en el catálogo completo | Confirmado | 002 |
| **RF-09** | Editar descripción y lote solo el creador del material o ACT-02. El código no se edita | Supuesto | 002 |
| **RF-10** | El tipo no se puede cambiar si el material tiene movimientos en cualquier tenant | Supuesto | 002 |
| **RF-11** | Registrar quién creó o modificó cada material y cuándo | Confirmado | 002 |

### Técnicos (spec 003)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-12** | Registrar técnicos del tenant con su NIF (LAxxxx) | Confirmado | 003 |
| **RF-13** | Un técnico pertenece a un solo tenant | Supuesto | 003 |

### Recojo de materiales (spec 004)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-14** | Un tenant recoge solo en el almacén de su región | Confirmado | 004 |
| **RF-15** | Una serie pertenece a un tenant y no cambia de región | Confirmado | 004 |
| **RF-16** | El recojo se registra por formulario con varias líneas. Cada línea suma al stock general del tenant | Confirmado | 004 |
| **RF-17** | Las series se ingresan pegando texto o escaneando una por una, con vista previa por fila y su estado | Confirmado | 004 |
| **RF-18** | Cada serie se normaliza (mayúsculas, sin espacios) y debe tener 12 caracteres alfanuméricos | Confirmado | 004 |
| **RF-19** | Si alguna serie es inválida, duplicada o ya existe, no se guarda ningún recojo | Confirmado | 004 |

### Stock inicial de técnicos (spec 005)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-20** | Cargar una sola vez el stock inicial de cada técnico el día de implementación. La forma de carga (Excel o formulario) está pendiente | Confirmado (carga única), **Pendiente** (forma) | 005 |

### Solicitud de asignación (spec 006)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-21** | Crear una solicitud de asignación por técnico, con líneas de material | Confirmado | 006 |
| **RF-22** | En seriados, el tenant elige series Disponibles de su inventario. Cada serie es una fila con cantidad 1 | Confirmado | 006 |
| **RF-23** | En no seriados, la cantidad es un entero mayor que 0 y no supera el disponible, descontando lo reservado | Confirmado | 006 |
| **RF-24** | Al enviar la solicitud, sus series y cantidades pasan a Reservada | Confirmado | 006 |
| **RF-25** | El sistema genera el Excel de asignación con Movimiento Z31, Centro PR05 y Almacén BE03 autocompletados | Confirmado | 006 |
| **RF-26** | El NIF se completa desde el técnico elegido y no es editable | Confirmado | 006 |

### Envío y revisión del almacén (spec 007)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-27** | El Excel se envía por correo al buzón del almacén de la región, con reintentos si falla | Confirmado (envío), **Supuesto** (reintentos) | 007 |
| **RF-28** | Registrar cada envío: destinatario, fecha y archivo exacto enviado | Supuesto | 007 |
| **RF-29** | El Responsable de almacén confirma o rechaza la solicitud dentro del sistema con un comentario del error si se rechaza | Confirmado | 007 |
| **RF-30** | Estados de la solicitud: Borrador, Enviada, Confirmada, Rechazada, Cancelada | Supuesto | 007 |
| **RF-31** | Al rechazar, las series vuelven a Disponible | Confirmado | 007 |

### Confirmación y actualización de stock (spec 008)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-32** | Al confirmar, las series pasan a Asignada al técnico, el stock del técnico sube y el stock general baja | Confirmado | 008 |

### Traspaso entre técnicos (spec 009)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-33** | Un traspaso mueve materiales entre técnicos del mismo tenant, con un Excel de dos hojas: Desasignación (Z32) y Asignación (Z31) | Confirmado | 009 |
| **RF-34** | El técnico origen y el destino no pueden ser el mismo | Supuesto | 009 |
| **RF-35** | El origen solo puede ceder materiales y series que tiene asignados, descontando lo reservado | Supuesto | 009 |
| **RF-36** | Lo que sale debe cuadrar con lo que entra, por material y por serie. Si no cuadra, se rechaza todo | Supuesto | 009 |
| **RF-37** | El Responsable de almacén acepta o rechaza el traspaso. Al aceptar, las series cambian de técnico. Al rechazar, no cambia nada | Confirmado (acepta o rechaza), **Supuesto** (efecto) | 009 |
| **RF-38** | Un traspaso no modifica el stock general del tenant | Confirmado | 009 |

### Conciliación con el reporte de Lari (spec 010)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-39** | Cargar el reporte de Lari crea una conciliación "En revisión" con las diferencias, sin cambiar el stock | Confirmado | 010 |
| **RF-40** | Solo puede haber una conciliación en revisión por tenant a la vez | Supuesto | 010 |
| **RF-41** | Reglas de ausencia: un técnico que no aparece en el reporte se ignora. Un material que falta a un técnico presente se asume en 0 | Confirmado | 010 |
| **RF-42** | Las diferencias de series se muestran en dos grupos, con el listado de cada serie: "en reporte, no en sistema" y "en sistema, no en reporte" | Confirmado | 010 |
| **RF-43** | La aprobación bloquea si hay materiales del reporte que no existen en el catálogo | Supuesto | 010 |
| **RF-44** | El Aprobador aprueba o rechaza la conciliación completa (todo o nada) | Confirmado | 010 |
| **RF-45** | Al aprobar, las series del reporte que no existen en el sistema se crean en el técnico, y las que el sistema tiene y el reporte no traen se retiran | Supuesto | 010 |
| **RF-46** | Al aprobar, cada ajuste registra valor anterior y valor nuevo | Confirmado | 010 |
| **RF-47** | Si el stock de un técnico cambió entre la carga y la aprobación, el sistema recalcula y exige revisar de nuevo | Supuesto | 010 |
| **RF-48** | Se rechaza el archivo completo si contiene técnicos que no pertenecen al tenant o a la región del reporte | Supuesto | 010 |

### Auditoría (transversal)

| ID | Requisito | Estado | Spec |
|---|---|---|---|
| **RF-49** | Todo movimiento y ajuste de stock registra usuario, fecha, valor anterior y valor nuevo | Confirmado | Transversal |
| **RF-50** | No se borran movimientos. Una corrección se hace con un movimiento nuevo | Confirmado | Transversal |

---