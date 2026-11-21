# Spec 006 - Solicitud de Asignación

Especificación técnica para la creación de solicitudes de asignación de materiales a técnicos.

## 1. Propósito

Permitir que los tenants creen solicitudes de asignación de materiales a sus técnicos. Las solicitudes incluyen materiales seriados (series específicas) y no seriados (cantidades), se validan contra el stock disponible, generan un Excel estandarizado y pasan las series a estado Reservado hasta la confirmación del almacén.

## Clarifications

### Session 2026-11-19

- Q: ¿Cómo se seleccionan varios técnicos en una solicitud? → A: Una solicitud puede incluir varios técnicos del tenant; el tenant los carga en orden (primero un técnico, luego otro) en la misma pantalla. Enmienda aprobada de la constitución 1.4.0.
- Q: ¿Cómo se representa el reparto en el Excel? → A: Un único Excel por solicitud con una tabla; cada fila indica su NIF de técnico. Las filas siguen el orden en que se capturaron las líneas; el movimiento es Z31.
- Q: ¿Qué cantidad sobrante se muestra? → A: Por material, el disponible del tenant menos las cantidades de la solicitud en curso; para seriados, las series disponibles menos las seleccionadas. Se actualiza al cambiar el formulario.
- Q: ¿Puede el tenant descargar el Excel de asignación? → A: Sí, desde el detalle de la solicitud, verificando el hash SHA-256.
- Q: ¿El almacén confirma o rechaza por técnico? → A: La solicitud completa, de una sola vez.
- Q: ¿Qué materiales aparecen en la nueva solicitud? → A: Solo los que el tenant tiene con existencias: stock general disponible (no seriados) o series `DISPONIBLE`, provenientes de recojos o stock inicial. No se muestra todo el catálogo.
- Q: En la ventana de series, ¿se puede marcar varias series a la vez? → A: Sí, selección múltiple; cada serie marcada se agrega como una fila.
- Q: ¿Los bloques de técnicos siguen editables hasta enviar? → A: Sí, todos los bloques permanecen en la pantalla y se pueden editar o quitar antes de enviar; la solicitud y el Excel se generan una sola vez.
- Q: ¿Qué pasa si se repite un material para el mismo técnico? → A: Se rechaza con un mensaje; no se unen ni se duplican líneas.
- Q: ¿Cómo se agregan materiales desde el panel lateral? → A: Se pueden marcar varios y pulsar "Agregar seleccionados"; se agregan al bloque del técnico activo. Si no hay bloque, se pide agregar un técnico.
- Q: ¿Dónde va el panel de materiales? → A: Fijo a la izquierda, siempre visible.
- Q: Si el lote incluye varios seriados, ¿cómo se eligen sus series? → A: Se agregan todas las líneas; las seriadas quedan pendientes con "Elegir series" y solo la ventana del primer seriado se abre automáticamente.
- Q: ¿El panel muestra cantidades actualizadas? → A: Sí, disponible y sobrante por material; se actualizan al agregar o quitar líneas y el material se deshabilita al llegar a 0.
- Q: ¿Qué pasa si se intenta asignar más de lo que queda disponible? → A: El campo se limita al sobrante en ese momento, muestra "solo quedan N" y el panel baja en vivo. El servidor vuelve a validar al enviar.
- Q: ¿Qué pasa si el stock cambia mientras el formulario está abierto? → A: Se revalida al enviar; si ya no alcanza, se rechaza con un mensaje y se refresca el sobrante. No hay refresco automático mientras se escribe.
- Q: ¿El desplegable de materiales debe mostrar la cantidad actualizada? → A: Sí; debe mostrar el sobrante y bajar a medida que se asignan materiales, recuperándose al quitar líneas. No debe quedarse en el disponible inicial.
- Q: Al guardar un borrador editado, ¿sigue siendo borrador? → A: Sí; “Guardar cambios” mantiene el estado `BORRADOR` y el envío sigue siendo una acción separada.
- Q: ¿Qué se puede editar en un borrador? → A: Todo: técnicos, fecha, materiales, cantidades y series, revalidando el stock al guardar.

## 2. Alcance

- Creación de solicitudes de asignación para uno o más técnicos
- Selección de series disponibles del inventario general
- Ingreso de cantidades para materiales no seriados
- Validación de disponibilidad (descontando lo reservado)
- Generación automática de Excel de asignación (ver `04-contratos/excel-asignacion.md`)
- Cambio de estado de series a Reservada
- Envío del Excel al almacén central
- Cálculo de días en mano para seriados (al confirmar)
- Alerta de cupo máximo de equipos

## 3. Actores

- **Tenant (ACT-01)**: Crea solicitudes de asignación a sus técnicos
- **Almacén (ACT-03)**: Recibe y confirma las solicitudes (spec 007)

## 4. Trazabilidad

### Historias de Usuario
- **HU-08** (RF-21, RF-22, RF-23): Como tenant, quiero armar una asignación con equipos serializados específicos y material fungible, validando existencia en stock
- **HU-09** (RF-63): Como tenant, quiero ser alertado si un técnico supera su cupo máximo de equipos sin liquidar
- **HU-10** (RF-25): Como tenant, quiero que el sistema genere automáticamente el Excel estandarizado de despacho
- **HU-11** (RF-21): Como tenant, quiero asignar materiales a mis técnicos
- **HU-12** (RF-28): Como tenant, quiero que el Excel se guarde de forma inmutable con firma SHA-256
- **HU-13** (RF-61): Como tenant, quiero ver los días en mano que tiene un equipo seriado

### Requisitos Funcionales
- **RF-21**: Crear una solicitud de asignación con líneas de material para uno o más técnicos
- **RF-22**: En seriados, el tenant elige series Disponibles de su inventario. Cada serie es una fila con cantidad 1
- **RF-23**: En no seriados, la cantidad es un entero mayor que 0 y no supera el disponible, descontando lo reservado
- **RF-24**: Al enviar la solicitud, sus series y cantidades pasan a Reservada
- **RF-25**: El sistema genera el Excel de asignación con Movimiento Z31, Centro PR05 y Almacén BE03 autocompletados
- **RF-26**: El NIF se completa desde el técnico elegido y no es editable
- **RF-61**: Una vez aceptado la asignación, inicia a contar los días de seriados en mano de cada técnico
- **RF-63**: Para equipos seriados que tengan 20 días en mano de un técnico, el sistema debe emitir una alerta

### Atributos de Calidad
- RF-23: Usabilidad (validación de disponibilidad en tiempo real)
- RF-25: Compatibilidad (Excel estandarizado)
- RF-28: Integridad (firma SHA-256)

## 5. Requisitos Funcionales

### 5.1 Creación por Bloques de Técnico (RF-21)
- Una solicitud de asignación puede incluir uno o más técnicos del tenant
- La pantalla trabaja por bloques: el usuario elige un técnico, agrega los materiales de ese técnico y luego agrega otro técnico con su propio bloque
- Los bloques se mantienen visibles en la misma pantalla y se pueden editar o quitar antes de enviar
- La solicitud y su único Excel se generan una sola vez, al enviar
- Cada línea indica el técnico de su bloque
- La solicitud puede tener múltiples líneas de material por técnico
- Cada línea puede ser seriada o no seriada
- Un material no puede repetirse para el mismo técnico; se rechaza con un mensaje
- La pantalla tiene un panel de materiales **fijo a la izquierda**, siempre visible
- El panel muestra solo materiales con existencias del tenant (stock general disponible o series `DISPONIBLE`), con su disponible y sobrante actualizados
- El desplegable de materiales muestra el **sobrante actualizado**, no el disponible inicial; baja al asignar y se recupera al quitar líneas
- Se pueden marcar varios materiales en el panel y pulsar "Agregar seleccionados"; se agregan al bloque del técnico activo
- Si no hay bloque de técnico activo, se pide agregar un técnico antes de agregar materiales
- Al llegar el sobrante a 0, el material se marca como no disponible y no se puede seleccionar
- Se muestra la cantidad sobrante por material mientras se captura

### 5.2 Selección de Series (RF-22)
- Al elegir un material seriado se abre una ventana con las series disponibles del material
- La ventana tiene una barra de búsqueda por número de serie
- Se pueden marcar varias series a la vez; cada serie marcada agrega una fila con cantidad 1
- Si se agregan varios materiales seriados en lote, la ventana del primero se abre automáticamente y las demás líneas quedan pendientes con el botón "Elegir series"
- No se puede enviar mientras una línea seriada no tenga series
- Solo se muestran series en estado Disponible
- La ventana excluye las series ya seleccionadas en otras líneas de la solicitud
- Si no hay series disponibles, la ventana muestra un mensaje
- No se escriben las series manualmente; se seleccionan del inventario disponible

### 5.3 Ingreso de Cantidades (RF-23)
- Para materiales no seriados, el tenant ingresa la cantidad
- La cantidad debe ser un entero mayor que 0
- La cantidad no puede superar el sobrante del material en toda la solicitud, sumando todos los técnicos
- El campo de cantidad se limita al sobrante en vivo; si se intenta superar, muestra "solo quedan N" y no lo permite
- El sobrante del panel y la etiqueta del desplegable de materiales bajan al agregar una línea y se recuperan al quitarla
- La disponibilidad se calcula descontando lo reservado en asignaciones pendientes
- Fórmula: `Sobrante = Stock General - Reservado - Cantidad de la solicitud en curso`
- Al enviar se revalida; si el stock cambió, se rechaza con un mensaje y se refresca el sobrante

### 5.4 Reserva al Enviar (RF-24)
- Al enviar la solicitud, las series seleccionadas pasan a estado Reservada
- Las cantidades de no seriados se reservan del stock general
- Mientras está Reservada, la serie no puede ser seleccionada en otra asignación
- Si el almacén rechaza la asignación, las series vuelven a Disponible

### 5.5 Generación de Excel (RF-25)
- El sistema genera automáticamente el Excel de asignación al enviar la solicitud (`BORRADOR → ENVIADA`); guardar un borrador no genera Excel
- El Excel tiene el formato definido en `04-contratos/excel-asignacion.md`
- Metadatos autocompletados: Movimiento Z31, Centro PR05, Almacén BE03
- El Excel se guarda con firma SHA-256 para garantizar integridad
- El Excel se envía por correo al buzón del almacén de la región

### 5.6 NIF Autocompletado (RF-26)
- El NIF del técnico se completa desde el técnico elegido
- El NIF no es editable en el formulario
- El NIF se copia al Excel de asignación

### 5.7 Cálculo de Días en Mano (RF-61)
- Una vez aceptada la asignación (por el almacén), inicia el conteo de días en mano
- Los días en mano se calculan desde la fecha de aceptación hasta la fecha actual o de devolución
- Este dato es informativo para el control de custodia
- Se muestra en el detalle del técnico y en reportes

### 5.8 Alerta de Cupo Máximo (RF-63)
- Para equipos seriados, el sistema emite una alerta si un técnico supera 20 días en mano
- La alerta se muestra al tenant cuando intenta crear o editar una asignación
- La alerta no bloquea la asignación, solo informa
- El propósito es cumplir la política de custodia de equipos

### 5.9 Edición de Borrador (RF-21)
- Una solicitud en estado `BORRADOR` se puede editar desde el listado y desde el detalle con la acción "Editar"
- La pantalla de edición precarga técnicos, fecha, líneas, cantidades y series existentes
- Se pueden cambiar técnicos, fecha, materiales, cantidades y series
- Al guardar se reemplazan las líneas de la solicitud, se revalida la disponibilidad y el sobrante, y la solicitud sigue en `BORRADOR`
- Guardar la edición no reserva series, no genera Excel y no envía correo
- Una solicitud que no está en `BORRADOR` no se puede editar; responde `409`
- Si el stock cambió y ya no alcanza, se rechaza el guardado con un mensaje y no se modifica la solicitud
- Cada cambio queda auditado con usuario, fecha y valores anterior/nuevo

## 6. Requisitos No Funcionales

### 6.1 Rendimiento
- La validación de disponibilidad debe ser rápida (< 1 segundo)
- La generación del Excel debe ser eficiente
- El selector de series debe cargar y filtrar rápidamente

### 6.2 Usabilidad
- El selector de series debe permitir búsqueda y filtrado
- Los errores de validación deben ser claros y específicos
- La alerta de cupo máximo debe ser visible pero no intrusiva

### 6.3 Integridad
- La generación del Excel debe incluir firma SHA-256
- La reserva de series debe ser transaccional
- No se pueden asignar series que no están disponibles

## 7. Criterios de Aceptación

### CA-01: Creación y Envío de Solicitud Válida
Dado un técnico y materiales disponibles
Cuando el tenant crea y envía una solicitud de asignación
Entonces la solicitud se crea, las series pasan a Reservada y se genera el Excel

### CA-02: Selección de Series Disponibles
Dado el inventario general del tenant
Cuando el tenant selecciona series para asignación
Entonces solo se muestran series en estado Disponible

### CA-03: Validación de Cantidad No Supera Disponible
Dado un material no seriado con stock disponible de 50
Cuando el tenant intenta asignar 60 unidades
Entonces el sistema rechaza la asignación y muestra el error

### CA-04: Cantidad Descontando Reservado
Dado un material con stock general de 50 y 20 reservados
Cuando el tenant intenta asignar
Entonces el disponible es 30 y no se puede asignar más de 30

### CA-05: Series Pasan a Reservada
Dado una solicitud de asignación creada
Cuando se consulta el estado de las series
Entonces las series están en estado Reservada

### CA-06: Generación de Excel Correcto
Dado una solicitud de asignación creada
Cuando se consulta el Excel generado
Entonces tiene los metadatos Z31, PR05, BE03 y el NIF correcto

### CA-07: NIF Autocompletado No Editable
Dado un técnico seleccionado en el formulario
Cuando el usuario intenta editar el NIF
Entonces el campo es de solo lectura

### CA-08: Días en Mano Inician al Aceptar
Dado una asignación aceptada por el almacén
Cuando se consulta los días en mano de las series
Entonces se cuentan desde la fecha de aceptación

### CA-09: Alerta de Cupo Máximo
Dado un técnico con 25 días en mano de equipos seriados
Cuando el tenant intenta crear una nueva asignación
Entonces el sistema muestra una alerta de cupo máximo

### CA-10: Serie No Disponible No Se Puede Asignar
Dado una serie en estado Asignada
Cuando el tenant intenta seleccionarla para asignación
Entonces la serie no aparece en el selector

### CA-11: Serie Reservada No Se Puede Asignar
Dado una serie en estado Reservada en otra asignación
Cuando el tenant intenta seleccionarla para asignación
Entonces la serie no aparece en el selector

### CA-12: Ventana de Series con Búsqueda
Dado un material seriado con series disponibles
Cuando el tenant lo selecciona
Entonces se abre una ventana con las series disponibles y una barra de búsqueda por número

### CA-13: Varios Técnicos por Bloques
Dado un técnico con materiales agregados
Cuando el tenant agrega otro técnico y sus materiales
Entonces ambos bloques permanecen en la misma solicitud y se genera un solo Excel

### CA-14: Material Repetido para el Mismo Técnico
Dado un material ya agregado a un técnico
Cuando el tenant intenta agregarlo de nuevo para ese técnico
Entonces la operación se rechaza con un mensaje

### CA-15: Panel Lateral de Materiales
Dado el formulario de asignación
Cuando el tenant lo abre
Entonces ve a la izquierda los materiales con existencias, su disponible y su sobrante, y puede marcar varios y agregarlos al bloque activo

### CA-16: Seriados Pendientes de Series
Dado un lote de materiales que incluye varios seriados
Cuando el tenant los agrega
Entonces todas las líneas se crean, solo la ventana del primer seriado se abre automáticamente y las demás quedan pendientes con "Elegir series"

### CA-17: Límite en Vivo del Sobrante
Dado un material con 2 unidades disponibles
Cuando el tenant asigna 1 a un técnico e intenta asignar 2 a otro
Entonces la segunda línea solo permite 1, muestra "solo quedan 1" y el panel reduce el sobrante en vivo

### CA-18: Revalidación al Enviar
Dado un formulario abierto con un sobrante calculado
Cuando el stock cambia antes de enviar
Entonces el envío se rechaza con un mensaje, no se reserva nada y el panel se refresca con el sobrante real

### CA-19: Desplegable de Materiales Actualizado
Dado un material con 2 unidades disponibles
Cuando el tenant asigna 1 unidad
Entonces la etiqueta del material en el desplegable muestra 1 restante y vuelve a 2 si se quita la línea

### CA-20: Editar un Borrador
Dado un borrador guardado
Cuando el tenant pulsa "Editar", cambia técnicos, fecha, materiales o cantidades y guarda
Entonces la solicitud sigue en `BORRADOR`, con las líneas actualizadas y el stock revalidado

### CA-21: No Editar una Solicitud Enviada
Dada una solicitud en estado `ENVIADA`
Cuando el tenant intenta abrir o guardar su edición
Entonces la operación se rechaza con `409` y no se modifica nada

## 8. Datos de Entrada

### Formulario de Solicitud de Asignación

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Técnico del bloque | Select | Sí | Técnico del tenant (solo activos) |
| Fecha | Date | Sí | Fecha de la solicitud (por defecto: hoy) |
| Panel de materiales | Lista multi-select fija a la izquierda | Sí | Materiales con existencias, disponible y sobrante; se marcan varios y se agregan al bloque activo |
| Material | Select | Condicional | Material con existencias del tenant (por línea) |
| Tipo de material | Read-only | Condicional | Seriado o no seriado (del catálogo) |
| Lote | Read-only | Condicional | Lote del material (del catálogo) |
| Series | Ventana modal multi-select | Condicional | Series disponibles con búsqueda (solo para seriados) |
| Cantidad | Number | Condicional | Cantidad no seriada; máximo el sobrante en vivo |

## 9. Datos de Salida

### Solicitud de Asignación

| Campo | Descripción |
|---|---|
| ID de solicitud | Identificador único de la solicitud |
| Estado | Borrador, Enviada, Confirmada, Rechazada, Cancelada |
| Técnicos | Técnicos destinatarios |
| NIF | NIF de cada técnico, por línea del Excel |
| Fecha | Fecha de creación |
| Líneas | Lista de materiales, series o cantidades |
| Excel | Ruta del archivo Excel generado |
| Hash SHA-256 | Firma del Excel |

## 10. Reglas de Negocio

1. Una solicitud de asignación puede incluir varios técnicos del tenant; cada línea tiene su técnico
2. Solo se pueden seleccionar series en estado Disponible
3. La cantidad no puede superar el sobrante del material en toda la solicitud, sumando todos los técnicos
4. Al enviar, las series pasan a Reservada
5. El Excel se genera automáticamente con metadatos fijos
6. El NIF se autocompleta y no es editable
7. Los días en mano inician al aceptar la asignación
8. Se alerta si el técnico supera 20 días en mano de seriados
9. Un material no se repite para el mismo técnico en la solicitud; se rechaza con un mensaje
10. Los bloques de técnicos se editan o quitan en pantalla hasta enviar; el Excel se genera una sola vez
11. El campo de cantidad se limita en vivo al sobrante; el servidor revalida al enviar
12. Si el stock cambió mientras el formulario estaba abierto, se rechaza el envío y se refresca el sobrante
13. Un borrador se puede editar completo: técnicos, fecha, líneas, cantidades y series; guardar no lo envía
14. Solo se edita un borrador; cualquier otro estado se rechaza y no se modifica nada

## 11. Consideraciones de Implementación

- La validación de disponibilidad debe ser eficiente (consultar índices de stock y series)
- El formulario debe recalcular el sobrante por material al cambiar cualquier línea y aplicar un máximo a las cantidades no seriadas
- La validación del servidor es la autoridad final; el límite en vivo solo mejora la experiencia
- La generación del Excel debe usar openpyxl y calcular el hash SHA-256
- La reserva de series debe ser transaccional
- La ventana de series debe soportar búsqueda y paginación para grandes volúmenes
- El cálculo de días en mano se hace al confirmar la asignación (spec 007)
- La alerta de cupo máximo se calcula por cada equipo seriado que supera los 20 días en mano, no por la suma de días entre equipos
- El envío del Excel por correo se implementa en spec 007
