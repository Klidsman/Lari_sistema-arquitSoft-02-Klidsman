# 03 - Requisitos Funcionales

Derivados de los RF-01 a RF-27 del documento de requerimientos brutos, agrupados por módulo.

| ID | Módulo | Requisito |
|----|--------|-----------|
| RF-01 | 1. Seguridad, Autenticación y Control de Accesos | Creación, modificación y desactivación de usuarios con roles Administrador, Subcontratista y Almacenero. |
| RF-02 | 1. Seguridad, Autenticación y Control de Accesos | Autenticación con usuario y contraseña encriptada; sesiones mediante tokens JWT con expiración configurable. |
| RF-03 | 1. Seguridad, Autenticación y Control de Accesos | Control de accesos RBAC por rol (vistas y acciones restringidas según lo definido en Sección 3). |
| RF-04 | 1. Seguridad, Autenticación y Control de Accesos | Registro de técnicos: nombres, apellidos, código de trabajador (LA), zona y estado operativo (Activo, Suspendido, De Baja). |
| RF-05 | 2. Catálogo y Gestión del Almacén Central | Clasificación de ítems en Serializados (trazabilidad individual: ONTs, módems, routers, decodificadores) y No serializados (medibles por cantidad/metraje: cable drop, conectores, rosetas, patchcords). |
| RF-06 | 2. Catálogo y Gestión del Almacén Central | Registro de lotes recibidos: fecha, guía de remisión, código de material, cantidad, y escaneo masivo de series/MAC para serializados. |
| RF-07 | 2. Catálogo y Gestión del Almacén Central | Balance en tiempo real diferenciando stock físico disponible de stock comprometido en despachos pendientes. |
| RF-08 | 3. Asignación, Despacho y Custodia Móvil | Creación de orden de despacho validando existencia de equipos serializados en almacén central y cantidades de fungible. |
| RF-09 | 3. Asignación, Despacho y Custodia Móvil | Validación previa al guardado: alerta si el técnico supera el cupo máximo de equipos retenidos sin liquidar. |
| RF-10 | 3. Asignación, Despacho y Custodia Móvil | Generación automática de Excel estandarizado (.xlsx): metadatos de cuadrilla, tabla de seriales, tabla de material menor. |
| RF-11 | 3. Asignación, Despacho y Custodia Móvil | Almacenamiento inmutable del Excel en almacenamiento local seguro con firma digital hash SHA-256 vinculada al despacho. |
| RF-12 | 4. Mensajería Interna y Confirmación de Entrega Física | Bandeja de despachos en tiempo real para el Almacenero con notificaciones sonoras y visuales automáticas. |
| RF-13 | 4. Mensajería Interna y Confirmación de Entrega Física | Previsualización de detalles y descarga del Excel original. |
| RF-14 | 4. Mensajería Interna y Confirmación de Entrega Física | Acción de confirmación de entrega física ejecutando una transacción en base de datos. |
| RF-15 | 4. Mensajería Interna y Confirmación de Entrega Física | Rechazo o solicitud de corrección con notificación de motivo al Subcontratista remitente. |
| RF-16 | 5. Conciliación Diaria por Diferencias | Importación del reporte diario de la contrata (Excel, CSV o texto tabulado). |
| RF-17 | 5. Conciliación Diaria por Diferencias | Algoritmo automático: comparar series asignadas al técnico vs. series declaradas por la contrata. |
| RF-18 | 5. Conciliación Diaria por Diferencias | Descargo automático: series ausentes del reporte de contrata pasan a estado *instalado*. |
| RF-19 | 5. Conciliación Diaria por Diferencias | Cálculo de consumo de insumos menores: stock inicial entregado − remanente reportado, imputado a la producción diaria. |
| RF-20 | 5. Conciliación Diaria por Diferencias | Alertas visuales categorizadas: (a) series reportadas nunca despachadas; (b) técnico reporta cero en mano pero la contrata indica pendientes. |
| RF-21 | 6. Logística Inversa y Devoluciones | Reingreso por devolución de campo: reincorporación al stock disponible y liberación de custodia del técnico. |
| RF-22 | 6. Logística Inversa y Devoluciones | Registro de equipos recuperados/bajas con número de serie y causa del retiro (averías, migraciones). |
| RF-23 | 6. Logística Inversa y Devoluciones | Generación de actas/listado de entrega para consolidar devolución física de equipos averiados a la contrata principal. |
| RF-24 | 7. Auditoría y Reportes Mensuales | Bitácora transaccional inmutable: cada movimiento de entrada, salida, reingreso o merma con usuario, fecha, hora, saldo previo y posterior. |
| RF-25 | 7. Auditoría y Reportes Mensuales | Repositorio consultable de Excels históricos con verificación de hash SHA-256. |
| RF-26 | 7. Auditoría y Reportes Mensuales | Corte mensual: totales de materiales solicitados/recibidos, asignados a cuadrillas, liquidados/instalados, % no justificado o merma. |
| RF-27 | 7. Auditoría y Reportes Mensuales | Exportación de resultados de auditoría y conciliación en formato Excel. |