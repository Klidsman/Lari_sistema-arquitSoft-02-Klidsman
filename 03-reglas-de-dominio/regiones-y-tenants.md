# Regiones y tenants

Reglas de dominio para la organización de regiones, almacenes centrales, tenants y cuentas de acceso.

## 1. Jerarquía

```text
Región → Almacén central
Región → Tenant → Cuenta única del tenant
Región → Responsable de almacén
```

- Cada región tiene un almacén central.
- Cada tenant pertenece a exactamente una región.
- Cada tenant tiene exactamente una cuenta operativa.
- Cada Responsable de almacén pertenece a exactamente una región.
- El Administrador de plataforma no pertenece a ningún tenant ni a ninguna región.

## 2. Región y almacén

- La región tiene código único y nombre.
- El almacén central tiene Centro, Almacén y buzón de correo.
- Centro, Almacén y buzón son parámetros de la región, no constantes del sistema.
- Una región puede tener varios tenants.
- Una región no se elimina; se desactiva cuando corresponda.
- Los cambios de región y almacén se auditan.

## 3. Tenant

- Tiene código único, nombre y región.
- La región se define al crear el tenant y no cambia en esta versión.
- Tiene estado Activo o Suspendido.
- Tiene exactamente una cuenta operativa.
- Un tenant no opera hasta que su cuenta esté activa.
- Suspender un tenant bloquea su cuenta y sus operaciones, pero conserva sus datos y su stock.
- Un tenant no se elimina.
- El aislamiento por tenant se aplica en el backend y, si es posible, en la base de datos.

## 4. Cuentas

### Administrador de plataforma
- Alcance global.
- Crea regiones, almacenes, tenants, la cuenta única del tenant y las cuentas de Responsable de almacén.
- Gestiona el catálogo compartido.
- No opera inventario, recojos, asignaciones, traspasos ni conciliaciones.
- Requiere segundo factor.

### Cuenta del tenant
- Alcance de un solo tenant.
- Es la única cuenta del tenant.
- Puede realizar todas las funciones del tenant:
  - Registrar recojos.
  - Crear asignaciones y traspasos.
  - Cargar reportes.
  - Aprobar o rechazar conciliaciones.
  - Gestionar técnicos.
  - Registrar materiales.
  - Consultar sus reportes y su auditoría.
- No puede ver datos de otro tenant.
- No puede confirmar solicitudes como almacén.
- No puede crear regiones, tenants, cuentas ni subcuentas.
- No tiene roles internos de Operador, Aprobador ni Responsable del tenant.

### Responsable de almacén
- Alcance de una sola región.
- Confirma o rechaza solicitudes y traspasos de su región.
- No ve ni opera datos de tenants ni de otras regiones.
- Requiere segundo factor.

### Técnico
- Actor pasivo.
- Recibe materiales.
- No inicia sesión en el sistema.

## 5. Reglas de acceso

- Cada tenant tiene exactamente una cuenta.
- Una cuenta pertenece a un tenant, a una región o a ninguno, nunca a un tenant y una región a la vez.
- El correo electrónico es único y es el identificador de inicio de sesión.
- No existe autoregistro.
- Toda cuenta nueva se crea inactiva y recibe una invitación para definir su contraseña.
- El token de invitación es de un solo uso, vence y se invalida al reenviar la invitación.
- Las cuentas de Administrador de plataforma y Responsable de almacén requieren segundo factor.
- Una cuenta desactivada no puede iniciar sesión ni conservar una sesión activa.
- Un tenant suspendido bloquea el acceso de su cuenta y sus operaciones.
- No se eliminan cuentas, tenants ni regiones; se desactivan o suspenden.
- El tenant no crea cuentas ni subcuentas.

## 6. Separación de funciones

- La separación de funciones existe entre actores:
  - El Administrador de plataforma no opera inventario.
  - El Responsable de almacén no opera inventario de tenants.
  - La cuenta del tenant no administra la plataforma ni el almacén.
- Dentro del tenant no hay separación entre operación y aprobación: la misma cuenta puede cargar y aprobar una conciliación.
- La auditoría registra qué cuenta realizó cada acción.

## 7. Aislamiento

- El tenant y la región se obtienen de la sesión autenticada, nunca de un parámetro del cliente.
- Una cuenta de tenant no puede ver ni modificar datos de otro tenant.
- Un Responsable de almacén no puede ver ni responder solicitudes de otra región.
- Un intento de acceso a un dato ajeno se trata como dato inexistente.
- Las claves únicas y los índices incluyen el tenant cuando corresponde.

## 8. Auditoría

- Toda alta de región, almacén, tenant o cuenta se audita.
- Todo cambio de rol se audita con rol anterior y nuevo.
- Toda desactivación de cuenta o suspensión de tenant se audita.
- Cada registro incluye usuario, fecha, valor anterior y valor nuevo.
- La auditoría es de solo inserción.
- No se registran contraseñas, tokens ni secretos de segundo factor.

## 9. Validaciones

- Código de región único.
- Código de tenant único.
- Correo electrónico único y válido.
- Tenant con región obligatoria.
- Una sola cuenta por tenant.
- Cuenta con alcance coherente.
- Buzón de almacén válido.
- Centro y Almacén obligatorios.
- Invitación vigente y no usada.
- Segundo factor completado para los roles que lo requieren.
- Cuenta activa y tenant activo para operar.
