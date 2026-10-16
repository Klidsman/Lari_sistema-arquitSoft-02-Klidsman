# 08 - Escenarios de Atributos de Calidad

Escenarios redactados en formato de tabla por **Elemento**: *Atributo de calidad, Fuente, Estímulo, Condición, Respuesta Esperada, Medida, Verificación y Estado*. Cada escenario concreta un atributo de calidad de `04-atributos-de-calidad.md` (RNF). Los IDs siguen el formato ESC-.

---

### ESC-01 — Seguridad (RNF-01)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Seguridad |
| Fuente | Usuario de un tenant |
| Estímulo | Intenta ver u operar datos de otro tenant a través de una URL, un formulario o un archivo Excel. |
| Condición | El sistema está en operación normal y el usuario está autenticado. |
| Respuesta Esperada | El sistema usa el tenant de la identidad autenticada e ignora el ajeno; si no puede resolverlo, rechaza la operación sin revelar datos de otro tenant. |
| Medida | Propuesta por validar: 0 accesos o modificaciones a datos de otro tenant. |
| Verificación | Pruebas de aislamiento en cada spec que toque datos de tenant. |
| Estado | Pendiente de aprobar la medida y de cubrir con pruebas todas las operaciones. |

### ESC-02 — Seguridad (RNF-02)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Seguridad |
| Fuente | Usuario de un tenant |
| Estímulo | Envía un `tenant_id` distinto al de su sesión en una petición o en un Excel. |
| Condición | El sistema está en operación normal. |
| Respuesta Esperada | El sistema descarta el valor del cliente y aplica el tenant de la identidad autenticada. |
| Medida | Propuesta por validar: 0 operaciones aplicadas a un tenant distinto al de la sesión. |
| Verificación | Prueba: un `tenant_id` ajeno en la petición no cambia el tenant de la operación. |
| Estado | Pendiente de aprobar la medida. |

### ESC-03 — Seguridad (RNF-03)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Seguridad |
| Fuente | Consulta de la aplicación o del worker |
| Estímulo | Se ejecuta una consulta sin contexto de tenant definido. |
| Condición | El sistema está en operación normal. |
| Respuesta Esperada | La base de datos no devuelve ninguna fila. |
| Medida | Propuesta por validar: 0 filas devueltas sin contexto de tenant. |
| Verificación | Prueba: una consulta sin tenant definido no devuelve filas. |
| Estado | Pendiente de aprobar la medida y de activar la seguridad por fila. |

### ESC-04 — Seguridad (RNF-20)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Seguridad |
| Fuente | Administrador de plataforma (ACT-02) |
| Estímulo | Intenta registrar un recojo, crear una asignación o aprobar una conciliación, incluso forzando la petición. |
| Condición | El sistema está en operación normal. |
| Respuesta Esperada | El sistema rechaza la operación; los privilegios de ACT-02 son explícitos y limitados. |
| Medida | Propuesta por validar: 0 operaciones de inventario permitidas a ACT-02. |
| Verificación | Prueba: la cuenta de ACT-02 no puede operar inventario aunque se fuerce la petición. |
| Estado | Pendiente de aprobar la medida y de definir los permisos explícitos. |

### ESC-05 — Seguridad (RNF-21)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Seguridad |
| Fuente | Administrador de plataforma o Almacén |
| Estímulo | Inicia sesión sin presentar el segundo factor. |
| Condición | Inicio de sesión. |
| Respuesta Esperada | El sistema deniega el acceso. |
| Medida | Propuesta por validar: 0 accesos a cuentas sensibles sin segundo factor. |
| Verificación | Prueba de inicio de sesión sin segundo factor. |
| Estado | Pendiente de aprobar la medida y de elegir el mecanismo de doble factor. |

### ESC-06 — Integridad (RNF-04)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Integridad |
| Fuente | Falla del sistema o del worker |
| Estímulo | Ocurre a mitad de una operación de stock. |
| Condición | Operación normal. |
| Respuesta Esperada | La operación se aplica completa o no se aplica; no queda estado parcial. |
| Medida | Propuesta por validar: 0 estados parciales tras un fallo. |
| Verificación | Prueba de fallo a mitad de una operación de stock. |
| Estado | Pendiente de aprobar la medida. |

### ESC-07 — Integridad (RNF-05)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Integridad |
| Fuente | Usuario de un tenant |
| Estímulo | Ingresa una serie que ya existe en el sistema. |
| Condición | Carga de series (recojo, asignación o conciliación). |
| Respuesta Esperada | El sistema rechaza la serie con el mismo mensaje de duplicado en todos los casos, sin revelar el tenant ni la región. |
| Medida | Propuesta por validar: 1 mensaje único; 0 revelaciones de tenant o región. |
| Verificación | Prueba: la restricción única global se aplica y el mensaje es idéntico en todos los casos. |
| Estado | Pendiente de aprobar la medida. |

### ESC-08 — Integridad (RNF-06)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Integridad |
| Fuente | Dos operaciones concurrentes |
| Estímulo | Mueven el mismo material o la misma serie al mismo tiempo. |
| Condición | Concurrencia. |
| Respuesta Esperada | El sistema aplica una y rechaza la otra; ninguna deja stock negativo ni una serie en dos estados. |
| Medida | Propuesta por validar: 0 stock negativo y 0 series en dos estados. |
| Verificación | Pruebas de concurrencia y restricciones en la base de datos. |
| Estado | Pendiente de aprobar la medida. |

### ESC-09 — Auditabilidad (RNF-07)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Auditabilidad |
| Fuente | Usuario autorizado |
| Estímulo | Realiza cualquier movimiento o ajuste de stock. |
| Condición | Operación normal. |
| Respuesta Esperada | El sistema registra usuario, fecha, valor anterior y valor nuevo. |
| Medida | Propuesta por validar: 100% de los movimientos y ajustes registrados. |
| Verificación | Verificación de los registros por operación. |
| Estado | Pendiente de aprobar la medida. |

### ESC-10 — Trazabilidad (RNF-08)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Trazabilidad |
| Fuente | Usuario o worker |
| Estímulo | Envía o carga un Excel. |
| Condición | Envío al almacén o carga del reporte de Lari. |
| Respuesta Esperada | El sistema guarda el archivo original con su huella (hash). |
| Medida | Propuesta por validar: 1 archivo y su hash por operación. |
| Verificación | Revisar que cada envío y cada carga tengan su archivo y su hash guardados. |
| Estado | Pendiente de aprobar la medida. |

### ESC-11 — Rendimiento (RNF-09)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Rendimiento |
| Fuente | Worker de conciliación |
| Estímulo | Procesa las conciliaciones de 100 tenants en la franja nocturna. |
| Condición | Franja nocturna, con la web en operación. |
| Respuesta Esperada | La operación diaria no se bloquea y la web responde con normalidad. |
| Medida | Pendiente: definir el tiempo máximo de respuesta de la web y la franja horaria. |
| Verificación | Prueba de carga con 100 conciliaciones simultáneas y medición de la respuesta de la web. |
| Estado | Pendiente de definir la medida. |

### ESC-12 — Rendimiento (RNF-10)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Rendimiento |
| Fuente | Usuario de un tenant |
| Estímulo | Pega miles de series en el formulario. |
| Condición | Ingreso de series. |
| Respuesta Esperada | La vista previa responde con fluidez y muestra el estado de cada fila. |
| Medida | Pendiente: definir el tiempo máximo de respuesta de la vista previa. |
| Verificación | Prueba con un pegado de miles de filas y medición del tiempo de respuesta. |
| Estado | Pendiente de definir la medida. |

### ESC-13 — Escalabilidad (RNF-11)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Escalabilidad |
| Fuente | Crecimiento del negocio |
| Estímulo | Se alcanza el volumen previsto: 100 tenants, 1.000 a 2.000 técnicos y 3 a 4 millones de movimientos al año. |
| Condición | Operación normal. |
| Respuesta Esperada | El sistema opera sin degradación perceptible. |
| Medida | Propuesta por validar: soportar el volumen de referencia sin degradación. |
| Verificación | Prueba de volumen con datos representativos. |
| Estado | Pendiente de aprobar la medida. |

### ESC-14 — Fiabilidad (RNF-12)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Fiabilidad |
| Fuente | Servidor de correo |
| Estímulo | Falla al enviar el Excel al almacén. |
| Condición | Envío al almacén. |
| Respuesta Esperada | El sistema reintenta el envío y conserva el registro; la solicitud no se pierde. |
| Medida | Propuesta por validar: 0 solicitudes enviadas sin registro de envío. |
| Verificación | Simular el fallo del correo y comprobar el registro y los reintentos. |
| Estado | Pendiente de aprobar la medida. |

### ESC-15 — Mantenibilidad (RNF-13)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Mantenibilidad |
| Fuente | Desarrollador |
| Estímulo | Cambia o prueba una regla de negocio. |
| Condición | Desarrollo y pruebas. |
| Respuesta Esperada | La regla se puede probar sin depender del Excel ni del correo. |
| Medida | Propuesta por validar: pruebas de reglas sin infraestructura externa. |
| Verificación | Ejecutar las pruebas del núcleo de reglas sin Excel ni correo. |
| Estado | Pendiente de aprobar la medida. |

### ESC-16 — Capacidad de prueba (RNF-14)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Capacidad de prueba |
| Fuente | Desarrollador |
| Estímulo | Añade un criterio de aceptación a una spec. |
| Condición | Desarrollo y pruebas. |
| Respuesta Esperada | Cada criterio de aceptación tiene al menos una prueba automatizada. |
| Medida | Propuesta por validar: 1 prueba por criterio. |
| Verificación | Revisar la suite y comprobar la cobertura de los criterios. |
| Estado | Pendiente de aprobar la medida. |

### ESC-17 — Configurabilidad (RNF-15)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Configurabilidad |
| Fuente | Administrador |
| Estímulo | Cambia los códigos Z31, Z32, PR05, BE03 o la longitud de serie. |
| Condición | Operación normal. |
| Respuesta Esperada | El sistema aplica el cambio por configuración, sin modificar código. |
| Medida | Propuesta por validar: 0 despliegues de código por cambio de parámetro. |
| Verificación | Cambiar un parámetro y comprobar el efecto sin desplegar. |
| Estado | Pendiente de aprobar la medida. |

### ESC-18 — Compatibilidad (RNF-16)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Compatibilidad |
| Fuente | Lari |
| Estímulo | Importa o exporta un Excel. |
| Condición | Intercambio con Lari. |
| Respuesta Esperada | El sistema conserva columnas y formato idénticos a los de Lari. |
| Medida | Propuesta por validar: coincidencia total con el ejemplo real de Lari. |
| Verificación | Validar los archivos contra el ejemplo real de Lari. |
| Estado | Pendiente de aprobar la medida y de obtener el ejemplo definitivo. |

### ESC-19 — Usabilidad (RNF-17)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Usabilidad |
| Fuente | Usuario de un tenant |
| Estímulo | Ingresa series por pegado o escaneo. |
| Condición | Ingreso de series. |
| Respuesta Esperada | El sistema no exige digitarlas una a una y muestra los errores por fila antes de guardar. |
| Medida | Propuesta por validar: 0 renglones con error guardados. |
| Verificación | Prueba de ingreso por pegado con filas válidas e inválidas. |
| Estado | Pendiente de aprobar la medida. |

### ESC-20 — Usabilidad (RNF-18)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Usabilidad |
| Fuente | Usuario de un tenant |
| Estímulo | Elige un material o un técnico en un formulario. |
| Condición | Formularios de recojo, asignación o traspaso. |
| Respuesta Esperada | El sistema completa descripción, lote y NIF automáticamente y no los deja editar. |
| Medida | Propuesta por validar: 100% de los campos derivados autocompletados y no editables. |
| Verificación | Prueba de autocompletado y de no edición de los campos derivados. |
| Estado | Pendiente de aprobar la medida. |

### ESC-21 — Idioma (RNF-19)

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Idioma |
| Fuente | Usuario |
| Estímulo | Usa la interfaz o lee la documentación. |
| Condición | Operación normal. |
| Respuesta Esperada | La interfaz y la documentación se presentan en español. |
| Medida | Propuesta por validar: 100% de los textos en español. |
| Verificación | Revisión de los textos de interfaz y documentación. |
| Estado | Pendiente de aprobar la medida. |

### ESC-22 — Disponibilidad

| Elemento | Descripción |
|---|---|
| Atributo de calidad | Disponibilidad |
| Fuente | Usuario de un tenant |
| Estímulo | Intenta operar durante la campaña o la franja de conciliación, o cuando falla un componente. |
| Condición | El sistema está publicado y cuenta con monitoreo. |
| Respuesta Esperada | El sistema mantiene disponibles las operaciones que puede atender y comunica los errores de forma controlada cuando un servicio necesario no responde. |
| Medida | Propuesta por validar: disponibilidad mensual de 99,5 % para las operaciones críticas. |
| Verificación | Revisar los registros de monitoreo y calcular los periodos de disponibilidad e interrupción. |
| Estado | Pendiente de aprobar la meta, definir las operaciones críticas y establecer las condiciones de mantenimiento. |
