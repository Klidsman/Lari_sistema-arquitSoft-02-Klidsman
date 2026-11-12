# Quickstart y validación: 003 Técnicos del tenant

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/003-tecnicos/spec.md`

Guía para levantar el proyecto y validar de extremo a extremo la gestión de técnicos: alta,
unicidad global del NIF, normalización, edición con NIF y tenant inmutables, desactivación,
reactivación, búsqueda por tenant, selectores para otros módulos y auditoría. Los detalles de
datos están en `data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Python 3.12 o superior.
- PostgreSQL 16 o superior.
- Redis 7 o superior (broker de Celery de la spec 001).
- Spec 001 implementada: `acceso.Usuario`, `tenants.Tenant`, `ContextoUsuarioMiddleware` y
  `auditoria.RegistroCambio` con `registrar_cambio`.
- Git y acceso al repositorio.
- En Windows, PowerShell 7 o superior; en Linux/macOS, bash.

## Configuración inicial

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Variables de entorno y base de datos: las mismas de
`05-especificaciones/001-tenants-y-acceso/quickstart.md`. No se agregan variables nuevas para esta
spec.

## Puesta en marcha

```powershell
python manage.py migrate
python manage.py runserver
```

Si la app `tecnicos` es nueva, `migrate` aplica `tecnicos/migrations/0001_initial.py`.

Datos mínimos para las pruebas manuales (crear desde la interfaz de la spec 001):

1. Una región con su almacén.
2. Un tenant activo y su cuenta activa (`USUARIO_TENANT`).
3. Un segundo tenant activo y su cuenta, para comprobar el aislamiento.
4. Un Administrador de plataforma con segundo factor.
5. Un Responsable de almacén con segundo factor.
6. Un técnico desactivado con historial en el primer tenant, para las pruebas de reactivación.

## Pruebas automatizadas

```powershell
# Toda la suite
pytest

# Solo este módulo
pytest tests/unit tests/integration tests/contract -k "tecnico"

# Con cobertura del módulo
pytest --cov=tecnicos
```

Las pruebas requieren PostgreSQL (no SQLite) porque validan `CheckConstraint` con expresión
regular, unicidad global, transiciones de estado y concurrencia real.

## Escenarios de validación manual

### 1. Alta de técnico

1. Iniciar sesión con la cuenta del tenant.
2. Ir a `/tecnicos/nuevo/`.
3. Registrar NIF `LA1234` y nombre `Juan Pérez`.
4. **Esperado**: el técnico aparece en `/tecnicos/` como Activo, asociado al tenant de la sesión;
   la auditoría administrativa muestra el alta con NIF, nombre y estado.

### 2. Formato y normalización del NIF

1. Intentar guardar con `LA123`, `LA12345`, `A1234`, `LA12A4`, `LA 1234` y `LA-1234`.
2. **Esperado**: `"El NIF debe tener el formato LAXXXX"` en todos los casos.
3. Intentar guardar con `la1234` y con `" LA1234 "`.
4. **Esperado**: se normaliza a `LA1234` y el técnico se guarda correctamente.

### 3. NIF único y doble envío

1. Guardar de nuevo `LA1234` desde la misma cuenta.
2. **Esperado**: `"El NIF ya está registrado"`; no se crea otro técnico.
3. Desde la cuenta del segundo tenant, intentar registrar `LA1234`.
4. **Esperado**: el mismo mensaje uniforme, sin indicar a qué tenant pertenece.
5. Hacer doble clic en Guardar con un NIF nuevo.
6. **Esperado**: se crea un solo técnico y la segunda petición responde
   `"El NIF ya está registrado"`.

### 4. NIF de un técnico desactivado

1. Desactivar un técnico con NIF `LA5678`.
2. Intentar crear otro técnico con `LA5678` en el mismo tenant.
3. **Esperado**: `"El NIF ya está registrado; reactiva el técnico existente"`.
4. Intentar crear `LA5678` desde el otro tenant.
5. **Esperado**: `"El NIF ya está registrado"`; no se revela el tenant propietario ni se sugiere
   reactivar un técnico ajeno.

### 5. Validación del nombre

1. Intentar guardar con nombre vacío y con nombre formado solo por espacios.
2. **Esperado**: `"El nombre es obligatorio"`.
3. Intentar guardar con 101 caracteres.
4. **Esperado**: `"El nombre no puede superar los 100 caracteres"`.
5. Registrar un nombre con espacios repetidos, por ejemplo `"  Juan   Pérez  "`.
6. **Esperado**: se guarda como `"Juan Pérez"`.
7. Registrar dos técnicos distintos con el mismo nombre.
8. **Esperado**: se permite; el NIF es el identificador, no el nombre.

### 6. Edición e inmutabilidad

1. Abrir un técnico y cambiar su nombre.
2. **Esperado**: el cambio se guarda y la auditoría muestra el valor anterior y el nuevo.
3. Verificar que el NIF y el tenant se muestran como solo lectura.
4. Forzar un `POST` con `nif=LA9999`.
5. **Esperado**: `400` `"El NIF no se puede cambiar"`.
6. Forzar un `POST` con `tenant_id` o `tenant` de otro tenant.
7. **Esperado**: `400` `"El tenant del técnico no se puede cambiar"`.
8. Guardar el formulario sin cambiar el nombre.
9. **Esperado**: no se genera un registro de auditoría nuevo.

### 7. Desactivación y conservación

1. Desactivar un técnico activo desde `/tecnicos/<id>/desactivar/`.
2. **Esperado**: el estado pasa a Desactivado y la auditoría registra `ACTIVO` → `DESACTIVADO`.
3. Buscar el NIF y el nombre en `/tecnicos/buscar/`.
4. **Esperado**: el técnico no aparece en el selector de operaciones nuevas.
5. Abrir el detalle del técnico.
6. **Esperado**: sus datos y su historial siguen visibles.
7. Repetir la desactivación.
8. **Esperado**: no cambia el estado ni se duplica la auditoría.
9. Si el técnico tiene stock asignado en un módulo consumidor, verificar que el stock no se borra.
10. **Esperado**: el stock sigue visible para devolución o traspaso.

### 8. Reactivación

1. Abrir un técnico desactivado y elegir Reactivar.
2. **Esperado**: vuelve a Activo y la auditoría registra `DESACTIVADO` → `ACTIVO`.
3. Buscar el NIF en `/tecnicos/buscar/`.
4. **Esperado**: vuelve a aparecer en el selector de operaciones nuevas.
5. Repetir la reactivación.
6. **Esperado**: no cambia el estado ni se duplica la auditoría.

### 9. Búsqueda y listado por tenant

1. Con la cuenta del tenant A, buscar `LA1234` y `Juan`.
2. **Esperado**: aparecen los técnicos del tenant A que coinciden por NIF o nombre.
3. Iniciar sesión con la cuenta del tenant B y repetir la búsqueda.
4. **Esperado**: no aparecen los técnicos del tenant A; solo los del tenant B.
5. Dejar la búsqueda vacía en `/tecnicos/`.
6. **Esperado**: listado del tenant A, paginado a 50 filas, ordenado por nombre y NIF.
7. Probar el filtro Activos/Desactivados/Todos.
8. **Esperado**: cada filtro muestra solo el estado correspondiente; Todos incluye ambos.

### 10. Aislamiento y accesos forzados

1. Con la cuenta del tenant B, abrir por URL directa el detalle, la edición, la desactivación y la
   reactivación de un técnico del tenant A.
2. **Esperado**: `404` `"El técnico no existe"` en todas las rutas, sin revelar datos del tenant A.
3. Enviar `tenant_id` del tenant A en el alta o la edición.
4. **Esperado**: el servidor lo ignora o lo rechaza; el técnico se asocia siempre al tenant de la
   sesión.

### 11. Permisos de Administrador y Responsable de almacén

1. Iniciar sesión como Administrador de plataforma e intentar crear, editar, desactivar y
   reactivar un técnico por URL directa.
2. **Esperado**: `403` `"No tienes permiso para gestionar técnicos"` en todas las rutas.
3. Repetir con el Responsable de almacén.
4. **Esperado**: el mismo `403`; tampoco ve el listado completo de técnicos.

### 12. Tenant suspendido y cuenta inactiva

1. Suspender el tenant desde la administración de la spec 001.
2. Iniciar sesión o intentar operar con su cuenta.
3. **Esperado**: no puede gestionar técnicos; recibe `403` `"El tenant está suspendido"` o se le
   impide la sesión según el middleware de 001.
4. Reactivar el tenant.
5. **Esperado**: los técnicos y su auditoría se conservan y la cuenta vuelve a operar.

### 13. Formulario viejo con técnico desactivado

1. Abrir en un módulo consumidor (por ejemplo, una asignación o un traspaso) un formulario con un
   técnico activo.
2. En otra sesión, desactivar ese técnico.
3. Enviar el formulario viejo.
4. **Esperado**: el servidor del módulo consumidor rechaza la operación con
   `"El técnico está desactivado"` mediante `validar_tecnico_para_operacion`; no se guarda la
   operación.

### 14. Sin eliminación e idempotencia

1. Enviar `DELETE` a `/tecnicos/<id>/` y a `/tecnicos/<id>/editar/`.
2. **Esperado**: `405`; no existe ruta de borrado.
3. Enviar `GET` a `/tecnicos/<id>/desactivar/` y a `/tecnicos/<id>/reactivar/`.
4. **Esperado**: `405`; las acciones de estado solo aceptan `POST`.

### 15. Auditoría

1. Abrir la consulta de auditoría administrativa de la spec 001 (o consultar
   `auditoria.RegistroCambio`).
2. **Esperado**: hay registros `entidad="Tecnico"` con `alta`, `nombre` y `activo`.
3. Inspeccionar los registros.
4. **Esperado**: no contienen contraseñas, tokens ni secretos; el alta incluye NIF, nombre y
   `estado=ACTIVO`; no se duplica el `tenant_id`.
5. Repetir una desactivación y una reactivación.
6. **Esperado**: no se agregan registros nuevos por las repeticiones.

### 16. Concurrencia

1. En dos sesiones simultáneas, intentar crear el mismo NIF nuevo.
2. **Esperado**: una alta tiene éxito y la otra falla con `"El NIF ya está registrado"`; existe una
   sola fila en la base.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest` pasa completo sobre PostgreSQL.
- [ ] Cada criterio de aceptación de `spec.md` tiene al menos una prueba automatizada.
- [ ] Los escenarios manuales 1–16 se completan con los resultados esperados.
- [ ] El NIF es único global y no se reutiliza tras una desactivación.
- [ ] El NIF y el tenant no se pueden modificar por ninguna vía.
- [ ] Solo la cuenta del tenant gestiona técnicos; Administrador y Responsable reciben `403`.
- [ ] Los selectores de operaciones nuevas solo muestran técnicos activos del tenant.
- [ ] Un técnico desactivado conserva su historial y su stock; no se elimina.
- [ ] La reactivación vuelve a habilitarlo y queda auditada.
- [ ] La auditoría registra altas, nombres y estados, sin secretos y en la misma transacción.
- [ ] No existe ninguna ruta de borrado de técnicos.
