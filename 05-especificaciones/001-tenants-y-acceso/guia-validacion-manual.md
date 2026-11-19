# Guía de validación manual — 001 Tenants, regiones y acceso

> **Estado**: ejecutada el 2026-11-14. Los 11 escenarios se completaron con los resultados
> esperados. El registro oficial está en `quickstart.md`, sección «Registro de validación
> manual». Esta guía queda como referencia para futuras revalidaciones.

**Propósito**: ejecutar y registrar los escenarios 1–11 de
`05-especificaciones/001-tenants-y-acceso/quickstart.md` (tarea **T102**) sobre PostgreSQL,
navegador real y aplicación autenticadora.

**Resultado esperado**: los 11 escenarios con su resultado real, sin secretos en la auditoría y
sin accesos cruzados entre tenants o regiones.

> Esta guía usa PowerShell en Windows y el entorno virtual del repositorio. Si ya tienes
> PostgreSQL y Redis en Docker, salta al paso 1.

---

## 0. Preparación del entorno

### 0.1 Contenedores

```powershell
docker ps --format "{{.Names}}`t{{.Ports}}"
```

Debes ver `lari-postgres` en el puerto **5434** y `lari-redis` en el **6379**. Si no existen:

```powershell
docker run --name lari-postgres -e POSTGRES_USER=lari_app `
  -e POSTGRES_PASSWORD=lari_app -e POSTGRES_DB=lari -p 5434:5432 -d postgres:16
docker run --name lari-redis -p 6379:6379 -d redis:7
```

Verifica la conexión:

```powershell
docker exec -e PGPASSWORD=lari_app lari-postgres psql -h 127.0.0.1 -U lari_app -d lari -c "select 1;"
```

### 0.2 `.env`

Debe contener, como mínimo:

```text
SECRET_KEY=dev-solo-local
DEBUG=True
DATABASE_URL=postgresql://lari_app:lari_app@localhost:5434/lari
REDIS_URL=redis://localhost:6379/0
TOTP_ENCRYPTION_KEY=<clave Fernet válida>
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=no-reply@lari.local
BASE_URL=http://localhost:8000
```

Si falta la clave TOTP:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copia el valor en `TOTP_ENCRYPTION_KEY=` y **no** lo versiones.

### 0.3 Migraciones y suite

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest -q
```

Debe terminar en `141 passed`.

### 0.4 Arranque

Terminal A:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Terminal B (necesaria para ver los correos de invitación):

```powershell
.\.venv\Scripts\celery.exe -A config worker -l info --pool=solo
```

> Con `EMAIL_BACKEND` de consola, el enlace `/invitacion/<token>/` aparece en la salida del
> worker, no en el navegador.

### 0.5 Cuenta administradora

```powershell
.\.venv\Scripts\python.exe manage.py crear_admin_plataforma --email admin@lari.local
```

Copia la URL `/invitacion/<token>/` que imprime el comando. Ábrela en el navegador, define una
contraseña de **12 caracteres o más** y confirma.

Después inicia sesión en `http://localhost:8000/login/`. Como el administrador aún no tiene
segundo factor, `/login/2fa/` mostrará el URI `otpauth://...`. Agrégalo a tu aplicación
autenticadora (Google Authenticator, Aegis, 1Password, etc.) e ingresa el código de 6 dígitos.

> **Ayuda local sin teléfono**: en otra terminal puedes imprimir el código actual del
> administrador:
>
> ```powershell
> .\.venv\Scripts\python.exe manage.py shell -c "import pyotp; from acceso.models import Usuario; from acceso.totp import descifrar_secreto; u=Usuario.objects.get(email='admin@lari.local'); print(pyotp.TOTP(descifrar_secreto(u.secreto_totp)).now())"
> ```

---

## 1. Alta de región y almacén

1. Como Administrador, abre `http://localhost:8000/plataforma/regiones/nueva/`.
2. Registra: código `LIM`, nombre `Lima`, Centro `PR05`, Almacén `BE03`, buzón
   `almacen.lim@lari.local`.
3. **Esperado**: redirección a `/plataforma/regiones/`, fila `LIM` visible y almacén con
   `PR05/BE03`.
4. Repite el alta con código `LIM`.
5. **Esperado**: estado `409` visible con `"El código de región ya existe"`.
6. Intenta con buzón `no-es-correo`.
7. **Esperado**: `"El buzón no es válido"`.
8. Intenta con Centro y Almacén vacíos.
9. **Esperado**: `"Centro y Almacén son obligatorios"`.

Verificación en auditoría (después del paso 3):

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from auditoria.models import RegistroCambio; print(list(RegistroCambio.objects.filter(entidad__in=['Region','Almacen'], campo='alta').values_list('entidad','campo','valor_nuevo')))"
```

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 2. Alta de tenant

1. Abre `http://localhost:8000/plataforma/tenants/nuevo/`.
2. Crea `TEN-001`, nombre `Tenant Lima`, región `LIM`.
3. **Esperado**: redirección al detalle, estado `Activo` y auditoría de alta.
4. Intenta guardar sin región.
5. **Esperado**: `"El tenant debe pertenecer a una región"`.
6. La región **no** se expone en ningún formulario de edición. La validación forzada es de
   servicio; ejecútala así:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from acceso.models import Usuario; from tenants.models import Tenant, Region; from tenants.services import actualizar_tenant, TenantInvalido; a=Usuario.objects.get(email='admin@lari.local'); t=Tenant.objects.get(codigo='TEN-001'); r=Region.objects.get(codigo='LIM'); 
try:
    actualizar_tenant(t, {'region': r.pk}, a)
    print('ERROR: permitió cambiar la región')
except TenantInvalido as e:
    print('OK:', e)"
```

7. **Esperado**: `OK: La región del tenant no se puede cambiar`.
8. Sin cuenta activa, el tenant no opera:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from tenants.models import Tenant; t=Tenant.objects.get(codigo='TEN-001'); print('tiene_cuenta_activa=', t.tiene_cuenta_activa())"
```

**Esperado**: `False`.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 3. Cuenta única del tenant e invitación

1. En el detalle de `TEN-001`, pulsa **Crear cuenta del tenant**.
2. Registra `tenant1@lari.local`.
3. **Esperado**: `302` al detalle; cuenta `Inactiva`, rol `USUARIO_TENANT`; en la terminal del
   worker aparece el enlace `/invitacion/<token>/`; la auditoría registra el alta.
4. Intenta crear una segunda cuenta para el mismo tenant (vuelve a la URL
   `/plataforma/tenants/<id>/cuenta/nueva/`).
5. **Esperado**: `"El tenant ya tiene una cuenta"`.
6. Intenta registrar el correo `admin@lari.local`.
7. **Esperado**: `"El correo ya está registrado"`.
8. Abre el enlace de invitación, define `ClaveTenant12345` y confirma.
9. **Esperado**: `302` a `/login/`; la cuenta queda activa y la invitación usada.
10. Reabre el mismo enlace.
11. **Esperado**: `"La invitación venció o ya fue usada"`.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from acceso.models import Usuario, Invitacion; u=Usuario.objects.get(email='tenant1@lari.local'); print('activo=', u.is_active, 'rol=', u.rol); print(list(Invitacion.objects.filter(usuario=u).values_list('enviada_en','usada_en')))"
```

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 4. Invitación vencida y reenvío

> En esta entrega **no existe ruta HTTP de reenvío** (T059 se cubrió a nivel de servicio). Si el
> contrato exige una ruta, regístralo como carencia.

1. Crea una cuenta de almacén desde `/plataforma/cuentas/nueva-almacen/` con
   `almacen1@lari.local` y región `LIM`. No aceptes la invitación.
2. Reenvía desde la consola, conservando el enlace anterior:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from acceso.models import Usuario; from acceso.services import reenviar_invitacion; a=Usuario.objects.get(email='admin@lari.local'); u=Usuario.objects.get(email='almacen1@lari.local'); inv=reenviar_invitacion(u, a); print('nueva invitacion', inv.pk, inv.expira_en)"
```

3. En el worker debe aparecer un enlace nuevo.
4. **Esperado**: el enlace anterior responde `410` con
   `"La invitación venció o ya fue usada"`; el nuevo sigue mostrando el formulario.
5. Fuerza el vencimiento de la invitación nueva:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from django.utils import timezone; from datetime import timedelta; from acceso.models import Invitacion; i=Invitacion.objects.filter(usuario__email='almacen1@lari.local', usada_en__isnull=True, revocada_en__isnull=True).latest('creada_en'); i.expira_en=timezone.now()-timedelta(hours=1); i.save(update_fields=['expira_en']); print(i.pk)"
```

6. Abre su enlace.
7. **Esperado**: `410` con el mismo mensaje uniforme.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 5. Inicio de sesión y segundo factor

1. Cierra sesión y vuelve a entrar como Administrador.
2. **Esperado**: tras correo y contraseña, redirige a `/login/2fa/`; cualquier otra ruta
   redirige también a `/login/2fa/` (sesión pendiente).
3. Ingresa el código TOTP.
4. **Esperado**: sesión abierta con acceso a `/plataforma/...`.
5. Repite con el Responsable de almacén `almacen1@lari.local` (primero acepta su invitación y
   configura su TOTP).
6. **Esperado**: también exige segundo factor.
7. Inicia sesión con `tenant1@lari.local`.
8. **Esperado**: **no** pide TOTP y solo accede a su propio alcance.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 6. Aislamiento entre tenants y regiones

> En esta entrega todavía no existen rutas de datos operativos del tenant (pertenecen a 002+).
> El aislamiento se valida con `/auditoria/acceso/` y con los servicios.

1. Crea un segundo tenant `TEN-002` en otra región (`TRU`, nombre `Trujillo`) con su cuenta
   activa `tenant2@lari.local`.
2. Como `tenant1@lari.local`, abre `/auditoria/acceso/`.
3. **Esperado**: solo aparecen registros de `TEN-001`; no aparece `TEN-002`.
4. Busca un registro de `TEN-002` y fuerza su id:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from auditoria.models import RegistroCambio; print(RegistroCambio.objects.filter(tenant__codigo='TEN-002').values_list('pk', flat=True))"
```

Abre `http://localhost:8000/auditoria/acceso/?registro_id=<id>` con la sesión de `TEN-001`.

5. **Esperado**: `404`, sin revelar el contenido.
6. Fuerza `?tenant_id=<id de TEN-002>&region_id=<id de TRU>` en `/` con la sesión de `TEN-001`.
7. **Esperado**: la página carga con el contexto de `TEN-001`; el servidor ignora los parámetros.
8. Con `tenant1@lari.local`, intenta `/plataforma/tenants/<id>/cuenta/nueva/`.
9. **Esperado**: `403`; el servicio también rechaza con
   `"No tienes permiso para administrar esta cuenta"`.

**Resultado:** X OK  ☐ Falló  Observaciones: ______________________________

---

## 7. Desactivación, reactivación y suspensión

1. Mantén una sesión abierta con `tenant1@lari.local` (ventana A).
2. En una ventana de incógnito, como Administrador, abre `/plataforma/cuentas/` y pulsa
   **Desactivar** sobre `tenant1@lari.local`.
3. **Esperado**: `302`; la cuenta queda inactiva; la auditoría registra `is_active`.
4. En la ventana A, navega a cualquier ruta.
5. **Esperado**: redirección a `/login/` (sesión invalidada).
6. Reactiva la cuenta desde `/plataforma/cuentas/`.
7. **Esperado**: `tenant1` puede iniciar sesión de nuevo; auditoría de reactivación.
8. Suspende `TEN-001` desde su detalle con **Suspender tenant**.
9. **Esperado**: estado `Suspendido`; la cuenta no puede iniciar sesión
   (`"El tenant está suspendido"`); datos y stock intactos.
10. Pulsa **Activar tenant**.
11. **Esperado**: `tenant1` vuelve a operar.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 8. Cambio de rol

1. Activa la cuenta `almacen1@lari.local` aceptando su invitación y configurando su TOTP.
2. Como Administrador, en `/plataforma/cuentas/`, selecciona **Administrador de plataforma**
   para esa cuenta y pulsa **Cambiar rol**.
3. **Esperado**: `302`; el rol cambia, `version_sesion` aumenta y la auditoría muestra el rol
   anterior y el nuevo.
4. Intenta cambiar el rol de `tenant1@lari.local`.
5. **Esperado**: `409` `"La cuenta del tenant no cambia de rol"`.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from acceso.models import Usuario; from auditoria.models import RegistroCambio; u=Usuario.objects.get(email='almacen1@lari.local'); print('rol=', u.rol, 'version=', u.version_sesion); print(list(RegistroCambio.objects.filter(entidad='Usuario', entidad_id=u.pk, campo='rol').values_list('valor_anterior','valor_nuevo')))"
```

> Nota: el cambio `ALMACEN → ADMIN` limpia la región. El cambio `ADMIN → ALMACEN` sin región se
> rechaza con `"El alcance de la cuenta no es válido"`, porque el contrato no envía región.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 9. Sin eliminación

1. No existe botón ni ruta de borrado en la interfaz.
2. Prueba `DELETE` con una sesión autenticada. Copia la cookie `sessionid` desde las DevTools del
   navegador y ejecuta (ajusta el id):

```powershell
curl.exe -i -X DELETE "http://localhost:8000/plataforma/regiones/1/editar/" `
  -H "Cookie: sessionid=<tu-sessionid>"
```

3. **Esperado**: `405 Method Not Allowed`.
4. Repite con `/plataforma/tenants/<id>/` y
   `/plataforma/cuentas/<id>/desactivar/`.
5. **Esperado**: `405` en ambos casos.
6. Confirma que los registros y su auditoría siguen existiendo:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from tenants.models import Region, Tenant; from acceso.models import Usuario; from auditoria.models import RegistroCambio; print('regiones=', Region.objects.count(), 'tenants=', Tenant.objects.count(), 'cuentas=', Usuario.objects.count(), 'auditoria=', RegistroCambio.objects.count())"
```

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 10. Auditoría

1. Como Administrador, abre `/auditoria/acceso/`.
2. **Esperado**: altas de región/tenant/cuenta, cambios de rol, desactivaciones y suspensiones,
   con entidad, id, campo, valor anterior, valor nuevo, usuario y fecha.
3. Prueba los filtros `entidad`, `entidad_id`, `usuario`, `desde`, `hasta`.
4. **Esperado**: el listado se filtra y pagina de 50 en 50.
5. Abre la misma ruta con `tenant1@lari.local`.
6. **Esperado**: solo registros de `TEN-001`.
7. Revisa que ningún valor contenga contraseñas, `token_hash` ni secretos TOTP:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from auditoria.models import RegistroCambio; prohibidos=('password','contraseña','token','secreto'); malos=[(r.pk,r.campo) for r in RegistroCambio.objects.all() if any(p in (r.campo+' '+r.valor_anterior+' '+r.valor_nuevo).lower() for p in prohibidos)]; print('sospechosos=', malos)"
```

8. **Esperado**: `sospechosos= []`.

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 11. Concurrencia

La concurrencia real requiere dos sesiones simultáneas.

1. Abre dos ventanas de incógnito, ambas como Administrador.
2. Prepara en ambas el alta de una región con el mismo código `CON`, nombre `Concurrente`,
   Centro `PR05`, Almacén `BE03`, buzón `con@lari.local`.
3. Envía ambas casi al mismo tiempo (Enter en las dos).
4. **Esperado**: una alta tiene éxito y la otra falla con `"El código de región ya existe"`; en
   base de datos queda **una sola** fila.
5. Repite con dos altas del tenant `TEN-CON`.
6. **Esperado**: una sola fila; la otra recibe `"El código de tenant ya existe"`.
7. Repite con dos cuentas para el mismo tenant desde dos ventanas.
8. **Esperado**: solo una se crea; la otra recibe `"El tenant ya tiene una cuenta"`.

Verificación:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from tenants.models import Region, Tenant; print('regiones CON=', Region.objects.filter(codigo='CON').count(), 'tenants TEN-CON=', Tenant.objects.filter(codigo='TEN-CON').count())"
```

**Resultado:** x OK  ☐ Falló  Observaciones: ______________________________

---

## 12. Cierre

1. Ejecuta de nuevo la suite y confirma que sigue verde:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --check
```

2. Registra el resultado en `quickstart.md`, sección **Criterios de salida**, marcando la
   tercera casilla cuando los 11 escenarios estén completos.
3. Adjunta esta tabla rellenada:

| # | Escenario | Resultado | Evidencia / observaciones |
|---|---|---|---|
| 1 | Alta de región y almacén | | |
| 2 | Alta de tenant | | |
| 3 | Cuenta única e invitación | | |
| 4 | Invitación vencida y reenvío | | |
| 5 | Login y segundo factor | | |
| 6 | Aislamiento tenant/región | | |
| 7 | Desactivación/suspensión | | |
| 8 | Cambio de rol | | |
| 9 | Sin eliminación | | |
| 10 | Auditoría | | |
| 11 | Concurrencia | | |

---

## Diferencias conocidas entre `quickstart.md` y la implementación actual

Estas diferencias son deliberadas o quedaron documentadas en las tareas; no impiden validar los
criterios de aceptación:

1. **No hay ruta de edición de tenant**: la región no editable se valida en el servicio
   (`actualizar_tenant`), tal como indica T054.
2. **No hay ruta HTTP de reenvío de invitación**: se valida con `reenviar_invitacion` desde
   consola, tal como permite T059.
3. **No existen aún rutas de datos operativos del tenant** (specs 002+): el aislamiento se
   comprueba con `/auditoria/acceso/` y los servicios.
4. **La invitación del comando `crear_admin_plataforma` no pasa por Celery**: el comando imprime
   la URL directamente; úsala para el primer acceso.
5. **Códigos de región**: solo alfanuméricos y se guardan en mayúsculas. Los códigos de tenant
   admiten `-` y `_`.
6. **La auditoría es inmutable**: además de revocar permisos, un trigger rechaza `UPDATE` y
   `DELETE`, porque el rol dueño de las tablas no queda bloqueado solo con `REVOKE`.
