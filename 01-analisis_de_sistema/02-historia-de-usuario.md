# 02 - Historias de Usuario

Formato: *Como <actor>, quiero <objetivo>, para <beneficio>.*
Criterios de aceptación resumidos a partir de los RF asociados.

**Fuente:** se extraen de la sección 3 "Historias de usuario" de `01-notas-de-descubrimiento.md` v3.1.
Los actores ahora son ACT-01 (Tenant), ACT-02 (Administrador de plataforma), ACT-03 (Almacén) y ACT-04 (Técnico).
Los roles dentro del tenant son Operador, Aprobador y Responsable del tenant (permisos, no actores separados [Supuesto, pregunta 14]).
**Regla 6 del documento de descubrimiento:** usar los nombres de rol Operador, Aprobador, Responsable del tenant, Responsable de almacén, Administrador de plataforma. **No usar "administrador"** para los roles de tenant ni de almacén.

## Módulo 1: Seguridad, Autenticación y Control de Accesos

- **HU-01** (RF-01): Como **Administrador de plataforma (ACT-02)**, quiero registrar regiones y su almacén con Centro, Almacén y buzón, para que cada región tenga su punto de entrega.
- **HU-02** (RF-12, RF-13): Como **Responsable del tenant (ACT-01)**, quiero registrar a mis técnicos con su NIF (LAxxxx), para poder asignarles materiales.
- **HU-03** (RF-05, RF-55): Como **Responsable del tenant (ACT-01)**, quiero crear Operadores y Aprobadores de mi tenant, para que cada persona haga solo lo que le corresponde.
- **HU-04** (RF-04): Como **Responsable de almacén (ACT-03)**, quiero ver solo las solicitudes de mi región, para responderlas.

## Módulo 2: Catálogo y Gestión del Almacén Central

- **HU-05** (RF-06, RF-11): Como **Operador (ACT-01)**, quiero registrar un material nuevo con código (11 dígitos), descripción, lote y tipo (seriado o no seriado), para usarlo en recojos y asignaciones.
- **HU-06** (RF-07, RF-08): Como **Operador (ACT-01)**, quiero buscar materiales por código o descripción en el catálogo completo, para elegirlos en los formularios.
- **HU-07** (RF-09, RF-10): Como **creador del material o ACT-02**, quiero editar su descripción o lote, para corregir datos de Lari. *[Sólo creador o ACT-02; el código no se edita]*

## Módulo 3: Asignación, Despacho y Custodia Móvil

- **HU-08** (RF-08): Como **Subcontratista** (contexto antiguo, ver HU-01), quiero armar una orden de despacho con equipos serializados específicos y material fungible, validando existencia en almacén, para preparar la entrega.
  *Nota: En el modelo v3.1 este actividad corresponde al Operador o Responsable del tenant (ACT-01) según su rol.*
- **HU-09** (RF-09): Como **Operador (ACT-01)**, quiero ser alertado si un técnico supera su cupo máximo de equipos sin liquidar, para cumplir la política de custodia.
- **HU-10** (RF-10): Como **usuario**, quiero que el sistema genere automáticamente el Excel estandarizado de despacho (metadatos de cuadrilla, tabla de seriales, tabla de material menor), para estandarizar documentos.
- **HU-11** (RF-11): Como **usuario**, quiero que el Excel se guarde de forma inmutable con firma SHA-256, para garantizar su integridad.

## Módulo 4: Mensajería Interna y Confirmación de Entrega Física

- **HU-12** (RF-12): Como **Almacenero** (contexto antiguo, RF-12 cubre registro de técnicos; en modelo v3.1 el Responsable de almacén ACT-03 gestiona la bandeja), quiero una bandeja de despachos en tiempo real con notificaciones sonoras y visuales, para atender solicitudes inmediatamente.
  *Nota: En modelo v3.1, la bandeja la gestiona el Responsable de almacén (ACT-03) o el Operador según permisos.*
- **HU-13** (RF-13): Como **Responsable de almacén (ACT-03)**, quiero previsualizar detalles y descargar el Excel original, para revisar antes de confirmar.
- **HU-14** (RF-14): Como **Responsable de almacén (ACT-03)**, quiero confirmar la entrega física mediante una transacción en base de datos, para cerrar el despacho.
- **HU-15** (RF-15): Como **Responsable de almacén (ACT-03)**, quiero rechazar o solicitar corrección de un despacho con motivo, notificando al remitente, para cuando un serial no coincida.

## Módulo 5: Conciliación Diaria por Diferencias

- **HU-16** (RF-16): Como **Operador (ACT-01)**, quiero cargar el reporte diario de la contrata (Excel, CSV o texto tabulado), para iniciar la conciliación.
- **HU-17** (RF-17): Como **Operador (ACT-01)**, quiero que el sistema compare series asignadas vs. series reportadas por la contrata, para detectar diferencias.
- **HU-18** (RF-18): Como **usuario**, quiero que las series ya no reportadas se actualicen a estado instalado automáticamente, para reflejar la liquidación.
- **HU-19** (RF-19): Como **usuario**, quiero que el consumo de fungibles se calcule (stock inicial − remanente reportado), para imputarlo a la producción del día.
- **HU-20** (RF-20): Como **usuario**, quiero alertas visuales categorizadas de discrepancias, para identificar material ajeno o técnicos con inconsistencias.

## Módulo 6: Logística Inversa y Devoluciones

- **HU-21** (RF-21): Como **Operador (ACT-01)**, quiero registrar equipos devueltos por el técnico y reincorporarlos al stock disponible, liberando su custodia.
- **HU-22** (RF-22): Como **usuario**, quiero registrar equipos recuperados/bajas (serie y causa: avería, migración), para controlar el flujo de retorno.
- **HU-23** (RF-23): Como **Responsable del tenant (ACT-01)** o **Operador (ACT-01)**, quiero generar el acta/formato de entrega de devoluciones a la contrata principal/Lari.
  *Nota: El destinatario externo es Lari (sistema externo, no actor); el reporte se importa para conciliación.*

## Módulo 7: Auditoría y Reportes Mensuales

- **HU-24** (RF-24): Como **Administrador de plataforma (ACT-02)**, quiero una bitácora inmutable de movimientos (usuario, fecha, hora, saldo previo y posterior), para auditoría.
- **HU-25** (RF-25): Como **Administrador de plataforma (ACT-02)** o **Responsable de almacén (ACT-03)**, quiero buscar y descargar Excels históricos verificando su hash SHA-256, para garantizar que no fueron alterados.
- **HU-26** (RF-26): Como **Administrador de plataforma (ACT-02)**, quiero un corte mensual con totales (solicitados, asignados, liquidados/instalados, % no justificado/merma).
- **HU-27** (RF-27): Como **usuario autorizado (ACT-01 o ACT-02)**, quiero exportar reportes de auditoría y conciliación mensual en Excel.

---