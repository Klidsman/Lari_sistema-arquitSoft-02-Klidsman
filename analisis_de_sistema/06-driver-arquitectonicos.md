# 06 - Drivers Arquitectónicos

Decisiones de arquitectura forzadas por los requisitos de negocio.

| Driver | Requisito / Contexto | Implicación arquitectónica | RF relacionados |
|--------|----------------------|----------------------------|-----------------|
| Seguridad como driver primario | RBAC estricto por rol | Separa capacidades de UI/API por rol desde el diseño. | RF-03 |
| Seguridad como driver primario | Sesiones JWT con expiración configurable | Favorece arquitectura stateless con validación de token en cada request. | RF-02 |
| Integridad documental y auditabilidad | Hash SHA-256 de cada Excel y almacenamiento inmutable | Se requiere almacenamiento de archivos con inmutabilidad lógica y bitácora append-only. | RF-11, RF-24, RF-25 |
| Integridad documental y auditabilidad | Transaccionalidad en confirmaciones de entrega y movimientos de stock | Operaciones críticas sobre base de datos transaccional. | RF-14, RF-24 |
| Tiempo real | Notificaciones sonoras/visuales y bandeja en vivo | Canal de eventos push (WebSocket/SSE) entre confirmación del Subcontratista y Almacenero. | RF-12 |
| Complejidad de conciliación | Comparación automática de series vs. reporte de contrata y cálculo de consumo | Lógica de negocio centralizada en un motor de conciliación con soporte a múltiples formatos de entrada. | RF-16, RF-17, RF-19 |
| Flujos operativos cruzados | Ciclo completo de custodia: despacho → confirmación → conciliación → devolución/logística inversa | Modelo de dominio con estados explícitos para equipos serializados y stock. | RF-08, RF-14, RF-21 |
| Generación documental estandarizada | Plantillas `.xlsx` fijas y actas de retorno | Componente dedicado de generación de documentos. | RF-10, RF-23 |
| Escalabilidad operativa moderada | Múltiples subcontratistas y técnicos, importaciones diarias por archivo | Suficiente con una aplicación web/backend único; priorizar trazabilidad sobre distribución. | — |