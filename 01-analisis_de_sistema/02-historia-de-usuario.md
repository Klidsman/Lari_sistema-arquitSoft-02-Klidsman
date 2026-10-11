# 02 - Historias de Usuario

Formato: *Como <actor>, quiero <objetivo>, para <beneficio>.*
Criterios de aceptación resumidos a partir de los RF asociados.

## Módulo 1: Seguridad, Autenticación y Control de Accesos

- **HU-01** (RF-01): Como Administrador, quiero crear, modificar y desactivar usuarios con rol Administrador, Subcontratista o Almacenero, para gestionar quién accede al sistema.
- **HU-02** (RF-02): Como usuario, quiero autenticarme con usuario y contraseña encriptada y mantener una sesión con token JWT de expiración configurable, para operar de forma segura.
- **HU-03** (RF-03): Como usuario, quiero ver solo las vistas y acciones permitidas por mi rol, para evitar accesos indebidos.
- **HU-04** (RF-04): Como Administrador, quiero registrar técnicos con nombre, apellidos, código LA, zona y estado operativo (Activo, Suspendido, De Baja), para controlar el padrón.

## Módulo 2: Catálogo y Gestión del Almacén Central

- **HU-05** (RF-05): Como Administrador/Subcontratista, quiero clasificar los ítems en serializados y no serializados, para diferenciar la trazabilidad requerida.
- **HU-06** (RF-06): Como Subcontratista/Almacenero, quiero registrar lotes de ingreso (fecha, guía de remisión, código, cantidad, series/MAC para serializados), para llevar control del material recibido.
- **HU-07** (RF-07): Como usuario, quiero consultar el balance actual diferenciando stock disponible de comprometido, para tomar decisiones de despacho.

## Módulo 3: Asignación, Despacho y Custodia Móvil

- **HU-08** (RF-08): Como Subcontratista, quiero armar una orden de despacho con equipos serializados específicos y material fungible, validando existencia en almacén, para preparar la entrega.
- **HU-09** (RF-09): Como Subcontratista, quiero ser alertado si un técnico supera su cupo máximo de equipos sin liquidar, para cumplir la política de custodia.
- **HU-10** (RF-10): Como usuario, quiero que el sistema genere automáticamente el Excel estandarizado de despacho (metadatos de cuadrilla, tabla de seriales, tabla de material menor), para estandarizar documentos.
- **HU-11** (RF-11): Como usuario, quiero que el Excel se guarde de forma inmutable con firma SHA-256, para garantizar su integridad.

## Módulo 4: Mensajería Interna y Confirmación de Entrega Física

- **HU-12** (RF-12): Como Almacenero, quiero una bandeja de despachos en tiempo real con notificaciones sonoras y visuales, para atender solicitudes inmediatamente.
- **HU-13** (RF-13): Como Almacenero, quiero previsualizar detalles y descargar el Excel original, para revisar antes de confirmar.
- **HU-14** (RF-14): Como Almacenero, quiero confirmar la entrega física mediante una transacción en base de datos, para cerrar el despacho.
- **HU-15** (RF-15): Como Almacenero, quiero rechazar o solicitar corrección de un despacho con motivo, notificando al remitente, para cuando un serial no coincida.

## Módulo 5: Conciliación Diaria por Diferencias

- **HU-16** (RF-16): Como Subcontratista, quiero cargar el reporte diario de la contrata (Excel, CSV o texto tabulado), para iniciar la conciliación.
- **HU-17** (RF-17): Como Subcontratista, quiero que el sistema compare series asignadas vs. series reportadas por la contrata, para detectar diferencias.
- **HU-18** (RF-18): Como usuario, quiero que las series ya no reportadas se actualicen a estado instalado automáticamente, para reflejar la liquidación.
- **HU-19** (RF-19): Como usuario, quiero que el consumo de fungibles se calcule (stock inicial − remanente reportado), para imputarlo a la producción del día.
- **HU-20** (RF-20): Como usuario, quiero alertas visuales categorizadas de discrepancias, para identificar material ajeno o técnicos con inconsistencias.

## Módulo 6: Logística Inversa y Devoluciones

- **HU-21** (RF-21): Como Subcontratista/Almacenero, quiero registrar equipos devueltos por el técnico y reincorporarlos al stock disponible, liberando su custodia.
- **HU-22** (RF-22): Como usuario, quiero registrar equipos recuperados/bajas (serie y causa: avería, migración), para controlar el flujo de retorno.
- **HU-23** (RF-23): Como usuario, quiero generar el acta/formato de entrega de devoluciones a la contrata principal.

## Módulo 7: Auditoría y Reportes Mensuales

- **HU-24** (RF-24): Como Administrador, quiero una bitácora inmutable de movimientos (usuario, fecha, hora, saldo previo y posterior), para auditoría.
- **HU-25** (RF-25): Como Administrador/Almacenero, quiero buscar y descargar Excels históricos verificando su hash SHA-256, para garantizar que no fueron alterados.
- **HU-26** (RF-26): Como Administrador, quiero un corte mensual con totales (solicitados, asignados, liquidados/instalados, % no justificado/merma).
- **HU-27** (RF-27): Como usuario autorizado, quiero exportar reportes de auditoría y conciliación mensual en Excel.
