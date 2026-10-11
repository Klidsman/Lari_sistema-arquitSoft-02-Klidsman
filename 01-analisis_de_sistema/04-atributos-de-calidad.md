# 04 - Atributos de Calidad

Propiedades no funcionales inferidas de los requerimientos.

| Atributo | Característica | RF relacionados |
|---|---|---|
| **RNF-01** | Seguridad | Un tenant nunca ve ni modifica datos de otro tenant, con excepción del catálogo | Confirmado | RF-03, RF-60 |
| **RNF-02** | Seguridad | El tenant_id nunca se acepta desde el cliente (formulario, URL o Excel); sale de la identidad autenticada | Confirmado | RF-02, RF-60 |
| **RNF-03** | Seguridad | La base de datos refuerza el aislamiento por tenant con seguridad por fila | Supuesto | RF-03 |
| **RNF-04** | Integridad | Toda operación de stock se aplica completa o no se aplica (atomicidad) | Confirmado | RF-32, RF-49 |
| **RNF-05** | Integridad | Cada serie existe una sola vez en todo el sistema. El mensaje de duplicado no revela tenant ni región | Confirmado | RF-45 |
| **RNF-06** | Integridad | Ninguna operación deja stock negativo, ni una serie en dos estados a la vez | Confirmado | RF-36, RF-42 |
| **RNF-07** | Auditibilidad | El 100% de movimientos y ajustes queda registrado con usuario, fecha y valores (valor anterior y valor nuevo) | Confirmado | RF-49, RF-50 |
| **RNF-08** | Trazabilidad | Se guarda el Excel original de cada envío y carga, con su huella (hash) para detectar duplicados | Supuesto | RF-28, RF-25 |
| **RNF-09** | Rendimiento | Las conciliaciones de los 100 tenants en la franja nocturna no afecten la operación diaria | Pendiente | — |
| **RNF-10** | Rendimiento | La vista previa de series responde con fluidez aunque se peguen miles de filas | Pendiente  | — |
| **RNF-11** | Escalabilidad | Soportar 100 tenants, 1.000 a 2.000 técnicos y unos 3 a 4 millones de movimientos al año | Supuesto | — |
| **RNF-12** | Fiabilidad | Un Excel enviado al almacén no se pierde aunque el correo falle; se reintenta | Supuesto | RF-27 |
| **RNF-13** | Mantenibilidad | Las reglas de negocio se pueden probar sin depender del Excel ni del correo | Supuesto | — |
| **RNF-14** | Capacidad de prueba | Cada criterio de aceptación de una spec tiene al menos una prueba automatizada | Confirmado | — |
| **RNF-15** | Configurabilidad | Códigos Z31, Z32, PR05, BE03, longitud de serie y parámetros de región son configuración, no constantes | Confirmado | RF-15 |
| **RNF-16** | Compatibilidad | Columnas y formato de los Excel idénticos a los de Lari | Confirmado | — |
| **RNF-17** | Usabilidad | El ingreso de series no exige digitarlas una a una, y los errores se muestran por fila antes de guardar | Confirmado | RF-17, RF-19 |
| **RNF-18** | Usabilidad | Los datos del catálogo y del técnico se completan solos en los formularios | Confirmado | RF-07, RF-26 |
| **RNF-19** | Idioma | Interfaz y documentación en español | Confirmado | — |
| **RNF-20** | Seguridad | Los privilegios de ACT-02 son un rol con alcance explícito y limitado. Ningún mecanismo técnico que omita los permisos (superusuario de base de datos o de framework) puede usarse para operar datos de tenants | Supuesto | — |
| **RNF-21** | Seguridad | Las cuentas de ACT-02 y de Responsable de almacén requieren autenticación de dos factores | Supuesto | — |