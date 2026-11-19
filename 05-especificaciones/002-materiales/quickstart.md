# Quickstart y validación: 002 Módulo de materiales

**Fase**: 1 | **Fecha**: 2026-11-12 | **Spec**: `05-especificaciones/002-materiales/spec.md`

Guía para levantar el proyecto y validar de extremo a extremo el catálogo compartido de
materiales: alta, unicidad, normalización, edición con permisos, inmutabilidad del código y del
tipo, búsqueda y auditoría. Los detalles de datos están en `data-model.md` y los contratos en
`contracts/`.

## Prerrequisitos

- Python 3.12 o superior.
- PostgreSQL 16 o superior.
- Redis 7 o superior (broker de Celery de la spec 001).
- Spec 001 implementada: `acceso.Usuario`, `ContextoUsuarioMiddleware` y
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
`05-especificaciones/001-tenants-y-acceso/quickstart.md`. No se agregan variables nuevas para
esta spec.

## Puesta en marcha

```powershell
python manage.py migrate
python manage.py runserver
```

Si la app `materiales` es nueva, `migrate` aplica `materiales/migrations/0001_initial.py`.

Datos mínimos para las pruebas manuales (crear desde la interfaz de la spec 001):

1. Una región con su almacén.
2. Un tenant y su cuenta activa.
3. Una segunda cuenta de otro tenant para comprobar el catálogo compartido.
4. Un Administrador de plataforma con segundo factor.
5. Al menos una cuenta de **Responsable de almacén** activa, que es la única que crea
   materiales y la que puede darlos de baja.

## Pruebas automatizadas

```powershell
# Toda la suite
pytest

# Solo este módulo
pytest tests/unit tests/integration tests/contract -k "material"

# Con cobertura del módulo
pytest --cov=materiales
```

Las pruebas requieren PostgreSQL (no SQLite) porque validan `CheckConstraint` con expresión
regular, unicidad global y concurrencia real.

## Escenarios de validación manual

### 1. Alta de material

1. Iniciar sesión con la cuenta del Responsable de almacén.
2. Ir a `/materiales/nuevo/`.
3. Registrar código `10402520279`, descripción `ROSETA`, lote `FIBERHOME` y tipo `Seriado`.
4. **Esperado**: el material aparece en `/materiales/` con creador y fecha; la auditoría
   administrativa muestra el alta con código, descripción, lote y tipo.

### 2. Código de 11 dígitos obligatorio

1. Intentar guardar con `1040252027` (10 dígitos), con `104025202799` (12) y con
   `10402520A79` (letra).
2. **Esperado**: `"El código debe tener 11 dígitos"` en los tres casos.
3. Intentar con `1040 2520279` y con `1040-2520279`.
4. **Esperado**: el mismo mensaje; no se aceptan espacios ni guiones internos.

### 3. Código único y doble clic

1. Guardar de nuevo el código `10402520279` desde la misma cuenta.
2. **Esperado**: `"El material ya existe"`, sin indicar qué cuenta o tenant lo creó.
3. Con otro Responsable de almacén (otra región), intentar registrar el mismo código.
4. **Esperado**: el mismo mensaje uniforme; el catálogo es global.
5. Con una cuenta de tenant o un Administrador de plataforma, intentar abrir
   `/materiales/nuevo/`.
6. **Esperado**: `403`; solo el Responsable de almacén crea materiales.
7. Hacer doble clic en Guardar con un código nuevo desde la cuenta de almacén.
8. **Esperado**: se crea un solo material y la segunda petición responde
   `"El material ya existe"`.
9. Dar de baja un material y volver a registrarlo con el mismo código.
10. **Esperado**: no se crea otra fila; el material se reactiva con los nuevos datos y la
    reactivación queda auditada.

### 4. Normalización de descripción y lote

1. Registrar un material con descripción `"  ROSETA   ÓPTICA  "` y lote `" fiberhome "`.
2. **Esperado**: se guarda `"ROSETA ÓPTICA"` y `"FIBERHOME"`.
3. Intentar guardar una descripción formada solo por espacios.
4. **Esperado**: `"La descripción es obligatoria"`.
5. Registrar un material sin lote.
6. **Esperado**: el lote queda vacío y el material aparece igualmente en la búsqueda.

### 5. Catálogo compartido

1. Con la cuenta del tenant A, buscar `10402520323`.
2. **Esperado**: aparece con su descripción y lote.
3. Iniciar sesión con la cuenta del tenant B y repetir la búsqueda.
4. **Esperado**: el mismo material, con los mismos datos; el catálogo no se filtra por tenant.

### 6. Búsqueda

1. Buscar `ROSETA` en `/materiales/` y en `/materiales/buscar/?q=ROSETA`.
2. **Esperado**: aparece `10402520279` con descripción y lote.
3. Buscar `1040252` (código parcial).
4. **Esperado**: aparecen los materiales cuyo código contiene ese texto.
5. Dejar la búsqueda vacía.
6. **Esperado**: listado completo, sin filtrar, paginado a 50 filas.

### 7. Edición y permisos

1. Como Responsable de almacén (aunque el material lo haya creado otra cuenta), abrir
   `/materiales/<id>/editar/` y cambiar la descripción.
2. **Esperado**: se guarda y la auditoría muestra el valor anterior y el nuevo.
3. Iniciar sesión con una cuenta de tenant e intentar editar el mismo material por URL directa.
4. **Esperado**: `403` `"No tienes permiso para editar este material"`.
5. Iniciar sesión como Administrador de plataforma y editar la descripción.
6. **Esperado**: se permite y se audita.
7. Verificar que el campo código no está disponible en el formulario y que una petición forzada
   con `codigo` responde `"El código no se puede cambiar"`.

### 8. Tipo inmutable con movimientos

1. Con un material sin stock ni movimientos, cambiar de Seriado a No seriado.
2. **Esperado**: se permite y se audita el campo `tipo` con el valor anterior y el nuevo.
3. Simular stock o movimientos (registrando una verificación de movimientos en la prueba de
   integración o con datos de la spec 004 cuando exista).
4. Intentar cambiar el tipo.
5. **Esperado**: `"El tipo no se puede cambiar: el material tiene movimientos"`.

### 9. Baja lógica, sin eliminación y conservación

1. Como Responsable de almacén, abrir `/materiales/` y pulsar **Dar de baja**.
2. **Esperado**: el material desaparece del listado y de la búsqueda; la fila se conserva con
   `activo=False` y la auditoría registra el cambio `True` → `False`.
3. Repetir la baja del mismo material.
4. **Esperado**: `200`, sin cambios ni auditoría nueva.
5. Enviar `DELETE` a `/materiales/<id>/editar/` y a `/materiales/<id>/baja/`.
6. **Esperado**: `405`; no existe borrado físico.
7. Desactivar la cuenta del creador desde la spec 001.
8. **Esperado**: el material y su auditoría se conservan.

### 10. Auditoría

1. Abrir la consulta de auditoría administrativa de la spec 001 (o consultar
   `auditoria.RegistroCambio`).
2. **Esperado**: hay registros `entidad="Material"` con `alta` y con un registro por cada campo
   modificado.
3. Inspeccionar los registros.
4. **Esperado**: no contienen contraseñas, tokens ni secretos; el alta incluye código,
   descripción, lote y tipo; no incluye `tenant_id`.

### 11. Concurrencia

1. En dos sesiones simultáneas, intentar crear el mismo código nuevo.
2. **Esperado**: una alta tiene éxito y la otra falla con `"El material ya existe"`; existe una
   sola fila en la base.

## Registro de validación manual

**Fecha**: 2026-11-14
**Entorno**: Windows, PostgreSQL 16 (contenedor `lari-postgres` en el puerto 5434), Redis 7,
Django 5.2 y Python 3.12.
**Guía seguida**: `05-especificaciones/002-materiales/guia-validacion-manual.md`.

| # | Escenario | Resultado |
|---|---|---|
| 1 | Alta de material | OK |
| 2 | Código de 11 dígitos | OK |
| 3 | Código único, doble clic y reactivación | OK |
| 4 | Normalización | OK |
| 5 | Catálogo compartido | OK |
| 6 | Búsqueda | OK |
| 7 | Edición y permisos | OK |
| 8 | Tipo inmutable | OK |
| 9 | Baja lógica y conservación | OK |
| 10 | Auditoría | OK |
| 11 | Concurrencia | OK |

Los 11 escenarios se completaron con los resultados esperados, incluida la creación exclusiva
por el Responsable de almacén, la baja lógica, la reactivación al re-registrar el código y la
edición por cualquier almacén.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [X] `pytest` pasa completo sobre PostgreSQL.
- [X] Cada criterio de aceptación de `spec.md` tiene al menos una prueba automatizada.
- [X] Los escenarios manuales 1–11 se completan con los resultados esperados.
- [X] El catálogo es visible para todos los tenants y no se filtra por tenant.
- [X] El código no se puede modificar por ninguna vía.
- [X] Solo el Responsable de almacén crea materiales.
- [X] Cualquier Responsable de almacén puede dar de baja cualquier material.
- [X] La baja es lógica: no borra la fila, la oculta de listados y búsquedas y queda auditada.
- [X] Cualquier Responsable de almacén o el Administrador de plataforma editan descripción y lote; la cuenta de tenant no.
- [X] La auditoría registra altas, cambios, bajas y reactivaciones por campo, sin secretos y en la misma transacción.
- [X] No existe ninguna ruta de borrado físico de materiales; `DELETE` responde `405`.
