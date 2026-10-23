# 04 - Atributos de Calidad

Propiedades no funcionales inferidas de los requerimientos. El estado sigue la convención del documento de descubrimiento v3.1: Confirmado, Supuesto o Pendiente.

| ID | Categoría | Descripción | 
|---|---|---|
| **RNF-01** | Seguridad | Un tenant nunca ve ni modifica datos de otro tenant, con excepción del catálogo |
| **RNF-02** | Seguridad | El tenant_id nunca se acepta desde el cliente (formulario, URL o Excel); sale de la identidad autenticada |
| **RNF-03** | Seguridad | La base de datos refuerza el aislamiento por tenant con seguridad por fila |
| **RNF-04** | Integridad | Toda operación de stock se aplica completa o no se aplica (atomicidad) |
| **RNF-05** | Integridad | Cada serie existe una sola vez en todo el sistema. El mensaje de duplicado no revela tenant ni región |
| **RNF-06** | Integridad | Ninguna operación deja stock negativo, ni una serie en dos estados a la vez |
| **RNF-07** | Auditabilidad | El 100% de movimientos y ajustes queda registrado con usuario, fecha y valores (valor anterior y valor nuevo) |
| **RNF-08** | Trazabilidad | Se guarda el Excel original de cada envío y carga, con su huella (hash) para detectar duplicados |
| **RNF-09** | Rendimiento | Las conciliaciones de los 100 tenants en la franja nocturna no afectan la operación diaria |
| **RNF-10** | Rendimiento | La vista previa de series responde con fluidez aunque se peguen miles de filas |
| **RNF-11** | Escalabilidad | Soportar 100 tenants, 1.000 a 2.000 técnicos y unos 3 a 4 millones de movimientos al año |
| **RNF-12** | Fiabilidad | Un Excel enviado al almacén no se pierde aunque el correo falle; se reintenta |
| **RNF-13** | Mantenibilidad | Las reglas de negocio se pueden probar sin depender del Excel ni del correo |
| **RNF-14** | Capacidad de prueba | Cada criterio de aceptación de una spec tiene al menos una prueba automatizada |
| **RNF-15** | Configurabilidad | Códigos Z31, Z32, PR05, BE03, longitud de serie y parámetros de región son configuración, no constantes |
| **RNF-16** | Compatibilidad | Columnas y formato de los Excel idénticos a los de Lari |
| **RNF-17** | Usabilidad | El ingreso de series no exige digitarlas una a una, y los errores se muestran por fila antes de guardar |
| **RNF-18** | Usabilidad | Los datos del catálogo y del técnico se completan solos en los formularios | Confirmado |
| **RNF-19** | Idioma | Interfaz y documentación en español |
| **RNF-20** | Seguridad | Los privilegios de ACT-02 son un rol con alcance explícito y limitado. Ningún mecanismo técnico que omita los permisos (superusuario de base de datos o de framework) puede usarse para operar datos de tenants |
| **RNF-21** | Seguridad | Las cuentas de ACT-02 y de Almacén (ACT-03) requieren autenticación de dos factores |
| **RNF-22** | Disponibilidad | El sistema mantiene disponibles las operaciones críticas y comunica los errores de forma controlada cuando un componente falla |
