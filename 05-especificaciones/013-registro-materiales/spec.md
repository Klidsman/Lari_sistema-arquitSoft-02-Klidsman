# Spec: Registro de materiales usados por técnicos y saldo mensual

## Trazabilidad
- Historias: HU-30, HU-31, HU-32, HU-33.
- Requisitos: RF-70 a RF-78.
- Atributos de calidad: integridad de datos, auditabilidad, aislamiento multitenant, usabilidad.

## Dependencias
- Spec 001: tenants, cuentas de acceso y alcance.
- Spec 002: catálogo de materiales.
- Spec 003: técnicos con NIF `LAXXXX`.
- Spec 004: recojo de materiales.
- Reglas: `03-reglas-de-dominio/registro-materiales.md`, `auditoria.md` y `stock.md` (solo como referencia; este módulo no modifica el stock).

## Objetivo
Permitir que cada tenant registre el material usado por sus técnicos en cada orden de liquidación y calcule, por mes, el saldo final de cada material a partir del saldo inicial, los despachos del almacén y el material usado.

## Alcance
- Catálogo de materiales habilitado por tenant.
- Saldo inicial mensual por material, cargado manualmente.
- Despachos del almacén registrados individualmente y vinculados a un recojo del sistema.
- Órdenes de liquidación por técnico y mes.
- Uso de materiales por orden y por técnico.
- Reporte mensual por material y detalle por técnico.
- Historial de cambios de órdenes, saldos iniciales y despachos.

## Actores y permisos
- Usuario del tenant con permiso para registrar materiales.
- La cuenta del tenant solo puede ver y modificar datos de su propio tenant.
- El Administrador de plataforma y el Responsable de almacén no operan este módulo, salvo que la spec 001 defina otra cosa.

## Conceptos
| Término | Significado |
|---|---|
| Catálogo habilitado | Lista fija de materiales que un tenant puede usar en este módulo |
| Saldo inicial | Cantidad de un material al inicio de un mes |
| Despacho del almacén | Salida de material registrada en el sistema y respaldada por un recojo |
| Uso | Cantidad de material consumida por un técnico en una orden |
| Saldo final | Saldo inicial + despachos del mes - uso del mes |
| Orden de liquidación | Orden identificada por un número, un técnico y una fecha |
| Periodo | Mes al que pertenece una orden o un saldo, con formato `YYYY-MM` |

## Datos

### Catálogo habilitado
- Cada tenant tiene una lista fija de materiales habilitados.
- Solo se pueden registrar usos y saldos de materiales habilitados y activos.
- Un material deshabilitado conserva su historial, pero no se puede usar en nuevas órdenes.

### Saldo inicial
- Se registra por tenant, material y periodo.
- La cantidad es un entero mayor o igual a 0.
- Solo existe un saldo inicial por tenant, material y periodo.
- Si el periodo no tiene saldo inicial cargado, se usa el saldo final del periodo anterior.
- Si no existe periodo anterior, el saldo inicial es 0.

### Despacho del almacén
- Se registra individualmente.
- Tiene fecha, material, cantidad y referencia al recojo del sistema.
- La cantidad es un entero mayor o igual a 0.
- El recojo y la línea de recojo deben pertenecer al tenant.
- La cantidad acumulada de despachos de una línea no puede superar la cantidad registrada en esa línea del recojo.

### Orden de liquidación
- Se identifica por tenant, técnico, número de orden y periodo.
- El número de orden es obligatorio.
- El periodo se obtiene de la fecha de liquidación.
- Una orden es única por técnico y mes.
- Si la cuenta del tenant ingresa una orden que ya existe para ese técnico y mes, se abre para editar; no se crea un duplicado.
- La misma orden puede existir en otro técnico o en otro mes.

### Uso de material
- Cada línea relaciona una orden, un técnico `LAXXXX`, un material y una cantidad.
- La cantidad es un entero mayor o igual a 0.
- Vacío o 0 significa que el material no se usó.
- Solo existe una línea por orden y material.
- El técnico de la línea debe coincidir con el técnico de la orden.

## Reglas de negocio

1. **Aislamiento multitenant.** Un tenant nunca ve ni modifica órdenes, saldos, despachos, usos o reportes de otro tenant.
2. **Catálogo fijo por tenant.** Cada tenant solo opera con sus materiales habilitados.
3. **Periodo de la orden.** El periodo de uso se obtiene únicamente de la fecha de liquidación de la orden.
4. **Unicidad de la orden.** No puede existir más de una orden con el mismo número para el mismo técnico y mes.
5. **Edición de orden existente.** Si al ingresar una orden se encuentra una coincidencia, se abre para editar y se registra el historial de los cambios.
6. **Cantidades válidas.** Toda cantidad debe ser un entero mayor o igual a 0. No se aceptan negativos, decimales ni texto.
7. **Saldo inicial mensual.** Cada mes puede tener un saldo inicial manual por material.
8. **Herencia del saldo.** Si un mes no tiene saldo inicial manual, el saldo inicial es el saldo final del mes anterior.
9. **Cálculo del saldo final.** `Saldo final = Saldo inicial + Despachos del mes - Uso del mes`.
10. **Despacho vinculado al recojo.** Todo despacho debe referenciar un recojo registrado en el sistema y no puede superar la cantidad de su línea.
11. **Uso por técnico.** El uso se registra por orden y por técnico `LAXXXX`; no se registra uso sin orden.
12. **Historial.** Toda edición de orden, saldo inicial o despacho registra usuario, fecha, valor anterior y valor nuevo.
13. **Sin borrado.** No se borran órdenes, usos, saldos ni despachos. Las correcciones se registran como cambios auditados.
14. **Independencia de conciliación.** Este módulo no lee, genera ni modifica la conciliación del Excel del almacén. Tampoco modifica el stock del sistema.

## Flujo de registro
1. La cuenta del tenant entra a “Registrar materiales”.
2. Selecciona un técnico del tenant.
3. Escribe el número de orden y la fecha de liquidación.
4. Presiona Enter.
5. El sistema busca la orden:
   - Si no existe, muestra el catálogo habilitado con cantidades en 0.
   - Si ya existe para ese técnico y mes, la abre para editar.
6. La cuenta del tenant llena solo la cantidad usada. Vacío o 0 significa no usado.
7. Guarda la orden.
8. El sistema conserva el técnico y la fecha, limpia el número de orden y deja el cursor listo para la siguiente orden.
9. La cuenta del tenant repite con el siguiente número de orden.
10. Al cambiar de técnico, se reinicia el formulario.

## Criterios de aceptación

- Dada la cuenta del tenant, cuando entra al sistema, entonces ve la opción “Registrar materiales” y solo puede seleccionar técnicos y materiales de su tenant.
- Dado un técnico `LA1234`, un número de orden y una fecha, cuando presiona Enter, entonces aparece el catálogo habilitado con cantidades en 0.
- Dado un técnico con una orden ya registrada en el mismo mes, cuando se ingresa el mismo número de orden, entonces se abre la orden existente para editar y no se crea un duplicado.
- Dado el mismo número de orden para otro técnico o para otro mes, cuando se guarda, entonces se permite porque la clave es distinta.
- Dada una cantidad vacía o 0, cuando se guarda la orden, entonces el material no suma como usado.
- Dada una cantidad negativa, decimal o con letras, cuando se guarda, entonces se rechaza con “La cantidad debe ser un número entero mayor o igual a 0”.
- Dado un mes con saldo inicial 100, despachos 20 y usado 30, cuando se consulta el reporte, entonces el saldo final es 90.
- Dado un mes sin saldo inicial cargado y con un mes anterior cuyo saldo final fue 90, cuando se consulta el reporte, entonces el saldo inicial del mes es 90.
- Dado un saldo inicial manual cargado para un mes, cuando se consulta el reporte, entonces ese valor prevalece y el cambio queda auditado.
- Dado un despacho vinculado a un recojo del tenant, cuando se guarda, entonces se registra y suma al mes correspondiente a su fecha.
- Dado un despacho vinculado a un recojo de otro tenant, cuando se guarda, entonces se rechaza.
- Dada una cantidad despachada mayor a la cantidad de la línea del recojo, cuando se guarda, entonces se rechaza.
- Dado un uso con un técnico distinto al técnico de la orden, cuando se guarda, entonces se rechaza.
- Dada una edición de una orden, saldo inicial o despacho, cuando se guarda, entonces queda un registro con fecha, usuario, valor anterior y valor nuevo.
- Dada la cuenta de otro tenant, cuando intenta consultar o modificar una orden, saldo, despacho o reporte, entonces no puede acceder y no se revela la existencia del dato.
- Dado un mes con uso y despachos, cuando se consulta el reporte, entonces se muestra el total por material y el detalle de uso por técnico.

## Casos borde
- Doble clic en Guardar: la restricción única evita duplicados; si la orden ya existe, se abre para editar.
- Cantidad con espacios: se normaliza antes de validar.
- Número de orden con espacios al inicio o al final: se recorta.
- Cambio de fecha de una orden a otro mes: se recalcula el periodo y se vuelve a validar la unicidad.
- Saldo inicial duplicado para el mismo mes: se actualiza el existente y se audita el cambio.
- Material deshabilitado: no se puede usar en nuevas órdenes, pero su historial se conserva.
- Mes sin saldo inicial ni periodo anterior: el saldo inicial es 0.
- Saldo final negativo: se muestra con alerta; no se oculta.
- Despacho con cantidad 0: se registra, pero no suma al total.
- Recojo sin línea identificada: se rechaza el despacho hasta que se seleccione la línea.
- Técnico desactivado con órdenes históricas: sus órdenes se conservan y se pueden consultar.

## Decisiones confirmadas
1. El catálogo habilitado referencia el catálogo compartido de la spec 002; no duplica descripciones ni códigos.
2. El número de orden tiene entre 1 y 30 caracteres alfanuméricos, sin espacios internos.
3. La frecuencia diaria, semanal o mensual es una forma de consultar o cargar entradas; el reporte siempre es mensual y no se guarda como atributo obligatorio.
4. Un saldo final negativo se muestra con alerta y no bloquea el registro.
5. El permiso del módulo se asigna a la cuenta única del tenant definida en la spec 001.

## Dependencia confirmada
- La spec 004 define las entidades de recojo y línea de recojo; este módulo solo las referencia.

## Fuera de alcance
- Conciliación del Excel del almacén.
- Importación de entradas por Excel.
- Modificación del stock del sistema.
- Modificación de recojos, asignaciones, traspasos o catálogo.
- Reportes de otros módulos.
- Exportación a Excel o PDF.
