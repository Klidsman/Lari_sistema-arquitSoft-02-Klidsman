# Quickstart y validación: 006 Solicitud de Asignación

**Fecha**: 2026-11-12 | **Spec**:
`05-especificaciones/006-solicitud-de-asignacion/spec.md`

Esta guía describe cómo validar la solicitud de asignación de extremo a extremo. No contiene código
de implementación: los modelos, servicios y contratos viven en `plan.md`, `data-model.md` y
`contracts/`.

## 1. Prerrequisitos

- **001 implementada**: proyecto Django, PostgreSQL, `acceso.Usuario`, `tenants.Region`,
  `tenants.Almacen` con `centro`/`codigo_almacen`/`buzon`, `tenants.Tenant`,
  `ContextoUsuarioMiddleware`, `auditoria.RegistroCambio` y
  `auditoria.services.registrar_cambio`.
- **002 implementada**: `materiales.Material` con catálogo global y `/materiales/buscar/`.
- **003 implementada**: `tecnicos.Tecnico` y `tecnicos.services.tecnicos_para_operacion`.
- **004 implementada**: app `series`, `series.Serie` y `EstadoSerie`.
- **008 (parte fundacional) implementada**: `stock.StockGeneral` y
  `stock.services.obtener_stock_general`/`calcular_disponible`. No se requiere la confirmación de
  asignaciones de 007/008 para validar 006.
- **006 implementada**: app `asignaciones`, rutas, plantillas, migraciones y `openpyxl` instalado.
- **007 no es prerrequisito**: para CA-08 y CA-09 se usa un fixture que fija `Serie.asignada_en` y deja
  las series `ASIGNADA`.
- PostgreSQL 16+; no se admite SQLite, ni en pruebas.
- Variables de entorno configuradas (base de datos, `MEDIA_ROOT`, correo de 001).
- `MOVIMIENTO_ASIGNACION="Z31"`, `DIAS_ALERTA_CUSTODIA=20` y
  `ASIGNACIONES_EXCEL_DIR="asignaciones"`.

## 2. Puesta en marcha

```powershell
# Crear y activar el entorno virtual (si no existe)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Verificar que no faltan migraciones
python manage.py makemigrations --check --dry-run
```

No se crea un superusuario de Django. La primera cuenta se crea con
`python manage.py crear_admin_plataforma` (001); la cuenta del tenant se crea por invitación.

### Datos de prueba sugeridos

| Dato | Ejemplo |
|---|---|
| Región | `REG-01`, almacén con `centro="PR05"` y `codigo_almacen="BE03"` |
| Tenant | `TEN-01`, estado `ACTIVO` |
| Cuenta | `tenant01@example.com`, rol `USUARIO_TENANT`, tenant `TEN-01`, 2FA no requerido |
| Cuenta almacén | `almacen@example.com`, rol `RESPONSABLE_ALMACEN` |
| Técnico activo | `LA0001`, nombre "Técnico Uno" |
| Técnico inactivo | `LA0002` |
| Material seriado | `12345678901`, lote `LOTE-A`, `es_seriado=True`, stock general 10 |
| Material no seriado | `12345678902`, lote `LOTE-B`, `es_seriado=False`, stock general 50 |
| Serie disponible | `ABC123456789` del material seriado, `DISPONIBLE` |
| Serie asignada | `XYZ987654321` del material seriado, `ASIGNADA` |
| Serie reservada | `LMN123456789` del material seriado, `RESERVADA` |
| Solicitud enviada | 20 unidades del material no seriado, estado `ENVIADA` |

Los datos se crean con los comandos o fixtures de 001, 002, 003, 004 y 008. No se escriben series
por SQL directo.

## 3. Comandos de verificación

```powershell
# Pruebas unitarias
pytest tests/unit/test_asignacion_validaciones.py tests/unit/test_asignacion_disponibilidad.py
pytest tests/unit/test_asignacion_excel.py tests/unit/test_asignacion_servicios.py

# Pruebas de integración
pytest tests/integration/test_asignacion_creacion.py tests/integration/test_asignacion_reserva.py
pytest tests/integration/test_asignacion_excel.py tests/integration/test_asignacion_custodia.py
pytest tests/integration/test_asignacion_concurrencia.py
pytest tests/integration/test_asignacion_auditoria.py tests/integration/test_asignacion_aislamiento.py

# Pruebas de contrato HTTP
pytest tests/contract/test_asignacion_lista_http.py tests/contract/test_asignacion_creacion_http.py
pytest tests/contract/test_asignacion_series_http.py
pytest tests/contract/test_asignacion_validacion_http.py
pytest tests/contract/test_asignacion_permisos_http.py

# Cobertura de la feature
pytest --cov=asignaciones --cov-report=term-missing
```

Todas las pruebas usan PostgreSQL. Si la suite intenta SQLite, se detiene: es un error de
configuración, no una prueba válida.

## 4. Escenarios manuales

Los escenarios usan la cuenta del tenant `TEN-01` salvo que se indique lo contrario. En todos, el
tenant y la región salen de la sesión.

### Escenario 1 — Crear y enviar una solicitud válida (CA-01, CA-05, CA-06)

1. Entrar como `USUARIO_TENANT` y abrir `/asignaciones/nueva/`.
2. Elegir el técnico `LA0001`; verificar que el NIF se muestra de solo lectura.
3. Agregar una línea del material seriado y seleccionar la serie `ABC123456789`.
4. Agregar una línea del material no seriado con cantidad 10.
5. Pulsar "Enviar".
6. Verificar la redirección al detalle.

**Resultado esperado**:

- La solicitud queda `ENVIADA`.
- La serie `ABC123456789` queda `RESERVADA`.
- El detalle muestra el hash SHA-256 de 64 caracteres y la ruta del Excel.
- El Excel contiene `Movimiento=Z31`, `Centro=PR05`, `Almacén=BE03` y el NIF del técnico.
- `StockGeneral` y `StockTecnico` no cambiaron.

### Escenario 2 — Guardar borrador y cancelar (borrador sin reserva)

1. Abrir `/asignaciones/nueva/` y elegir técnico `LA0001`.
2. Agregar una serie y una cantidad.
3. Pulsar "Guardar borrador".
4. Verificar que el detalle muestra `BORRADOR`, sin Excel y con "Enviar"/"Cancelar".
5. Verificar que la serie sigue `DISPONIBLE`.
6. Pulsar "Cancelar".

**Resultado esperado**:

- La solicitud queda `CANCELADA`.
- No se generó Excel.
- La serie sigue `DISPONIBLE`.
- No se reservó cantidad.

### Escenario 3 — Disponibilidad descontando reservado (CA-03, CA-04)

1. Con el material no seriado en stock 50 y una solicitud `ENVIADA` de 20 unidades.
2. Abrir `/asignaciones/nueva/` y escribir cantidad 30 para ese material.
3. Pulsar la validación en tiempo real.

**Resultado esperado**:

- El fragmento muestra `data-disponible="30"` y `data-valido="true"`.
- Cambiar la cantidad a 31 muestra `data-valido="false"` y
  "La cantidad supera el stock disponible".
- Enviar 31 unidades responde `400` con el mismo mensaje.
- El borrador o solicitud rechazada no suma al reservado.

### Escenario 4 — Selector de series (CA-02, CA-10, CA-11)

1. En el formulario, elegir el material seriado.
2. Abrir el selector de series y buscar por número o por material.

**Resultado esperado**:

- Solo aparece `ABC123456789` (`DISPONIBLE`).
- `XYZ987654321` (`ASIGNADA`) no aparece.
- `LMN123456789` (`RESERVADA`) no aparece.
- La búsqueda por código o descripción del material devuelve el mismo resultado.
- La respuesta es HTML; no hay JSON.

### Escenario 5 — NIF no editable (CA-07)

1. En el formulario, seleccionar el técnico `LA0001`.
2. Intentar modificar el NIF desde el inspector o forzar `nif=LA9999` en el `POST`.

**Resultado esperado**:

- El campo visible es de solo lectura.
- El valor forzado se ignora.
- El Excel y la solicitud usan `LA0001`.

### Escenario 6 — Días en mano al confirmar (CA-08)

1. Usar un fixture o el flujo de 007 para dejar una solicitud `CONFIRMADA` con
   `Serie.asignada_en` hace 10 días y su serie `ASIGNADA` al técnico.
2. Abrir el detalle de la solicitud.

**Resultado esperado**:

- La serie muestra 10 días en mano.
- Una solicitud `ENVIADA` o `BORRADOR` no muestra días en mano.
- Una serie devuelta o traspasada no se cuenta como custodia (según 009/011).

### Escenario 7 — Alerta de cupo máximo (CA-09)

1. Con un técnico que tiene una serie `ASIGNADA` confirmada hace 25 días.
2. Abrir `/asignaciones/nueva/` para ese técnico.

**Resultado esperado**:

- Se muestra "El técnico supera los 20 días en mano".
- La alerta es visible pero no intrusiva.
- El botón "Enviar" sigue habilitado y la solicitud puede crearse.
- Con 19 o 20 días no se alerta; con 21 o más, sí.

### Escenario 8 — Permisos y aislamiento

1. Entrar como `ADMIN_PLATAFORMA`: abrir `/asignaciones/`.
2. Entrar como `RESPONSABLE_ALMACEN`: abrir `/asignaciones/`.
3. Entrar como cuenta del tenant `TEN-02`: abrir el detalle de una solicitud de `TEN-01`.
4. Suspender `TEN-01` y reintentar como su cuenta.

**Resultado esperado**:

- Admin y Almacén reciben `403` "No tienes permiso para crear asignaciones".
- La cuenta de `TEN-02` recibe `404` "La solicitud no existe".
- El tenant suspendido recibe `403` "El tenant está suspendido".
- Ninguna respuesta revela datos del otro tenant.

### Escenario 9 — Concurrencia

1. Preparar dos solicitudes en borrador del mismo tenant con 30 unidades cada una y stock
   disponible 50.
2. Enviarlas simultáneamente desde dos procesos o con dos clientes.

**Resultado esperado**:

- Solo una queda `ENVIADA`; la otra recibe `400` "La cantidad supera el stock disponible".
- El total reservado nunca supera 50.
- Si dos solicitudes seleccionan la misma serie, solo una la reserva; la otra recibe
  "La serie no está disponible".

### Escenario 10 — Auditoría

1. Crear, enviar y cancelar solicitudes según los escenarios anteriores.
2. Consultar `auditoria.RegistroCambio` para las entidades afectadas.

**Resultado esperado**:

- Alta de solicitud y de cada línea.
- Envío con totales y hash.
- Una reserva `Serie/estado` por serie.
- Cancelación.
- Ningún registro con contraseña, token, secreto TOTP ni contenido del Excel.

## 5. Criterios de salida

La feature se considera validada cuando:

- [ ] `pytest` de 006 pasa completo sobre PostgreSQL.
- [ ] Cada CA-01…CA-11 tiene al menos una prueba en verde.
- [ ] `makemigrations --check --dry-run` no detecta cambios pendientes.
- [ ] Crear y enviar deja la solicitud `ENVIADA`, las series `RESERVADA` y el Excel con hash.
- [ ] Guardar borrador no reserva ni genera Excel; cancelar no libera series.
- [ ] `StockGeneral` y `StockTecnico` no cambian en 006.
- [ ] El Excel contiene Z31, centro y almacén de la región, y el NIF del técnico.
- [ ] El disponible descuenta lo reservado y el envío revalida con bloqueo.
- [ ] Una serie `ASIGNADA` o `RESERVADA` no aparece en el selector.
- [ ] Los días en mano se calculan desde `Serie.asignada_en`; `confirmada_en` solo respalda datos históricos y la alerta evalúa cada equipo.
- [ ] Admin, Almacén, tenant suspendido y otro tenant reciben `403`/`404` según corresponde.
- [ ] La auditoría se escribe en la misma transacción y no contiene secretos.
- [ ] Las correcciones documentales de `plan.md` están aplicadas antes de implementar.

## 6. Problemas frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| La validación dice disponible 0 | No existe `StockGeneral` para el material | Verificar 008 y el tenant |
| Una serie no aparece | Está `RESERVADA`/`ASIGNADA` o es de otro tenant | Revisar `Serie.estado` y `tenant` |
| El envío responde `409` | La solicitud no está `BORRADOR` | Releer el estado; no reenviar |
| El NIF no cambia | Es de solo lectura y se copia del técnico | Corregir el técnico en 003 |
| La alerta no aparece | Ningún equipo supera 20 días | Revisar `Serie.asignada_en`, el respaldo `confirmada_en` y `DIAS_ALERTA_CUSTODIA` |
| El Excel falta | El envío falló y se revirtió | Revisar logs; no hay solicitud `ENVIADA` |
| Un test intenta SQLite | Configuración de pruebas incorrecta | Ajustar `config/settings/test.py` a PostgreSQL |
| Una solicitud de otro tenant da `200` | Filtro de tenant ausente | Corregir el servicio y la vista; es un fallo de aislamiento |
