# Spec 010 - Conciliación de Stock

Especificación técnica para la conciliación del stock del tenant contra el reporte de Lari.

## 1. Propósito

Permitir que los tenants carguen el reporte diario de Lari para conciliar su stock. El sistema compara el stock del tenant con el reporte, detecta diferencias, muestra alertas categorizadas y permite aprobar o rechazar la conciliación. Al aprobar, el stock se ajusta según el reporte de Lari.

## 2. Alcance

- Carga del reporte de Lari (Excel, ver `04-contratos/excel-conciliacion.md`)
- Comparación de stock del sistema vs reporte de Lari
- Detección de diferencias de series (en reporte/no en sistema, en sistema/no en reporte)
- Detección de diferencias de cantidades para no seriados
- Alertas visuales categorizadas de discrepancias
- Reglas de ausencia (técnicos y materiales)
- Aprobación o rechazo de la conciliación (todo o nada)
- Ajuste de stock al aprobar (series se crean/retiran, cantidades se actualizan)
- Actualización de stock de fungibles a la cantidad reportada por Lari
- Recálculo si el stock cambió entre carga y aprobación

## 3. Actores

- **Tenant (ACT-01)**: Carga el reporte, revisa diferencias y aprueba/rechaza la conciliación

## 4. Trazabilidad

### Historias de Usuario
- **HU-18** (RF-39): Como tenant, quiero cargar el reporte diario de la contrata en Excel `.xlsx`, para iniciar la conciliación
- **HU-19** (RF-42): Como tenant, quiero que el sistema compare series asignadas vs. series reportadas por la contrata, para detectar diferencias
- **HU-20** (RF-45): Como tenant, quiero que las series ya no reportadas se actualicen a estado instalado automáticamente, para reflejar la liquidación
- **HU-21** (RF-64): Como tenant, quiero que el stock de fungibles se actualice a la cantidad reportada por Lari
- **HU-22** (RF-42, RF-43): Como tenant, quiero alertas visuales categorizadas de discrepancias, para identificar material ajeno o técnicos con inconsistencias
- **HU-03** (RF-44): Como tenant, quiero aprobar o rechazar conciliación realizada con el reporte

### Requisitos Funcionales
- **RF-39**: Cargar el reporte de Lari crea una conciliación "En revisión" con las diferencias, sin cambiar el stock
- **RF-40**: Solo puede haber una conciliación en revisión por tenant a la vez
- **RF-41**: Reglas de ausencia: un técnico que no aparece en el reporte se ignora. Un material que falta a un técnico presente se asume en 0
- **RF-42**: Las diferencias de series se muestran en dos grupos, con el listado de cada serie: "en reporte, no en sistema" y "en sistema, no en reporte"
- **RF-43**: La aprobación bloquea si hay materiales del reporte que no existen en el catálogo
- **RF-44**: El tenant aprueba o rechaza la conciliación completa (todo o nada)
- **RF-45**: Al aprobar, las series del reporte que no existen en el sistema se crean en el técnico, y las que el sistema tiene y el reporte no traen se retiran
- **RF-46**: Al aprobar, cada ajuste registra valor anterior y valor nuevo
- **RF-47**: Si el stock de un técnico cambió entre la carga y la aprobación, el sistema recalcula y exige revisar de nuevo
- **RF-48**: Se rechaza el archivo completo si contiene técnicos desconocidos o que no pertenecen a la región del reporte; las filas de técnicos de otro tenant de la misma región se ignoran
- **RF-64**: El stock de fungibles se actualiza a la cantidad reportada por Lari

### Atributos de Calidad
- RF-39: Integridad (no cambia stock al cargar)
- RF-42: Usabilidad (alertas categorizadas)
- RF-44: Consistencia (todo o nada)
- RF-46: Trazabilidad (auditoría de ajustes)

## 5. Requisitos Funcionales

### 5.1 Carga del Reporte (RF-39)
- El tenant carga el reporte de Lari (Excel, ver `04-contratos/excel-conciliacion.md`)
- El sistema lee la hoja "GENERAL" del Excel
- El sistema filtra solo las filas donde el técnico pertenece al tenant
- Las filas con técnicos de otros tenants de la misma región se ignoran silenciosamente
- Las filas con técnicos desconocidos o de otra región rechazan el archivo completo
- Al cargar, se crea una conciliación en estado "En revisión"
- El stock no se modifica al cargar (solo se comparan)

### 5.2 Una Conciliación en Revisión a la Vez (RF-40)
- Solo puede haber una conciliación en estado "En revisión" por tenant
- Si el tenant intenta cargar un nuevo reporte mientras hay una en revisión, se rechaza
- El tenant debe aprobar o rechazar la conciliación actual antes de cargar otra

### 5.3 Reglas de Ausencia (RF-41)
- Si un técnico del tenant no aparece en el reporte, se ignora (no se asume 0)
- Si un técnico aparece en el reporte pero un material que tiene en el sistema no aparece, se asume cantidad 0
- Si el reporte contiene técnicos desconocidos o de otra región, se rechaza el archivo completo
  (RF-48); los técnicos de otro tenant de la misma región se ignoran

### 5.4 Diferencias de Series (RF-42)
- El sistema compara las series asignadas vs las series reportadas
- Las diferencias se muestran en dos grupos:
  - "En reporte, no en sistema": series que el reporte indica pero el sistema no tiene
  - "En sistema, no en reporte": series que el sistema tiene pero el reporte no indica
- Cada grupo lista cada serie afectada

### 5.5 Alertas Categorizadas (HU-22, RF-42, RF-43)
- Las diferencias se muestran con alertas visuales categorizadas
- Categorías:
  - Material ajeno: series en reporte que no están en el sistema
  - Técnicos con inconsistencias: técnicos con muchas diferencias
  - Series faltantes: series en sistema que no están en reporte
- Si hay materiales del reporte que no existen en el catálogo, la aprobación se bloquea (RF-43)

### 5.6 Aprobación/Rechazo (RF-44)
- El tenant aprueba o rechaza la conciliación completa
- No se pueden aprobar parcialmente algunos ajustes
- Regla de todo o nada

### 5.7 Ajustes al Aprobar (RF-45, RF-64)
- Al aprobar:
  - Para seriados:
    - Las series del reporte que no existen en el sistema se crean en el técnico
    - Las series que el sistema tiene y el reporte no traen se retiran (o marcan como instaladas)
  - Para no seriados:
    - El stock del técnico se actualiza a la cantidad reportada en "Libre utilización"
    - No se calcula consumo; se toma directamente la cantidad del reporte
- Cada ajuste registra valor anterior y valor nuevo (RF-46)

### 5.8 Recálculo si Hubo Cambios (RF-47)
- Si el stock de un técnico cambió entre la carga y la aprobación:
  - El sistema recalcula las diferencias
  - Exige que el tenant revise de nuevo antes de aprobar
  - Muestra un aviso de que hubo cambios

### 5.9 Validación de Técnicos (RF-48)
- Si el reporte contiene técnicos desconocidos o que no pertenecen a la región del reporte, se
  rechaza el archivo completo
- Las filas de técnicos de otro tenant de la misma región se ignoran silenciosamente

## 6. Requisitos No Funcionales

### 6.1 Rendimiento
- La carga del reporte debe ser eficiente para grandes volúmenes
- La comparación de series debe ser rápida
- El recálculo de diferencias debe ser rápido

### 6.2 Usabilidad
- Las alertas visuales deben ser claras y categorizadas
- El aviso de cambios debe ser visible
- La interfaz debe permitir revisar las diferencias en detalle

### 6.3 Integridad
- La carga no modifica stock
- La aprobación es transaccional
- No se pueden tener conciliaciones parciales

## 7. Criterios de Aceptación

### CA-01: Carga Crea Conciliación En Revisión
Dado un reporte de Lari válido
Cuando el tenant carga el archivo
Entonces se crea una conciliación en estado "En revisión" sin modificar stock

### CA-02: Solo Una Conciliación en Revisión
Dado un tenant con una conciliación en revisión
Cuando intenta cargar otro reporte
Entonces se rechaza la carga

### CA-03: Técnico Ausente se Ignora
Dado un técnico del tenant que no aparece en el reporte
Cuando el sistema procesa el reporte
Entonces el técnico se ignora (no se asume 0)

### CA-04: Material Ausente se Asume 0
Dado un técnico en el reporte sin un material que tiene en el sistema
Cuando el sistema procesa el reporte
Entonces se asume cantidad 0 para ese material

### CA-05: Diferencias de Series se Muestran
Dado un reporte con diferencias de series
Cuando el sistema compara
Entonces muestra dos grupos: "en reporte, no en sistema" y "en sistema, no en reporte"

### CA-06: Alertas Categorizadas
Dado un reporte con diferencias
Cuando el sistema muestra las alertas
Entonces categoriza por material ajeno, técnicos con inconsistencias, series faltantes

### CA-07: Aprobación Bloquea si Material No Existe
Dado un reporte con un material que no está en el catálogo
Cuando el tenant intenta aprobar
Entonces la aprobación se bloquea

### CA-08: Aprobación Todo o Nada
Dado una conciliación con diferencias
Cuando el tenant aprueba
Entonces todos los ajustes se aplican o ninguno

### CA-09: Ajustes al Aprobar
Dado una conciliación aprobada
Cuando se consulta el stock
Entonces se actualizó según el reporte de Lari

### CA-10: Auditoría de Ajustes
Dado una conciliación aprobada
Cuando se consulta la auditoría
Entonces cada ajuste registra valor anterior y valor nuevo

### CA-11: Recálculo si Hubo Cambios
Dado que el stock cambió entre carga y aprobación
Cuando el tenant intenta aprobar
Entonces el sistema recalcula y exige revisar de nuevo

### CA-12: Técnico No Pertenece Rechaza Archivo
Dado un reporte con un técnico desconocido o que no pertenece a la región
Cuando el tenant carga el archivo
Entonces se rechaza el archivo completo; un técnico de otro tenant de la misma región se ignora

## 8. Datos de Entrada

### Carga de Reporte

- Archivo Excel `.xlsx` (no `.xls`, CSV ni texto tabulado)
- Formato definido en `04-contratos/excel-conciliacion.md`

## 9. Datos de Salida

### Conciliación

| Campo | Descripción |
|---|---|
| ID de conciliación | Identificador único de la conciliación |
| Estado | En revisión, Aprobada, Rechazada |
| Fecha carga | Fecha y hora de carga del reporte |
| Fecha aprobación | Fecha y hora de aprobación (si aplica) |
| Archivo | Nombre del archivo reporte |
| Diferencias series | Lista de series "en reporte, no en sistema" |
| Diferencias series | Lista de series "en sistema, no en reporte" |
| Diferencias cantidades | Lista de materiales con diferencias de cantidad |
| Alertas | Alertas categorizadas de discrepancias |

## 10. Reglas de Negocio

1. El reporte de Lari prevalece sobre el stock del sistema al aprobar
2. Cargar el reporte no modifica stock
3. Solo una conciliación en revisión por tenant
4. Técnico ausente del reporte se ignora
5. Material ausente a técnico presente se asume 0
6. Las diferencias se muestran en dos grupos
7. Aprobación es todo o nada
8. Stock de fungibles se actualiza a la cantidad reportada
9. Si el stock cambió entre carga y aprobación, se recalcula
10. Técnicos desconocidos o de otra región rechazan el archivo; los de otro tenant de la misma región se ignoran

## 11. Consideraciones de Implementación

- La lectura del Excel usa openpyxl
- La comparación de series usa índices para rendimiento
- El filtrado por tenant se hace al leer el Excel
- La aprobación usa transacción para asegurar todo o nada
- El recálculo de diferencias se puede hacer a demanda o en background
- La actualización de stock usa funciones de spec 008
