# Spec: Técnicos del tenant

## Trazabilidad
- Historias: HU-02.
- Historias relacionadas: HU-09, HU-11, HU-30, HU-33.
- Requisitos: RF-12, RF-13, RF-26.
- Requisitos relacionados: RF-61, RF-62, RF-63, que consumen la identidad del técnico y se implementan en las specs 006, 009 y 010.
- Atributos de calidad: RNF-07, RNF-18.
- Restricciones: RES-13.
- Drivers: DRV-07, DRV-10.
- ADR: ADR-003, ADR-007, ADR-019.

## Dependencias
- Spec 001: cuenta única del tenant, tenant y alcance de la sesión.
- Spec 002: catálogo de materiales. No se requiere para el alta, pero comparte auditoría.
- Specs 004, 005, 006, 009, 010 y 013: consumen los técnicos para recojos, stock inicial, asignaciones, traspasos, conciliación y registro de materiales.
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `registro-materiales.md` y `auditoria.md`.
- Este módulo no modifica stock, series, asignaciones, traspasos ni conciliaciones.

## Objetivo
Permitir que la cuenta única del tenant registre y mantenga los técnicos de su propio tenant, con su NIF, para asignarles materiales, traspasarlos y conciliar su stock sin mezclar datos entre tenants.

## Alcance
- Alta de técnicos del tenant con NIF y nombre.
- Edición del nombre y del estado del técnico.
- NIF inmutable después del alta.
- Búsqueda y autocompletado por NIF o nombre dentro del tenant.
- Desactivación y reactivación de técnicos.
- Conservación del historial y del stock asociado al técnico.
- Auditoría de altas, cambios, desactivaciones y reactivaciones.
- Aislamiento por tenant.
- Integración con los selectores de técnicos de los demás módulos.

## Fuera de alcance
- Cuentas de acceso para técnicos.
- Inicio de sesión del técnico.
- Asignaciones, traspasos, devoluciones, stock, conciliación y registro de materiales.
- Configuración del cupo máximo de equipos sin liquidar.
- Cálculo de días en mano o de alertas de custodia.
- Eliminación física de técnicos.
- Cambio de tenant de un técnico.
- Carga masiva de técnicos por Excel.
- Datos personales adicionales como teléfono, dirección, DNI completo o datos bancarios.
- Gestión de cuadrillas, turnos, vacaciones o nómina.
- Historial de cambios de NIF, porque el NIF es inmutable.
- Sincronización con Lari o con sistemas externos.

## Actores
| Actor | Alcance | Responsabilidad |
|---|---|---|
| Cuenta del tenant (ACT-01) | Un tenant | Crea, edita, busca, desactiva y reactiva los técnicos de su tenant |
| Administrador de plataforma (ACT-02) | Global | No gestiona técnicos ni tiene permiso para crear, editar o desactivar técnicos |
| Responsable de almacén (ACT-03) | Una región | No gestiona técnicos ni ve su listado completo |
| Técnico (ACT-04) | Un tenant | Actor pasivo: recibe materiales y no inicia sesión en el sistema |

## Datos del técnico
| Campo | Obligatorio | Regla |
|---|---|---|
| NIF | Sí | Formato `LAXXXX`: prefijo `LA` y 4 dígitos. Se guarda en mayúsculas. Único en todo el sistema. No editable después del alta |
| Nombre | Sí | Entre 1 y 100 caracteres, sin espacios al inicio ni al final. Los espacios internos repetidos se colapsan |
| Estado | Sí | Activo o Desactivado. Por defecto, Activo |
| Tenant | Sí | Se obtiene de la cuenta autenticada. No es editable |
| Creado por / creado en | Sí | Se registra automáticamente |
| Actualizado por / actualizado en | No | Se registra en cada cambio |

- El técnico no almacena la región: se obtiene de su tenant.
- El NIF es el identificador que se usa en los Excel de asignación, traspaso y conciliación.
- El nombre es informativo y sirve para la búsqueda y la interfaz.

## Reglas de negocio

1. **Pertenencia.** Todo técnico pertenece a exactamente un tenant. La relación no cambia después del alta.
2. **Aislamiento.** La cuenta del tenant solo ve y opera técnicos de su tenant. El tenant se obtiene de la sesión, nunca de un parámetro del cliente.
3. **NIF único global.** No puede existir más de un técnico con el mismo NIF, aunque estén en tenants distintos.
4. **Formato del NIF.** Debe cumplir `LA` seguido de 4 dígitos. Se normaliza a mayúsculas y se eliminan espacios externos.
5. **NIF inmutable.** El NIF no se edita después del alta. Si se registró mal, se desactiva el técnico y se crea uno nuevo con el NIF correcto.
6. **Nombre obligatorio.** No se aceptan nombres vacíos ni formados solo por espacios.
7. **Alta exclusiva del tenant.** Solo la cuenta del tenant crea técnicos. El Administrador de plataforma y el Responsable de almacén no pueden hacerlo.
8. **Sin eliminación.** Un técnico no se borra; se desactiva. Su historial, su stock y sus documentos se conservan.
9. **Desactivación.** Un técnico desactivado no se ofrece para nuevas asignaciones, traspasos, órdenes de liquidación ni otras operaciones nuevas.
10. **Historial visible.** Los datos de un técnico desactivado siguen siendo consultables para auditoría, reportes y documentos históricos.
11. **Stock pendiente.** La desactivación no borra el stock del técnico. Ese stock sigue visible y debe devolverse o traspasarse según las specs 009 y 011.
12. **Reactivación.** La cuenta del tenant puede reactivar un técnico desactivado. La reactivación queda auditada y lo vuelve a habilitar para nuevas operaciones.
13. **NIF no reutilizable.** Como el técnico no se elimina, no se crea otro técnico con el NIF de uno desactivado. Se reactiva el registro existente.
14. **Búsqueda limitada.** La búsqueda por NIF o nombre solo devuelve técnicos del tenant de la sesión.
15. **Autocompletado.** En los formularios de asignación, traspaso, conciliación y registro de materiales, el NIF se completa desde el técnico elegido y no es editable.
16. **Solo activos en operaciones nuevas.** Los selectores de nuevas operaciones muestran solo técnicos activos. Un formulario viejo con un técnico desactivado se rechaza en el servidor.
17. **Auditoría.** Toda alta, cambio de nombre, desactivación y reactivación registra usuario, fecha, valor anterior y valor nuevo.
18. **Permisos en backend.** Las reglas de rol, tenant y estado se validan en el servidor, no solo en la interfaz.
19. **Tenant suspendido.** Si el tenant está suspendido, su cuenta no puede operar y, por tanto, tampoco gestionar técnicos.
20. **Sin cuentas de técnico.** El técnico no tiene usuario, contraseña ni sesión. Es un actor pasivo.
21. **Sin cambio de tenant.** Un técnico no se mueve de tenant. Si se requiere, se desactiva en el tenant actual y se crea en el nuevo, siempre que el NIF no esté en uso.
22. **Nombre no único.** Dos técnicos pueden tener el mismo nombre; el NIF es el identificador del técnico.

## Flujos

### Alta de técnico
1. La cuenta del tenant entra a “Técnicos” y elige “Nuevo técnico”.
2. Ingresa NIF y nombre.
3. El sistema normaliza el NIF a mayúsculas y valida el formato.
4. El sistema valida que el NIF no exista en el sistema.
5. El sistema asigna el tenant de la sesión.
6. Crea el técnico en estado Activo y registra la auditoría.
7. El técnico aparece en el listado y en los selectores de nuevas operaciones.

### Edición de técnico
1. La cuenta del tenant abre un técnico de su tenant.
2. Puede cambiar el nombre.
3. El NIF y el tenant se muestran como solo lectura.
4. Al guardar, el sistema valida y audita cada campo modificado.
5. Si intenta cambiar el NIF o el tenant, el servidor rechaza la operación.

### Desactivación
1. La cuenta del tenant abre un técnico activo de su tenant.
2. Confirma la desactivación.
3. El sistema marca el técnico como Desactivado y audita el cambio.
4. El técnico deja de aparecer en los selectores de nuevas operaciones.
5. Su historial y su stock se conservan.

### Reactivación
1. La cuenta del tenant abre un técnico desactivado de su tenant.
2. Confirma la reactivación.
3. El sistema lo marca como Activo y audita el cambio.
4. El técnico vuelve a estar disponible para nuevas operaciones.

### Búsqueda y autocompletado
1. La cuenta del tenant escribe un NIF o parte del nombre.
2. El sistema busca solo en los técnicos de su tenant.
3. Devuelve NIF, nombre y estado.
4. En operaciones nuevas, el selector muestra solo técnicos activos.
5. Al elegir un técnico, el NIF se completa automáticamente y no se puede editar en ese formulario.

## Criterios de aceptación

- Dada la cuenta de un tenant, cuando registra un técnico con NIF `LA1234` y nombre válido, entonces el técnico queda activo, asociado a su tenant y con el alta auditada.
- Dado un NIF `LA1234` ya registrado en el mismo tenant, cuando se intenta registrar otro técnico con ese NIF, entonces se rechaza con “El NIF ya está registrado”.
- Dado un NIF `LA1234` ya registrado en otro tenant, cuando se intenta registrar en el tenant actual, entonces se rechaza con el mismo mensaje, sin revelar el tenant al que pertenece.
- Dado un NIF `la1234` o con espacios externos, cuando se guarda, entonces se normaliza a `LA1234`.
- Dado un NIF `LA123`, `LA12345`, `A1234` o `LA12A4`, cuando se intenta guardar, entonces se rechaza con “El NIF debe tener el formato LAXXXX”.
- Dado un nombre vacío o formado solo por espacios, cuando se intenta guardar, entonces se rechaza con “El nombre es obligatorio”.
- Dado un nombre de más de 100 caracteres, cuando se intenta guardar, entonces se rechaza con “El nombre no puede superar los 100 caracteres”.
- Dado un técnico existente, cuando la cuenta del tenant cambia su nombre, entonces el cambio se guarda y se audita el valor anterior y el nuevo.
- Dado un técnico existente, cuando se intenta cambiar el NIF, entonces el campo no está disponible y el servidor rechaza la operación.
- Dado un técnico existente, cuando se intenta cambiar el tenant, entonces el servidor rechaza la operación.
- Dado un técnico activo, cuando se desactiva, entonces deja de aparecer en los selectores de nuevas operaciones y su historial se conserva.
- Dado un técnico desactivado con stock u órdenes históricas, cuando se consulta su historial, entonces sus datos siguen visibles.
- Dado un técnico desactivado, cuando la cuenta del tenant lo reactiva, entonces vuelve a estar activo y la reactivación queda auditada.
- Dado el NIF de un técnico desactivado, cuando se intenta crear otro técnico con ese NIF, entonces se rechaza y se indica que debe reactivar el existente.
- Dada la cuenta de un tenant, cuando busca por NIF o por nombre, entonces solo obtiene técnicos de su tenant.
- Dado un formulario manipulado con el identificador de un técnico de otro tenant, cuando se intenta guardar, entonces el servidor rechaza la operación sin revelar datos del otro tenant.
- Dado un Administrador de plataforma o un Responsable de almacén, cuando intenta crear, editar o desactivar un técnico, entonces el servidor rechaza la operación aunque se fuerce la petición.
- Dado un técnico desactivado usado en un formulario viejo de asignación, traspaso u orden, cuando se envía, entonces el servidor rechaza la operación.
- Dado un técnico con stock asignado, cuando se desactiva, entonces su stock no se borra y sigue visible para devolución o traspaso.
- Dados dos altas simultáneas con el mismo NIF, cuando ambas intentan guardar, entonces una se guarda y la otra se rechaza por la restricción única.
- Dado un intento de eliminar un técnico, entonces el sistema no lo permite y solo ofrece desactivarlo.

## Casos borde
- NIF con espacios externos o minúsculas: se normaliza y luego se valida. Con guiones o espacios internos: se rechaza.
- NIF con longitud incorrecta o caracteres no numéricos después de `LA`: se rechaza.
- Nombre con espacios repetidos: se colapsan antes de guardar.
- Nombre con caracteres especiales: se permiten, salvo que la política del proyecto indique lo contrario.
- Técnico desactivado con stock pendiente: se conserva y se muestra como pendiente de devolución o traspaso.
- Técnico desactivado con órdenes, asignaciones o conciliaciones históricas: se conserva y se puede consultar.
- Intento de crear un técnico con el NIF de un técnico desactivado: se rechaza y se sugiere reactivarlo.
- Intento de reactivar un técnico de otro tenant: se rechaza como inexistente.
- Intento de desactivar dos veces: la segunda operación no cambia el estado y no duplica la auditoría.
- Búsqueda con texto vacío: devuelve el listado del tenant, paginado.
- Cuenta del tenant desactivada o tenant suspendido: no puede gestionar técnicos.
- Formulario viejo con un técnico que fue desactivado mientras se editaba: se rechaza al guardar.
- Dos sesiones de la misma cuenta crean el mismo NIF: una falla por restricción única.
- Técnico con NIF válido pero nombre duplicado: se permite; el nombre no es único.

## Supuestos a confirmar
1. El NIF tiene el formato `LA` seguido de exactamente 4 dígitos. Si Lari usa otra longitud, se ajusta la regla y la restricción.
2. El NIF es único en todo el sistema. Si Lari permite el mismo NIF en dos tenants, se cambia a único por tenant.
3. El NIF no se edita después del alta. Si el negocio necesita corregirlo, se desactiva el técnico y se crea uno nuevo.
4. El nombre es obligatorio, de 1 a 100 caracteres.
5. El estado se modela como Activo o Desactivado, con valor inicial Activo.
6. Un técnico desactivado puede reactivarse; no se elimina.
7. El cupo máximo de equipos sin liquidar no forma parte del alta del técnico; se definirá en la spec de asignación o como parámetro del tenant.
8. No se guardan datos personales adicionales del técnico en esta versión.
9. El tenant se obtiene de la sesión autenticada y no se acepta desde el formulario.
10. La auditoría usa la tabla compartida `RegistroCambio`.

## Fuera de alcance
- Cuentas de acceso o credenciales para técnicos.
- Asignación, traspaso, devolución, baja o conciliación de materiales.
- Cálculo de días en mano, cupos o alertas de custodia.
- Carga masiva por Excel.
- Eliminación física de técnicos.
- Cambio de tenant o de región de un técnico.
- Sincronización automática con Lari.
- Datos bancarios, nómina, vacaciones, turnos o evaluación de desempeño.
- Gestión de cuadrillas o jerarquías entre técnicos.
- Historial de versiones del NIF.
