# Quickstart y validación: 008 Confirmación y Actualización de Stock

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/008-confirmacion-y-actualizacion-de-stock/spec.md`

Guía para validar los modelos y servicios de stock y la actualización atómica que ocurre al
confirmar una solicitud. 008 no tiene interfaz propia: la validación se hace con pruebas
automatizadas y con la confirmación ya implementada por 007. Los detalles de datos están en
`data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Python 3.12 o superior.
- PostgreSQL 16 o superior con un rol de aplicación **sin** `SUPERUSER` ni `BYPASSRLS`.
- Redis 7 o superior, requerido por la infraestructura de 001/007 aunque 008 no encola tareas.
- Specs 001, 002, 003, 004, 006 y 007 implementadas hasta el punto que consume 008; en particular:
  - `AUTH_USER_MODEL="acceso.Usuario"` y `ContextoUsuarioMiddleware`.
  - `materiales.Material` con `es_seriado`.
  - `tecnicos.Tecnico` con `tenant`.
  - `series.Serie` con `EstadoSerie`.
  - `asignaciones.SolicitudAsignacion`/`LineaAsignacion` y `confirmar_solicitud` de 007.
  - `auditoria.services.registrar_cambio`.
- La app `stock` registrada en `config/settings/base.py` y sus migraciones aplicadas.

Si falta cualquiera de estos prerrequisitos, la validación se detiene y se reporta; no se crea una
infraestructura paralela.

## Configuración inicial

Seguir la configuración de `05-especificaciones/001-tenants-y-acceso/quickstart.md` (venv,
dependencias, PostgreSQL, Redis y `.env`). Después:

```powershell
python manage.py migrate
python manage.py check
```

Comprobar que la app quedó registrada y que las tablas existen:

```powershell
python manage.py shell -c "from stock.models import StockGeneral, StockTecnico; print(StockGeneral._meta.db_table, StockTecnico._meta.db_table)"
```

**Esperado**: `stock_general stock_tecnico`, sin errores de importación.

No se crean datos por migración: `StockGeneral` y `StockTecnico` empiezan vacías. El stock inicial
lo cargan 004 (recojos) y 005 (stock inicial de técnicos) usando los servicios de 008.

## Pruebas automatizadas

```powershell
# Servicios y validaciones de 008
pytest tests/unit/test_stock_servicios.py tests/unit/test_stock_validaciones.py

# Integración de stock
pytest tests/integration/test_stock_incrementos.py tests/integration/test_stock_decrementos.py
pytest tests/integration/test_stock_confirmacion.py tests/integration/test_stock_concurrencia.py
pytest tests/integration/test_stock_auditoria.py

# Contratos internos
pytest tests/contract/test_stock_servicios_contrato.py tests/contract/test_stock_confirmacion_contrato.py

# Todo 008
pytest -k "stock"

# Cobertura del módulo
pytest --cov=stock
```

Las pruebas requieren PostgreSQL real; no se ejecutan sobre SQLite porque validan
`CheckConstraint`, `UniqueConstraint`, `select_for_update` y concurrencia.

## Escenarios de validación

Los escenarios se ejecutan con pruebas que crean sus propios datos (tenant, región, técnico,
materiales, series y solicitud `ENVIADA`) y llaman a `stock.services` o a
`asignaciones.services.confirmar_solicitud` de 007. No se documenta el cuerpo de las pruebas; el
detalle de firmas está en `contracts/servicios-stock.md`.

### CA-01: Series pasan a `ASIGNADA`

1. Crear una solicitud `ENVIADA` con al menos una línea seriada y sus series `RESERVADA`.
2. Confirmar con `confirmar_solicitud(solicitud, actor_almacen)`.

**Esperado**: cada serie de la solicitud queda `ASIGNADA`; ninguna serie de otra solicitud ni de
otro tenant cambia. Una serie que no estaba `RESERVADA` aborta la confirmación con
`SerieNoReservada` y deja todo como estaba.

Prueba principal: `test_series_pasan_a_asignada_al_confirmar`.

### CA-02: Stock del técnico sube

1. Partir de `StockTecnico(tecnico, material) = 10`.
2. Confirmar una asignación de 5 series del mismo material.

**Esperado**: `StockTecnico.cantidad == 15`; se crea la fila si el técnico no tenía stock del
material (0 → 5). El total agregado por material se escribe una sola vez.

Prueba principal: `test_stock_tecnico_sube_con_series_y_no_seriados`.

### CA-03: Stock general baja

1. Partir de `StockGeneral(tenant, material) = 100`.
2. Confirmar una asignación de 5 series del mismo material.

**Esperado**: `StockGeneral.cantidad == 95`. Si el stock no alcanza, la confirmación falla con
`StockInsuficiente` y el stock queda en 100; nunca se crea una fila con cantidad negativa.

Prueba principal: `test_stock_general_baja_con_series_y_no_seriados`.

### CA-04: Actualización transaccional

1. Preparar una solicitud válida.
2. Forzar un fallo en la actualización del stock técnico (por ejemplo, un doble con una excepción
   inyectada en `incrementar_stock_tecnico`).
3. Confirmar y capturar el error.
4. Consultar series, stock general, stock técnico y auditoría.

**Esperado**: no hay cambios en ninguno de los cuatro; la solicitud sigue `ENVIADA` y
`confirmada_en` sigue nula. Ninguna actualización parcial es visible.

Prueba principal: `test_confirmacion_fallida_revierte_todo`.

### CA-05: Días en mano inician con la confirmación

1. Confirmar una asignación de material seriado y registrar `confirmada_en`.
2. Calcular los días en mano con la lógica de 006 usando una fecha de referencia del día siguiente.

**Esperado**: 1 día. 008 no crea contador ni tabla; `confirmada_en` lo escribe 007 en la misma
transacción y 008 solo lo lee.

Prueba principal: `test_dias_en_mano_inician_en_confirmada_en`.

### CA-06: Auditoría completa

1. Confirmar una solicitud con series y con líneas no seriadas.
2. Consultar `auditoria.RegistroCambio` de la transacción.

**Esperado**:

- Un registro `Serie/estado` `RESERVADA→ASIGNADA` por cada serie.
- Un registro `StockTecnico/cantidad` por material agregado, con valor anterior y nuevo.
- Un registro `StockGeneral/cantidad` por material agregado, con valor anterior y nuevo.
- Actor igual al usuario de la sesión que confirma; sin secretos, binarios ni rutas absolutas.
- El registro `SolicitudAsignacion/estado` es de 007 y aparece una sola vez.

Prueba principal: `test_auditoria_completa_de_series_y_stock`.

### CA-07: No seriados actualizan cantidad

1. Partir de `StockGeneral = 200` y `StockTecnico = 0` para un material no seriado.
2. Confirmar una asignación de 50 unidades.

**Esperado**: `StockTecnico == 50` y `StockGeneral == 150`. La cantidad se agrega por material, no
se crea una fila por unidad.

Prueba principal: `test_no_seriados_actualizan_cantidad_agregada`.

## Escenarios complementarios

### Servicios fundacionales

- `incrementar_stock_general` y `decrementar_stock_general` suman y restan con auditoría.
- `incrementar_stock_tecnico` y `decrementar_stock_tecnico` hacen lo propio y crean la fila si no
  existe, con `tenant = tecnico.tenant`.
- Un `StockTecnico` cuya fila existente tenga un `tenant` distinto al del técnico produce
  `TenantNoCoincide` y no se modifica.
- `cantidad=0` y `cantidad=-1` producen `CantidadInvalida` y no escriben.
- Un decremento mayor al stock produce `StockInsuficiente` y deja la fila intacta.
- `obtener_stock_general`/`obtener_stock_tecnico` devuelven `0` sin crear filas.

### Disponibilidad y reservado

- `calcular_reservado` suma solo líneas no seriadas de solicitudes `ENVIADA` del mismo tenant y
  material.
- Una solicitud `CONFIRMADA`, `RECHAZADA` o en borrador no suma al reservado.
- `calcular_disponible = max(0, stock general − reservado)`; material sin stock devuelve `0`.

### Concurrencia

- Dos confirmaciones simultáneas de la misma solicitud: solo una mueve stock; la otra recibe `409`.
- Dos decrementos simultáneos sobre la misma fila no dejan cantidad negativa.
- El orden `SolicitudAsignacion → Tenant → StockGeneral → StockTecnico → Serie` no produce
  interbloqueo en una prueba con dos transacciones.
- Insertar una cantidad negativa por SQL falla por `CheckConstraint`.
- Duplicar `(tenant, material)` o `(tecnico, material)` falla por `UniqueConstraint`.

### Integración con 007 y rechazo

- Si 008 falla, 007 revierte y la solicitud sigue `ENVIADA`.
- Si 007 falla después de 008, el stock y las series se revierten.
- El rechazo libera series `RESERVADA→DISPONIBLE` y no mueve stock.
- La notificación al tenant solo se emite después del commit.

### Rendimiento

- Confirmar 100 series se resuelve en menos de 2 segundos y sin una consulta por línea.

## Verificación de aislamiento

1. Crear dos tenants con materiales, técnicos y stock propios.
2. Confirmar una solicitud de `TEN-001`.
3. Consultar el stock y la auditoría desde `TEN-002` y desde un Responsable de almacén de otra
   región.

**Esperado**: `TEN-002` no ve stock, series ni auditoría de `TEN-001`; una petición forzada con
`tenant_id` ajeno se rechaza o se ignora y la operación queda en el tenant de la sesión.
`StockGeneral` y `StockTecnico` se filtran por su `tenant_id`; en `StockTecnico` debe coincidir con
`tecnico.tenant`.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest -k "stock"` pasa completo sobre PostgreSQL.
- [ ] CA-01…CA-07 tienen al menos una prueba automatizada en verde.
- [ ] No existe ningún camino que cree `StockGeneral` o `StockTecnico` con cantidad negativa.
- [ ] Los decrementos bloquean y validan antes de restar; no se usa `F()` ciego.
- [ ] Series y stock se actualizan exactamente una vez por confirmación.
- [ ] La auditoría contiene los tres tipos de registro y no duplica la de la solicitud.
- [ ] `SolicitudAsignacion.estado` y `confirmada_en` solo los escribe 007.
- [ ] El rechazo no mueve stock y libera series según 007.
- [ ] Ningún tenant ve datos de otro y `StockTecnico.tenant` coincide siempre con `tecnico.tenant`.
- [ ] No se agregaron endpoints, vistas, plantillas ni tareas Celery a 008.
