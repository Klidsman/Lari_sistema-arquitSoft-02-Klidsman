# Plan de Implementación - Desglose de Tareas por Spec

## Orden de Implementación Recomendado

Las specs deben implementarse en este orden debido a las dependencias:

1. **Spec 001 - Tenants y Acceso** (base de todo el sistema)
2. **Spec 002 - Materiales** (catálogo compartido)
3. **Spec 003 - Técnicos** (depende de tenants)
4. **Spec 004 - Recojo de Materiales** (depende de técnicos y materiales)
5. **Spec 008 - Confirmación y Actualización de Stock** (servicio compartido, sin UI)
6. **Spec 005 - Stock Inicial de Técnicos** (depende de técnicos, materiales y stock)
7. **Spec 006 - Solicitud de Asignación** (depende de técnicos, materiales y stock)
8. **Spec 007 - Envío y Revisión del Almacén** (depende de asignaciones)
9. **Spec 009 - Traspaso entre Técnicos** (depende de técnicos, materiales y stock)
10. **Spec 010 - Conciliación de Stock** (depende de técnicos, materiales y stock)
11. **Spec 011 - Logística Inversa y Devoluciones** (depende de técnicos y stock)
12. **Spec 013 - Registro de Materiales** (módulo independiente, depende de técnicos y materiales)
13. **Spec 012 - Reportes Mensuales** (puede ser al final, depende de todos los módulos)

---

## Spec 001 - Tenants y Acceso

### Fase 1: Configuración Base
- [ ] Crear proyecto Django
- [ ] Configurar PostgreSQL
- [ ] Configurar Redis (para Celery)
- [ ] Configurar middleware de contexto de tenant
- [ ] Configurar sistema de autenticación

### Fase 2: Modelos
- [ ] Crear app `tenants`
- [ ] Implementar modelo `Tenant`
- [ ] Implementar modelo `Usuario`
- [ ] Implementar modelo `Region`
- [ ] Crear migraciones
- [ ] Crear superusuario inicial

### Fase 3: Servicios
- [ ] Implementar servicio de validación de cuenta tenant
- [ ] Implementar servicio de creación de tenant
- [ ] Implementar servicio de creación de usuario

### Fase 4: Vistas y UI
- [ ] Implementar vista de login
- [ ] Implementar vista de registro de tenant
- [ ] Implementar middleware de tenant

### Fase 5: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de middleware

---

## Spec 002 - Materiales

### Fase 1: Modelos
- [ ] Crear app `materiales`
- [ ] Implementar modelo `Material`
- [ ] Implementar modelo `Lote`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de validación de material
- [ ] Implementar servicio de búsqueda de material

### Fase 3: Vistas y UI
- [ ] Implementar vista de catálogo de materiales
- [ ] Implementar vista de creación de material

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas

---

## Spec 003 - Técnicos

### Fase 1: Modelos
- [ ] Crear app `tecnicos`
- [ ] Implementar modelo `Tecnico`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de validación de técnico
- [ ] Implementar servicio de normalización de NIF
- [ ] Implementar servicio de activación/desactivación
- [ ] Implementar servicio de técnicos para operación

### Fase 3: Vistas y UI
- [ ] Implementar vista de lista de técnicos
- [ ] Implementar vista de creación de técnico
- [ ] Implementar vista de edición de técnico

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas

---

## Spec 004 - Recojo de Materiales

### Fase 1: Modelos
- [ ] Crear app `recojos`
- [ ] Implementar modelo `Recojo`
- [ ] Implementar modelo `LineaRecojo`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de validación de series
- [ ] Implementar servicio de normalización de series
- [ ] Implementar servicio de creación de recojo
- [ ] Implementar servicio de generación de Excel

### Fase 3: Vistas y UI
- [ ] Implementar vista de lista de recojos
- [ ] Implementar vista de creación de recojo
- [ ] Implementar selector de series con HTMX

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de validación de series

---

## Spec 008 - Confirmación y Actualización de Stock

### Fase 1: Modelos
- [ ] Crear app `stock`
- [ ] Implementar modelo `StockGeneral`
- [ ] Implementar modelo `StockTecnico`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de incremento de stock técnico
- [ ] Implementar servicio de decremento de stock técnico
- [ ] Implementar servicio de incremento de stock general
- [ ] Implementar servicio de decremento de stock general
- [ ] Implementar servicio de cálculo de disponibilidad
- [ ] Implementar servicio de auditoría de stock

### Fase 3: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de restricciones de base de datos

---

## Spec 005 - Stock Inicial de Técnicos

### Fase 1: Modelos
- [ ] Crear app `stock_inicial`
- [ ] Implementar modelo `CargaStockInicial`
- [ ] Implementar modelo `LineaStockInicial`
- [ ] Agregar campo a `Tenant` para marcar stock inicial cargado
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de lectura de Excel
- [ ] Implementar servicio de procesamiento de Excel
- [ ] Implementar servicio de carga de stock inicial
- [ ] Implementar servicio de edición de stock inicial
- [ ] Implementar servicio de validación de series

### Fase 3: Vistas y UI
- [ ] Implementar vista de carga de stock inicial
- [ ] Implementar vista de edición de stock inicial
- [ ] Implementar vista de carga por formulario

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de edición

---

## Spec 006 - Solicitud de Asignación

### Fase 1: Modelos
- [ ] Crear app `asignaciones`
- [ ] Implementar modelo `SolicitudAsignacion`
- [ ] Implementar modelo `LineaAsignacion`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de validación de disponibilidad
- [ ] Implementar servicio de validación de cupo máximo
- [ ] Implementar servicio de creación de solicitud
- [ ] Implementar servicio de envío de solicitud
- [ ] Implementar servicio de generación de Excel
- [ ] Implementar servicio de cancelación de solicitud

### Fase 3: Vistas y UI
- [ ] Implementar vista de lista de solicitudes
- [ ] Implementar vista de creación de solicitud
- [ ] Implementar selector de series con HTMX
- [ ] Implementar validación en tiempo real

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de validación

---

## Spec 007 - Envío y Revisión del Almacén

### Fase 1: Modelos
- [ ] Agregar modelo `EnvioCorreo` a app `asignaciones`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de envío de correo (Celery task)
- [ ] Implementar servicio de reintentos
- [ ] Implementar servicio de confirmación de solicitud
- [ ] Implementar servicio de rechazo de solicitud
- [ ] Implementar servicio de notificaciones en tiempo real
- [ ] Implementar servicio de búsqueda de Excels históricos

### Fase 3: Configuración Celery
- [ ] Configurar Celery
- [ ] Configurar worker de Celery
- [ ] Configurar Redis como broker

### Fase 4: Vistas y UI
- [ ] Implementar vista de bandeja de despachos (almacén)
- [ ] Implementar vista de detalle de solicitud (almacén)
- [ ] Implementar vista de confirmación/rechazo
- [ ] Implementar vista de búsqueda de Excels históricos
- [ ] Implementar WebSocket para notificaciones

### Fase 5: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de Celery tasks
- [ ] Pruebas de vistas
- [ ] Pruebas de WebSocket

---

## Spec 009 - Traspaso entre Técnicos

### Fase 1: Modelos
- [ ] Crear app `traspasos`
- [ ] Implementar modelo `SolicitudTraspaso`
- [ ] Implementar modelo `LineaTraspaso`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de validación de técnicos mismo tenant
- [ ] Implementar servicio de validación de disponibilidad en origen
- [ ] Implementar servicio de validación de cuadre
- [ ] Implementar servicio de creación de traspaso
- [ ] Implementar servicio de envío de traspaso
- [ ] Implementar servicio de generación de Excel (dos hojas)
- [ ] Implementar servicio de confirmación de traspaso
- [ ] Implementar servicio de rechazo de traspaso
- [ ] Implementar servicio de cancelación de traspaso

### Fase 3: Vistas y UI
- [ ] Implementar vista de lista de traspasos
- [ ] Implementar vista de creación de traspaso
- [ ] Implementar selector de series del técnico origen
- [ ] Implementar vista de detalle de traspaso

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de cuadre

---

## Spec 010 - Conciliación de Stock

### Fase 1: Modelos
- [ ] Crear app `conciliaciones`
- [ ] Implementar modelo `Conciliacion`
- [ ] Implementar modelo `DiferenciaSerie`
- [ ] Implementar modelo `DiferenciaCantidad`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de lectura de Excel de Lari
- [ ] Implementar servicio de validación de reporte
- [ ] Implementar servicio de filtrado por tenant
- [ ] Implementar servicio de comparación de series
- [ ] Implementar servicio de comparación de cantidades
- [ ] Implementar servicio de creación de conciliación
- [ ] Implementar servicio de recálculo de diferencias
- [ ] Implementar servicio de aprobación de conciliación
- [ ] Implementar servicio de rechazo de conciliación

### Fase 3: Vistas y UI
- [ ] Implementar vista de lista de conciliaciones
- [ ] Implementar vista de carga de reporte
- [ ] Implementar vista de detalle de conciliación
- [ ] Implementar vista de aprobación/rechazo
- [ ] Implementar alertas visuales categorizadas

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de lectura de Excel

---

## Spec 011 - Logística Inversa y Devoluciones

### Fase 1: Modelos
- [ ] Crear app `logistica_inversa`
- [ ] Implementar modelo `Devolucion`
- [ ] Implementar modelo `LineaDevolucion`
- [ ] Implementar modelo `BajaEquipo`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de validación de series
- [ ] Implementar servicio de registro de devolución
- [ ] Implementar servicio de registro de baja
- [ ] Implementar servicio de generación de acta de devolución

### Fase 3: Vistas y UI
- [ ] Implementar vista de lista de devoluciones
- [ ] Implementar vista de registro de devolución
- [ ] Implementar vista de lista de bajas
- [ ] Implementar vista de registro de baja
- [ ] Implementar vista de descarga de acta

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de generación de acta

---

## Spec 013 - Registro de Materiales

### Fase 1: Modelos
- [ ] Crear app `registro_materiales`
- [ ] Implementar modelo `MaterialHabilitado`
- [ ] Implementar modelo `SaldoInicialPeriodo`
- [ ] Implementar modelo `DespachoAlmacen`
- [ ] Implementar modelo `OrdenLiquidacion`
- [ ] Implementar modelo `UsoMaterialOrden`
- [ ] Implementar modelo `RegistroCambio` (si no existe)
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de cálculo de periodo
- [ ] Implementar servicio de validación de cantidad
- [ ] Implementar servicio de guardar orden
- [ ] Implementar servicio de registrar saldo inicial
- [ ] Implementar servicio de registrar despacho
- [ ] Implementar servicio de cálculo de saldo inicial efectivo
- [ ] Implementar servicio de cálculo de saldo final
- [ ] Implementar servicio de reporte mensual

### Fase 3: Vistas y UI
- [ ] Implementar vista de registro por orden
- [ ] Implementar vista de contexto de orden (HTMX)
- [ ] Implementar vista de guardado de orden
- [ ] Implementar vista de historial de cambios
- [ ] Implementar vista de entradas manuales
- [ ] Implementar vista de saldo inicial
- [ ] Implementar vista de despachos
- [ ] Implementar vista de reporte mensual

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de aislamiento multitenant

---

## Spec 012 - Reportes Mensuales

### Fase 1: Modelos
- [ ] Crear app `reportes`
- [ ] Implementar modelo `CorteMensual`
- [ ] Crear migraciones

### Fase 2: Servicios
- [ ] Implementar servicio de cálculo de totales mensuales
- [ ] Implementar servicio de generación de corte mensual
- [ ] Implementar servicio de regeneración de corte mensual
- [ ] Implementar servicio de exportación de auditoría a Excel
- [ ] Implementar servicio de exportación de conciliación a Excel

### Fase 3: Vistas y UI
- [ ] Implementar vista de lista de cortes mensuales
- [ ] Implementar vista de generación de corte
- [ ] Implementar vista de detalle de corte
- [ ] Implementar vista de regeneración de corte
- [ ] Implementar vista de exportación de auditoría
- [ ] Implementar vista de exportación de conciliación

### Fase 4: Pruebas
- [ ] Pruebas de modelos
- [ ] Pruebas de servicios
- [ ] Pruebas de vistas
- [ ] Pruebas de cálculo de merma

---

## Tareas Transversales

### Middleware y Contexto
- [ ] Implementar middleware de contexto de tenant
- [ ] Implementar decoradores de permisos
- [ ] Implementar RLS en PostgreSQL (opcional)

### Auditoría
- [ ] Crear app `auditoria` (si no existe)
- [ ] Implementar modelo `RegistroCambio`
- [ ] Implementar servicio de registro de cambios
- [ ] Integrar con todas las specs

### Excel
- [ ] Crear módulo compartido de generación de Excel
- [ ] Implementar función de cálculo de hash SHA-256
- [ ] Integrar con todas las specs que generan Excel

### Pruebas
- [ ] Configurar pytest
- [ ] Crear fixtures comunes
- [ ] Crear factory para tenants
- [ ] Crear factory para técnicos
- [ ] Crear factory para materiales
- [ ] Configurar coverage

### Despliegue
- [ ] Configurar Docker
- [ ] Configurar gunicorn
- [ ] Configurar nginx
- [ ] Configurar scripts de migración
