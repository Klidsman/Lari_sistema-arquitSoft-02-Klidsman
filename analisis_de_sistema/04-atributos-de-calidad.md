# 04 - Atributos de Calidad

Propiedades no funcionales inferidas de los requerimientos.

| Atributo | Característica | RF relacionados |
|----------|----------------|-----------------|
| Seguridad | Autenticación con contraseñas encriptadas y sesiones JWT de duración configurable. | RF-02 |
| Seguridad | Control de accesos basado en roles (RBAC) en vistas y acciones. | RF-03 |
| Seguridad | Bitácora protegida contra borrado. | RF-24 |
| Integridad y Trazabilidad | Firma digital (hash SHA-256) de cada Excel de despacho y verificación posterior. | RF-11, RF-25 |
| Integridad y Trazabilidad | Trazabilidad individual de equipos serializados: serie, MAC, custodio y estado en cada momento. | — |
| Integridad y Trazabilidad | Registro inmutable de saldos previo/posterior en cada movimiento. | RF-24 |
| Disponibilidad y Tiempo Real | Bandeja de despachos con notificaciones sonoras y visuales automáticas. | RF-12 |
| Disponibilidad y Tiempo Real | Balance de existencias actualizado en tiempo real. | RF-07 |
| Exactitud y Confiabilidad | Conciliación automática de series versus reporte de contrata. | RF-17 |
| Exactitud y Confiabilidad | Alertas categorizadas ante discrepancias. | RF-20 |
| Exactitud y Confiabilidad | Validaciones previas antes de persistir despachos (existencia de series, cupos de custodia). | RF-08, RF-09 |
| Usabilidad | Previsualización y descarga directa del Excel de despacho. | RF-13 |
| Usabilidad | Notificación clara de motivos de rechazo o corrección. | RF-15 |
| Usabilidad | Reportes exportables en Excel. | RF-27 |
| Auditabilidad | Historial consultable de mensajería y despachos por meses anteriores. | RF-25 |
| Auditabilidad | Consolidado mensual de métricas operativas. | RF-26 |
| Rendimiento | Escaneo/importación masiva de números de serie y MAC en ingresos. | RF-06 |
| Rendimiento | Algoritmo de conciliación automática debe procesar reportes diarios completos sin intervención manual extensiva. | RF-17 a RF-19 |
| Mantenibilidad y Extensibilidad | Importación flexible de reportes de contrata: Excel, CSV o texto tabulado. | RF-16 |
| Mantenibilidad y Extensibilidad | Catálogo extensible de tipos de material (serializados y no serializados). | RF-05 |