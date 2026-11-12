---

description: "Lista de tareas para la implementación de 001 Tenants, regiones y acceso"
---

# Tareas: 001 Tenants, regiones y acceso

**Entrada**: Documentos de diseño en `05-especificaciones/001-tenants-y-acceso/`

**Prerrequisitos**: `plan.md` (obligatorio), `spec.md` (obligatorio), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: **INCLUIDAS y obligatorias**. La constitución (principio VIII y puerta de pruebas) exige al menos una prueba por criterio de aceptación, y `plan.md` (§Pruebas) enumera los nombres propuestos. Cada historia escribe primero sus pruebas, las ve fallar y luego implementa.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario asociada (`US1`…`US6`)
- Todas las rutas de archivo son relativas a la raíz del repositorio

## Origen de las historias de usuario

`spec.md` no numera historias propias; declara trazabilidad a HU-01, HU-04 y HU-34…HU-38 y describe flujos y criterios de aceptación. Las historias siguientes se derivan de esos flujos, de los actores y del orden de dependencia técnica (la identidad habilita todo lo demás).

| Historia | Prioridad | Origen en `spec.md` |
|---|---|---|
| US1 — Inicio de sesión con segundo factor y sesión revocable | P1 | Flujo «Inicio de sesión», regla 10, criterios de 2FA y revocación |
| US2 — Regiones con almacén central | P2 | Flujo «Alta de región y almacén», entidad Región, criterios de alta/duplicado/buzón |
| US3 — Tenants en una región | P3 | Flujo «Alta de tenant», entidad Tenant, criterios de región obligatoria/inmutable |
| US4 — Cuenta única del tenant y cuentas administrativas con invitación | P4 | Flujos «Alta de la cuenta del tenant», «Alta de cuenta de almacén» y «Aceptación de invitación» |
| US5 — Desactivación, reactivación, suspensión y cambio de rol | P5 | Flujos «Desactivación de cuenta» y «Suspensión de tenant», reglas 12–15 |
| US6 — Aislamiento por tenant/región y auditoría consultable | P6 | Reglas 2, 3, 17 y 18; criterios de aislamiento y auditoría |

## Convenciones de rutas

Proyecto Django único en la raíz: `config/`, `tenants/`, `acceso/`, `auditoria/`, `templates/`, `static/`, `tests/{unit,integration,contract}/`.

---

## Fase 1: Setup (infraestructura compartida)

**Propósito**: inicializar el proyecto Django, la configuración por entornos y el entorno de pruebas sobre PostgreSQL.

- [ ] T001 Crear el esqueleto del proyecto Django con `manage.py`, `config/__init__.py`, `config/settings/{base,dev,prod,test}.py`, `config/urls.py`, `config/wsgi.py` y `config/asgi.py`
- [ ] T002 [P] Declarar dependencias en `requirements.txt` (Django LTS 5.x, `psycopg[binary]`, `celery`, `redis`, `pyotp`, `cryptography`, `dj-database-url`, `python-dotenv`, `gunicorn`) y en `requirements-dev.txt` (`pytest`, `pytest-django`, `pytest-cov`)
- [ ] T003 [P] Configurar lectura de variables de entorno en `config/settings/base.py` y documentar las claves en `.env.example` (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `TOTP_ENCRYPTION_KEY`, `EMAIL_*`, `DEFAULT_FROM_EMAIL`)
- [ ] T004 [P] Crear `pyproject.toml` con configuración de `pytest` y `pytest-django`, `DJANGO_SETTINGS_MODULE=config.settings.test` y marcador de base PostgreSQL obligatoria (sin SQLite)
- [ ] T005 [P] Crear la configuración de pruebas en `config/settings/test.py` con base PostgreSQL de pruebas, `EMAIL_BACKEND` en memoria y `CELERY_TASK_ALWAYS_EAGER=True`
- [ ] T006 [P] Crear `templates/base.html`, `templates/parciales/mensajes.html` y `static/css/base.css` con la estructura mínima de la interfaz server-rendered
- [ ] T007 [P] Configurar en `config/settings/base.py` `LANGUAGE_CODE=es`, `TIME_ZONE` del proyecto, `LOGIN_URL="/login/"` y `STATICFILES_DIRS`/`TEMPLATES` apuntando a `static/` y `templates/`

---

## Fase 2: Fundacional (prerrequisitos bloqueantes)

**Propósito**: modelos base, identidad, auditoría, middleware y utilidades que TODAS las historias necesitan.

**⚠️ CRÍTICO**: ninguna historia puede comenzar hasta completar esta fase. Los modelos de las seis entidades se crean aquí porque `AUTH_USER_MODEL` debe existir antes de la primera migración y porque `Usuario` referencia `tenants.Region` y `tenants.Tenant` (`plan.md` §Migraciones).

- [ ] T008 Crear las apps `tenants`, `acceso` y `auditoria` con sus `apps.py` y registrarlas en `INSTALLED_APPS` de `config/settings/base.py`
- [ ] T009 [P] Implementar `Region`, `Almacen` y `Tenant` en `tenants/models.py` con `codigo=CharField(max_length=20, unique=True)`, `nombre=CharField(max_length=100)`, `Almacen.centro`/`codigo_almacen` de 20 caracteres, `buzon=EmailField()`, `Tenant.estado` con choices `ACTIVO`/`SUSPENDIDO` por defecto `ACTIVO`, `CheckConstraint(region_codigo_obligatorio)` (`codigo <> ''`), `CheckConstraint(almacen_parametros_obligatorios)` (`centro <> '' AND codigo_almacen <> ''`), `CheckConstraint(tenant_codigo_obligatorio)`, `CheckConstraint(tenant_estado_valido)` (`estado IN ('ACTIVO','SUSPENDIDO')`), `Index(region, estado, name="tenant_region_estado")` y `Tenant.tiene_cuenta_activa()`
- [ ] T010 [P] Implementar `UsuarioManager` en `acceso/managers.py` con `create_user(email, password=None, **extra_fields)` que aplique `normalize_email`, `is_active=False` por defecto, `set_unusable_password()` cuando no hay contraseña y los métodos `para_tenant(tenant)` y `para_region(region)`
- [ ] T011 Implementar `Rol` (`TextChoices`: `ADMIN_PLATAFORMA`, `USUARIO_TENANT`, `RESPONSABLE_ALMACEN`) y `Usuario(AbstractUser)` en `acceso/models.py` con `username=None`, `email=EmailField(unique=True)`, `tenant`/`region` FK `null=True, blank=True, on_delete=PROTECT`, `version_sesion=PositiveIntegerField(default=0)`, `secreto_totp=CharField(max_length=64, blank=True)`, `segundo_factor_habilitado=BooleanField(default=False)`, `USERNAME_FIELD="email"`, `REQUIRED_FIELDS=[]`, `CheckConstraint(usuario_alcance_coherente)` y `UniqueConstraint(["tenant"], condition=Q(rol=USUARIO_TENANT), name="un_usuario_tenant_por_tenant")`
- [ ] T012 Agregar `Invitacion` en `acceso/models.py` con `usuario` FK `CASCADE`, `token_hash=CharField(max_length=64, unique=True)`, `correo=EmailField()`, `expira_en`, `enviada_en`/`usada_en`/`revocada_en` nulos, `ultimo_error=TextField(blank=True)`, `creada_por` FK `PROTECT`, `creada_en` `auto_now_add` e `Index(["usuario","usada_en","revocada_en"], name="invitacion_vigente")`
- [ ] T013 [P] Implementar `RegistroCambio` en `auditoria/models.py` con `entidad=CharField(max_length=50)`, `entidad_id=BigIntegerField()`, `campo=CharField(max_length=50)`, `valor_anterior`/`valor_nuevo` `TextField(blank=True)`, `usuario` FK `PROTECT`, `fecha` `auto_now_add` e índices `(entidad, entidad_id)` y `(usuario, fecha)`
- [ ] T014 [P] Implementar `auditoria/services.py` con `registrar_cambio(entidad, entidad_id, campo, valor_anterior, valor_nuevo, usuario)` de solo inserción y helpers `serializar_valor()`; debe rechazar explícitamente contraseñas, tokens, `token_hash` y secretos TOTP
- [ ] T015 [P] Implementar `acceso/totp.py` con `cifrar_secreto()`/`descifrar_secreto()` usando `cryptography.fernet.Fernet` y `TOTP_ENCRYPTION_KEY`, `generar_uri_otpauth(usuario)` y `verificar_codigo(usuario, codigo)` con `pyotp`
- [ ] T016 [P] Implementar `ContextoUsuarioMiddleware` en `acceso/middleware.py`: rechaza cuentas inactivas, tenants suspendidos y `version_sesion` desactualizada comparando la sesión con la base; publica `request.usuario`, `request.rol`, `request.tenant` y `request.region` derivados solo del usuario autenticado, nunca del cliente
- [ ] T017 [P] Implementar decoradores `requiere_rol(*roles)`, `requiere_tenant` y `requiere_region` en `acceso/decorators.py`, devolviendo `403` con `"No tienes permiso para administrar esta cuenta"` cuando corresponda
- [ ] T018 Configurar en `config/settings/base.py` `AUTH_USER_MODEL="acceso.Usuario"`, `MIDDLEWARE` con `ContextoUsuarioMiddleware` después de la autenticación y los validadores `MinimumLengthValidator(12)`, `UserAttributeSimilarityValidator`, `CommonPasswordValidator` y `NumericPasswordValidator`
- [ ] T019 [P] Crear `config/celery.py` con la app Celery, `config/__init__.py` con `app = Celery("config")` y la configuración de broker `REDIS_URL`
- [ ] T020 Generar y revisar las migraciones iniciales `tenants/migrations/0001_initial.py`, `acceso/migrations/0001_initial.py` y `auditoria/migrations/0001_initial.py`; verificar que `AUTH_USER_MODEL` esté configurado antes de `migrate` y que no se creen credenciales ni superusuarios en ninguna migración
- [ ] T021 [P] Crear `conftest.py` con fixtures `region`, `almacen`, `tenant`, `usuario_admin`, `usuario_tenant`, `usuario_almacen` y `cliente_autenticado` sobre PostgreSQL, y un fixture que fije `version_sesion` en la sesión de prueba

**Checkpoint**: esquema, identidad, auditoría y middleware listos; las historias pueden comenzar.

---

## Fase 3: US1 — Inicio de sesión con segundo factor y sesión revocable (P1) 🎯

**Objetivo**: autenticación por correo y contraseña, TOTP obligatorio para Administrador de plataforma y Responsable de almacén, cierre de sesión y revocación inmediata por `version_sesion`; incluye el comando de arranque `crear_admin_plataforma`.

**Prueba independiente**: crear un Administrador con `crear_admin_plataforma`, aceptar su invitación, iniciar sesión sin TOTP (no se abre la sesión), completar TOTP (sesión abierta), incrementar `version_sesion` en la base y verificar que la siguiente petición cierra la sesión.

### Pruebas de US1 (escribir primero, deben fallar)

- [ ] T022 [P] [US1] Pruebas de contrato de `GET/POST /login/` en `tests/contract/test_login.py`: `302` sin 2FA, `302` a `/login/2fa/` con 2FA, `400` `"Correo o contraseña incorrectos"` uniforme, `403` `"La cuenta está desactivada"`, `403` `"El tenant está suspendido"`
- [ ] T023 [P] [US1] Pruebas de contrato de `/login/2fa/` y `POST /logout/` en `tests/contract/test_auth_2fa.py`: éxito `302`, `400` `"Debes completar el segundo factor"`, `403` `"Debes iniciar sesión"` sin sesión pendiente, `403` sin CSRF en logout
- [ ] T024 [P] [US1] Pruebas de integración de sesión en `tests/integration/test_sesion.py`: `pendiente_2fa` solo accede a `/login/2fa/`, `/logout/` y estáticos; `version_sesion` desactualizada cierra la sesión; admin y almacén exigen segundo factor; cuenta de tenant no lo exige
- [ ] T025 [P] [US1] Pruebas unitarias de `acceso/totp.py` en `tests/unit/test_totp.py`: cifrado/descifrado del secreto, rechazo de secreto corrupto y verificación de un código TOTP válido e inválido
- [ ] T026 [P] [US1] Pruebas unitarias del comando en `tests/unit/test_comando_admin.py`: `crear_admin_plataforma --email admin@lari.local` crea rol `ADMIN_PLATAFORMA` sin tenant ni región, inactivo, con invitación y sin superusuario de Django

### Implementación de US1

- [ ] T027 [US1] Implementar el backend de autenticación por correo en `acceso/authentication.py` y registrarlo en `AUTHENTICATION_BACKENDS`
- [ ] T028 [US1] Implementar `LoginForm`, `SegundoFactorForm` y `ConfigurarTotpForm` en `acceso/forms.py` con los mensajes exactos del contrato
- [ ] T029 [US1] Implementar `iniciar_sesion(correo, password)`, `verificar_segundo_factor(usuario, codigo)`, `renovar_version_sesion(usuario)` y `estado_sesion_pendiente()` en `acceso/services.py`, guardando `version_sesion` en la sesión y aplicando `transaction.atomic` + `select_for_update` al incrementar la versión
- [ ] T030 [US1] Implementar las vistas `login`, `login_2fa`, `logout` y `configurar_2fa` en `acceso/views.py` con CSRF, estado `pendiente_2fa` y mensajes del contrato
- [ ] T031 [US1] Implementar la vista inicial por rol en `acceso/views.py` y la redirección `302` posterior al login según `request.rol`
- [ ] T032 [US1] Registrar las rutas `/login/`, `/login/2fa/`, `/logout/` y `/perfil/` en `acceso/urls.py` e incluirlas en `config/urls.py`
- [ ] T033 [US1] Crear `templates/acceso/login.html`, `templates/acceso/login_2fa.html`, `templates/acceso/configurar_2fa.html`, `templates/acceso/perfil.html` y `templates/inicio.html`
- [ ] T034 [US1] Implementar el comando `crear_admin_plataforma` en `acceso/management/commands/crear_admin_plataforma.py`, que crea la cuenta con rol explícito, `is_active=False`, contraseña inutilizable e invitación, sin superusuario ni credenciales conocidas por el operador

**Checkpoint**: US1 funcional y verificable de forma independiente (login, 2FA, logout, revocación).

---

## Fase 4: US2 — Regiones con almacén central (P2)

**Objetivo**: el Administrador de plataforma lista, crea y edita regiones con su almacén central en una sola transacción, con validaciones y auditoría por campo.

**Prueba independiente**: con un Administrador autenticado con 2FA, crear `LIM/Lima/PR05/BE03/buzón válido` y comprobar región + almacén + auditoría; repetir código (409), buzón inválido y Centro vacío.

### Pruebas de US2 (escribir primero, deben fallar)

- [ ] T035 [P] [US2] Pruebas de contrato de regiones en `tests/contract/test_regiones.py`: `GET` listado paginado, alta `302`, `409` `"El código de región ya existe"`, `400` `"El buzón no es válido"`, `400` `"Centro y Almacén son obligatorios"`, `400` `"El nombre es obligatorio"`, edición auditada y `405` ante `DELETE`
- [ ] T036 [P] [US2] Pruebas de integración en `tests/integration/test_regiones.py`: `crear_region` guarda región y almacén atómicamente con auditoría `alta`; código duplicado falla por restricción única; `actualizar_region` audita cada campo con valor anterior y nuevo; `activa=False` impide nuevos tenants
- [ ] T037 [P] [US2] Pruebas de base de datos en `tests/integration/test_restricciones_region.py`: inserción directa con `codigo=""` y con `centro=""`/`codigo_almacen=""` falla por `CheckConstraint`; dos regiones con el mismo código fallan por `unique`

### Implementación de US2

- [ ] T038 [P] [US2] Implementar `RegionForm` y `AlmacenForm` en `tenants/forms.py` con `codigo` alfanumérico de 1–20 caracteres, `nombre` no vacío, `centro`/`almacen` obligatorios y `buzon` con formato válido
- [ ] T039 [US2] Implementar `crear_region(datos, actor)` en `tenants/services.py`: valida rol `ADMIN_PLATAFORMA`, código único, Centro/Almacén/buzón; en `transaction.atomic` crea región, almacén y auditoría de alta; traduce `IntegrityError` a `"El código de región ya existe"`
- [ ] T040 [US2] Implementar `actualizar_region(region, datos, actor)` en `tenants/services.py`: solo `ADMIN_PLATAFORMA`, `select_for_update`, sin permitir cambiar `codigo`, audita cada campo modificado en la misma transacción
- [ ] T041 [US2] Implementar en `tenants/views.py` las vistas `listar_regiones` (50 por página), `crear_region` (`GET/POST`) y `editar_region` (`GET/POST`) protegidas con `@requiere_rol(Rol.ADMIN_PLATAFORMA)`
- [ ] T042 [US2] Registrar las rutas `/plataforma/regiones/`, `/plataforma/regiones/nueva/` y `/plataforma/regiones/<int:id>/editar/` en `tenants/urls.py` e incluirlas en `config/urls.py`
- [ ] T043 [US2] Crear `templates/tenants/regiones_lista.html`, `templates/tenants/region_form.html` y el parcial `templates/tenants/_tabla_regiones.html` con HTMX para el listado
- [ ] T044 [US2] Asegurar que no exista ruta ni vista de borrado de regiones y que `DELETE` sobre las rutas existentes responda `405`

**Checkpoint**: US2 funcional de forma independiente sobre la base de US1.

---

## Fase 5: US3 — Tenants en una región (P3)

**Objetivo**: el Administrador de plataforma lista, crea y consulta tenants; la región es obligatoria, debe estar activa y es inmutable después del alta.

**Prueba independiente**: crear `TEN-001` en `LIM` (queda `ACTIVO` con auditoría), rechazar alta sin región y con región inactiva, rechazar código duplicado y verificar que el servicio rechaza cambiar la región.

### Pruebas de US3 (escribir primero, deben fallar)

- [ ] T045 [P] [US3] Pruebas de contrato de tenants en `tests/contract/test_tenants.py`: listado paginado, alta `302` al detalle, `400` `"El tenant debe pertenecer a una región"`, `400` `"La región seleccionada no está disponible"`, `409` `"El código de tenant ya existe"`, detalle `200` y `404` inexistente
- [ ] T046 [P] [US3] Pruebas de integración en `tests/integration/test_tenants.py`: `crear_tenant` atómico con auditoría; región obligatoria; región inactiva rechazada; código duplicado por restricción única; `actualizar_tenant` rechaza cambiar `region` con `"La región del tenant no se puede cambiar"`
- [ ] T047 [P] [US3] Prueba de integración en `tests/integration/test_tenant_operacion.py`: `Tenant.tiene_cuenta_activa()` es `False` sin cuenta activa y un tenant sin cuenta activa no opera (petición autenticada de su cuenta inactiva rechazada por el middleware)

### Implementación de US3

- [ ] T048 [P] [US3] Implementar `TenantForm` en `tenants/forms.py` con `codigo`, `nombre` y `region` limitada a regiones activas; el formulario de edición no incluye `region`
- [ ] T049 [US3] Implementar `crear_tenant(datos, actor)` en `tenants/services.py`: solo `ADMIN_PLATAFORMA`, región activa obligatoria, código único, `estado="ACTIVO"` por defecto, auditoría de alta en la misma transacción
- [ ] T050 [US3] Implementar `actualizar_tenant(tenant, datos, actor)` en `tenants/services.py`: si `datos` contiene `region` distinta de `tenant.region`, lanza error `"La región del tenant no se puede cambiar"`; audita solo los campos modificados
- [ ] T051 [US3] Implementar `listar_tenants` (50 por página, orden por `codigo`), `crear_tenant` (`GET/POST`) y `detalle_tenant` en `tenants/views.py`, este último mostrando la cuenta única o su ausencia
- [ ] T052 [US3] Registrar `/plataforma/tenants/`, `/plataforma/tenants/nuevo/` y `/plataforma/tenants/<int:id>/` en `tenants/urls.py`
- [ ] T053 [US3] Crear `templates/tenants/tenants_lista.html`, `templates/tenants/tenant_form.html` y `templates/tenants/tenant_detalle.html` con el estado, la región y la cuenta asociada
- [ ] T054 [US3] Verificar que `Tenant.region` no se exponga en ningún formulario de edición y que una petición forzada con `region` falle en el servicio (sin ruta de edición en `contracts/http-endpoints.md`, la validación es de servicio)

**Checkpoint**: US3 funcional de forma independiente (requiere US1; no requiere US2 para sus servicios, aunque la UI depende de que existan regiones).

---

## Fase 6: US4 — Cuenta única del tenant y cuentas administrativas con invitación (P4)

**Objetivo**: el Administrador crea la cuenta única de un tenant y las cuentas de almacén inactivas, genera invitaciones de un solo uso (72 h, hash SHA-256), envía el correo asíncronamente tras el commit y permite definir la contraseña.

**Prueba independiente**: crear la cuenta de `TEN-001`, ver la invitación en el backend de correo, aceptarla con una contraseña de 12+ caracteres, verificar cuenta activa e invitación usada; reintentar el mismo token (410), reenviar (invalida el anterior) y forzar vencimiento (410).

### Pruebas de US4 (escribir primero, deben fallar)

- [ ] T055 [P] [US4] Pruebas de contrato de cuentas en `tests/contract/test_cuentas.py`: alta de cuenta de tenant `302`, `409` `"El tenant ya tiene una cuenta"`, `409` `"El correo ya está registrado"`, `400` `"El correo no es válido"`, listado paginado con correo/rol/alcance/estado
- [ ] T056 [P] [US4] Pruebas de contrato de invitación en `tests/contract/test_invitacion.py`: `GET` con token válido `200`, `POST` con contraseña válida `302` a `/login/`, `410` `"La invitación venció o ya fue usada"` para vencida/usada/revocada, `400` con mensaje del validador para contraseña débil
- [ ] T057 [P] [US4] Pruebas de integración de invitaciones en `tests/integration/test_invitaciones.py`: `enviar_invitacion` guarda solo el hash SHA-256 de 64 hex, fija `expira_en` a +72 h, revoca pendientes anteriores y registra `enviada_en` o `ultimo_error`; `aceptar_invitacion` activa la cuenta, marca `usada_en` y audita
- [ ] T058 [P] [US4] Pruebas de integración en `tests/integration/test_cuentas_almacen.py`: `crear_cuenta_almacen` crea cuenta inactiva `RESPONSABLE_ALMACEN` sin tenant con invitación y auditoría; correo duplicado rechazado
- [ ] T059 [P] [US4] Pruebas de contrato de reenvío en `tests/contract/test_reenvio_invitacion.py`: reenviar invalida el token anterior y el nuevo funciona (si no existe ruta según contrato, se cubre a nivel de servicio y se documenta la carencia)

### Implementación de US4

- [ ] T060 [P] [US4] Implementar `acceso/tokens.py` con `generar_token()` (`secrets.token_urlsafe(32)`) y `hash_token(token)` (SHA-256 hex de 64 caracteres)
- [ ] T061 [P] [US4] Implementar `CuentaTenantForm`, `CuentaAlmacenForm` e `InvitacionPasswordForm` en `acceso/forms.py` con correo válido y política de contraseña de 12 caracteres mínimo
- [ ] T062 [US4] Implementar `crear_cuenta_tenant(tenant, correo, actor)` en `acceso/services.py`: solo `ADMIN_PLATAFORMA`; verifica correo único y que el tenant no tenga cuenta (activa o desactivada); crea `is_active=False`, `rol="USUARIO_TENANT"`, `set_unusable_password()`; genera invitación y auditoría en `transaction.atomic`; traduce `IntegrityError` a `"El tenant ya tiene una cuenta"`
- [ ] T063 [US4] Implementar `crear_cuenta_almacen(region, correo, actor)` en `acceso/services.py`: crea cuenta inactiva `RESPONSABLE_ALMACEN` sin tenant, con invitación y auditoría
- [ ] T064 [US4] Implementar `enviar_invitacion(usuario, actor)` y `reenviar_invitacion(usuario, actor)` en `acceso/services.py`: revocan pendientes, crean el token, guardan solo el hash, fijan `expira_en=ahora+72h` y encolan el correo con `transaction.on_commit`
- [ ] T065 [US4] Implementar `aceptar_invitacion(token, password)` en `acceso/services.py`: busca por hash, valida vigencia/uso/revocación, valida contraseña, activa la cuenta, marca `usada_en`, guarda la contraseña y audita el evento
- [ ] T066 [US4] Implementar la tarea Celery `enviar_correo_invitacion` en `acceso/tasks.py` con reintentos, registro de `enviada_en` o `ultimo_error` (sin datos sensibles) y enlace `/invitacion/<token>/`
- [ ] T067 [US4] Implementar en `acceso/views.py` las vistas `crear_cuenta_tenant`, `crear_cuenta_almacen` y `listar_cuentas` (50 por página) protegidas con `@requiere_rol(Rol.ADMIN_PLATAFORMA)`
- [ ] T068 [US4] Implementar la vista pública `aceptar_invitacion` (`GET/POST /invitacion/<token>/`) en `acceso/views.py` con `410` uniforme para token inválido, vencido, usado o revocado
- [ ] T069 [US4] Registrar `/plataforma/tenants/<int:id>/cuenta/nueva/`, `/plataforma/cuentas/`, `/plataforma/cuentas/nueva-almacen/` e `/invitacion/<str:token>/` en `acceso/urls.py`
- [ ] T070 [US4] Crear `templates/acceso/cuenta_form.html`, `templates/acceso/cuentas_lista.html` y `templates/acceso/invitacion_form.html`, mostrando el resultado del envío y el error de correo cuando exista

**Checkpoint**: US4 funcional de forma independiente; la cuenta creada queda inactiva hasta aceptar la invitación.

---

## Fase 7: US5 — Desactivación, reactivación, suspensión y cambio de rol (P5)

**Objetivo**: el Administrador desactiva/reactiva cuentas, suspende/activa tenants y cambia el rol de cuentas administrativas; toda acción invalida sesiones e incrementa `version_sesion`, queda auditada y no elimina datos.

**Prueba independiente**: con una sesión de tenant abierta, desactivar su cuenta y comprobar que la siguiente petición se rechaza y la auditoría se conserva; reactivarla; suspender el tenant y verificar bloqueo; cambiar el rol de una cuenta de almacén y ver el rol anterior/nuevo auditado.

### Pruebas de US5 (escribir primero, deben fallar)

- [ ] T071 [P] [US5] Pruebas de contrato de acciones en `tests/contract/test_acciones_cuenta.py`: desactivar/reactivar `302` con `version_sesion++`, `404` cuenta ajena/inexistente, `405` ante `DELETE`, cambio de rol `302`, `409` `"La cuenta del tenant no cambia de rol"`, `400` `"No puedes asignar ese rol"`, `400` `"El alcance de la cuenta no es válido"`
- [ ] T072 [P] [US5] Pruebas de contrato de suspensión en `tests/contract/test_suspension_tenant.py`: suspender `302` con auditoría y sesiones invalidadas; tenant ya suspendido `200` sin auditoría nueva; `404` inexistente; ausencia de ruta de borrado
- [ ] T073 [P] [US5] Pruebas de integración en `tests/integration/test_revocacion.py`: desactivar invalida la sesión abierta y conserva historial y auditoría; cambio de rol incrementa `version_sesion` y la siguiente petición usa el rol nuevo; suspender/activar tenant bloquea y restaura la operación sin modificar datos ni stock
- [ ] T074 [P] [US5] Pruebas de integración en `tests/integration/test_cambio_rol.py`: `cambiar_rol` audita `rol` con valor anterior y nuevo; rechaza cuentas `USUARIO_TENANT`; valida coherencia de alcance; `reactivar_cuenta` sobre tenant suspendido responde `409` `"El tenant está suspendido"`
- [ ] T075 [P] [US5] Pruebas de integración en `tests/integration/test_sin_eliminacion.py`: no existe ruta de borrado para región, tenant ni cuenta y los registros con su auditoría persisten tras desactivar o suspender

### Implementación de US5

- [ ] T076 [US5] Implementar `verificar_alcance(actor, objetivo)` en `acceso/services.py` según `plan.md` §Cuentas y lanzar `"No tienes permiso para administrar esta cuenta"` cuando no aplique
- [ ] T077 [US5] Implementar `cambiar_rol(usuario, nuevo_rol, actor)` en `acceso/services.py`: solo `ADMIN_PLATAFORMA`, rechaza `USUARIO_TENANT`, valida compatibilidad de alcance, usa `select_for_update`, incrementa `version_sesion` y audita rol anterior/nuevo en la misma transacción
- [ ] T078 [US5] Implementar `desactivar_cuenta(usuario, actor)` y `reactivar_cuenta(usuario, actor)` en `acceso/services.py` con validación de alcance, `select_for_update`, incremento de `version_sesion`, auditoría de `is_active` y guarda de tenant suspendido al reactivar
- [ ] T079 [US5] Implementar `suspender_tenant(tenant, actor)` y `activar_tenant(tenant, actor)` en `tenants/services.py`: solo `ADMIN_PLATAFORMA`, cambian `estado`, invalidan la sesión de la cuenta del tenant, auditan `estado` y no tocan datos ni stock; idempotentes respecto del estado final
- [ ] T080 [US5] Implementar las vistas `desactivar_cuenta`, `reactivar_cuenta` y `cambiar_rol` en `acceso/views.py`, solo `POST` y protegidas con `@requiere_rol(Rol.ADMIN_PLATAFORMA)`
- [ ] T081 [US5] Implementar las vistas `suspender_tenant` y `activar_tenant` en `tenants/views.py`, solo `POST` y protegidas con `@requiere_rol(Rol.ADMIN_PLATAFORMA)`
- [ ] T082 [US5] Registrar `/plataforma/cuentas/<int:id>/desactivar/`, `/reactivar/` y `/rol/` en `acceso/urls.py`, y `/plataforma/tenants/<int:id>/suspender/` y `/activar/` en `tenants/urls.py`
- [ ] T083 [US5] Agregar a `templates/acceso/cuentas_lista.html` y `templates/tenants/tenant_detalle.html` los formularios `POST` con CSRF para las acciones, sin ofrecer nunca borrado

**Checkpoint**: US5 funcional; revocación inmediata verificada en sesiones abiertas.

---

## Fase 8: US6 — Aislamiento por tenant/región y auditoría consultable (P6)

**Objetivo**: ninguna cuenta ve datos de otro tenant o región (respuesta `404` sin revelar existencia); el Administrador no opera inventario; `/auditoria/acceso/` respeta el alcance de cada rol y no contiene secretos; RLS refuerza el filtrado en PostgreSQL.

**Prueba independiente**: con dos tenants activos, consultar por URL el recurso del otro tenant (404) y forzar `tenant_id` en un formulario (se ignora); con dos regiones, el Responsable de almacén solo ve su región; `/auditoria/acceso/` muestra solo registros del alcance y nunca contraseñas/tokens/secretos.

### Pruebas de US6 (escribir primero, deben fallar)

- [ ] T084 [P] [US6] Pruebas de aislamiento en `tests/integration/test_aislamiento.py`: tenant no ve datos de otro tenant (`404`), `tenant_id`/`region_id` enviados por el cliente se ignoran, Responsable de almacén no ve otra región, cuenta de tenant no puede crear cuentas (sin ruta y servicio rechaza)
- [ ] T085 [P] [US6] Pruebas de restricciones de alcance en `tests/integration/test_restricciones_usuario.py`: inserción directa con tenant y región a la vez falla; dos cuentas `USUARIO_TENANT` para el mismo tenant falla por `UniqueConstraint`; correo duplicado falla por `unique`
- [ ] T086 [P] [US6] Pruebas de concurrencia en `tests/integration/test_concurrencia.py`: dos altas simultáneas con el mismo código o correo producen una sola fila y un `IntegrityError` traducido; dos cuentas de tenant simultáneas dejan solo una
- [ ] T087 [P] [US6] Pruebas de contrato de auditoría en `tests/contract/test_auditoria.py`: `ADMIN` ve todo, `TENANT` solo su tenant, `ALMACEN` solo su región, recurso ajeno `404`, paginación y filtros `entidad`, `entidad_id`, `desde`, `hasta`, `usuario`
- [ ] T088 [P] [US6] Pruebas de inmutabilidad y secretos en `tests/integration/test_auditoria_inmutable.py`: `UPDATE` y `DELETE` sobre `auditoria_registrocambio` fallan por permisos; ningún registro contiene contraseñas, `token_hash` ni secretos TOTP; altas, cambio de rol, desactivación y suspensión generan sus filas
- [ ] T089 [P] [US6] Prueba de separación de funciones en `tests/integration/test_roles_negocio.py`: la cuenta del tenant no tiene subroles (solo `USUARIO_TENANT`) y puede ejecutar cualquier acción de su tenant; el Administrador de plataforma no tiene acceso a rutas de inventario, recojos, asignaciones, traspasos ni conciliaciones (`404`/`403`)

### Implementación de US6

- [ ] T090 [US6] Implementar en `acceso/services.py` los helpers de consulta con alcance (`cuentas_visibles_para(actor)`, `registros_visibles_para(actor)`) que deriven tenant/región de `request.usuario` y nunca de parámetros del cliente
- [ ] T091 [US6] Implementar `consultar_auditoria(actor, filtros)` en `auditoria/services.py` con filtrado de alcance, paginación de 50 y exclusión silenciosa de registros ajenos
- [ ] T092 [US6] Implementar la vista `auditoria_acceso` (`GET /auditoria/acceso/`) en `auditoria/views.py`, la ruta en `auditoria/urls.py` y su inclusión en `config/urls.py`, con `404` para consultas directas a un id ajeno
- [ ] T093 [US6] Crear `templates/auditoria/acceso_lista.html` con entidad, entidad_id, campo, valor anterior, valor nuevo, usuario y fecha, más filtros HTMX
- [ ] T094 [US6] Crear `tenants/migrations/0002_rls.py` y `acceso/migrations/0002_rls.py` con políticas RLS sobre tablas operativas usando `app.tenant_id`/`app.region_id`, y hacer que `ContextoUsuarioMiddleware` fije esas variables de sesión; el rol de aplicación no debe ser superusuario ni `BYPASSRLS`
- [ ] T095 [US6] Agregar en `auditoria/migrations/0002_permisos.py` la revocación de `UPDATE` y `DELETE` al rol de aplicación sobre la tabla de auditoría (PostgreSQL)
- [ ] T096 [US6] Revisar que ninguna vista acepte `tenant_id` ni `region_id` de formularios, URLs o archivos, y que todo acceso ajeno responda `404` sin revelar existencia

**Checkpoint**: todas las historias funcionales e independientes; aislamiento y auditoría verificados.

---

## Fase 9: Pulido y asuntos transversales

**Propósito**: cerrar calidad, seguridad y documentación sobre todas las historias.

- [ ] T097 [P] Ejecutar `pytest --cov=tenants --cov=acceso --cov=auditoria` y cerrar brechas hasta cubrir cada criterio de aceptación de `spec.md` en `tests/`
- [ ] T098 [P] Revisar la matriz de permisos de `contracts/http-endpoints.md` contra las rutas reales y corregir desviaciones en `acceso/urls.py`, `tenants/urls.py` y `auditoria/urls.py`
- [ ] T099 [P] Endurecer seguridad en `config/settings/base.py`/`prod.py`: cookies `Secure`/`HttpOnly`/`SameSite`, CSRF, `SECURE_*`, validadores de contraseña y ausencia de secretos en logs
- [ ] T100 [P] Verificar el rendimiento del middleware (overhead p95 < 50 ms) y que los listados administrativos paginen a 50 filas en `acceso/views.py`, `tenants/views.py` y `auditoria/views.py`
- [ ] T101 [P] Actualizar `README.md` con la puesta en marcha de `quickstart.md` (venv, PostgreSQL, Redis, `.env`, `migrate`, `crear_admin_plataforma`, `celery worker`, `pytest`)
- [ ] T102 Ejecutar los escenarios manuales 1–11 de `quickstart.md` contra PostgreSQL y registrar el resultado en el mismo documento
- [ ] T103 Ejecutar la suite completa sobre PostgreSQL (`pytest`) y confirmar los criterios de salida de `quickstart.md`, incluida la ausencia de secretos en auditoría y la revocación inmediata de sesiones

---

## Dependencias y orden de ejecución

### Dependencias de fase

- **Setup (Fase 1)**: sin dependencias.
- **Fundacional (Fase 2)**: depende de Setup y **bloquea todas las historias** (modelos, `AUTH_USER_MODEL`, auditoría, middleware, TOTP).
- **Historias (Fases 3–8)**: dependen de la Fase 2. US2–US6 dependen funcionalmente de US1 para la validación manual (login con 2FA), aunque sus servicios se prueban con fixtures autenticados.
- **Pulido (Fase 9)**: depende de las historias que se deseen entregar.

### Dependencias entre historias

- **US1 (P1)**: sin dependencias posteriores a la Fase 2.
- **US2 (P2)**: requiere US1 para el flujo HTTP; sus servicios y formularios son independientes.
- **US3 (P3)**: requiere US1 (y datos de región para la UI, no para el servicio).
- **US4 (P4)**: requiere US3 (tenant existente) y US1 (usuario/invitación); sus pruebas usan fixtures propios.
- **US5 (P5)**: requiere US4 para tener cuentas que desactivar/reactivar/cambiar de rol.
- **US6 (P6)**: requiere US1–US5 para auditar y filtrar datos reales.

### Dentro de cada historia

1. Pruebas primero y en rojo.
2. Modelos → formularios → servicios → vistas → rutas → plantillas.
3. La auditoría se escribe dentro de la misma transacción que el cambio.
4. No se avanza con pruebas en rojo (constitución, puerta de pruebas).

### Oportunidades de paralelización

- Setup y Fundacional: todas las tareas `[P]` de archivos distintos.
- Tras la Fase 2: US1 y US2 pueden iniciarse en paralelo; US3–US4 después de sus modelos/tenant; US5–US6 al final.
- Dentro de cada historia: las pruebas `[P]` se escriben en paralelo y los formularios/modelos de archivos distintos también.

---

## Ejemplo de paralelización: US1

```bash
# Escribir primero todas las pruebas de US1 (archivos distintos):
Task: "Pruebas de contrato /login/ en tests/contract/test_login.py"
Task: "Pruebas de contrato /login/2fa/ y /logout/ en tests/contract/test_auth_2fa.py"
Task: "Pruebas de integración de sesión en tests/integration/test_sesion.py"
Task: "Pruebas unitarias de acceso/totp.py en tests/unit/test_totp.py"
Task: "Pruebas unitarias del comando en tests/unit/test_comando_admin.py"
```

## Ejemplo de paralelización: US4

```bash
# Pruebas en paralelo:
Task: "Pruebas de contrato de cuentas en tests/contract/test_cuentas.py"
Task: "Pruebas de contrato de invitación en tests/contract/test_invitacion.py"
Task: "Pruebas de integración de invitaciones en tests/integration/test_invitaciones.py"

# Implementación paralelizable (archivos distintos):
Task: "Implementar acceso/tokens.py"
Task: "Implementar formularios en acceso/forms.py"
Task: "Implementar tarea Celery en acceso/tasks.py"
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 (Setup).
2. Completar Fase 2 (Fundacional) — **crítica**.
3. Completar Fase 3 (US1).
4. **DETENERSE y VALIDAR**: login, 2FA, logout y revocación por `version_sesion`.
5. Desplegar/demostrar si está listo.

> US1 por sí sola no entrega valor de negocio completo (no hay regiones ni tenants). Para una primera demo funcional de negocio, entregar **US1 + US2 + US3 + US4**; US5 y US6 completan la operación segura y auditable.

### Entrega incremental

1. Setup + Fundacional → base lista.
2. US1 → validar sesión y 2FA.
3. US2 → regiones y almacenes con auditoría.
4. US3 → tenants con región inmutable.
5. US4 → cuentas e invitaciones (primer flujo completo de alta de tenant).
6. US5 → desactivación, suspensión y cambio de rol con revocación inmediata.
7. US6 → aislamiento, RLS y auditoría consultable.
8. Cada historia se valida con sus pruebas y con `quickstart.md` antes de continuar.

### Estrategia de equipo en paralelo

1. Todo el equipo completa Setup + Fundacional.
2. Al terminar la Fase 2:
   - Persona A: US1 (autenticación y 2FA).
   - Persona B: US2 (regiones y almacenes, servicios y formularios).
   - Persona C: US3 (tenants, servicios y formularios).
3. Luego US4 (depende de US3) y, en paralelo, US5 sobre las cuentas ya creadas.
4. US6 al final, cuando existan datos y acciones auditables.

---

## Notas

- `[P]` significa archivos distintos y sin dependencia de tareas incompletas.
- `[Story]` traza cada tarea a su historia y a los criterios de aceptación de `spec.md`.
- Toda alta, cambio de rol, desactivación y suspensión debe dejar auditoría en la misma transacción.
- Nunca se registran contraseñas, hashes de contraseña, tokens de invitación, `token_hash` ni secretos TOTP.
- El tenant y la región se derivan de la sesión; `tenant_id`/`region_id` del cliente se ignoran o rechazan.
- No existen rutas de borrado para regiones, tenants ni cuentas.
- `contracts/http-endpoints.md` no define rutas de edición de tenant, reenvío de invitación ni alta de cuenta de almacén como pantalla propia: esas operaciones se cubren por servicio y se validan con pruebas de integración; si se requieren en la UI, actualizar primero el contrato (constitución, «documento primero»).
- Commit tras cada tarea o grupo lógico; detenerse en cada checkpoint para validar la historia de forma independiente.
- Evitar: tareas vagas, conflictos en el mismo archivo y dependencias entre historias que rompan la independencia.
