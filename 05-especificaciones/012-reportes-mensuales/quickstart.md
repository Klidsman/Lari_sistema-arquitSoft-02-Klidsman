# Quickstart y validación: 012 Reportes Mensuales

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/012-reportes-mensuales/spec.md`

Guía para validar el corte mensual, el cálculo de merma y las exportaciones de auditoría y
conciliación. Los detalles de datos están en `data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Python 3.12+.
- PostgreSQL 16+ con rol sin `SUPERUSER` ni `BYPASSRLS`.
- Specs 001–011 implementadas hasta lo que 012 consume.
- `RegistroCambio.tenant` nullable y `Conciliacion.ajustes_aplicados` aplicados.
- `SolicitudAsignacion`/`LineaAsignacion`, `Devolucion`/`LineaDevolucion` y `Conciliacion` con datos
  de prueba.
- App `reportes` registrada en `config/settings/base.py` y migraciones aplicadas.

Si falta cualquiera, la validación se detiene y se reporta.

## Configuración inicial

Seguir la configuración de `05-especificaciones/001-tenants-y-acceso/quickstart.md` (venv,
dependencias, PostgreSQL y `.env`). Después:

```powershell
python manage.py migrate
python manage.py check
```

Comprobar la tabla y los campos de apoyo:

```powershell
python manage.py shell -c "from reportes.models import CorteMensual; from auditoria.models import RegistroCambio; from conciliaciones.models import Conciliacion; print(CorteMensual._meta.db_table, RegistroCambio._meta.get_field('tenant'), Conciliacion._meta.get_field('ajustes_aplicados'))"
```

**Esperado**: `reportes_cortemensual` y los campos existen, sin errores.

No se crean cortes por migración. Los datos de prueba se crean con fixtures o con los flujos normales
de 006/007/008/010/011.

## Pruebas automatizadas

```powershell
# Servicios y Excel
pytest tests/unit/test_reportes_servicios.py tests/unit/test_reportes_excel.py

# Integración
pytest tests/integration/test_corte_mensual.py tests/integration/test_exportacion_auditoria.py
pytest tests/integration/test_exportacion_conciliacion.py tests/integration/test_reportes_auditoria.py
pytest tests/integration/test_reportes_concurrencia.py

# Contrato HTTP
pytest tests/contract/test_reportes_http.py

# Todo 012
pytest -k "reporte or corte or merma"

# Cobertura
pytest --cov=reportes
```

Las pruebas requieren PostgreSQL real; validan restricciones parciales, agregaciones, RLS y
concurrencia.

## Escenarios de validación

Los escenarios usan pruebas con datos propios: tenants, técnicos, solicitudes confirmadas, series
`INSTALADA`, devoluciones y conciliaciones.

### CA-01: Corte mensual con totales

1. Generar un corte para un mes/año con datos.
2. Consultar el detalle.

**Esperado**: muestra solicitados, asignados, liquidados/instalados, devueltos, no justificado y %
merma; el corte queda guardado con versión 1.

Prueba principal: `test_corte_mensual_con_totales`.

### CA-02: Cálculo de merma correcto

1. Preparar 100 asignados, 80 liquidados/instalados y 5 devueltos en el mes.
2. Generar el corte.

**Esperado**: no justificado = 15 y % merma = 15.00. Con 0 asignados, merma 0. Si los eventos superan
los asignados, no justificado se acota a 0.

Prueba principal: `test_calculo_merma_correcto`.

### CA-03: Exportación de auditoría a Excel

1. Generar un corte con movimientos auditados en el mes.
2. Descargar la auditoría.

**Esperado**: un `.xlsx` de una hoja con Fecha, Usuario, Entidad, Acción, Valor anterior y Valor
nuevo, solo del tenant (o global si Admin), ordenado por fecha.

Prueba principal: `test_exportar_auditoria_excel`.

### CA-04: Exportación de conciliación a Excel

1. Generar un corte con conciliaciones del mes.
2. Descargar la conciliación.

**Esperado**: un `.xlsx` con Fecha, Estado, Tenant (solo global), Diferencias series, Diferencias
cantidades y Ajustes aplicados.

Prueba principal: `test_exportar_conciliacion_excel`.

## Escenarios complementarios

### Corte

- Un corte por tenant/mes/año y uno global por mes/año; duplicados `409`.
- Mes 1–12 y año 2000–2100; valores inválidos `400`.
- Regenerar incrementa `version`, actualiza totales y audita valores anterior/nuevo.
- Un corte ajeno devuelve `404`; el global solo lo ve el Admin.
- Un mes sin datos genera totales 0 y merma 0.

### Cálculo

- Series y no seriados cuentan como unidades: 1 por serie, cantidad por no seriado.
- Solicitados excluye `BORRADOR` y `CANCELADA`; asignados usa `confirmada_en` del mes.
- Liquidados/instalados usa `Serie/estado → INSTALADA` del mes; no suma `INACTIVA`.
- Devueltos usa `Devolucion.fecha` del mes.
- Los filtros usan `[inicio, fin)` y la zona configurada.

### Exportación de auditoría

- Solo registros del tenant; el global incluye todos.
- Columnas, orden y fechas correctos.
- No hay secretos, binarios ni rutas.
- Sin registros: archivo con encabezados.

### Exportación de conciliación

- Solo conciliaciones del mes del tenant; global incluye todos.
- Conteos de diferencias y `ajustes_aplicados` correctos.
- Sin conciliaciones: archivo con encabezados.

### Permisos y aislamiento

- El Admin puede generar/ver global y cualquier tenant.
- El tenant solo su tenant; no puede forzar global ni otro `tenant_id`.
- Un corte/exportación de otro tenant devuelve `404`.

### Concurrencia

- Dos generaciones simultáneas del mismo alcance/mes dejan una sola; la otra `409`.
- Dos regeneraciones simultáneas serializan y no pierden la versión.
- El orden no produce interbloqueo.

### Rendimiento

- Corte de 10 000 líneas y exportación de 5 000 registros en tiempo razonable, sin N+1.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest -k "reporte or corte or merma"` pasa completo sobre PostgreSQL.
- [ ] CA-01…CA-04 tienen al menos una prueba automatizada en verde.
- [ ] El corte guarda totales exactos y la merma se calcula con la regla documentada.
- [ ] El global y el tenant están aislados; el Admin ve el global.
- [ ] Las exportaciones contienen solo los datos del alcance y no persisten archivos.
- [ ] Regenerar audita valores anterior/nuevo y aumenta la versión.
- [ ] 012 no modifica stock, series, asignaciones ni conciliaciones.
- [ ] No se agregaron dependencias, Celery, correo ni permisos Django por cadena.
