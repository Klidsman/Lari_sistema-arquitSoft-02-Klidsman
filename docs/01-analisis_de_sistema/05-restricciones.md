# 05 - Restricciones

Restricciones técnicas y operativas impuestas por el negocio o el contexto. Derivadas de la sección 6 "Restricciones" de `01-notas-de-descubrimiento.md` v3.1. Los IDs de restricción siguen el formato RES-.

| ID | Categoría | Descripción |
|---|---|---|
| RES-18 | Seguridad y Acceso | Solo el Administrador de plataforma (ACT-02) crea la cuenta única del tenant (ACT-01) y las cuentas de Almacén (ACT-03) |
| RES-19 | Seguridad y Acceso | Una cuenta de Almacén (ACT-03) tiene alcance de una sola región y no ve ni responde solicitudes de otra región |
| RES-13 | Seguridad y Acceso | Los formularios no permiten editar NIF, Movimiento, Centro, Almacén, lote ni descripción |
| RES-14 | Integridad Documental | Los movimientos y ajustes de stock no se borran; una corrección se hace con un movimiento nuevo |
| RES-11 | Integridad Documental | El catálogo de materiales es compartido por todos los tenants y su código es único global |
| RES-12 | Integridad Documental | El lote es un atributo fijo del material y es informativo; no separa el stock |
| RES-01 | Formatos y Estándares | Serie de 12 caracteres alfanuméricos. La longitud es fija; los caracteres pueden variar en equipos nuevos |
| RES-02 | Formatos y Estándares | Código de material de 11 dígitos |
| RES-03 | Formatos y Estándares | Movimientos fijos del formato Lari: Z31 (asignación) y Z32 (desasignación) |
| RES-04 | Formatos y Estándares | Centro PR05 y Almacén BE03 son iguales en todas las regiones por ahora |
| RES-08 | Formatos y Estándares | El recojo se registra por formulario, no por Excel |
| RES-09 | Formatos y Estándares | La entrega al almacén se hace por Excel enviado por correo al buzón regional |
| RES-10 | Formatos y Estándares | Lari envía los reportes de conciliación por región, en Excel (formato pendiente, ver sección 10) |
| RES-07 | Formatos y Estándares | Una serie no cambia de región |
| RES-21 | Formatos y Estándares | El acta de entrega de devoluciones a Lari se intercambia por Excel y correo; no hay integración directa |
| RES-23 | Formatos y Estándares | Los reportes de auditoría y de conciliación mensual se exportan en Excel |
| RES-05 | Operativas | Un tenant recoge solo en el almacén de su región |
| RES-06 | Operativas | No existen traspasos entre tenants |
| RES-16 | Operativas | El stock inicial de técnicos se carga una sola vez, el día de implementación |
| RES-17 | Operativas | Los materiales no se borran en esta versión |
| RES-20 | Operativas | Un equipo dado de baja (avería o migración) sale del stock disponible y no se reasigna |
| RES-22 | Operativas | El consumo de fungibles se calcula solo con el remanente reportado por Lari; el sistema no mide consumo propio |
| RES-15 | Integración | No existe integración directa con los sistemas de Lari; el intercambio es por Excel y correo |
