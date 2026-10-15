# 03 - Requisitos Funcionales

Cada RF indica la spec donde se implementa. Los estados siguen la convención del documento de descubrimiento v3.1:

### Acceso, regiones y cuentas (spec 001)

| ID | Requisito |
|---|---|
| **RF-01** | Cada tenant pertenece a exactamente una región |
| **RF-02** | Cada región tiene un almacén con Centro, Almacén y buzón de correo |
| **RF-03** | Un usuario de tenant solo ve y opera datos de su tenant |
| **RF-04** | La cuenta de Responsable de almacén ve y responde solo las solicitudes de su región |
| **RF-05** | El Responsable del tenant gestiona los usuarios de su tenant (ver RF-55) |
| **RF-51** | Solo ACT-02 crea regiones, almacenes, tenants y cuentas de Responsable del tenant y de Responsable de almacén |
| **RF-52** | Un tenant no opera hasta que tenga una cuenta de Responsable del tenant activa |
| **RF-53** | Una cuenta de Responsable de almacén pertenece a una sola región y no ve ni responde solicitudes de otra |
| **RF-54** | Al crear una cuenta, el sistema envía una invitación al correo del usuario para definir su contraseña |
| **RF-55** | El tenant asigna y concilia reportes |
| **RF-56** | Desactivar una cuenta retira su acceso de inmediato y conserva su historial |
| **RF-57** | Desactivar un tenant suspende sus operaciones. Sus datos y su stock se conservan sin cambios |
| **RF-58** | ACT-02 no registra recojos, asignaciones ni traspasos, y no aprueba conciliaciones |
| **RF-59** | Toda alta de región, tenant o cuenta, cambio de rol y desactivación queda registrada con usuario, fecha y valores |
| **RF-60** | Una cuenta pertenece a un solo tenant (roles de tenant) o a una sola región (Responsable de almacén). Las cuentas de ACT-02 no pertenecen a ninguno |

### Catálogo de materiales (spec 002)

| ID | Requisito |
|---|---|
| **RF-06** | Registrar material con código (11 dígitos), descripción, lote y tipo (seriado o no seriado) |
| **RF-07** | Al elegir un material en cualquier formulario, descripción y lote se completan solos y no son editables ahí |
| **RF-08** | Buscar materiales por código o descripción en el catálogo completo |
| **RF-09** | Editar descripción y lote solo almacen o ACT-03. El código tambien edita |
| **RF-10** | El tipo no se puede cambiar si el material tiene movimientos en cualquier tenant |
| **RF-11** | Registrar quién creó o modificó cada material y cuándo |

### Técnicos (spec 003)

| ID | Requisito |
|---|---|
| **RF-12** | Registrar técnicos del tenant con su NIF (LAxxxx) |
| **RF-13** | Un técnico pertenece a un solo tenant |

### Recojo de materiales (spec 004)

| ID | Requisito |
|---|---|
| **RF-14** | Un tenant recoge solo en el almacén de su región |
| **RF-15** | Una serie pertenece a un tenant y no cambia de región |
| **RF-16** | El recojo se registra por formulario con varias líneas. Cada línea suma al stock general del tenant |
| **RF-17** | Las series se ingresan pegando texto o escaneando una por una, con vista previa por fila y su estado |
| **RF-18** | Cada serie se normaliza (mayúsculas, sin espacios) y debe tener 12 caracteres alfanuméricos |
| **RF-19** | Si alguna serie es inválida, duplicada o ya existe, no se guarda ningún recojo |

### Stock inicial de técnicos (spec 005)

| ID | Requisito |
|---|---|
| **RF-20** | Cargar una sola vez el stock inicial de cada técnico el día de implementación. La forma de carga (Excel o formulario) está pendiente |

### Solicitud de asignación (spec 006)

| ID | Requisito |
|---|---|
| **RF-21** | Crear una solicitud de asignación por técnico, con líneas de material |
| **RF-22** | En seriados, el tenant elige series Disponibles de su inventario. Cada serie es una fila con cantidad 1 |
| **RF-23** | En no seriados, la cantidad es un entero mayor que 0 y no supera el disponible, descontando lo reservado |
| **RF-24** | Al enviar la solicitud, sus series y cantidades pasan a Reservada |
| **RF-25** | El sistema genera el Excel de asignación con Movimiento Z31, Centro PR05 y Almacén BE03 autocompletados |
| **RF-26** | El NIF se completa desde el técnico elegido y no es editable |
| **RF-61** | Una vez aceptado la asignación, inicia a contar los dias de seriados en mano de cada tecnico |
| **RF-62** | Una vez aceptado el traspaso, vuelve a iniciar el contado de los dias de seriados en mano de cada tecnico |
| **RF-63** | Para equipos seriados que tengan 20 dias en mano de un tecnico, el sistema debera emitir una alerta |

### Envío y revisión del almacén (spec 007)

| ID | Requisito |
|---|---|
| **RF-27** | El Excel se envía por correo al buzón del almacén de la región, con reintentos si falla |
| **RF-28** | Registrar cada envío: destinatario, fecha y archivo exacto enviado |
| **RF-29** | El Responsable de almacén confirma o rechaza la solicitud dentro del sistema con un comentario del error si se rechaza |
| **RF-30** | Estados de la solicitud: Borrador, Enviada, Confirmada, Rechazada, Cancelada |
| **RF-31** | Al rechazar, las series vuelven a Disponible |

### Confirmación y actualización de stock (spec 008)

| ID | Requisito |
|---|---|
| **RF-32** | Al confirmar, las series pasan a Asignada al técnico, el stock del técnico sube y el stock general baja |

### Traspaso entre técnicos (spec 009)

| ID | Requisito |
|---|---|
| **RF-33** | Un traspaso mueve materiales entre técnicos del mismo tenant, con un Excel de dos hojas: Desasignación (Z32) y Asignación (Z31) |
| **RF-34** | El técnico origen y el destino no pueden ser el mismo |
| **RF-35** | El origen solo puede ceder materiales y series que tiene asignados, descontando lo reservado |
| **RF-36** | Lo que sale debe cuadrar con lo que entra, por material y por serie. Si no cuadra, se rechaza todo |
| **RF-37** | El Responsable de almacén acepta o rechaza el traspaso. Al aceptar, las series cambian de técnico. Al rechazar, no cambia nada |
| **RF-38** | Un traspaso no modifica el stock general del tenant |

### Conciliación con el reporte de Lari (spec 010)

| ID | Requisito |
|---|---|
| **RF-39** | Cargar el reporte de Lari crea una conciliación "En revisión" con las diferencias, sin cambiar el stock |
| **RF-40** | Solo puede haber una conciliación en revisión por tenant a la vez |
| **RF-41** | Reglas de ausencia: un técnico que no aparece en el reporte se ignora. Un material que falta a un técnico presente se asume en 0 |
| **RF-42** | Las diferencias de series se muestran en dos grupos, con el listado de cada serie: "en reporte, no en sistema" y "en sistema, no en reporte" |
| **RF-43** | La aprobación bloquea si hay materiales del reporte que no existen en el catálogo |
| **RF-44** | El tenant aprueba o rechaza la conciliación completa (todo o nada) |
| **RF-45** | Al aprobar, las series del reporte que no existen en el sistema se crean en el técnico, y las que el sistema tiene y el reporte no traen se retiran |
| **RF-46** | Al aprobar, cada ajuste registra valor anterior y valor nuevo |
| **RF-47** | Si el stock de un técnico cambió entre la carga y la aprobación, el sistema recalcula y exige revisar de nuevo |
| **RF-48** | Se rechaza el archivo completo si contiene técnicos que no pertenecen al tenant o a la región del reporte |
| **RF-64** | El consumo de fungibles se calcula como el stock inicial menos el remanente reportado |

### Logística inversa y devoluciones (spec 011)

| ID | Requisito |
|---|---|
| **RF-65** | Registrar la devolución de equipos del técnico: cada serie sale de su stock y vuelve a Disponible, liberando su custodia |
| **RF-66** | Registrar equipos recuperados o de baja con su serie y causa (avería, migración); salen del stock disponible |
| **RF-67** | Generar el acta de entrega de devoluciones a Lari (contrata principal) |

### Reportes mensuales (spec 012)

| ID | Requisito |
|---|---|
| **RF-68** | Generar un corte mensual con totales de solicitados, asignados, liquidados o instalados, y el porcentaje no justificado (merma) |
| **RF-69** | Exportar a Excel los reportes de auditoría y de conciliación mensual |

### Auditoría (transversal)

| ID | Requisito |
|---|---|
| **RF-49** | Todo movimiento y ajuste de stock registra usuario, fecha, valor anterior y valor nuevo |
| **RF-50** | No se borran movimientos. Una corrección se hace con un movimiento nuevo |

---