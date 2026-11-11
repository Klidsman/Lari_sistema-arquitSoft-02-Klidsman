# Spec: Tenants, regiones y acceso

## Trazabilidad
- Historias: HU-01, HU-04, HU-34, HU-35, HU-36, HU-37, HU-38.
- Requisitos: RF-01, RF-02, RF-03, RF-04, RF-05, RF-51 a RF-60.
- Atributos de calidad: RNF-01, RNF-02, RNF-03, RNF-20, RNF-21.
- Restricciones: RES-05, RES-18, RES-19.
- Drivers: DRV-01, DRV-07, DRV-11.

## Dependencias
- Constitución del proyecto.
- ADR-002: multitenencia con esquema compartido.
- ADR-003: jerarquía región → tenant → técnico.
- ADR-007: identidad del tenant desde la sesión.
- ADR-008: cookie de sesión.
- ADR-014: privilegios limitados del Administrador de plataforma.
- ADR-015: stack tecnológico.
- Reglas: `03-reglas-de-dominio/regiones-y-tenants.md` y `auditoria.md`.

## Objetivo
Definir las regiones, los almacenes centrales, los tenants y las cuentas de acceso, con una sola cuenta operativa por tenant que concentra todas las funciones de su propio tenant, y con alcances separados para el Administrador de plataforma y el Responsable de almacén.

## Alcance
- Registro de regiones con su almacén central: Centro, Almacén y buzón de correo.
- Registro de tenants asignados a una región.
- Una sola cuenta de tenant, creada por el Administrador de plataforma.
- Cuentas de Administrador de plataforma y de Responsable de almacén.
- Invitación por correo para definir la contraseña.
- Autenticación de dos factores para Administrador de plataforma y Responsable de almacén.
- Desactivación de cuentas y suspensión de tenants.
- Revocación inmediata de acceso.
- Auditoría de altas, cambios de rol y desactivaciones.
- Aislamiento de datos por tenant y por región.

## Fuera de alcance
- Subcuentas dentro de un tenant.
- Roles internos del tenant: Operador, Aprobador o Responsable del tenant.
- Separación de funciones entre carga y aprobación de conciliaciones dentro del tenant.
- Registro de técnicos y su NIF, que corresponde a la spec 003.
- Catálogo de materiales, que corresponde a la spec 002.
- Recojos, asignaciones, traspasos, conciliaciones y stock.
- Autoregistro de usuarios.
- Inicio de sesión con proveedores externos, SSO o LDAP.
- Recuperación de contraseña y recuperación de códigos de segundo factor.
- Eliminación física de regiones, tenants o cuentas.
- Cambio de región de un tenant.
- Gestión de más de una región por tenant.
- Facturación o planes comerciales.

## Actores
| Actor | Alcance | Responsabilidad |
|---|---|---|
| Administrador de plataforma (ACT-02) | Global | Crea regiones, almacenes, tenants, la cuenta única del tenant y las cuentas de Responsable de almacén. Gestiona el catálogo compartido y consulta la auditoría de acceso. No opera inventario ni aprueba conciliaciones |
| Responsable de almacén (ACT-03) | Una región | Confirma o rechaza solicitudes y traspasos de su región. No ve ni opera datos de tenants ni de otras regiones |
| Tenant (ACT-01) | Un tenant | Opera con una sola cuenta todas las funciones de su tenant: recojos, asignaciones, traspasos, reportes, conciliaciones, técnicos, materiales y auditoría de su tenant |
| Técnico (ACT-04) | Un tenant | Actor pasivo: recibe materiales y no inicia sesión en el sistema |

## Cuenta del tenant
Cada tenant tiene exactamente una cuenta operativa.

| Puede | No puede |
|---|---|
| Registrar recojos, crear asignaciones y traspasos | Ver datos de otro tenant |
| Cargar reportes y aprobar o rechazar conciliaciones | Confirmar solicitudes como almacén |
| Gestionar técnicos y materiales de su tenant | Crear regiones, tenants o cuentas |
| Consultar sus reportes y su auditoría | Operar fuera de su región |
| Administrar todas las funciones del tenant | Crear subcuentas o roles internos |

La misma cuenta que carga una conciliación puede aprobarla. No existe separación de funciones dentro del tenant.

## Entidades

### Región
- Tiene un código único, un nombre y un almacén central.
- El almacén central tiene Centro, Almacén y buzón de correo.
- Centro y Almacén son parámetros configurables de la región, no constantes del sistema.
- Una región puede tener varios tenants.
- Una región no se elimina; se desactiva cuando corresponda.
- Toda alta o cambio de región y almacén queda auditada.

### Tenant
- Tiene un código único, un nombre y una región.
- Pertenece a exactamente una región.
- La región se define al crear el tenant y no cambia en esta versión.
- Tiene estado Activo o Suspendido.
- Tiene exactamente una cuenta operativa.
- Un tenant no opera hasta que su cuenta esté activa.
- Suspender un tenant bloquea su cuenta y sus operaciones, pero conserva sus datos y su stock sin cambios.
- Un tenant no se elimina.

### Cuenta
- Se identifica por correo electrónico único.
- Tiene uno de estos alcances:
  - Administrador de plataforma: sin tenant y sin región.
  - Cuenta del tenant: un tenant, sin región.
  - Responsable de almacén: una región, sin tenant.
- Puede estar activa o desactivada.
- No se elimina; se desactiva.
- Una cuenta desactivada no puede iniciar sesión ni conservar una sesión activa.
- El correo electrónico es el identificador de inicio de sesión.
- No existe más de una cuenta de tenant por tenant.
- El tenant no crea cuentas; solo el Administrador de plataforma crea la cuenta del tenant.

### Invitación
- Se crea al dar de alta una cuenta.
- Se envía al correo de la cuenta para que el usuario defina su contraseña.
- El token es de un solo uso y tiene vencimiento.
- Un token vencido, usado o revocado no permite definir contraseña.
- Reenviar una invitación invalida la anterior.
- La invitación no se envía a un correo que ya pertenece a una cuenta.

## Reglas de negocio

1. **Jerarquía.** Toda región tiene un almacén central; todo tenant pertenece a una región; toda cuenta de tenant pertenece a un tenant.
2. **Aislamiento por tenant.** La cuenta del tenant solo ve y opera datos de su tenant. El tenant se obtiene de la sesión autenticada, nunca de un parámetro del cliente.
3. **Aislamiento por región.** Un Responsable de almacén solo ve y responde solicitudes de su región.
4. **Alcance de la cuenta.** Una cuenta no puede pertenecer a un tenant y a una región a la vez.
5. **Alta centralizada.** Solo el Administrador de plataforma crea regiones, almacenes, tenants, la cuenta única del tenant y las cuentas de Responsable de almacén.
6. **Una sola cuenta por tenant.** Cada tenant tiene exactamente una cuenta operativa. No se crean subcuentas ni roles internos.
7. **Operación habilitada.** Un tenant no opera hasta que su cuenta esté activa.
8. **Invitación obligatoria.** Toda cuenta nueva recibe una invitación para definir su contraseña. No se crean cuentas con contraseña conocida por el administrador.
9. **Token de un solo uso.** El token de invitación vence, no se reutiliza y se invalida al reenviar la invitación.
10. **Dos factores.** Las cuentas de Administrador de plataforma y de Responsable de almacén requieren un segundo factor para iniciar sesión.
11. **Correo único.** No puede existir más de una cuenta con el mismo correo electrónico.
12. **Desactivación inmediata.** Desactivar una cuenta retira su acceso de inmediato, invalida sus sesiones y conserva su historial.
13. **Suspensión del tenant.** Suspender un tenant bloquea su cuenta y sus operaciones, sin modificar datos ni stock.
14. **Cambio de rol.** Solo el Administrador de plataforma puede cambiar el rol de una cuenta de Administrador de plataforma o de Responsable de almacén. La cuenta del tenant no cambia de rol: se desactiva o reactiva. El cambio se aplica de inmediato y queda auditado con el rol anterior y el nuevo.
15. **Sin eliminación.** No se borran regiones, tenants ni cuentas. Se desactivan o suspenden.
16. **Auditoría.** Toda alta de región, tenant o cuenta, cambio de rol y desactivación registra usuario, fecha, valor anterior y valor nuevo.
17. **Separación de funciones entre actores.** El Administrador de plataforma no registra recojos, asignaciones ni traspasos, y no aprueba conciliaciones, aunque fuerce la petición.
18. **Permisos en backend.** Las reglas de alcance y rol se validan en el servidor, no solo en la interfaz.
19. **Parámetros configurables.** Centro, Almacén y buzón son datos de la región, no constantes del sistema.
20. **Sin autoregistro.** Ningún usuario crea su propia cuenta fuera del flujo de invitación.
21. **Sin separación interna.** La cuenta del tenant puede cargar y aprobar la misma conciliación. No existen Operador, Aprobador ni Responsable del tenant.

## Flujos

### Alta de región y almacén
1. El Administrador de plataforma registra código, nombre, Centro, Almacén y buzón.
2. El sistema valida el código único y el formato del buzón.
3. El sistema guarda la región y su almacén en una sola operación.
4. El alta queda auditada.

### Alta de tenant
1. El Administrador de plataforma elige una región activa.
2. Registra código y nombre del tenant.
3. El sistema valida el código único y la región.
4. El tenant queda en estado Activo, pero no opera hasta que su cuenta esté activa.
5. El alta queda auditada.

### Alta de la cuenta del tenant
1. El Administrador de plataforma elige el tenant.
2. Registra el correo de la cuenta.
3. El sistema valida que el correo sea único y que el tenant no tenga ya una cuenta.
4. El sistema crea la cuenta inactiva con alcance de tenant.
5. El sistema genera y envía la invitación.
6. El alta queda auditada.

### Alta de cuenta de almacén
1. El Administrador de plataforma elige la región.
2. Registra el correo de la cuenta.
3. El sistema valida el correo único.
4. Crea la cuenta inactiva con alcance de región.
5. Genera y envía la invitación.
6. El alta queda auditada.

### Aceptación de invitación
1. El usuario abre el enlace de invitación.
2. El sistema valida que el token exista, no esté vencido, no haya sido usado y no haya sido revocado.
3. El usuario define su contraseña.
4. El sistema activa la cuenta, marca la invitación como usada y registra el evento.
5. El usuario inicia sesión.

### Inicio de sesión
1. El usuario ingresa correo y contraseña.
2. El sistema rechaza cuentas desactivadas y tenants suspendidos.
3. Si el rol exige segundo factor, el sistema lo solicita antes de abrir la sesión.
4. Al completar, el sistema abre la sesión con el alcance del usuario.

### Desactivación de cuenta
1. El Administrador de plataforma desactiva la cuenta.
2. El sistema la marca como desactivada e invalida sus sesiones.
3. El historial de la cuenta se conserva.
4. La desactivación queda auditada.

### Suspensión de tenant
1. El Administrador de plataforma suspende el tenant.
2. El sistema bloquea el acceso de su cuenta y sus operaciones.
3. Los datos y el stock se conservan sin cambios.
4. La suspensión queda auditada.

## Criterios de aceptación

- Dado un Administrador de plataforma, cuando registra una región con código único, nombre, Centro, Almacén y buzón, entonces la región y su almacén se guardan y el alta queda auditada.
- Dado un código de región ya existente, cuando se intenta registrar otra región con ese código, entonces se rechaza con “El código de región ya existe”.
- Dado un tenant sin región, cuando se intenta guardar, entonces se rechaza con “El tenant debe pertenecer a una región”.
- Dado un tenant con una región asignada, cuando se intenta cambiar la región, entonces el campo no está disponible y el servidor rechaza la operación.
- Dado un tenant sin cuenta activa, cuando se intenta operar, entonces el sistema bloquea la operación.
- Dado un Administrador de plataforma, cuando crea la cuenta única de un tenant, entonces la cuenta queda inactiva, se genera una invitación y se envía al correo.
- Dado un tenant que ya tiene cuenta, cuando se intenta crear otra, entonces se rechaza con “El tenant ya tiene una cuenta”.
- Dada la cuenta del tenant, cuando intenta crear una cuenta o subcuenta, entonces la acción no está disponible y el servidor la rechaza.
- Dada una invitación vencida, usada o revocada, cuando el usuario intenta definir su contraseña, entonces se rechaza.
- Dada la cuenta activa de un tenant, cuando carga y aprueba una conciliación, entonces el sistema lo permite porque no hay separación de funciones internas.
- Dada la cuenta de un tenant, cuando intenta consultar o modificar datos de otro tenant, entonces el sistema no devuelve el dato y no revela su existencia.
- Dado un Responsable de almacén, cuando intenta ver solicitudes de otra región, entonces el sistema no las devuelve.
- Dado un Administrador de plataforma, cuando intenta registrar un recojo, una asignación o un traspaso, o aprobar una conciliación, entonces el servidor rechaza la operación aunque se fuerce la petición.
- Dado un usuario con cuenta activa, cuando se desactiva su cuenta, entonces su sesión deja de ser válida de inmediato y su historial se conserva.
- Dado un tenant activo, cuando se suspende, entonces su cuenta no puede iniciar sesión ni operar, y sus datos y stock permanecen sin cambios.
- Dado un Administrador de plataforma o un Responsable de almacén, cuando inicia sesión sin completar el segundo factor, entonces no se abre la sesión.
- Dado un cambio de rol de una cuenta administrativa, cuando se guarda, entonces el rol anterior y el nuevo quedan auditados y el cambio se aplica de inmediato.
- Dada una cuenta del tenant, cuando se intenta cambiar su rol, entonces se rechaza; solo se permite desactivarla o reactivarla.
- Dado un correo electrónico ya registrado, cuando se intenta crear otra cuenta con ese correo, entonces se rechaza.
- Dado un intento de crear una cuenta con tenant y región a la vez, entonces se rechaza.
- Dado un intento de eliminar una región, tenant o cuenta, entonces el sistema no lo permite y solo ofrece desactivar o suspender.
- Dada cualquier alta, cambio de rol o desactivación, cuando finaliza, entonces existe un registro con usuario, fecha, valor anterior y valor nuevo.

## Casos borde
- Invitación vencida: se rechaza y se permite reenviar una nueva.
- Reenvío de invitación: invalida el token anterior.
- Invitación enviada a un correo que ya tiene cuenta: se rechaza.
- Cuenta desactivada con sesión abierta: la siguiente petición se rechaza.
- Tenant suspendido con su cuenta conectada: la siguiente petición se rechaza.
- Cambio de rol con sesión abierta: la siguiente petición usa el rol nuevo.
- Dos altas simultáneas con el mismo código de región, código de tenant o correo: una falla por restricción única.
- Dos cuentas de tenant para el mismo tenant: la segunda falla por restricción única.
- Cuenta con tenant y región a la vez: se rechaza.
- Cuenta del tenant desactivada: el tenant queda sin operación hasta que el Administrador de plataforma reactive la cuenta existente.
- Administrador de plataforma sin tenant ni región: es un estado válido.
- Intento de eliminar una cuenta o tenant: se rechaza; se desactiva o suspende.
- Pérdida del segundo factor: la recuperación queda fuera de alcance; la cuenta se desactiva y se crea una nueva.
- Buzón de almacén inválido: se rechaza.
- Centro o Almacén vacíos: se rechaza.

## Supuestos y decisiones confirmadas
1. La región de un tenant no cambia después de crearlo.
2. Decisión confirmada: la cuenta del tenant puede realizar todas las funciones del tenant, incluida la aprobación de sus propias conciliaciones.
3. La invitación vence a las 72 horas.
4. El correo electrónico es el identificador de inicio de sesión y es único globalmente.
5. La reactivación de una cuenta o de un tenant se permite al Administrador de plataforma y queda auditada.
6. El segundo factor se implementa con TOTP y la recuperación de códigos queda fuera de alcance.
7. La contraseña debe cumplir la política de seguridad configurada; se propone un mínimo de 12 caracteres.
8. Los códigos de región y tenant son alfanuméricos, de 1 a 20 caracteres.
9. Centro y Almacén se precargan con PR05 y BE03, pero son editables por región.
10. La cuenta del tenant puede consultar la auditoría de su tenant, pero no la de otros tenants.
11. Si el tenant necesita que varias personas operen, se comparte la única cuenta o se define una funcionalidad futura de cuentas adicionales con el mismo alcance.
