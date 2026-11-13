# Quickstart y validación: 011 Logística Inversa y Devoluciones

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/011-logistica-inversa-y-devoluciones/spec.md`

Guía para validar devoluciones de series, bajas por avería/migración, generación del acta y auditoría.
Los detalles de datos están en `data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Python 3.12+.
- PostgreSQL 16+ con rol sin `SUPERUSER` ni `BYPASSRLS`.
- Specs 001, 002, 003, 004, 005, 008, 009 y 010 implementadas hasta lo que 011 consume.
- `series.Serie` con `tecnico`/`asignada_en` y estados `INSTALADA`/`INACTIVA`.
- `StockTecnico`/`StockGeneral` con servicios de incremento/decremento de 008.
- App `logistica_inversa` registrada en `config/settings/base.py` y migraciones aplicadas.

Si falta cualquiera, la validación se detiene y se reporta.

## Configuración inicial

Seguir la configuración de `05-especificaciones/001-tenants-y-acceso/quickstart.md` (venv,
dependencias, PostgreSQL y `.env`). Después:

```powershell
python manage.py migrate
python manage.py check
```

Comprobar el estado terminal y las tablas:

```powershell
python manage.py shell -c "from series.models import EstadoSerie; from logistica_inversa.models import Devolucion, LineaDevolucion, BajaEquipo; print(EstadoSerie.INACTIVA, Devolucion._meta.db_table, BajaEquipo._meta.db_table)"
```

**Esperado**: `INACTIVA`, `logistica_inversa_devolucion` y `logistica_inversa_bajaequipo`, sin
errores.

No se crean devoluciones ni bajas por migración. Los datos de prueba se crean con fixtures o con el
flujo normal de 005/008/009.

## Pruebas automatizadas

```powershell
# Servicios y acta
pytest tests/unit/test_logistica_inversa_servicios.py tests/unit/test_logistica_inversa_acta.py

# Integración
pytest tests/integration/test_devolucion_registro.py tests/integration/test_devolucion_stock.py
pytest tests/integration/test_baja_registro.py tests/integration/test_baja_stock.py
pytest tests/integration/test_logistica_inversa_concurrencia.py
pytest tests/integration/test_logistica_inversa_auditoria.py

# Contrato HTTP
pytest tests/contract/test_logistica_inversa_http.py

# Todo 011
pytest -k "logistica_inversa or devolucion or baja"

# Cobertura
pytest --cov=logistica_inversa
```

Las pruebas requieren PostgreSQL real; validan restricciones, bloqueos, RLS y concurrencia.

## Escenarios de validación

Los escenarios usan pruebas con datos propios: tenant, región, técnico, materiales, series
`ASIGNADA`, `StockTecnico` y `StockGeneral`.

### CA-01: Devolución libera custodia

1. Tener un técnico con series `ASIGNADA`.
2. Registrar una devolución con esas series.

**Esperado**: las series quedan `DISPONIBLE`, `tecnico=None`, `asignada_en=None`; el stock del
técnico baja y el general sube por el mismo total; el acta se genera.

Prueba principal: `test_devolucion_libera_custodia`.

### CA-02: Series devueltas pueden reasignarse

1. Devolver una serie.
2. Asignarla a otro técnico con el flujo de 006/008.

**Esperado**: la serie puede seleccionarse de nuevo y asignarse; no queda bloqueada por la devolución.

Prueba principal: `test_series_devueltas_pueden_reasignarse`.

### CA-03: Recuperación con causa

1. Registrar una baja de una serie `ASIGNADA` con causa `AVERIA`.

**Esperado**: la serie queda `INACTIVA`, sin técnico; el stock del técnico baja en 1; se registra la
causa y no se toca el stock general.

Prueba principal: `test_recuperacion_con_causa`.

### CA-04: Baja por migración

1. Registrar una baja de una serie `DISPONIBLE` con causa `MIGRACION`.

**Esperado**: la serie queda `INACTIVA`; el stock general baja en 1; el stock técnico no cambia; se
registra la causa.

Prueba principal: `test_baja_por_migracion`.

### CA-05: Generación de acta

1. Registrar una devolución con varias series.
2. Descargar el acta.

**Esperado**: un `.xlsx` de una hoja con tenant, región, fecha de generación, ID, NIF, material,
descripción, serie y fecha de devolución. El hash queda registrado; una alteración bloquea la
descarga.

Prueba principal: `test_generacion_acta`.

### CA-06: Auditoría de devoluciones

1. Registrar una devolución.
2. Consultar `RegistroCambio`.

**Esperado**: `Devolucion/alta`, una `LineaDevolucion/alta` por serie, `Devolucion/acta`,
`Serie/estado`, `Serie/tecnico`, `Serie/asignada_en`, y los `StockTecnico`/`StockGeneral/cantidad` de
008, con actor y valores anterior/nuevo.

Prueba principal: `test_auditoria_devoluciones`.

## Escenarios complementarios

### Devolución

- Serie no asignada al técnico: `409` “La serie no está asignada al técnico”.
- Serie reservada en un traspaso `ENVIADA`: `409` “La serie está reservada en otro traspaso”.
- Serie `INSTALADA`/`INACTIVA`: rechazo.
- Serie de otro tenant: rechazo sin revelar el tenant.
- Fecha futura: `400`.
- Sin series o serie duplicada: `400`.
- Un fallo del acta revierte la devolución y no deja archivo parcial.
- El stock nunca queda negativo.

### Baja

- Causa faltante o inválida: `400`.
- Serie `RESERVADA`: rechazo.
- Serie `INSTALADA`/`INACTIVA`: rechazo.
- Serie de otro tenant: rechazo.
- Doble baja: falla por `OneToOneField`.
- Baja de serie en técnico: solo baja `StockTecnico`.
- Baja de serie en general: solo baja `StockGeneral`.
- No se elimina la serie ni se toca el otro nivel de stock.

### Acta

- Una sola hoja y metadatos correctos.
- Tabla completa y ordenada por serie.
- Hash estable; descarga `200`; archivo ausente `404`; hash alterado `409`.
- Ruta relativa segura; no se expone la ruta física.
- No hay correo del sistema.

### Concurrencia

- Dos devoluciones simultáneas de la misma serie: solo una pasa.
- Dos bajas simultáneas: solo una crea la baja.
- Devolución y traspaso simultáneos: si la serie está reservada, la devolución falla.
- Orden `Tenant → StockGeneral (material) → StockTecnico (material) → Serie` sin interbloqueo.

### Auditoría

- Todos los eventos, con valor anterior y nuevo.
- Los cambios de stock son los de 008 y no se duplican.
- Sin secretos, binarios, rutas absolutas ni datos de otro tenant.

### Aislamiento

- Tenant A no ve devoluciones ni bajas de B.
- Un recurso ajeno devuelve `404`.
- Las series, el stock y el acta de otro tenant no se consultan.
- `LineaDevolucion.tenant` y `BajaEquipo.tenant` coinciden con la operación.

### Rendimiento

- Devolución de 100 series en menos de 2 segundos, sin una consulta por serie.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest -k "logistica_inversa or devolucion or baja"` pasa completo sobre PostgreSQL.
- [ ] CA-01…CA-06 tienen al menos una prueba automatizada en verde.
- [ ] La devolución deja series `DISPONIBLE` y mueve stock del técnico al general.
- [ ] La baja deja `INACTIVA` y descuenta solo el nivel correcto.
- [ ] Las series no se eliminan ni se reasignan tras la baja.
- [ ] El acta se genera al registrar, es inmutable y se descarga verificando el hash.
- [ ] La auditoría está completa y no duplica la de 008.
- [ ] Ningún tenant ve datos de otro.
- [ ] No se agregaron dependencias, correo, Celery ni permisos Django por cadena.
