# Quickstart y validación: 005 Stock Inicial de Técnicos

**Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/005-stock-inicial-de-tecnicos/spec.md`

Esta guía describe cómo validar el stock inicial de técnicos de extremo a extremo. No contiene
código de implementación: los modelos, servicios y contratos viven en `plan.md`, `data-model.md` y
`contracts/`.

## 1. Prerrequisitos

- **001 implementada**: proyecto Django, PostgreSQL, `acceso.Usuario`, `tenants.Region`,
  `tenants.Tenant`, `ContextoUsuarioMiddleware`, `auditoria.RegistroCambio` y
  `auditoria.services.registrar_cambio`.
- **002 implementada**: `materiales.Material` con catálogo global.
- **003 implementada**: `tecnicos.Tecnico` y sus servicios.
- **004 implementada**: app `series`, `series.Serie` y `series.services`.
- **008 (parte fundacional) implementada**: `stock.StockTecnico`,
  `stock.services.incrementar_stock_tecnico` y `stock.services.decrementar_stock_tecnico`.
  `stock.StockGeneral` puede existir, pero no se usa en 005.
- **005 implementada**: app `stock_inicial`, rutas, plantillas, migraciones y comando de reinicio.
- Entorno con PostgreSQL 16+; no se admite SQLite.
- Variables de entorno de la aplicación configuradas (base de datos, correo, etc.).
- `PERMITIR_REINICIO_STOCK_INICIAL=False` salvo en el escenario de reinicio controlado.

## 2. Puesta en marcha

```powershell
# Crear y activar el entorno virtual (si no existe)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Cargar datos mínimos de prueba (región, tenant, cuenta, técnicos y materiales)
# Usar los comandos o fixtures de las specs 001, 002 y 003.
```

No se crea un superusuario de Django. La primera cuenta se crea con
`python manage.py crear_admin_plataforma` (001), y la cuenta del tenant se crea por invitación.

### Datos de prueba sugeridos

| Dato | Ejemplo |
|---|---|
| Región | `REG-01`, con almacén central configurado |
| Tenant | `TEN-01`, estado `ACTIVO` |
| Cuenta | `tenant01@example.com`, rol `USUARIO_TENANT`, tenant `TEN-01` |
| Técnicos | `LA0001` (activo), `LA0002` (activo), `LA0003` (desactivado) |
| Material seriado | `12345678901`, lote `LOTE-A`, `es_seriado=True` |
| Material no seriado | `12345678902`, lote `LOTE-B`, `es_seriado=False` |
| Serie válida | `ABC123456789` |
| Serie existente | `XYZ987654321` (creada en otro tenant) |

## 3. Comandos de verificación

```powershell
# Migraciones y estado
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan

# Pruebas de la feature
pytest tests/unit/test_stock_inicial_validaciones.py tests/unit/test_stock_inicial_excel.py tests/unit/test_stock_inicial_servicios.py
pytest tests/integration/test_stock_inicial_carga.py tests/integration/test_stock_inicial_stock.py
pytest tests/integration/test_stock_inicial_edicion.py tests/integration/test_stock_inicial_auditoria.py
pytest tests/integration/test_stock_inicial_concurrencia.py tests/integration/test_stock_inicial_reinicio.py
pytest tests/integration/test_stock_inicial_aislamiento.py
pytest tests/contract/test_stock_inicial_estado_http.py tests/contract/test_stock_inicial_carga_http.py
pytest tests/contract/test_stock_inicial_validacion_http.py tests/contract/test_stock_inicial_edicion_http.py
pytest tests/contract/test_stock_inicial_permisos_http.py

# Cobertura de la feature
pytest --cov=stock_inicial --cov-report=term-missing

# Comando de reinicio: ayuda y guardas
python manage.py reiniciar_stock_inicial --help
```

## 4. Escenarios manuales

Los escenarios usan la cuenta del tenant `TEN-01` salvo que se indique lo contrario. En todos, el
tenant y la región salen de la sesión.

### Escenario 1 — Carga por Excel exitosa (CA-01)

1. Entrar como `USUARIO_TENANT` y abrir `/stock-inicial/`.
2. Descargar o preparar un `.xlsx` con:
   - una serie `ABC123456789` del material seriado para `LA0001`;
   - 10 unidades del material no seriado para `LA0001`;
   - 5 unidades del material no seriado para `LA0002`.
3. Subir el archivo en “Validar Excel”.
4. Verificar que el fragmento muestra `data-valido="true"` y el resumen.
5. Enviar el archivo a “Cargar stock inicial”.
6. Verificar la redirección al detalle.

**Resultado esperado**:

- Existe una `CargaStockInicial` con `metodo=EXCEL`, nombre y hash.
- El detalle muestra 2 técnicos, 3 líneas, 1 serie y 15 de cantidad.
- El tenant queda con `stock_inicial_cargado=True` y `fecha_stock_inicial`.
- La serie `ABC123456789` está `ASIGNADA`.
- `StockTecnico` de `LA0001` tiene 1 del seriado y 10 del no seriado; el de `LA0002`, 5 del no
  seriado.
- `StockGeneral` no cambió.

### Escenario 2 — Carga por formulario exitosa (CA-02)

1. Abrir `/stock-inicial/formulario/`.
2. En la sección de `LA0001`, elegir el material seriado y pegar `DEF123456789`.
3. Agregar otra línea con el material no seriado y cantidad 7.
4. En la sección de `LA0002`, agregar 3 unidades del material no seriado.
5. Guardar.

**Resultado esperado**:

- Una sola carga con `metodo=FORMULARIO`, sin nombre ni hash.
- Las series `DEF123456789` en `ASIGNADA`.
- El stock del técnico coincide con lo ingresado; el general no cambia.
- El tenant queda marcado como cargado.

### Escenario 3 — Técnico inexistente (CA-03)

1. Preparar un Excel con `Nº ident.fis.1=LA9999`.
2. Validar y cargar.

**Resultado esperado**: error "El técnico no existe en este tenant"; no se crea ninguna carga,
línea, serie ni stock.

### Escenario 4 — Material inexistente (CA-04)

1. Preparar un Excel con `Material=99999999999`.
2. Validar y cargar.

**Resultado esperado**: error "El material no existe en el catálogo"; no se crea nada.

### Escenario 5 — Serie duplicada en el Excel (CA-05)

1. Preparar un Excel con la misma serie `ABC123456789` dos veces.
2. Validar y cargar.

**Resultado esperado**: error "La serie está duplicada en la carga" en la segunda ocurrencia; no se
crea nada.

### Escenario 6 — Serie ya existente (CA-06)

1. Crear una serie `XYZ987654321` en otro tenant (o usar una existente).
2. Preparar un Excel con esa serie para `TEN-01`.
3. Validar y cargar.

**Resultado esperado**: error "La serie ya está registrada en el sistema"; el mensaje no revela el
tenant, la región ni el técnico de origen; no se crea nada.

### Escenario 7 — Carga única (CA-07)

1. Completar el escenario 1.
2. Intentar cargar otro Excel o formulario.

**Resultado esperado**: `409` con "El stock inicial ya fue cargado para este tenant"; no se crea una
segunda carga ni se modifica el stock.

### Escenario 8 — Asignación directa al técnico (CA-08)

1. Completar el escenario 1.
2. Consultar el stock del técnico `LA0001`.
3. Consultar el stock general del tenant.

**Resultado esperado**: el stock del técnico refleja lo cargado; el stock general no cambió; no hay
movimiento de stock general por la carga inicial.

### Escenario 9 — Auditoría de carga (CA-09)

1. Completar el escenario 1.
2. Consultar `auditoria.RegistroCambio` para la carga.

**Resultado esperado**:

- un `CargaStockInicial/alta` con usuario, fecha, método, nombre de archivo, hash y totales;
- un `LineaStockInicial/alta` por línea;
- un `Serie/alta` por serie;
- registros de `Tenant/stock_inicial_cargado` y `Tenant/fecha_stock_inicial`;
- registros de `StockTecnico/cantidad` por material;
- ningún secreto ni `tenant_id` separado.

### Escenario 10 — Transaccionalidad (CA-10)

1. Preparar un Excel con 100 filas válidas y 1 fila con un técnico inexistente.
2. Validar y cargar.

**Resultado esperado**: no se crea ninguna carga, línea, serie, stock ni auditoría; el detalle no
existe; el tenant sigue sin cargar.

### Escenario 11 — Editar: agregar serie (CA-11)

1. Completar el escenario 1.
2. Abrir la edición.
3. Agregar una serie nueva `GHI123456789` para `LA0001` con el material seriado.
4. Guardar.

**Resultado esperado**: la serie se crea `ASIGNADA`, la línea se agrega, el stock del técnico sube 1,
el stock general no cambia y se audita `Serie/alta`, `LineaStockInicial/alta` y
`StockTecnico/cantidad`.

### Escenario 12 — Editar: eliminar serie (CA-12)

1. Completar el escenario 1.
2. Abrir la edición.
3. Marcar la serie `ABC123456789` para eliminar.
4. Guardar.

**Resultado esperado**: la línea y la serie se eliminan, el stock del técnico baja 1, el stock
general no cambia y se auditan `LineaStockInicial/baja`, `Serie/baja` y `StockTecnico/cantidad`. La
auditoría conserva el número de serie eliminado.

### Escenario 13 — Editar: modificar cantidad (CA-13)

1. Completar el escenario 1.
2. Abrir la edición.
3. Cambiar la cantidad del material no seriado de `LA0001` de 10 a 12.
4. Guardar.

**Resultado esperado**: la cantidad de la línea cambia a 12, el stock del técnico sube 2, el stock
general no cambia y se audita `LineaStockInicial/cantidad` con 10 y 12.

### Escenario 14 — Edición transaccional

1. Abrir la edición.
2. Agregar una serie válida y, en la misma operación, intentar eliminar una serie que ya no está
   `ASIGNADA` o dejar una cantidad en 0.
3. Guardar.

**Resultado esperado**: `400`; no se aplica ninguna de las dos operaciones; no hay cambios de stock,
series, líneas ni auditoría.

### Escenario 15 — Permisos y aislamiento

1. Entrar como `ADMIN_PLATAFORMA` y abrir `/stock-inicial/`; repetir con
   `RESPONSABLE_ALMACEN`.
2. Suspender el tenant y entrar como su cuenta.
3. Con la cuenta de otro tenant, abrir `/stock-inicial/<id>/` de `TEN-01`.
4. Enviar `tenant_id` y `region_id` en el formulario y en la URL.

**Resultado esperado**:

- Admin y Almacén: `403` con el mensaje correspondiente.
- Tenant suspendido: `403` con "El tenant está suspendido".
- Otro tenant: `404` con "El stock inicial no existe".
- `tenant_id`/`region_id` forzados se ignoran; la carga usa el tenant de la sesión.

### Escenario 16 — Archivo `.xls`

1. Intentar validar un archivo `.xls`.

**Resultado esperado**: `400` con "El archivo debe ser un Excel .xlsx"; no se escribe nada. El
usuario debe guardar el archivo como `.xlsx` y reintentar.

### Escenario 17 — Vista previa sin escrituras

1. Ejecutar `validar-excel` con un archivo válido y con uno inválido.
2. Contar filas de `CargaStockInicial`, `LineaStockInicial`, `Serie`, `StockTecnico` y
   `RegistroCambio` antes y después.

**Resultado esperado**: los conteos no cambian; el fragmento muestra `data-valido` y los errores por
fila.

### Escenario 18 — Reinicio controlado

1. En un entorno de desarrollo/pruebas, definir `PERMITIR_REINICIO_STOCK_INICIAL=True`.
2. Ejecutar:

```powershell
python manage.py reiniciar_stock_inicial --tenant TEN-01 --usuario admin@example.com --confirmar
```

3. Repetir sin `--confirmar` y con la configuración apagada.

**Resultado esperado**:

- Con la configuración activa, actor Admin y `--confirmar`: se borran carga, líneas y series; se
  descuenta el stock del técnico; el tenant vuelve a `stock_inicial_cargado=False`; se audita todo.
- Sin `--confirmar`: no se ejecuta y se muestra la advertencia.
- Con la configuración apagada: error "El reinicio del stock inicial está deshabilitado".
- Con un actor que no es Admin: error "No tienes permiso para reiniciar el stock inicial".
- Si el stock o las series ya cambiaron: error "El stock inicial ya fue modificado; no se puede
  reiniciar" y no se borra nada.

### Escenario 19 — Concurrencia

1. Abrir dos sesiones del mismo tenant.
2. En ambas, validar dos Excel válidos distintos.
3. Enviar la carga casi al mismo tiempo.

**Resultado esperado**: una sola carga, un solo conjunto de líneas y un solo stock; la perdedora
recibe "El stock inicial ya fue cargado para este tenant" (`409`). No quedan filas parciales.

### Escenario 20 — Rendimiento

1. Generar un Excel de 100 filas con técnicos y materiales repetidos.
2. Medir la validación y la carga con `django_assert_num_queries` o el depurador de consultas.

**Resultado esperado**: la validación no hace una consulta por fila para técnicos, materiales ni
series; el detalle no tiene N+1; la vista previa no escribe.

## 5. Criterios de salida

La feature se considera validada cuando:

- [ ] `python manage.py makemigrations --check --dry-run` no detecta cambios pendientes.
- [ ] `python manage.py migrate` aplica las migraciones de `tenants` y `stock_inicial` sin errores.
- [ ] Todas las pruebas de `tests/` pasan sobre PostgreSQL.
- [ ] Hay al menos una prueba por CA-01…CA-13 y todas están en verde.
- [ ] La cobertura de `stock_inicial` es la acordada por el equipo y no hay líneas críticas sin
      cubrir.
- [ ] Los escenarios 1–20 se ejecutan y coinciden con el resultado esperado.
- [ ] `StockGeneral` no cambia en ninguna carga o edición.
- [ ] No se crea otra tabla de series ni una columna `serie` de texto.
- [ ] El mensaje de serie existente es uniforme y no revela el tenant.
- [ ] La carga, la edición y el reinicio son todo o nada.
- [ ] La auditoría se conserva y no contiene secretos.
- [ ] `ADMIN_PLATAFORMA` y `RESPONSABLE_ALMACEN` reciben `403`; otro tenant recibe `404`.
- [ ] `tenant_id`/`region_id` forzados se ignoran.
- [ ] El comando de reinicio está deshabilitado por defecto y no tiene ruta HTTP.
- [ ] No se crea ni se requiere superusuario de Django.

## 6. Solución de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| "El archivo debe ser un Excel .xlsx" | Archivo `.xls` o `.csv` | Guardar como `.xlsx` y reintentar. |
| "El archivo no tiene la columna obligatoria: …" | Cabecera distinta o faltante | Usar los nombres exactos del contrato. |
| "El técnico no existe en este tenant" | NIF mal escrito o de otro tenant | Verificar el NIF y el tenant de la sesión. |
| "El material no existe en el catálogo" | Código inexistente o con espacios | Verificar el catálogo global. |
| "La serie ya está registrada en el sistema" | Serie existente en cualquier tenant | Usar otra serie; el mensaje no revela el propietario. |
| "El stock inicial ya fue cargado para este tenant" | Carga previa | Usar la edición, no una nueva carga. |
| "El stock inicial aún no ha sido cargado" | Edición antes de la carga | Completar la carga primero. |
| "La serie ya no pertenece al stock inicial del técnico" | La serie fue devuelta o traspasada | No se puede eliminar desde el stock inicial; usar el flujo correspondiente. |
| "El técnico no tiene suficiente stock" | El stock ya cambió | Revisar el stock actual; no se permite dejar saldos negativos. |
| El reinicio no se ejecuta | Configuración apagada o falta `--confirmar` | Activar solo en desarrollo/pruebas y confirmar. |
