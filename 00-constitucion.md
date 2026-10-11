# Constitución del proyecto

Versión: 1.2 · Última modificación: [fecha]

## 1. Propósito
Plataforma multitenant para subcontratistas de Lari, organizados por región.
Cada región tiene su almacén central. Cada subcontratista (tenant) pertenece a
una región, controla los materiales que recibe de ese almacén, los asigna a sus
técnicos, traspasa materiales entre ellos y cuadra su stock contra los reportes
de Lari.

## 2. Principios de negocio
Cada principio es una línea; el detalle vive en `03-reglas-de-dominio/`.

1. **Aislamiento multitenant.** Un tenant nunca ve ni modifica datos de otro.
   La única excepción es el catálogo de materiales, que es compartido.
2. **Regiones.** Cada tenant pertenece a una sola región. Recoge solo en el
   almacén de su región, y Lari envía sus reportes por región. Una serie
   pertenece a una región durante toda su vida.
3. **Dos niveles de stock.** Stock general del tenant y stock por técnico.
   Un material pasa del primero al segundo solo mediante una asignación
   confirmada por el almacén central.
4. **El stock general solo sube con recojos registrados** y baja con
   asignaciones confirmadas. Los traspasos no lo modifican.
5. **Traspaso = mover, no crear.** Lo que sale de un técnico entra en otro del
   mismo tenant. El total del tenant no cambia. No existen traspasos entre tenants.
6. **No se asigna más de lo disponible**, descontando lo reservado.
7. **Cada serie existe una sola vez** en todo el sistema y está en un solo lugar
   a la vez. Formato: 12 caracteres alfanuméricos (A-Z, 0-9). Estados: Disponible,
   Reservada, Asignada.
8. **Seriados y no seriados.** Un seriado genera una fila por serie, con Cantidad 1.
   Un no seriado genera una fila con la cantidad que digita el tenant.
9. **El lote es un atributo fijo del material**, autocompletado en todos los
   formularios y Excel. Es informativo y no separa el stock.
10. **El reporte de Lari manda.** En una conciliación aprobada, el reporte prevalece
    sobre el stock del sistema. Un técnico ausente del reporte se ignora; un material
    ausente de un técnico presente se asume en 0.
11. **Los ajustes requieren aprobación humana.** Cargar un reporte no modifica stock;
    la conciliación se aprueba o rechaza completa.
12. **Todo o nada.** Formularios, traspasos y cargas de Excel se aplican completos o
    no se aplican. Nunca quedan a medias.
13. **Nada cambia el stock sin dejar rastro.** Todo movimiento y ajuste registra
    usuario, fecha, valor anterior y valor nuevo. No se borran movimientos; se
    corrigen con uno nuevo.
14. **Las discrepancias se muestran, no se ocultan.** Las diferencias de series se
    alertan listando cada serie afectada.

## 3. Formularios y Excel
- Cada formulario de asignación o traspaso pertenece a un solo técnico (en el
  traspaso, un origen y un destino). El NIF se completa desde la lista de técnicos
  del tenant y no se escribe.
- Las series se eligen del inventario general del tenant (solo Disponibles); no se
  escriben en el formulario de asignación.
- Descripción y lote se completan desde el catálogo al elegir el material.
- Movimiento, Centro y Almacén son fijos y se autorrellenan:
  - Z31: asignación (el técnico recibe).
  - Z32: desasignación (el técnico cede).
  - Centro (PR05) y Almacén (BE03) son parámetros de la región. Hoy tienen el mismo
    valor en todas las regiones, pero no están fijados en el código.
- El recojo se registra por formulario, no por Excel.
- Los formatos de Excel se definen en `04-contratos/`, no en el código.

## 4. Principios técnicos
- El filtrado por tenant se aplica en el backend (y, si la base de datos lo permite,
  también en ella), nunca solo en la interfaz.
- Las reglas de negocio viven en el backend, no en el frontend.
- Toda operación que modifica stock es transaccional.
- Los valores configurables (longitud de serie, códigos Z31 y Z32, parámetros de
  región: Centro, Almacén y buzón) son configuración, no constantes en el código.
- Toda serie referencia a su tenant, y de ahí se obtiene su región.
- Cada criterio de aceptación de una spec tiene al menos una prueba.
- Idioma: interfaz y documentación en español; código en [por definir].

## 5. Método de trabajo
- Ciclo por funcionalidad: spec → plan → tareas → implementación.
- `spec.md` describe **qué** y cómo se valida; no menciona tecnología. `plan.md`
  describe **cómo**, dentro de la arquitectura definida.
- No se implementa nada que no esté en una spec aprobada.
- Si al implementar se descubre que la spec o la arquitectura están mal, se corrige
  el documento primero y luego el código.
- Las specs referencian las reglas de dominio; no las repiten.
- Cada spec declara su trazabilidad (historias, requisitos, atributos de calidad).

## 6. Qué NO hacer
- No modificar stock fuera de una operación auditada.
- No borrar movimientos ni ajustes.
- No aplicar parcialmente un Excel o un formulario con errores.
- No revelar a un tenant que una serie pertenece a otro.
- No agregar funcionalidades fuera de la spec "por si acaso".
- No permitir que el usuario edite NIF, Movimiento, Centro, Almacén, lote ni
  descripción en los formularios.

## 7. Glosario
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

## 8. Gobierno de este documento
- Cambia solo cuando cambia el negocio o una decisión técnica global.
- Todo cambio se anota con fecha y motivo, y se revisa el impacto en las specs existentes.


1. **Simplicidad primero**: Python 3.12+ y solo biblioteca estándar en la
   aplicación. Única dependencia de desarrollo permitida: pytest.
2. **La spec manda**: ningún comportamiento se implementa si no está en la
   spec activa. Si falta una decisión, se detiene el trabajo y se pregunta.
3. **Lógica separada de interfaz**: el núcleo (core) no imprime ni lee de
   consola. La CLI es una capa fina. Todo el core es testeable sin la CLI.
4. **Tests como puerta**: cada tarea termina con sus tests en verde.
   Prohibido avanzar con tests en rojo.
5. **Datos locales y transparentes**: persistencia en un único archivo JSON
   legible. Nada de bases de datos ni de red.
6. **Idioma**: código e identificadores en inglés; mensajes al usuario y
   documentación en español.



- **Stack:** Python 3.12+, Django (LTS), PostgreSQL, Celery con Redis,
  openpyxl para Excel, HTMX para la interfaz, pytest para pruebas.
- **Idioma del código:** inglés para nombres de código; interfaz y
  documentación en español.