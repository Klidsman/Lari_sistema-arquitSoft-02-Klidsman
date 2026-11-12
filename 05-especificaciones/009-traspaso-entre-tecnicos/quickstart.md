# Quickstart y validación: 009 Traspaso entre Técnicos

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/009-traspaso-entre-tecnicos/spec.md`

Guía para validar el traspaso de materiales entre técnicos del mismo tenant: creación, selección de
series/cantidades, validación de disponibilidad y cuadre, generación del Excel de dos hojas, envío,
confirmación/rechazo y reinicio de días en mano. Los detalles de datos están en `data-model.md` y los
contratos en `contracts/`.

## Prerrequisitos

- Python 3.12 o superior.
- PostgreSQL 16+ con rol de aplicación sin `SUPERUSER` ni `BYPASSRLS`.
- Redis no es necesario para 009: no hay correo ni tareas Celery.
- Specs 001, 002, 003, 004, 005, 006, 007 y 008 implementadas hasta el punto que 009 consume.
- `series.Serie` con `tecnico` y `asignada_en` (migración de 009/004) y datos históricos rellenados.
- `StockTecnico` de 008 con servicios de incremento/decremento.
- App `traspasos` registrada en `config/settings/base.py` y migraciones aplicadas.

Si falta cualquiera, la validación se detiene y se reporta.

## Configuración inicial

Seguir la configuración de `05-especificaciones/001-tenants-y-acceso/quickstart.md` (venv,
dependencias, PostgreSQL y `.env`). Después:

```powershell
python manage.py migrate
python manage.py check
```

Comprobar los campos de custodia y las tablas nuevas:

```powershell
python manage.py shell -c "from series.models import Serie; from traspasos.models import SolicitudTraspaso, LineaTraspaso; print(Serie._meta.get_field('tecnico'), Serie._meta.get_field('asignada_en'), SolicitudTraspaso._meta.db_table, LineaTraspaso._meta.db_table)"
```

**Esperado**: los campos existen y las tablas son `traspasos_solicitudtraspaso` y
`traspasos_lineatraspaso`, sin errores.

No se crean traspasos por migración. Los datos de prueba se crean con fixtures o con el flujo normal
de 004/005/008.

## Pruebas automatizadas

```powershell
# Servicios, cuadre y Excel
pytest tests/unit/test_traspaso_servicios.py tests/unit/test_traspaso_cuadre.py tests/unit/test_traspaso_excel.py

# Integración
pytest tests/integration/test_traspaso_creacion.py tests/integration/test_traspaso_envio.py
pytest tests/integration/test_traspaso_confirmacion.py tests/integration/test_traspaso_rechazo.py
pytest tests/integration/test_traspaso_concurrencia.py tests/integration/test_traspaso_auditoria.py

# Contrato HTTP
pytest tests/contract/test_traspaso_http.py

# Todo 009
pytest -k "traspaso"

# Cobertura
pytest --cov=traspasos
```

Las pruebas requieren PostgreSQL real; validan `CheckConstraint`, `UniqueConstraint`,
`select_for_update`, RLS y concurrencia.

## Escenarios de validación

Los escenarios usan pruebas con datos propios: tenant, región, dos técnicos, materiales seriados y no
seriados, stock técnico y series `ASIGNADA`. El detalle de firmas está en
`contracts/servicios-traspaso.md`.

### CA-01: Traspaso entre técnicos del mismo tenant

1. Crear un traspaso entre `LA0001` (origen) y `LA0002` (destino) con 2 series y 10 unidades no
   seriadas.
2. Enviar la solicitud.
3. Descargar el Excel.

**Esperado**: el archivo tiene dos hojas, `Desasignación` (Z32, NIF de `LA0001`) y `Asignación`
(Z31, NIF de `LA0002`), con las mismas líneas. El estado es `ENVIADA` y el hash SHA-256 está
registrado. No se movió stock ni custodia todavía.

Prueba principal: `test_traspaso_mismo_tenant_genera_excel_dos_hojas`.

### CA-02: Origen y destino distintos

1. Intentar crear un traspaso con el mismo técnico como origen y destino.

**Esperado**: `400` con “El técnico origen y destino no pueden ser el mismo”; no se crea la
solicitud. La restricción de base también lo impide.

Prueba principal: `test_origen_destino_iguales_se_rechaza`.

### CA-03: Solo cede lo que tiene asignado

1. Partir de `StockTecnico(origen, material) = 10` y sin reservas.
2. Intentar traspasar 15 unidades no seriadas.

**Esperado**: `409` con “La cantidad supera el stock del técnico”; no se crea el traspaso. Con una
reserva `ENVIADA` de 4 unidades, el disponible es 6 y traspasar 7 también se rechaza.

Prueba principal: `test_solo_cede_lo_que_tiene_asignado`.

### CA-04: Cuadre de series

1. Construir una proyección de cuadre donde la serie `ABC123456789` aparece en la salida pero no en la
   entrada.
2. Ejecutar `validar_cuadre_traspaso`.

**Esperado**: `CuadreIncorrecto` con “Lo que sale debe cuadrar con lo que entra”; no se guarda el
traspaso ni el Excel. También se rechaza una serie duplicada o con material/lote distinto.

Prueba principal: `test_cuadre_series_incorrecto_rechaza`.

### CA-05: Cuadre de cantidades

1. Construir una proyección donde salen 50 unidades y entran 40 del mismo material.
2. Ejecutar `validar_cuadre_traspaso`.

**Esperado**: `CuadreIncorrecto`; no se guarda nada. La proyección real generada desde la lista
canónica siempre cuadra; la prueba demuestra que una manipulación o línea perdida se detecta.

Prueba principal: `test_cuadre_cantidades_incorrecto_rechaza`.

### CA-06: Confirmación cambia de técnico

1. Enviar un traspaso con series `ASIGNADA` al origen.
2. Confirmar como Responsable de almacén de la región.
3. Consultar `Serie.tecnico`.

**Esperado**: cada serie apunta al técnico destino y conserva `estado=ASIGNADA`. El stock del origen
bajó y el del destino subió por el mismo total. El estado de la solicitud es `CONFIRMADA`.

Prueba principal: `test_confirmar_cambia_tecnico_de_series`.

### CA-07: Rechazo no cambia nada

1. Enviar un traspaso.
2. Rechazar con un motivo.
3. Consultar series, stock y stock general.

**Esperado**: las series siguen `ASIGNADA` al origen, el stock técnico no cambió y el stock general
tampoco. La solicitud queda `RECHAZADA` con el motivo y `rechazada_en`. Un motivo vacío o solo
espacios devuelve `400`.

Prueba principal: `test_rechazar_no_cambia_nada`.

### CA-08: Stock general invariable

1. Registrar `StockGeneral` antes de crear.
2. Crear, enviar, confirmar y consultar.
3. Repetir con un rechazo y una cancelación.

**Esperado**: `StockGeneral.cantidad` es idéntica en todos los casos. Solo cambia `StockTecnico` al
confirmar.

Prueba principal: `test_stock_general_invariable`.

### CA-09: Días en mano reinician al traspasar

1. Partir de una serie con `asignada_en` hace 10 días en el origen.
2. Confirmar el traspaso.
3. Calcular los días en mano con la lógica de 006.

**Esperado**: `Serie.asignada_en` es la fecha de confirmación del traspaso y los días en mano en el
destino son 0. La fecha anterior queda en la auditoría `Serie/asignada_en`.

Prueba principal: `test_dias_en_mano_reinician_al_traspasar`.

## Escenarios complementarios

### Creación y edición

- Un borrador no reserva series ni cantidades y no genera Excel.
- Editar líneas de un borrador revalida disponibilidad y cuadre; no toca stock ni series.
- Editar un traspaso `ENVIADA`, `CONFIRMADA`, `RECHAZADA` o `CANCELADA` devuelve `409`.
- Un traspaso de otro tenant devuelve `404`.

### Disponibilidad y selector

- `calcular_reservado_tecnico` suma líneas no seriadas y cuenta 1 por serie de solicitudes `ENVIADA`.
- `calcular_disponible_tecnico` aplica `max(0, stock técnico − reservado)`.
- `series_disponibles_para_traspaso` muestra solo series `ASIGNADA` del origen, del material y no
  reservadas.
- Un técnico destino inactivo se rechaza; un origen inactivo con stock puede vaciarse.

### Envío

- Enviar un traspaso sin líneas o con líneas inválidas devuelve `409`/`400` y no genera Excel.
- Enviar dos veces el mismo traspaso: la segunda recibe `409`.
- Si el Excel no se puede escribir, el estado no cambia y no queda archivo parcial.
- El correo no se envía porque 009 no lo implementa.

### Confirmación y rechazo

- Confirmar un traspaso que ya no está `ENVIADA` devuelve `409`.
- Si una serie dejó de estar en el origen antes de confirmar, se revierte todo.
- Si el stock del origen no alcanza, se revierte todo.
- Dos confirmaciones simultáneas dejan una sola `CONFIRMADA` y un solo movimiento.
- El rechazo exige motivo y no mueve stock ni custodia.

### Concurrencia

- Dos envíos simultáneos que compiten por la misma serie: solo uno reserva; el otro recibe
  `SerieReservada`.
- Dos traspasos que intentan vaciar el mismo stock: solo uno confirma; el otro recibe
  `StockTecnicoInsuficiente`.
- El orden de bloqueo `SolicitudTraspaso → Tenant → StockTecnico (material, técnico) → Serie` no
  produce interbloqueo.
- Confirmación y rechazo simultáneos de la misma solicitud: solo uno gana.

### Auditoría

- Crear produce un alta de solicitud y una por línea.
- Enviar produce `BORRADOR→ENVIADA` y un registro de Excel.
- Confirmar produce `ENVIADA→CONFIRMADA`, `Serie/tecnico` y `Serie/asignada_en` por serie.
- Los `StockTecnico/cantidad` aparecen una sola vez, escritos por 008.
- Rechazar produce estado y motivo, sin eventos de serie ni stock.
- No hay secretos, binarios, rutas absolutas ni datos de otro tenant.

### Excel e integridad

- El archivo tiene dos hojas y los metadatos Z32/Z31, Centro, Almacén, NIF, tenant, región e ID.
- El hash es estable y la descarga se bloquea si el archivo se altera.
- La ruta es relativa y no se expone en la respuesta.

### Aislamiento

- El tenant A no ve ni opera traspasos del tenant B.
- El almacén de otra región recibe `404`.
- Las series y el stock de otro tenant no se consultan ni se modifican.
- `LineaTraspaso.tenant` coincide siempre con `SolicitudTraspaso.tenant`.

### Rendimiento

- Un traspaso de 100 series se valida y confirma en menos de 2 segundos, sin una consulta por serie.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest -k "traspaso"` pasa completo sobre PostgreSQL.
- [ ] CA-01…CA-09 tienen al menos una prueba automatizada en verde.
- [ ] El stock general no cambia en ningún escenario.
- [ ] Las series cambian de técnico solo al confirmar y conservan `ASIGNADA`.
- [ ] `Serie.asignada_en` se reinicia al confirmar y 006 calcula los días desde ese campo.
- [ ] El Excel tiene dos hojas, cuadra y se descarga verificando el hash.
- [ ] Las reservas se derivan de `ENVIADA` y se liberan al rechazar o cancelar.
- [ ] La auditoría está completa y no duplica la de 008.
- [ ] Ningún tenant ve datos de otro.
- [ ] No se agregaron correo, Celery, permisos Django por cadena ni cambios a `StockGeneral`.
