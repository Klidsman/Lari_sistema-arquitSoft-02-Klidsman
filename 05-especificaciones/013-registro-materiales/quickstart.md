# Quickstart y validación: 013 Registro de Materiales

**Fase**: 1 | **Fecha**: 2026-11-13 | **Spec**:
`05-especificaciones/013-registro-materiales/spec.md`

Guía para validar la carga masiva de órdenes, el registro de materiales, el bloqueo de saldos
negativos, el dashboard y el cierre mensual. Los detalles de datos están en `data-model.md` y los
contratos en `contracts/`.

## Prerrequisitos

- Python 3.12+.
- PostgreSQL 16+ con rol sin `SUPERUSER` ni `BYPASSRLS`.
- Specs 001, 002 y 003 implementadas.
- `MaterialHabilitado`, `SaldoInicialPeriodo` y `DespachoAlmacen` existentes en 013; `DespachoAlmacen` con `tenant`, `material`, `fecha` y `cantidad`.
- `auditoria.RegistroCambio` con `tenant`.
- App `registro_materiales` registrada en `config/settings/base.py` y migraciones aplicadas.

Si falta cualquiera, la validación se detiene y se reporta.

## Configuración inicial

Seguir la configuración de `05-especificaciones/001-tenants-y-acceso/quickstart.md` (venv,
dependencias, PostgreSQL y `.env`). Después:

```powershell
python manage.py migrate
python manage.py check
```

Comprobar las tablas:

```powershell
python manage.py shell -c "from registro_materiales.models import CargaOrdenes, OrdenLiquidacion, UsoMaterialOrden, DespachoAlmacen, CierreMensual; print(CargaOrdenes._meta.db_table, OrdenLiquidacion._meta.db_table, DespachoAlmacen._meta.db_table, CierreMensual._meta.db_table)"
```

**Esperado**: las tablas existen, sin errores.

## Pruebas automatizadas

```powershell
# Unitarias
pytest tests/unit/test_registro_carga.py tests/unit/test_registro_materiales.py
pytest tests/unit/test_registro_saldos.py tests/unit/test_registro_exportacion.py

# Integración
pytest tests/integration/test_carga_ordenes.py tests/integration/test_materiales_uso.py
pytest tests/integration/test_bloqueo_negativo.py tests/integration/test_dashboard.py
pytest tests/integration/test_cierre_mensual.py tests/integration/test_auditoria.py
pytest tests/integration/test_concurrencia.py tests/integration/test_aislamiento.py

# Contrato HTTP
pytest tests/contract/test_registro_http.py

# Todo 013
pytest -k "registro"

# Cobertura
pytest --cov=registro_materiales
```

Las pruebas requieren PostgreSQL real; validan restricciones, bloqueos, RLS y concurrencia.

## Escenarios de validación

### 1. Menú y aislamiento (CA-01)

1. Iniciar sesión como cuenta del tenant.
2. Abrir “Registrar materiales”.
3. Intentar acceder a datos de otro tenant.

**Esperado**: el menú aparece; solo se ven técnicos, materiales, órdenes y saldos del tenant. Un
recurso ajeno devuelve `404`.

### 2. Catálogo habilitado (CA-02)

1. Abrir la pantalla de catálogo y habilitar dos materiales.
2. Deshabilitar uno.
3. Abrir una orden nueva.

**Esperado**: solo aparecen materiales activos con cantidades en 0. El deshabilitado conserva
historial y no se ofrece en nuevas órdenes.

### 3. Normalización de la lista (CA-03)

Pegar una lista con:

- espacios al inicio/final;
- líneas vacías;
- mayúsculas/minúsculas repetidas;
- una línea con dos valores.

**Esperado**: se recortan espacios, se descartan vacías, se deduplica sin distinguir mayúsculas y se
rechaza la línea con más de un valor.

### 4. Carga idempotente (CA-04)

1. Cargar una lista para un técnico/mes.
2. Volver a pegar la misma lista.

**Esperado**: las existentes se omiten; no se duplican.

### 5. Orden de otro técnico (CA-05)

1. Cargar una orden que ya existe para LA0234.
2. Seleccionar LA1234 y cargarla.

**Esperado**: se crea para LA1234 y el resumen indica que también existe para LA0234.

### 6. Resumen de carga (CA-06)

**Esperado**:

```text
12 leídas, 3 nuevas para LA1234, 9 ya existían para LA1234
(2 de ellas también existen para LA0234)
```

### 7. Deshacer carga (CA-07)

1. Deshacer una carga reciente sin materiales.

**Esperado**: se eliminan solo las órdenes nuevas del lote y queda auditoría. Si alguna tiene
materiales, se bloquea y se indica cuál.

### 8. Orden existente se abre (CA-08)

1. Seleccionar técnico y mes.
2. Buscar una orden existente del técnico/mes.

**Esperado**: se abre para editar; no se duplica. Si el mismo número existe en otro mes, no aparece
hasta cambiar el mes seleccionado.

### 9. Cambio de mes (CA-09)

1. Abrir una orden y cambiar la fecha de instalación a otro mes.

**Esperado**: se recalcula el periodo, se revalida la clave y se recalculan ambos meses.

### 10. Cantidad 0 (CA-10)

1. Dejar una cantidad vacía o en 0.

**Esperado**: no suma como usado.

### 11. Cantidad inválida (CA-11)

1. Ingresar negativos, decimales o letras.

**Esperado**: “La cantidad debe ser un número entero mayor o igual a 0”.

### 12. Bloqueo de saldo negativo (CA-12)

1. Disponible del mes: 45.
2. Uso acumulado: 40.
3. Intentar usar 10.

**Esperado**: no se guarda; se muestra disponible 45, usado 40 y faltante 5.

### 13. Advertencia atípica (CA-13)

1. Ingresar una cantidad superior a 3 veces el promedio mensual de los últimos 3 meses cerrados.

**Esperado**: se advierte, pero se guarda. La advertencia se resuelve con una justificación o con una
justificación de cierre; hasta entonces bloquea el cierre.

### 14. Saldo final (CA-14)

1. Inicial 100, despachos 20, usado 30.

**Esperado**: saldo final 90.

### 15. Herencia de saldo (CA-15)

1. Mes anterior con final 90.
2. Mes actual sin saldo manual.

**Esperado**: inicial 90.

### 16. Saldo manual prevalece (CA-16)

1. Cargar saldo manual distinto.
2. Consultar el reporte.

**Esperado**: prevalece y el cambio queda auditado. Si el saldo manual dejaría el mes en negativo
frente al uso ya registrado, se rechaza.

### 17. Despachos existentes (CA-17)

1. Registrar un despacho en `DespachoAlmacen`.
2. Consultar el mes en 013.

**Esperado**: su cantidad suma al disponible sin volver a registrarse en materiales. Si el mes está
cerrado, el alta/edición del despacho se rechaza con `PeriodoCerrado`.

### 18. Historial de edición (CA-18)

1. Editar una orden, un uso o un saldo.
2. Consultar el historial.

**Esperado**: usuario, fecha, valor anterior y valor nuevo.

### 19. Órdenes pendientes (CA-19)

1. Cargar órdenes sin materiales.
2. Abrir el panel de pendientes.

**Esperado**: aparecen con filtro por antigüedad y acceso al registro.

### 20. Cierre con checklist (CA-20)

1. Intentar cerrar un mes con órdenes pendientes, negativos o advertencias sin resolver.

**Esperado**: el cierre se bloquea hasta resolver o justificar. Una advertencia se resuelve con
`resolver_advertencia` o con una justificación de cierre; después se permite cerrar.

### 21. Cierre y traspaso (CA-21)

1. Ejecutar `python manage.py respaldar_bd --destino backups/` y copiar la referencia emitida.
2. Cerrar un mes con saldo final 30.
3. Consultar el mes siguiente.

**Esperado**: el inicial es 30 y el saldo está congelado. Sin una referencia válida de respaldo, el
cierre se bloquea.

### 22. Reapertura (CA-22)

1. Reabrir un mes cerrado con motivo.

**Esperado**: se registra quién, cuándo y por qué; el mes vuelve a abrirse.

### 23. Exportación (CA-23)

1. Exportar reporte mensual y detalle de órdenes.
2. Elegir Excel o CSV.

**Esperado**: archivo con datos del tenant, totales, detalle por técnico y sin datos ajenos.

## Escenarios complementarios

### Carga masiva

- Lista vacía: no crea nada.
- Línea con tabs/comas: rechazada.
- Misma orden en otro mes: permitida.
- Doble clic en confirmar: no duplica.

### Materiales

- Uso que deja saldo 0: permitido.
- Uso que deja negativo: bloqueado.
- Material deshabilitado con historial: se muestra en orden existente, no en nuevas.
- Cambio de fecha a mes cerrado: `409`.

### Dashboard

- Filtros por mes, técnico, material y fechas.
- Saldo negativo con alerta.
- Detalle por técnico.
- Sin N+1.

### Cierre

- Sin backup: bloqueado.
- Con pendientes justificados: permitido.
- Reapertura y recálculo.
- Un mes cerrado rechaza usos y saldos con `409`.

### Exportación

- Reporte y órdenes en `.xlsx` y `.csv`.
- Sin datos de otro tenant.
- Periodo sin datos genera archivo válido.

## Criterios de salida

- [ ] `pytest -k "registro"` pasa completo sobre PostgreSQL.
- [ ] CA-01…CA-23 tienen al menos una prueba automatizada.
- [ ] La carga masiva es idempotente y deshacible sin materiales.
- [ ] El uso no puede dejar saldo negativo.
- [ ] La advertencia atípica no bloquea, pero sí el cierre sin resolver.
- [ ] El saldo final se hereda y se congela al cerrar.
- [ ] Los despachos se leen de `DespachoAlmacen` sin doble registro.
- [ ] El cierre exige checklist y backup.
- [ ] La reapertura exige motivo y queda auditada.
- [ ] Excel/CSV solo contienen datos del tenant.
- [ ] No se modifica stock, series, asignaciones, traspasos ni conciliaciones.
