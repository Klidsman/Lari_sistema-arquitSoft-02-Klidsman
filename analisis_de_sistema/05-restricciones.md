# 05 - Restricciones

Restricciones técnicas y operativas impuestas por el negocio o el contexto.

| Categoría | Restricción | RF relacionados |
|-----------|-------------|-----------------|
| Seguridad y Acceso | Los tokens JWT deben tener expiración configurable; no se especifica mecanismo alternativo de sesión. | RF-02 |
| Seguridad y Acceso | Solo tres roles definidos (Administrador, Subcontratista, Almacenero); el Técnico no es usuario del sistema. | RF-03, RF-04 |
| Integridad Documental | Todo Excel de despacho debe almacenarse de forma inmutable en almacenamiento local seguro y firmado con SHA-256 antes de ser vinculado al despacho. | RF-10, RF-11 |
| Integridad Documental | La bitácora de movimientos debe ser protegida contra borrado. | RF-24 |
| Formatos y Estándares | El formato de despacho debe ser `.xlsx` estandarizado: metadatos de cuadrilla, tabla de seriales y tabla de material menor. | RF-10 |
| Formatos y Estándares | Los reportes de la contrata principal solo se aceptan en Excel, CSV o texto tabulado. | RF-16 |
| Formatos y Estándares | Las credenciales de Subcontratista y Almacenero las crea exclusivamente el Administrador. | RF-03 |
| Operativas | El reporte de stock diario proviene de la contrata principal y es la fuente de verdad para la conciliación; el sistema no lo edita. | RF-16, RF-17 |
| Operativas | Cupo máximo de equipos retenidos sin liquidar por técnico: debe validarse antes de guardar un despacho. | RF-09 |
| Operativas | Las exportaciones de auditoría y conciliación se entregan en formato Excel. | RF-27 |
| De Integración | El sistema depende de documentos físicos/emitidos por la contrata principal (guías de remisión, reportes de stock); la importación es por carga de archivos, no integración API. | RF-06, RF-16 |