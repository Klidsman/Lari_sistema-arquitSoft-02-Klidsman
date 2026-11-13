# Spec 013 — Registro de Materiales

## 1. Propósito

Permitir que cada tenant controle, mes a mes, el material disponible y el material usado por sus técnicos en las órdenes de instalación.

```text
disponible = saldo inicial + despachos del almacén
saldo final = disponible − material usado en órdenes
```

El saldo final de un mes es el saldo inicial del mes siguiente, salvo que exista una carga manual.

El módulo es independiente de la conciliación del Excel del almacén y no modifica el stock del sistema.

## 1.1 Trazabilidad

- **Historias:** HU-30, HU-31, HU-32 y HU-33.
- **Requisitos:** RF-70 a RF-78.
- **Cobertura:** carga masiva de órdenes, registro de materiales, saldos, despachos existentes, dashboard, cierre mensual y exportación.

## 2. Alcance

- Catálogo de materiales habilitado por tenant.
- Carga masiva de órdenes por técnico y mes.
- Registro de materiales usados por orden.
- Saldo inicial mensual manual.
- Lectura de los despachos del almacén ya registrados en `DespachoAlmacen`.
- Dashboard mensual por material y detalle por técnico.
- Panel de órdenes pendientes de materiales.
- Advertencias por cantidades atípicas.
- Cierre mensual con checklist, congelamiento y reapertura.
- Exportación del reporte mensual y del detalle de órdenes a Excel o CSV.

## 3. Actores y permisos

- **Tenant (ACT-01)**: única cuenta operativa del tenant. Es el único actor del módulo.
- El Administrador de plataforma y el Responsable de almacén no operan este módulo.
- Cada tenant solo ve y modifica sus propios datos.
- No se usan permisos Django por cadena; el rol y el tenant se validan en los servicios.

## 4. Conceptos

| Término | Significado |
|---|---|
| Catálogo habilitado | Materiales del catálogo compartido que el tenant puede usar en el módulo |
| Saldo inicial | Cantidad de un material al inicio de un mes |
| Despacho del almacén | Cantidad de material recogida en el mes, registrada en `DespachoAlmacen` |
| Orden | Orden de instalación identificada por número, técnico y mes |
| Uso | Cantidad de material consumida por un técnico en una orden |
| Disponible | Saldo inicial + despachos del mes |
| Saldo final | Disponible − uso del mes |
| Periodo | Mes `YYYY-MM` |
| Cierre | Congelamiento del saldo final de un mes y traspaso al mes siguiente |

## 5. Datos

### 5.1 Catálogo habilitado

- Cada tenant tiene una lista fija de materiales habilitados.
- Solo se pueden registrar usos y saldos de materiales habilitados y activos.
- Un material deshabilitado conserva su historial, pero no se ofrece en nuevas órdenes.
- El tenant puede activar o desactivar materiales desde la pantalla de catálogo.
- El catálogo referencia `materiales.Material`; no duplica códigos, descripciones ni lotes.

### 5.2 Despacho del almacén

- `DespachoAlmacen` ya forma parte de 013 y es la única fuente de despachos.
- Para el cálculo se usan `tenant`, `material`, `fecha` y `cantidad`.
- Los despachos no se registran de nuevo desde la pantalla de materiales.
- La fecha del despacho define el mes al que suma.
- La cantidad es un entero mayor o igual a 0.
- Un despacho con cantidad 0 se conserva, pero no suma.
- La guarda de mes cerrado se aplica también al alta/edición existente de `DespachoAlmacen`; no se modifica su estructura.
- El respaldo previo al cierre es una operación externa; la aplicación exige y registra su referencia.

### 5.3 Saldo inicial

- Se registra por tenant, material y periodo.
- La cantidad es un entero mayor o igual a 0.
- Solo existe un saldo inicial manual por tenant, material y periodo.
- Si no hay saldo manual, se usa el saldo final del periodo anterior.
- Si no hay periodo anterior con datos, el saldo inicial es 0.
- El saldo final de un mes cerrado pasa a ser el saldo inicial del mes siguiente.

### 5.4 Orden

- Se identifica por `(tenant, técnico, periodo, número de orden)`.
- El número de orden es obligatorio, de 1 a 30 caracteres alfanuméricos, sin espacios internos.
- El mismo número puede existir para otro técnico o en otro mes.
- Para un mismo técnico y mes, el número no se repite.
- La carga masiva pide el mes de las órdenes; por defecto el actual.
- El mes puede cambiarse al registrar la fecha de instalación de los materiales.
- Si la orden ya existe para el técnico y mes, se abre para editar; no se duplica.
- Una orden sin materiales registrados se considera pendiente.

### 5.5 Uso de material

- Relaciona una orden, un técnico, un material y una cantidad.
- Solo existe una línea por orden y material.
- La cantidad es un entero mayor o igual a 0.
- Vacío o 0 significa que el material no se usó.
- El técnico de la línea debe coincidir con el técnico de la orden.
- El uso se descuenta del disponible del mes.

### 5.6 Advertencia de cantidad atípica

- Si la cantidad usada supera un umbral configurable frente al promedio mensual de los últimos 3 meses cerrados del material, se registra una advertencia.
- El promedio se calcula con el total mensual usado por material, no con el promedio por orden.
- La advertencia no bloquea el guardado.
- Debe resolverse o justificarse antes del cierre mensual; una advertencia resuelta o con justificación de cierre no bloquea.

### 5.7 Cierre mensual

- El cierre congela el saldo por material.
- Antes de cerrar se revisa una lista de chequeo:
  - órdenes del mes sin materiales;
  - materiales con saldo negativo;
  - advertencias sin resolver.
- Solo se cierra si los puntos están resueltos o justificados.
- El cierre registra quién lo hizo, cuándo y la referencia del respaldo de base de datos.
- Un mes cerrado no admite cambios de órdenes, usos, saldos ni despachos.
- Para modificarlo se reabre con motivo; la reapertura queda auditada.

## 6. Reglas de negocio

1. **Aislamiento multitenant.** Un tenant nunca ve ni modifica datos de otro.
2. **Catálogo fijo por tenant.** Solo se opera con materiales habilitados y activos.
3. **Periodo de la orden.** Se obtiene del mes de carga y puede cambiar con la fecha de instalación.
4. **Unicidad de la orden.** No se repite `(tenant, técnico, periodo, número)`; el mismo número puede existir para otro técnico o mes.
5. **Carga masiva idempotente.** Pegar la misma lista varias veces solo agrega las órdenes nuevas para el técnico y mes.
6. **Orden de otro técnico.** Si el número existe para otro técnico, se crea para el técnico seleccionado y el resumen lo informa.
7. **Edición de orden existente.** Se abre para editar y se registra historial.
8. **Cantidades válidas.** Enteros mayores o iguales a 0; no se aceptan negativos, decimales ni texto.
9. **Saldo inicial mensual.** Manual si existe; si no, se hereda del final anterior.
10. **Cálculo del saldo final.** `inicial + despachos − uso`.
11. **Despachos existentes.** Se leen de `DespachoAlmacen`; no se registran dos veces.
12. **Bloqueo de negativo.** No se guarda un uso que deje el saldo del mes en negativo.
13. **Advertencia atípica.** Una cantidad muy alta se advierte, pero no se bloquea.
14. **Historial.** Toda edición de orden, uso o saldo registra usuario, fecha, valor anterior y valor nuevo.
15. **Sin borrado ordinario.** No se borran órdenes, usos, saldos ni despachos; la única excepción es deshacer una carga de órdenes nuevas sin materiales.
16. **Cierre y reapertura.** El cierre congela; la reapertura exige motivo y se audita.
17. **Exportación.** Reporte mensual y detalle de órdenes en Excel o CSV.
18. **Independencia.** No se lee, genera ni modifica la conciliación; no se modifica el stock.

## 7. Flujos

### 7.1 Registrar órdenes

1. El tenant elige **Registrar órdenes**.
2. Selecciona el técnico y el mes (por defecto el actual).
3. Pega la lista.
4. El sistema normaliza:
   - quita espacios al inicio y al final;
   - descarta líneas vacías;
   - rechaza líneas con más de un valor o espacios internos;
   - elimina duplicados sin distinguir mayúsculas/minúsculas.
5. Compara con las órdenes existentes del tenant.
6. Muestra el resumen:
   - leídas;
   - nuevas para el técnico y mes;
   - ya existentes para el técnico y mes;
   - cuántas también existen para otro técnico.
7. El tenant confirma.
8. El sistema crea solo las órdenes nuevas y registra el lote en `CargaOrdenes`.
9. El tenant puede deshacer la carga mientras las órdenes nuevas no tengan materiales.
10. El deshacer elimina solo las órdenes nuevas del lote y queda auditado.

### 7.2 Registrar materiales

1. El tenant elige **Registrar materiales**.
2. Selecciona el técnico y el mes (por defecto el actual).
3. Busca la orden por número exacto dentro de ese mes, sin distinguir mayúsculas/minúsculas.
4. Si no existe en ese mes, se muestra el catálogo habilitado con cantidades en 0; al guardar se crea la orden.
5. Si existe, se abre para editar.
6. Si el número existe para el mismo técnico en otro mes, no se muestra: es otra orden. Para abrirla, se selecciona ese otro mes.
7. Ingresa una sola fecha de instalación; por defecto hoy y editable.
8. La fecha define el mes de la orden. Si cambia el mes:
   - se revalida la clave;
   - se recalculan ambos meses;
   - si alguno está cerrado, se exige reapertura.
9. Registra solo cantidades usadas; vacío o 0 no suma.
10. El sistema calcula el disponible del mes y el uso total.
11. Si el uso superara el disponible, no guarda y muestra el faltante.
12. Si la cantidad es atípicamente alta, muestra una advertencia y permite guardar.
13. Al guardar, el uso se descuenta del disponible y queda asociado al técnico.
14. Cada cambio guarda historial.

### 7.3 Entradas y saldos

1. El tenant carga el saldo inicial manual por material y mes.
2. El sistema muestra los despachos del mes desde `DespachoAlmacen` en modo lectura.
3. No se registran despachos en esta pantalla.
4. Si se corrige un despacho en su pantalla de origen, el dashboard se recalcula.
5. Si el mes está cerrado, se exige reapertura para modificar el saldo.

### 7.4 Dashboard

1. El tenant filtra por mes, técnico, material o rango de fechas.
2. El sistema muestra:
   - saldo inicial;
   - despachos;
   - usado;
   - saldo final;
   - órdenes;
   - técnicos con uso.
3. Muestra tabla por material y detalle por técnico.
4. Un saldo final negativo se muestra con alerta.

### 7.5 Pendientes

1. El sistema lista las órdenes del mes sin materiales.
2. Se filtra por antigüedad (más de 1, 3, 7 o 30 días) y técnico.
3. Cada fila permite abrir el registro de materiales.

### 7.6 Cierre

1. El tenant entra a **Cierre mensual**.
2. El sistema muestra la lista de chequeo.
3. El tenant resuelve o justifica cada punto; las advertencias se resuelven con una justificación.
4. El respaldo se ejecuta fuera de la aplicación con el comando de operaciones; el sistema exige la referencia emitida.
5. El tenant confirma.
6. El sistema congela el saldo por material y lo pasa al mes siguiente.
7. Se registra quién cerró y cuándo.
8. Un mes cerrado no admite cambios.

### 7.7 Reapertura

1. El tenant solicita reabrir un mes cerrado.
2. Ingresa un motivo obligatorio.
3. El sistema registra usuario, fecha y motivo.
4. El mes vuelve a abrirse.
5. Se corrigen los datos y se vuelve a cerrar.

### 7.8 Exportación

1. El tenant elige reporte mensual o detalle de órdenes.
2. Selecciona Excel o CSV.
3. El sistema genera el archivo con datos de su tenant.
4. El archivo se descarga.

## 8. Criterios de aceptación

### CA-01: Menú y aislamiento
Dada la cuenta del tenant, cuando entra al módulo, entonces ve las opciones del módulo y solo opera con técnicos, materiales, órdenes y saldos de su tenant.

### CA-02: Catálogo habilitado
Dado un tenant con materiales habilitados, cuando registra una orden nueva, entonces ve solo los materiales activos de su catálogo con cantidades en 0.

### CA-03: Carga masiva normalizada
Dada una lista con espacios, líneas vacías, mayúsculas/minúsculas y duplicados, cuando se procesa, entonces se normaliza, se descartan vacías y se eliminan duplicados.

### CA-04: Carga masiva idempotente
Dada una lista con órdenes ya existentes para el técnico y mes, cuando se vuelve a pegar, entonces las existentes se omiten y no se duplican.

### CA-05: Orden de otro técnico
Dada una orden que existe para otro técnico, cuando se carga para el técnico seleccionado, entonces se crea para este y el resumen indica que también existe para el otro.

### CA-06: Resumen de carga
Dada una lista procesada, cuando se muestra el resumen, entonces indica leídas, nuevas, omitidas y cuántas también existen para otro técnico.

### CA-07: Deshacer carga
Dada una carga reciente sin materiales, cuando se deshace, entonces se eliminan solo las órdenes nuevas del lote y se audita.

### CA-08: Orden existente se abre
Dada una orden existente para el técnico y mes, cuando se busca, entonces se abre para editar y no se duplica.

### CA-09: Cambio de mes
Dada una orden con fecha de instalación en otro mes, cuando se guarda, entonces se recalcula el periodo y se revalida la clave.

### CA-10: Cantidad 0
Dada una cantidad vacía o 0, cuando se guarda, entonces el material no suma como usado.

### CA-11: Cantidad inválida
Dada una cantidad negativa, decimal o con letras, cuando se guarda, entonces se rechaza con el mensaje correspondiente.

### CA-12: Bloqueo de saldo negativo
Dado un disponible de 45 y un uso total de 40, cuando se intenta usar 10, entonces no se guarda porque faltan 5.

### CA-13: Advertencia atípica
Dada una cantidad muy superior al promedio del material, cuando se guarda, entonces se advierte pero no se bloquea.

### CA-14: Saldo final
Dado un mes con inicial 100, despachos 20 y usado 30, cuando se consulta el reporte, entonces el saldo final es 90.

### CA-15: Herencia de saldo
Dado un mes sin saldo manual y un mes anterior con final 90, cuando se consulta, entonces el inicial es 90.

### CA-16: Saldo manual prevalece
Dado un saldo inicial manual, cuando se consulta, entonces prevalece sobre la herencia y el cambio se audita.

### CA-17: Despachos existentes
Dado un despacho registrado en `DespachoAlmacen`, cuando se consulta el mes, entonces su cantidad suma sin volver a registrarse.

### CA-18: Historial de edición
Dada una edición de orden, uso o saldo, cuando se guarda, entonces queda un registro con usuario, fecha, valor anterior y valor nuevo.

### CA-19: Órdenes pendientes
Dada una orden sin materiales, cuando se consulta el panel, entonces aparece con filtro por antigüedad.

### CA-20: Cierre con checklist
Dado un mes con pendientes, negativos o advertencias sin resolver, cuando se intenta cerrar, entonces se bloquea hasta resolver o justificar.

### CA-21: Cierre y traspaso
Dado un mes cerrado, cuando se consulta el mes siguiente, entonces el saldo final congelado es su saldo inicial.

### CA-22: Reapertura
Dado un mes cerrado, cuando se reabre, entonces se exige motivo y queda registro de quién y cuándo.

### CA-23: Exportación
Dado un reporte mensual o detalle de órdenes, cuando se exporta, entonces se genera Excel o CSV solo con datos del tenant.

## 9. Casos borde

- Doble clic en guardar: la clave única evita duplicados.
- Cantidad con espacios: se normaliza.
- Número de orden con espacios al inicio/final: se recorta.
- Línea con más de un valor: se rechaza.
- Orden existente para otro técnico: se informa y se crea para el técnico actual.
- Cambio de fecha a otro mes: recalcula y revalida.
- Mes cerrado: exige reapertura.
- Material deshabilitado: no se usa en nuevas órdenes; historial conservado.
- Mes sin saldo inicial ni anterior: 0.
- Saldo final negativo: alerta; no se oculta.
- Despacho con cantidad 0: se registra, no suma.
- Orden sin materiales: pendiente para el cierre.
- Advertencia sin resolver: bloquea el cierre hasta justificar.

## 10. Decisiones confirmadas

1. `DespachoAlmacen` ya existe en 013 y es la fuente única de despachos.
2. El despacho solo aporta `tenant`, `material`, `fecha` y `cantidad`; no se vuelve a registrar.
3. La carga masiva pide el mes de las órdenes y permite cambiarlo al registrar materiales.
4. El mismo número de orden puede existir para otro técnico o en otro mes.
5. El bloqueo de saldos negativos es prioritario.
6. El cierre mensual con checklist es prioritario.
7. El respaldo de base de datos es externo; la app registra su referencia.
8. La advertencia de cantidad atípica usa 3 veces el promedio de los últimos 3 meses, configurable.
9. La modificación de un mes cerrado exige reapertura con motivo.
10. La exportación es a Excel o CSV.

## 11. Fuera de alcance

- Conciliación del Excel del almacén.
- Modificación del stock del sistema.
- Modificación de asignaciones, traspasos, recojos o catálogo compartido.
- Registro manual de despachos desde la pantalla de materiales.
- Importación de entradas por Excel.
- Reportes de otros módulos.
