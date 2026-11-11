# Spec 012 - Reportes Mensuales

Especificación técnica para la generación de reportes mensuales y exportación a Excel.

## 1. Propósito

Permitir que el Administrador de plataforma y los tiles generen reportes mensuales de auditoría y conciliación, y exportarlos a Excel. Los reportes incluyen cortes mensuales con totales de solicitados, asignados, liquidados/instalados y porcentaje no justificado (merma).

## 2. Alcance

- Generación de corte mensual con totales
- Cálculo de porcentaje no justificado (merma)
- Exportación a Excel de reportes de auditoría
- Exportación a Excel de reportes de conciliación mensual
- Consulta histórica de reportes

## 3. Actores

- **Administrador de plataforma (ACT-02)**: Genera reportes mensuales globales
- **Tenant (ACT-01)**: Genera reportes mensuales de su tenant

## 4. Trazabilidad

### Historias de Usuario
- **HU-28** (RF-68): Como Administrador de plataforma, quiero un corte mensual con totales (solicitados, asignados, liquidados/instalados, % no justificado/merma)
- **HU-29** (RF-69): Como tenant o Administrador de plataforma, quiero exportar reportes de auditoría y conciliación mensual en Excel

### Requisitos Funcionales
- **RF-68**: Generar un corte mensual con totales de solicitados, asignados, liquidados o instalados, y el porcentaje no justificado (merma)
- **RF-69**: Exportar a Excel los reportes de auditoría y conciliación mensual

### Atributos de Calidad
- RF-68: Exactitud (cálculo correcto de totales)
- RF-69: Compatibilidad (Excel estandarizado)

## 5. Requisitos Funcionales

### 5.1 Corte Mensual (RF-68)
- El sistema genera un corte mensual con los siguientes totales:
  - Solicitados: total de materiales solicitados en el mes
  - Asignados: total de materiales asignados a técnicos en el mes
  - Liquidados/Instalados: total de materiales liquidados o instalados en el mes
  - Porcentaje no justificado (merma): calculado como (no justificado / asignados) * 100
- El corte se puede generar por tenant o global (todos los tenants)
- El corte se puede generar por mes y año específicos

### 5.2 Cálculo de Merma
- La merma se calcula como: `(no justificado / asignados) * 100`
- No justificado = asignados - (liquidados + instalados + devueltos)
- El porcentaje indica la proporción de materiales que no fueron justificados

### 5.3 Exportación a Excel (RF-69)
- El sistema permite exportar reportes de auditoría mensual a Excel
- El sistema permite exportar reportes de conciliación mensual a Excel
- El Excel contiene los datos detallados del mes
- El formato es estandarizado y compatible con los sistemas de Lari

## 6. Requisitos No Funcionales

### 6.1 Rendimiento
- La generación del corte mensual debe ser eficiente
- La exportación a Excel debe ser rápida

### 6.2 Exactitud
- Los cálculos de totales deben ser precisos
- El porcentaje de merma debe calcularse correctamente

### 6.3 Compatibilidad
- El Excel debe ser compatible con los sistemas de Lari

## 7. Criterios de Aceptación

### CA-01: Corte Mensual con Totales
Dado un mes y año específicos
Cuando se genera el corte mensual
Entonces muestra solicitados, asignados, liquidados/instalados y % merma

### CA-02: Cálculo de Merma Correcto
Dado 100 asignados, 80 liquidados y 5 devueltos
Cuando se calcula la merma
Entonces muestra 15% no justificado

### CA-03: Exportación de Auditoría a Excel
Dado un reporte de auditoría mensual
Cuando se exporta a Excel
Entonces el archivo contiene todos los movimientos del mes

### CA-04: Exportación de Conciliación a Excel
Dado un reporte de conciliación mensual
Cuando se exporta a Excel
Entonces el archivo contiene todas las conciliaciones del mes

## 8. Datos de Salida

### Corte Mensual

| Campo | Descripción |
|---|---|
| Mes | Mes del reporte |
| Año | Año del reporte |
| Tenant | Tenant (si aplica) |
| Solicitados | Total de materiales solicitados |
| Asignados | Total de materiales asignados |
| Liquidados/Instalados | Total de materiales liquidados o instalados |
| Devueltos | Total de materiales devueltos |
| No justificado | Asignados - (Liquidados + Instalados + Devueltos) |
| % Merma | (No justificado / Asignados) * 100 |

### Reporte de Auditoría Mensual

| Campo | Descripción |
|---|---|
| Fecha | Fecha del movimiento |
| Usuario | Usuario que realizó el movimiento |
| Entidad | Tipo de entidad (StockTecnico, StockGeneral, Serie, etc.) |
| Acción | Acción realizada (asignación, traspaso, devolución, etc.) |
| Valor anterior | Valor antes del cambio |
| Valor nuevo | Valor después del cambio |

### Reporte de Conciliación Mensual

| Campo | Descripción |
|---|---|
| Fecha | Fecha de la conciliación |
| Estado | Estado de la conciliación |
| Diferencias series | Número de diferencias de series |
| Diferencias cantidades | Número de diferencias de cantidades |
| Ajustes aplicados | Número de ajustes aplicados |

## 9. Reglas de Negocio

1. El corte mensual calcula totales de solicitados, asignados, liquidados/instalados
2. La merma se calcula como porcentaje de no justificados sobre asignados
3. La exportación a Excel genera archivos estandarizados
4. Los reportes pueden ser por tenant o globales

## 10. Consideraciones de Implementación

- El corte mensual agrega movimientos del mes específico
- La exportación a Excel usa openpyxl
- Los cálculos se hacen con consultas eficientes a la base de datos
- Los reportes se pueden almacenar o generar a demanda
