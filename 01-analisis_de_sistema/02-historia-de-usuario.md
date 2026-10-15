# 02 - Historias de Usuario


## Módulo 1: Seguridad, Autenticación y Control de Accesos

- **HU-01** (RF-02, RF-51): Como **Administrador de plataforma (ACT-02)**, quiero registrar regiones y su almacén con Centro, Almacén y buzón, para que cada región tenga su punto de entrega.
- **HU-02** (RF-12, RF-13): Como **tenant (ACT-01)**, quiero registrar a mis técnicos con su NIF (LAxxxx), para poder asignarles materiales.
- **HU-03** (RF-44): Como **tenant (ACT-01)**, quiero aprobar o rechazar conciliación realizada con el reporte.
- **HU-04** (RF-04): Como **Almacén (ACT-03)**, quiero ver solo las solicitudes de mi región, para responderlas.

## Módulo 2: Catálogo y Gestión del Almacén Central

- **HU-05** (RF-06, RF-11): Como **tenant (ACT-01)**, quiero registrar un material nuevo con código (11 dígitos), descripción, lote y tipo (seriado o no seriado).
- **HU-06** (RF-07, RF-08): Como **tenant (ACT-01)**, quiero buscar materiales por código o descripción en el catálogo completo, para elegirlos en los formularios de asignacion.
- **HU-07** (RF-09, RF-10): Como **Almacén (ACT-03)**, quiero editar su descripción, lote y codigo de material, para corregir datos de Lari.

## Módulo 3: Asignación, Despacho

- **HU-08** (RF-21, RF-22, RF-23): Como **tenant (ACT-01)**, quiero armar una asignacion con equipos serializados específicos y material fungible, validando existencia en stock.
- **HU-09** (RF-63): Como **tenant (ACT-01)**, quiero ser alertado si un técnico supera su cupo máximo de equipos sin liquidar, para cumplir la política de custodia.
- **HU-10** (RF-25): Como **tenant (ACT-01)**, quiero que el sistema genere automáticamente el Excel estandarizado de despacho (metadatos de cuadrilla, tabla de seriales, tabla de material menor), para estandarizar documentos.
- **HU-11** (RF-21): Como **tenant (ACT-01)**, quiero asignar materiales a mis tecnicos.
- **HU-12** (RF-28): Como **tenant (ACT-01)**, quiero que el Excel se guarde de forma inmutable con firma SHA-256, para garantizar su integridad.
- **HU-13** (RF-61): Como **tenant (ACT-01)**, quiero ver los dias en mano que tiene un equipo seriado.



## Módulo 4: Mensajería Interna y Confirmación de Entrega Física

- **HU-14** (RF-29, RF-30): Como **Almacén (ACT-03)**, quiero una bandeja de despachos en tiempo real con notificaciones sonoras y visuales, para atender solicitudes inmediatamente.
- **HU-15** (RF-28): Como **Almacén (ACT-03)**, quiero previsualizar detalles y descargar el Excel original, para revisar antes de confirmar.
- **HU-16** (RF-29, RF-32): Como **Almacén (ACT-03)**, quiero confirmar la asignacion.
- **HU-17** (RF-29, RF-31): Como **Almacén (ACT-03)**, quiero rechazar o solicitar corrección de una asignacion con motivo, notificando al remitente, para cuando un serial no coincida o cantidades no cuadren.

## Módulo 5: Conciliación Diaria por Diferencias

- **HU-18** (RF-39): Como **tenant (ACT-01)**, quiero cargar el reporte diario de la contrata (Excel, CSV o texto tabulado), para iniciar la conciliación.
- **HU-19** (RF-42): Como **tenant (ACT-01)**, quiero que el sistema compare series asignadas vs. series reportadas por la contrata, para detectar diferencias.
- **HU-20** (RF-45): Como **tenant (ACT-01)**, quiero que las series ya no reportadas se actualicen a estado instalado automáticamente, para reflejar la liquidación.
- **HU-21** (RF-64): Como **tenant (ACT-01)**, quiero que el consumo de fungibles se calcule (stock inicial − remanente reportado), para imputarlo a la producción del día.
- **HU-22** (RF-42, RF-43): Como **tenant (ACT-01)**, quiero alertas visuales categorizadas de discrepancias, para identificar material ajeno o técnicos con inconsistencias.

## Módulo 6: Logística Inversa y Devoluciones

- **HU-23** (RF-65): Como **tenant (ACT-01)**, quiero registrar equipos devueltos por el técnico y retirarlos del stock disponible, liberando su custodia.
- **HU-24** (RF-66): Como **tenant (ACT-01)**, quiero registrar equipos recuperados/bajas (serie y causa: avería, migración), para controlar el flujo de retorno.
- **HU-25** (RF-67): Como **tenant (ACT-01)**, quiero generar el acta de entrega de devoluciones a la contrata principal/Lari.

## Módulo 7: Auditoría y Reportes Mensuales

- **HU-26** (RF-49, RF-50): Como **Administrador de plataforma (ACT-02)**, quiero una bitácora inmutable de movimientos (usuario, fecha, hora, saldo previo y posterior), para auditoría.
- **HU-27** (RF-28): Como **Administrador de plataforma (ACT-02)** o **Almacén (ACT-03)**, quiero buscar y descargar Excels históricos verificando su hash SHA-256, para garantizar que no fueron alterados.
- **HU-28** (RF-68): Como **Administrador de plataforma (ACT-02)**, quiero un corte mensual con totales (solicitados, asignados, liquidados/instalados, % no justificado/merma).
- **HU-29** (RF-69): Como **tenant (ACT-01) o Administrador de plataforma (ACT-02)**, quiero exportar reportes de auditoría y conciliación mensual en Excel.

---
