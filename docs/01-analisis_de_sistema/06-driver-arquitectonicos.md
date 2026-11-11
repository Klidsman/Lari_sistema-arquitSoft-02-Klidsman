# 06 - Drivers Arquitectónicos

Necesidades de calidad que más condicionan la arquitectura. Cada driver tiene su **origen** en los atributos de calidad de `04-atributos-de-calidad.md` (RNF). Los IDs siguen el formato DRV-.

| ID | Driver arquitectónico | Origen | ¿Por qué influye en la arquitectura? |
|---|---|---|---|
| **DRV-01** | Aislamiento multitenant con una excepción (catálogo compartido) | RNF-01, RNF-02, RNF-03 (Seguridad) | Exige modelar `tenant_id` en todas las tablas operativas y reforzar el aislamiento en varias capas (aplicación y base de datos), dejando el catálogo como única excepción |
| **DRV-02** | Consistencia transaccional del stock | RNF-04, RNF-06 (Integridad) | Obliga a agrupar cada operación de stock en una transacción atómica que no deje estados parciales, stock negativo ni una serie en dos estados |
| **DRV-03** | Unicidad global de series sin revelar el tenant | RNF-05 (Integridad) | Imponer una restricción única global y un mensaje de duplicado idéntico en todos los casos, para no revelar en qué tenant está una serie |
| **DRV-04** | Libro de movimientos inmutable | RNF-07 (Auditabilidad) | Requiere un registro de solo inserción con valor anterior y valor nuevo, y descartar el borrado o la edición de movimientos |
| **DRV-05** | Picos nocturnos de conciliación para 100 tenants | RNF-09, RNF-11 (Rendimiento, Escalabilidad) | Los picos de conciliación no deben bloquear la operación diaria, lo que obliga a separar el procesamiento pesado de la web (worker y colas) con límites de concurrencia |
| **DRV-06** | Entrega fiable al almacén por correo | RNF-12 (Fiabilidad) | Que un envío no se pierda aunque falle el correo obliga a registrar el envío en la misma transacción de la solicitud y a reintentar |
| **DRV-07** | Jerarquía región → tenant → técnico | RNF-01, RNF-02 (Seguridad) | La separación por región condiciona el modelo de datos y los permisos: los parámetros del almacén (Centro, Almacén, buzón) y el alcance del Almacén dependen de la región, y cada tenant queda acotado a la suya |
| **DRV-08** | Formatos externos fijos de Lari | RNF-15, RNF-16 (Configurabilidad, Compatibilidad) | Los formatos de Lari exigen adaptadores de entrada y salida aislados del dominio y parámetros configurables (Z31, Z32, PR05, BE03) en lugar de constantes |
| **DRV-09** | Operación en campo y de digitación intensiva | RNF-17, RNF-18 (Usabilidad) | Exige formularios con autocompletado y validación por fila, y el ingreso de series por pegado o escaneo, sin exigir digitarlas una a una |
| **DRV-10** | Volumen y crecimiento de 100 tenants | RNF-11 (Escalabilidad) | El volumen previsto (100 tenants, miles de técnicos y millones de movimientos al año) obliga a índices compuestos que empiezan por tenant y a un esquema compartido |
| **DRV-11** | Administración centralizada de accesos y separación de funciones entre actores | RNF-20, RNF-21 (Seguridad) | La separación de funciones entre actores exige un rol de plataforma con permisos explícitos (sin superusuario de base de datos ni de framework) y doble factor en las cuentas sensibles |
| **DRV-12** | Logística inversa: devolución y baja de equipos | RNF-04, RNF-06, RNF-07 (Integridad, Auditabilidad) | Las devoluciones y bajas cambian el stock del técnico y el disponible; deben ser movimientos atómicos y auditables, y un equipo dado de baja no puede reasignarse |
| **DRV-13** | Consumo de fungibles y reportes mensuales desde el reporte de Lari | RNF-08, RNF-16 (Trazabilidad, Compatibilidad) | El consumo y los reportes derivan del reporte de Lari y se entregan en Excel, lo que exige conservar el archivo con su hash y respetar el formato acordado |
| **DRV-14** | Disponibilidad de las operaciones críticas | RNF-22 (Disponibilidad) | Exige monitoreo, degradación controlada (atender lo que sí se puede y comunicar los errores de forma controlada) y recuperación de componentes, lo que condiciona el despliegue separado de web y worker y la operación |
