# Spec 009 - Traspaso entre Técnicos

Especificación técnica para el traspaso de materiales entre técnicos del mismo tenant, con origen y
destino múltiples en forma 1→N o N→1.

## 1. Propósito

Permitir que los técnicos de un tenant se traspasen materiales entre sí usando el **stock actual de
cada técnico**. Un traspaso puede ser de **un técnico a uno o varios técnicos** o de **varios técnicos
a un técnico**, siempre con al menos dos técnicos distintos implicados. El sistema genera un Excel de
dos hojas (Desasignación Z32 y Asignación Z31), requiere confirmación del almacén y no modifica el
stock general del tenant.

## 2. Alcance

- Creación de solicitudes de traspaso entre técnicos del mismo tenant
- Selección de series/cantidades desde el stock actual de cada técnico origen
- Estructura 1→N (un origen, varios destinos) o N→1 (varios orígenes, un destino)
- Validación de disponibilidad por técnico origen
- Generación automática de Excel de dos hojas (ver `04-contratos/excel-traspaso.md`)
- Cambio de técnico de las series y del stock técnico al confirmar
- No modificación del stock general del tenant
- Inicio del conteo de días en mano para seriados (al confirmar)
- Interfaz con listas de stock actual del técnico origen y del técnico destino

## 3. Actores

- **Tenant (ACT-01)**: Crea solicitudes de traspaso entre sus técnicos
- **Responsable de almacén (ACT-03)**: Confirma o rechaza los traspasos

## 4. Trazabilidad

### Requisitos Funcionales
- **RF-33**: Un traspaso mueve materiales entre técnicos del mismo tenant, con un Excel de dos hojas: Desasignación (Z32) y Asignación (Z31)
- **RF-34**: Un traspaso debe implicar al menos dos técnicos distintos y adoptar la forma 1→N o N→1; ningún técnico puede ser origen y destino de la misma línea
- **RF-35**: Cada origen solo puede ceder materiales y series que tiene asignados, descontando lo reservado
- **RF-36**: Lo que sale de cada técnico debe cuadrar con lo que entra en su destino, por material y por serie. Si no cuadra, se rechaza todo
- **RF-37**: El Responsable de almacén acepta o rechaza el traspaso. Al aceptar, las series cambian de técnico y el stock se mueve por línea. Al rechazar, no cambia nada
- **RF-38**: Un traspaso no modifica el stock general del tenant
- **RF-39**: La interfaz muestra el stock actual de los técnicos de origen y de destino para elegir qué desasignar y qué requiere el traspaso

### Atributos de Calidad
- RF-35: Consistencia (validación de disponibilidad)
- RF-36: Integridad (cuadre de lo que sale y entra)
- RF-38: Consistencia (stock general invariable)
- RF-39: Usabilidad (stock visible antes de elegir)

## 5. Requisitos Funcionales

### 5.1 Traspaso entre Técnicos del Mismo Tenant (RF-33)
- Un traspaso mueve materiales entre técnicos del mismo tenant
- No existen traspasos entre tenants
- Al enviar, el sistema genera un Excel de dos hojas:
  - Hoja 1: Desasignación (Z32), agrupada por técnico origen
  - Hoja 2: Asignación (Z31), agrupada por técnico destino

### 5.2 Variedad y Forma del Traspaso (RF-34)
- Un traspaso debe implicar **al menos dos técnicos distintos**
- Formas admitidas:
  - **1→N**: un único técnico origen entrega a uno o varios destinos
  - **N→1**: varios técnicos origen entregan a un único destino
- No se admite un traspaso con varios orígenes y varios destinos a la vez
- Ninguna línea puede tener el mismo técnico como origen y destino
- Si no se cumple la forma, se rechaza la solicitud

### 5.3 Disponibilidad en el Origen (RF-35)
- Cada técnico origen solo puede ceder materiales y series que tiene asignados
- La disponibilidad se calcula **por técnico y material**, descontando lo reservado en traspasos
  pendientes
- Solo se pueden traspasar series en estado Asignada al técnico origen
- Fórmula: `Disponible(tecnico, material) = StockTecnico(tecnico, material) - Reservado(tecnico, material)`
- Varias líneas del mismo origen y material se agregan antes de comparar con el disponible

### 5.4 Cuadre de Lo que Sale y Entra (RF-36)
- Lo que sale de cada técnico origen debe cuadrar con lo que entra en el destino de cada línea
- El cuadre se hace por material, por lote y por serie
- Si no cuadra, se rechaza todo el traspaso
- Ejemplo de cuadre:
  - Por serie: la serie ABC123 sale del origen A y entra en el destino B
  - Por material: 50 unidades de cable salen de A y 50 entran en B
- La suma de salidas de todos los orígenes es igual a la suma de entradas de todos los destinos

### 5.5 Confirmación del Almacén (RF-37)
- El Responsable de almacén acepta o rechaza el traspaso
- Al aceptar, **por cada línea**:
  - Las series cambian del técnico origen al técnico destino de esa línea
  - El stock del origen de la línea baja
  - El stock del destino de la línea sube
  - Se inicia el conteo de días en mano para seriados (RF-62)
- Al rechazar:
  - No cambia nada
  - Las series siguen en su técnico origen
  - Se requiere un comentario del motivo

### 5.6 Stock General Invariable (RF-38)
- Un traspaso no modifica el stock general del tenant
- Solo se mueve material entre técnicos
- El total del tenant no cambia con traspasos

### 5.7 Stock Visible en la Interfaz (RF-39)
- La pantalla de traspaso se organiza en tres columnas:
  1. **Técnico que entrega**: se elige un técnico.
  2. **Materiales en mano**: solo se muestran los materiales del técnico elegido, con su cantidad
     en mano; para no seriados se digita la cantidad y para seriados se marcan las series.
  3. **Técnicos que reciben**: se marcan uno o varios técnicos y se revisa el resumen de lo que
     recibirán.
- La lista de stock muestra material, descripción, lote, tipo y cantidad
- El stock del técnico origen sirve para elegir qué desasignar
- El resumen del traspaso muestra los materiales y series que recibirá cada técnico seleccionado
- La consulta es de solo lectura, filtrada por el tenant de la sesión

## 6. Requisitos No Funcionales

### 6.1 Consistencia
- La validación de cuadre debe ser precisa
- El stock general no debe modificarse nunca

### 6.2 Rendimiento
- La validación de disponibilidad debe ser rápida y agrupar por técnico y material
- La generación del Excel de dos hojas debe ser eficiente

### 6.3 Integridad
- El traspaso debe ser transaccional
- No se pueden tener traspasos parciales

## 7. Criterios de Aceptación

### CA-01: Traspaso entre Técnicos del Mismo Tenant
Dado un tenant con dos técnicos
Cuando el tenant crea y envía un traspaso entre ellos
Entonces el sistema genera el Excel de dos hojas

### CA-02: Origen y Destino Distintos y Variedad de Técnicos
Dado que el usuario selecciona el mismo técnico como origen y destino de una línea
Cuando el sistema valida
Entonces rechaza la solicitud
Dado un traspaso que no implica al menos dos técnicos distintos o que mezcla varios orígenes con varios destinos
Entonces el sistema lo rechaza por estructura inválida

### CA-03: Solo Cede lo que Tiene Asignado
Dado un técnico origen con stock de 10
Cuando intenta traspasar 15
Entonces el sistema rechaza por insuficiente

### CA-04: Cuadre de Series
Dado un traspaso con serie ABC123 que sale pero no entra
Cuando el sistema valida
Entonces rechaza el traspaso

### CA-05: Cuadre de Cantidades
Dado un traspaso con 50 unidades que salen pero 40 entran
Cuando el sistema valida
Entonces rechaza el traspaso

### CA-06: Confirmación Cambia de Técnico
Dado un traspaso confirmado
Cuando se consulta el técnico de las series
Entonces cada serie está en el técnico destino de su línea

### CA-07: Rechazo No Cambia Nada
Dado un traspaso rechazado
Cuando se consulta el técnico de las series
Entonces las series siguen en su técnico origen

### CA-08: Stock General Invariable
Dado un traspaso confirmado
Cuando se consulta el stock general del tenant
Entonces no cambió

### CA-09: Días en Mano Reinician al Traspasar
Dado una serie con 10 días en mano en el técnico origen
Cuando se confirma el traspaso
Entonces reinicia el conteo en el técnico destino (RF-62)

### CA-10: Traspaso 1→N
Dado un técnico origen con stock de dos materiales
Cuando el tenant traspasa un material a un técnico y otro material a otro técnico
Entonces el sistema acepta la solicitud y cada destino recibe solo sus líneas

### CA-11: Traspaso N→1
Dados dos técnicos origen con stock
Cuando el tenant traspasa materiales de ambos a un único técnico destino
Entonces el sistema acepta la solicitud, descuenta a cada origen y suma todo al destino

### CA-12: Stock Visible Antes de Elegir
Dado un técnico con stock registrado
Cuando el usuario consulta su stock en la pantalla de traspaso
Entonces ve material, descripción, lote, tipo y cantidad, sin poder modificarlo

## 8. Datos de Entrada

### Formulario de Traspaso

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| Forma del traspaso | Select | Sí | `1→N` (un técnico a varios) o `N→1` (varios a uno) |
| Fecha | Date | Sí | Fecha del traspaso (por defecto: hoy) |
| Técnico para consultar stock | Select | No | Carga la lista de stock del técnico (solo lectura) |
| Línea: técnico origen | Select | Sí | Técnico que cede en esa línea |
| Línea: técnico destino | Select | Sí | Técnico que recibe en esa línea; distinto del origen |
| Línea: material | Select | Condicional | Material del catálogo |
| Línea: tipo de material | Read-only | Condicional | Seriado o no seriado (del catálogo) |
| Línea: lote | Read-only | Condicional | Lote del material (del catálogo) |
| Línea: series | Multi-select | Condicional | Series del técnico origen (solo para seriados) |
| Línea: cantidad | Number | Condicional | Cantidad (solo para no seriados) |

## 9. Datos de Salida

### Solicitud de Traspaso

| Campo | Descripción |
|---|---|
| ID de solicitud | Identificador único de la solicitud |
| Estado | Borrador, Enviada, Confirmada, Rechazada, Cancelada |
| Técnicos origen | Técnicos que ceden, derivados de las líneas |
| Técnicos destino | Técnicos que reciben, derivados de las líneas |
| Fecha | Fecha de creación |
| Líneas | Lista de líneas, cada una con técnico origen, técnico destino, material, series o cantidad |
| Excel | Ruta del archivo Excel generado |
| Hash SHA-256 | Firma del Excel |

## 10. Reglas de Negocio

1. Un traspaso es entre técnicos del mismo tenant
2. Un traspaso implica al menos dos técnicos distintos
3. Un traspaso es 1→N o N→1; no se mezclan varios orígenes con varios destinos
4. Ninguna línea tiene el mismo técnico como origen y destino
5. Cada origen solo puede ceder lo que tiene asignado
6. Lo que sale de cada origen debe cuadrar con lo que entra en el destino de la línea
7. Al confirmar, las series y el stock se mueven según el origen y destino de cada línea
8. Al rechazar, no cambia nada
9. El stock general del tenant no cambia
10. Los días en mano reinician al traspasar (RF-62)
11. La interfaz muestra el stock actual de los técnicos consultados, filtrado por tenant

## 11. Consideraciones de Implementación

- La validación de disponibilidad consulta el stock del técnico origen de cada línea
- El cuadre se valida al crear la solicitud (no solo al confirmar)
- La generación del Excel de dos hojas usa openpyxl y agrupa por técnico
- El cambio de técnico de series actualiza `series.Serie.tecnico` y reinicia `series.Serie.asignada_en`; la migración de esos campos se coordina con las specs 004/005/008/011
- El stock general no se toca en ningún momento
- La actualización de stock técnico se hace con las funciones de spec 008
