# Quickstart y validación: 001 Tenants, regiones y acceso

**Fase**: 1 | **Fecha**: 2026-11-11 | **Spec**: `05-especificaciones/001-tenants-y-acceso/spec.md`

Guía para levantar el proyecto y validar de extremo a extremo las regiones, tenants, cuentas,
invitaciones, segundo factor, revocación de sesiones y auditoría. Los detalles de datos están
en `data-model.md` y los contratos en `contracts/`.

## Prerrequisitos

- Python 3.12 o superior.
- PostgreSQL 16 o superior con un rol de aplicación **sin** `SUPERUSER` ni `BYPASSRLS`.
- Redis 7 o superior (broker de Celery).
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

Crear la base y el rol (ejemplo; ajustar credenciales):

```sql
CREATE ROLE lari_app LOGIN PASSWORD 'cambiar-en-local';
CREATE DATABASE lari OWNER lari_app;
```

Variables de entorno mínimas para desarrollo (`.env`, nunca versionado):

```text
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=dev-solo-local
DATABASE_URL=postgresql://lari_app:cambiar-en-local@localhost:5432/lari
REDIS_URL=redis://localhost:6379/0
TOTP_ENCRYPTION_KEY=<clave-Fernet-generada-localmente>
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=no-reply@lari.local
```

Generar una clave Fernet local (guardarla solo en `.env`):

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Puesta en marcha

```powershell
python manage.py migrate
python manage.py crear_admin_plataforma --email admin@lari.local
python manage.py runserver
```

En otra terminal, para el envío de invitaciones:

```powershell
celery -A config worker -l info
```

Con `EMAIL_BACKEND` de consola, la invitación aparece en la salida del worker: copiar el
enlace `/invitacion/<token>/` para continuar.

`crear_admin_plataforma` crea una cuenta `ADMIN_PLATAFORMA` con invitación; no crea
superusuario de Django ni de base de datos.

## Pruebas automatizadas

```powershell
# Toda la suite
pytest

# Solo esta funcionalidad
pytest tests/unit tests/integration tests/contract -k "region or tenant or cuenta or invitacion or acceso"

# Con cobertura del módulo
pytest --cov=tenants --cov=acceso --cov=auditoria
```

Las pruebas requieren PostgreSQL (no SQLite) porque validan restricciones condicionales, RLS y
concurrencia real.

## Escenarios de validación manual

### 1. Alta de región y almacén

1. Iniciar sesión como Administrador con segundo factor.
2. Ir a `/plataforma/regiones/nueva/`.
3. Registrar código `LIM`, nombre `Lima`, Centro `PR05`, Almacén `BE03` y un buzón válido.
4. **Esperado**: la región y su almacén aparecen en `/plataforma/regiones/`; la auditoría
   muestra el alta.
5. Repetir con el mismo código.
6. **Esperado**: `"El código de región ya existe"`.
7. Enviar un buzón inválido o Centro vacío.
8. **Esperado**: `"El buzón no es válido"` o `"Centro y Almacén son obligatorios"`.

### 2. Alta de tenant

1. Ir a `/plataforma/tenants/nuevo/` y crear `TEN-001` en la región `LIM`.
2. **Esperado**: tenant `ACTIVO`, visible en el listado, con auditoría de alta.
3. Intentar guardar sin región.
4. **Esperado**: `"El tenant debe pertenecer a una región"`.
5. Abrir la edición del tenant.
6. **Esperado**: la región no es editable; una petición forzada con otra región se rechaza con
   `"La región del tenant no se puede cambiar"`.
7. Antes de crear la cuenta, intentar operar con el tenant.
8. **Esperado**: la operación se bloquea porque no hay cuenta activa.

### 3. Cuenta única del tenant e invitación

1. En el detalle del tenant, abrir `/plataforma/tenants/<id>/cuenta/nueva/`.
2. Registrar `tenant1@lari.local`.
3. **Esperado**: cuenta inactiva con rol `USUARIO_TENANT`; invitación generada; correo visible
   en la consola del worker; auditoría de alta.
4. Intentar crear una segunda cuenta para el mismo tenant.
5. **Esperado**: `"El tenant ya tiene una cuenta"`.
6. Intentar registrar un correo ya usado por otra cuenta.
7. **Esperado**: `"El correo ya está registrado"`.
8. Abrir el enlace de la invitación, definir una contraseña de al menos 12 caracteres.
9. **Esperado**: cuenta activa, invitación marcada como usada y auditoría del evento.
10. Reabrir el mismo enlace.
11. **Esperado**: `"La invitación venció o ya fue usada"`.

### 4. Invitación vencida, revocada y reenvío

1. Crear una cuenta de almacén y no aceptar la invitación.
2. Reenviar la invitación desde el detalle de la cuenta.
3. **Esperado**: el enlace anterior deja de funcionar (`410`); el nuevo enlace funciona.
4. Forzar en base de datos `expira_en` al pasado y abrir el enlace.
5. **Esperado**: `"La invitación venció o ya fue usada"`.

### 5. Inicio de sesión y segundo factor

1. Iniciar sesión como Administrador sin completar el TOTP.
2. **Esperado**: no se abre la sesión; solo se accede a `/login/2fa/`.
3. Completar el TOTP.
4. **Esperado**: sesión abierta con alcance global.
5. Repetir con un Responsable de almacén.
6. **Esperado**: también exige segundo factor.
7. Iniciar sesión con la cuenta del tenant.
8. **Esperado**: no exige segundo factor y el alcance es solo su tenant.

### 6. Aislamiento entre tenants y regiones

1. Crear dos tenants (`TEN-001`, `TEN-002`) con sus cuentas activas.
2. Iniciar sesión con la cuenta de `TEN-001` e intentar abrir un recurso de `TEN-002` por URL
   directa.
3. **Esperado**: `404`, sin revelar que el recurso existe.
4. Forzar un `tenant_id` de `TEN-002` en un formulario.
5. **Esperado**: el servidor lo ignora o lo rechaza; la operación queda en `TEN-001`.
6. Iniciar sesión como Responsable de almacén de otra región e intentar consultar solicitudes
   de la primera.
7. **Esperado**: no se devuelven datos (`404` o listado vacío).
8. Con la cuenta del tenant, intentar crear una cuenta o subcuenta.
9. **Esperado**: la ruta no existe y el servicio rechaza la operación.

### 7. Desactivación, reactivación y suspensión

1. Con una cuenta de tenant con sesión abierta, desactivarla desde
   `/plataforma/cuentas/<id>/desactivar/`.
2. **Esperado**: la siguiente petición de esa sesión se rechaza; el historial y la auditoría se
   conservan.
3. Reactivar la cuenta.
4. **Esperado**: puede iniciar sesión de nuevo; auditoría de reactivación.
5. Suspender su tenant desde `/plataforma/tenants/<id>/suspender/`.
6. **Esperado**: la cuenta no puede iniciar sesión ni operar; datos y stock intactos; auditoría
   de suspensión.
7. Reactivar el tenant y verificar que la cuenta vuelve a operar.

### 8. Cambio de rol

1. Crear una cuenta de Responsable de almacén y activarla.
2. Cambiar su rol a Administrador de plataforma desde
   `/plataforma/cuentas/<id>/rol/`.
3. **Esperado**: el cambio se aplica de inmediato, `version_sesion` aumenta y la auditoría
   muestra el rol anterior y el nuevo.
4. Intentar cambiar el rol de una cuenta de tenant.
5. **Esperado**: `"La cuenta del tenant no cambia de rol"`; solo se permite desactivarla o
   reactivarla.

### 9. Sin eliminación

1. Intentar `DELETE` sobre una región, un tenant o una cuenta.
2. **Esperado**: `405` o ruta inexistente; la interfaz solo ofrece desactivar o suspender.
3. Verificar que los registros y su auditoría siguen existiendo.

### 10. Auditoría

1. Abrir `/auditoria/acceso/` como Administrador.
2. **Esperado**: se ven altas, cambios de rol, desactivaciones y suspensiones con usuario,
   fecha, valor anterior y nuevo.
3. Abrir la misma ruta como cuenta de tenant.
4. **Esperado**: solo se ven registros de su tenant.
5. Inspeccionar los registros.
6. **Esperado**: no contienen contraseñas, tokens ni secretos TOTP.

### 11. Concurrencia

1. En dos sesiones simultáneas, intentar crear la misma región o el mismo tenant con el mismo
   código.
2. **Esperado**: una alta tiene éxito y la otra falla por restricción única con el mensaje de
   duplicado.
3. Intentar crear dos cuentas para el mismo tenant en paralelo.
4. **Esperado**: solo una se crea; la otra falla con `"El tenant ya tiene una cuenta"`.

## Criterios de salida

La funcionalidad se considera validada cuando:

- [ ] `pytest` pasa completo sobre PostgreSQL.
- [ ] Cada criterio de aceptación de `spec.md` tiene al menos una prueba automatizada.
- [ ] Los escenarios manuales 1–11 se completan con los resultados esperados.
- [ ] La auditoría no contiene secretos y es de solo inserción.
- [ ] Un tenant nunca ve datos de otro y un Responsable de almacén nunca ve otra región.
- [ ] La desactivación y la suspensión invalidan sesiones de inmediato.
