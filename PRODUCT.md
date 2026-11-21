# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Cuenta única del tenant (usuario primario, confirmado).** El subcontratista que opera el día a día: registra recojos del almacén central, crea solicitudes de asignación y traspasos, carga los reportes de Lari, concilia el stock, y gestiona técnicos y materiales de su propio tenant. Es una sola cuenta por tenant, sin subcuentas ni roles internos; la misma cuenta que carga una conciliación puede aprobarla.
- **Responsable de almacén.** Alcance de una región: confirma o rechaza solicitudes de asignación y traspasos de su región y envía reportes de materiales. No ve datos de tenants ni de otras regiones.
- **Administrador de plataforma.** Alcance global: crea regiones, almacenes, tenants, la cuenta única de cada tenant y las cuentas de Responsable de almacén; administra el catálogo compartido y consulta la auditoría de acceso. Nunca opera inventario, recojos, asignaciones, traspasos ni conciliaciones.
- **Técnico (código LAxxxx).** Actor pasivo del tenant: recibe y devuelve materiales, no inicia sesión. Sus datos existen para asignar, traspasar y conciliar.

## Product Purpose

Sistema web de control de inventario y custodia de equipos de telecomunicaciones para una empresa subcontratista que opera con la contrata principal Lari. Gestiona el almacén central de cada región, despacha equipos y materiales a las cuadrillas de técnicos, y concilia lo asignado contra lo reportado por Lari como instalado.

El éxito tiene dos caras, ambas confirmadas: (1) que la conciliación cierre sin descuadres inexplicables y con trazabilidad completa de cada serie, y (2) que el proyecto cumpla su entrega académica del curso de Arquitectura de Software, con spec aprobada y pruebas en verde.

## Positioning

El sistema es un instrumento de control y conciliación, no un ERP ni un sustituto de la fuente contractual: en una conciliación aprobada, el reporte de Lari prevalece sobre el stock del sistema, y la aprobación es siempre humana. No existe integración directa con los sistemas de Lari; el intercambio es por Excel y correo. Lo que un producto vecino no podría copiar sin cambiar su modelo es la jerarquía Región → Tenant → Técnico con una sola cuenta operativa por tenant, el aislamiento estricto entre subcontratistas competidores sobre una base compartida, y la trazabilidad de serie individual (12 caracteres, única en todo el sistema y en un solo lugar a la vez).

## Operating Context

- Operación real de almacén: el recojo se registra por formulario; las series se escanean con lector de código de barras que se comporta como teclado. Los materiales no seriados se digitan por cantidad; los seriados generan una fila por serie con Cantidad 1.
- Circulación de documentos: Excel de asignación, traspaso, stock inicial, conciliación y reportes; actas de devolución; envío por correo al buzón de la región. Los formatos viven en `04-contratos/` como configuración, no como constantes del código.
- Parámetros por región: Centro, Almacén y buzón son datos de la región. Movimiento es Z31 para asignación y Z32 para desasignación. La longitud y el formato de la serie son configurables.
- Acceso: login por correo electrónico, invitación de un solo uso con vencimiento, 2FA TOTP obligatorio para Administrador de plataforma y Responsable de almacén. No hay autoregistro ni recuperación de contraseña o de códigos.
- Trabajo de escritorio en navegador, en español, con conexión a PostgreSQL y un worker Celery separado para tareas de correo y procesos de fondo.
- Contexto de curso: el repositorio es también evidencia de arquitectura (docs de análisis, C4 y ADR); la spec y la constitución son la autoridad del comportamiento.

## Capabilities and Constraints

- Alcance funcional por specs: 001 tenants y acceso, 002 materiales, 003 técnicos, 004 recojo de materiales, 005 stock inicial de técnicos, 006 solicitud de asignación, 007 envío y revisión del almacén, 008 confirmación y actualización de stock, 009 traspaso entre técnicos, 010 conciliación de stock, 011 logística inversa y devoluciones, 012 reportes mensuales, 013 registro de materiales.
- Stack fijado por la constitución y las ADR: Python 3.12+, Django LTS 5.x, PostgreSQL 16+ (RLS como respaldo), Celery + Redis, HTMX, `openpyxl`, `pyotp`, `cryptography`. Sin SQLite, ni en pruebas. Monolito modular; la lógica de negocio vive en `services.py` de cada app.
- Aislamiento: tenant y región se derivan solo de la sesión (`request.usuario`), nunca de parámetros del cliente. Acceso ajeno responde 404, sin revelar existencia ni propietario. El catálogo de materiales es global, sin `tenant_id`; su código es único global.
- Invariantes de stock: dos niveles (general del tenant y por técnico); solo una asignación confirmada mueve material del general al técnico; los traspasos nunca cambian el stock general ni el total del tenant; no se asigna más de lo disponible descontando reservas; el lote es informativo y no separa stock; una baja no se reasigna.
- No se eliminan regiones, tenants, cuentas ni materiales: se desactivan o suspenden. Toda alta o cambio se audita en `auditoria.RegistroCambio`, en la misma transacción; la auditoría es de solo inserción y nunca guarda contraseñas, tokens ni secretos TOTP.
- Idioma: interfaz, documentación y nombres de código en español.
- Decisión abierta (no inventar): no hay requisito de accesibilidad específico declarado en la documentación del producto.
- Decisión abierta (no inventar): no hay dominio público, licencia ni destino de despliegue definidos.

## Brand Commitments

- Nombre de producto: «Lari», usado en la interfaz como «Lari · Control de materiales». Es lo único vinculante según la persona responsable.
- No existe logo, manual de marca ni paleta corporativa. La apariencia actual de `templates/` y `static/css/base.css` es un punto de partida, no una identidad confirmada.
- Tono confirmado por la documentación: español directo y operativo, sin marketing ni promesas comerciales.

## Evidence on Hand

- Verdad de dominio: `.specify/memory/constitution.md`, `03-reglas-de-dominio/`, `04-contratos/` y las specs 001–013 en `05-especificaciones/`.
- Implementación existente: apps Django (`tenants`, `acceso`, `auditoria`, `materiales`, `tecnicos`, `recojos`, `asignaciones`, `traspasos`, `conciliaciones`, `logistica_inversa`, `reportes`, `registro_materiales`) y plantillas en `templates/`.
- Contexto de arquitectura y curso: `docs/` (actores, requisitos, calidad, ADR, C4).
- Ausencias que no se deben fabricar: no hay clientes reales, testimonios, métricas de negocio, precios, planes, fotos de operación ni material de prensa. Cualquier cifra o caso de éxito tendría que venir de la persona responsable.

## Product Principles

1. **La sesión manda.** Tenant y región salen de la sesión autenticada; un intento de acceso ajeno se trata como inexistente (404). Ninguna pantalla ni formulario confía en identificadores enviados por el cliente.
2. **Todo o nada, y con rastro.** Toda operación de stock es transaccional y deja auditoría inmutable en la misma transacción; no hay estados intermedios ni correcciones sin movimiento nuevo.
3. **La fuente de verdad es de Lari, la decisión es humana.** Cargar un reporte no cambia stock; la conciliación se aprueba o rechaza completa, mostrando cada serie discrepante.
4. **La operación real manda.** Escaneo de series, Excel, correo y una sola cuenta por tenant son el flujo, no una limitación a esquivar; la interfaz debe hacer ese trabajo rápido y a prueba de error.
5. **Documento primero.** No se implementa nada fuera de una spec aprobada; ante conflicto se corrige el documento y luego el código.
