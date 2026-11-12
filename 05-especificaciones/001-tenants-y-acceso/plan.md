# Plan técnico: 001 Tenants, regiones y acceso

**Branch**: `001-tenants-y-acceso` | **Date**: 2026-11-11 | **Spec**: `05-especificaciones/001-tenants-y-acceso/spec.md`

**Input**: Spec en `05-especificaciones/001-tenants-y-acceso/spec.md`

## Summary

Implementar la base de identidad y alcance del sistema: regiones con su almacén central,
tenants con una única cuenta operativa, cuentas de Administrador de plataforma y de
Responsable de almacén, invitación por correo, autenticación de dos factores y auditoría
inmutable. El diseño usa un modelo de usuario personalizado con rol y referencias opcionales
a tenant o región, aislamiento derivado de la sesión (nunca del cliente), revocación
inmediata mediante versión de sesión y restricciones de base de datos como fuente de verdad
ante altas concurrentes.

## Technical Context

**Language/Version**: Python 3.12+ (fijado por la constitución y ADR-015)

**Primary Dependencies**: Django LTS 5.x, HTMX, Celery con Redis, `pyotp` (TOTP) y
`cryptography` (cifrado del secreto TOTP). Dependencias adicionales justificadas en
`research.md`.

**Storage**: PostgreSQL 16+ con seguridad por fila (RLS) como respaldo del filtrado de
aplicación; Redis como broker de Celery.

**Testing**: pytest, pytest-django y pruebas de integración contra PostgreSQL (sin SQLite
para RLS y restricciones condicionales).

**Target Platform**: servidor Linux (Gunicorn + Nginx), aplicación web server-rendered con
HTMX; desarrollo local en Windows o Linux.

**Project Type**: aplicación web monolítica modular Django (un solo despliegue y worker
separado).

**Performance Goals**: overhead del middleware de contexto menor a 50 ms p95 por petición;
listados administrativos paginados (50 filas); envío de invitaciones asíncrono para no
bloquear el alta.

**Constraints**: aislamiento multitenant no negociable; tenant y región solo desde la sesión;
revocación de sesiones inmediata; auditoría de solo inserción; segundo factor obligatorio
para Administrador de plataforma y Responsable de almacén; sin eliminación física de
regiones, tenants ni cuentas.

**Scale/Scope**: ~100 tenants con una cuenta cada uno; 3 roles; 16 rutas HTTP; 6 entidades
(`Region`, `Almacen`, `Tenant`, `Usuario`, `Invitacion`, `RegistroCambio`).

## Constitution Check

*GATE: verificado antes de la Fase 0 y re-evaluado después de la Fase 1.*

| Principio | Resultado | Evidencia / decisión |
|---|---|---|
| I. Aislamiento multitenant (NO NEGOCIABLE) | PASA | Tenant y región salen de `request.usuario`; middleware y servicios revalidan alcance; RLS en PostgreSQL; acceso ajeno se trata como inexistente |
| II. Jerarquía Región → Tenant → Técnico | PASA | `Region → Almacen` 1:1; `Tenant → Region` obligatoria; una cuenta por tenant; Responsable de almacén con una región; Administrador sin tenant ni región |
| III. Invariantes de stock | N/A | Esta spec no modifica stock |
| IV. Identidad y unicidad de series | N/A | Esta spec no gestiona series |
| V. Integridad transaccional | PASA | Altas, invitaciones, auditoría, cambios de rol y suspensiones en `transaction.atomic`; correo después del commit |
| VI. Auditoría inmutable y trazabilidad | PASA | `RegistroCambio` de solo inserción, en la misma transacción; nunca guarda contraseñas, tokens ni secretos |
| VII. Autoridad del reporte de Lari | N/A | Esta spec no procesa conciliaciones |
| VIII. Spec-driven, pruebas y simplicidad | PASA | Cada criterio de aceptación tiene prueba; se usan las dependencias del stack y solo dos adicionales justificadas |

Sin violaciones que justificar. `Complexity Tracking` queda vacío.

## Project Structure

### Documentation (this feature)

```text
05-especificaciones/001-tenants-y-acceso/
├── plan.md              # Este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   ├── http-endpoints.md
│   └── auditoria-registro.md
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

```text
manage.py
config/
├── settings/
│   ├── base.py
│   ├── dev.py
│   ├── prod.py
│   └── test.py
├── urls.py
├── celery.py
└── wsgi.py

tenants/
├── models.py            # Region, Almacen, Tenant
├── services.py
├── forms.py
├── views.py
├── urls.py
├── admin.py
└── migrations/

acceso/
├── models.py            # Usuario, Invitacion
├── managers.py
├── services.py
├── authentication.py
├── middleware.py
├── forms.py
├── views.py
├── urls.py
├── management/commands/crear_admin_plataforma.py
└── migrations/

auditoria/
├── models.py            # RegistroCambio
├── services.py
├── views.py
├── urls.py
└── migrations/

templates/
├── acceso/
├── tenants/
├── auditoria/
└── base.html

static/
tests/
├── unit/
├── integration/
└── contract/
```

**Structure Decision**: proyecto Django único en la raíz del repositorio. Cada spec futura
agrega su propia app (`catalogo`, `tecnicos`, etc.) sin cambiar el despliegue. `config/`
concentra settings, URLs y Celery; las reglas de negocio viven en `services.py` de cada app,
nunca en las vistas. `tests/` se separa por tipo para que las pruebas de contrato HTTP y las
de integración con PostgreSQL sean explícitas.

## Referencias
- Spec: `05-especificaciones/001-tenants-y-acceso/spec.md`
- Reglas: `03-reglas-de-dominio/regiones-y-tenants.md`, `auditoria.md`
- ADR: ADR-002, ADR-003, ADR-007, ADR-008, ADR-014, ADR-015, ADR-019
- Stack: Django LTS, PostgreSQL, HTMX y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `tenants`: modelos `Region`, `Almacen` y `Tenant`.
- App Django nueva `acceso`: modelo de usuario `Usuario`, `Invitacion` y vistas de autenticación.
- App `auditoria`: modelo `RegistroCambio`, compartido. Si no existe, se crea aquí.
- Middleware de contexto de tenant, región y sesión.
- No se modifican módulos de inventario, catálogo, recojos ni conciliación.

## Modelo de datos

### App `tenants`

```python
class Region(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(codigo=""),
                name="region_codigo_obligatorio",
            ),
        ]
```

```python
class Almacen(models.Model):
    region = models.OneToOneField(Region, on_delete=models.PROTECT, related_name="almacen")
    centro = models.CharField(max_length=20)          # parámetro de la región
    codigo_almacen = models.CharField(max_length=20)   # parámetro de la región
    buzon = models.EmailField()
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(centro="") & ~Q(codigo_almacen=""),
                name="almacen_parametros_obligatorios",
            ),
        ]
```

```python
class Tenant(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="tenants")
    estado = models.CharField(
        max_length=10,
        choices=[("ACTIVO", "Activo"), ("SUSPENDIDO", "Suspendido")],
        default="ACTIVO",
    )
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+"
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(codigo=""),
                name="tenant_codigo_obligatorio",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=["ACTIVO", "SUSPENDIDO"]),
                name="tenant_estado_valido",
            ),
        ]
        indexes = [
            models.Index(fields=["region", "estado"], name="tenant_region_estado"),
        ]

    def tiene_cuenta_activa(self):
        return self.usuarios.filter(
            rol="USUARIO_TENANT",
            is_active=True,
        ).exists()
```

- La región del tenant no se expone en el formulario de edición.
- El servicio rechaza cualquier intento de cambiar `region` después de creado.
- Centro y Almacén se precargan desde configuración (`PR05` y `BE03`), pero se guardan por región.
- `Tenant.tiene_cuenta_activa()` determina si el tenant puede operar.

### App `acceso`

```python
class Rol(models.TextChoices):
    ADMIN_PLATAFORMA = "ADMIN_PLATAFORMA", "Administrador de plataforma"
    USUARIO_TENANT = "USUARIO_TENANT", "Cuenta del tenant"
    RESPONSABLE_ALMACEN = "RESPONSABLE_ALMACEN", "Responsable de almacén"


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El correo es obligatorio")
        extra_fields.setdefault("is_active", False)
        usuario = self.model(email=self.normalize_email(email), **extra_fields)
        if password is None:
            usuario.set_unusable_password()
        else:
            usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario
```

```python
class Usuario(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=30, choices=Rol.choices)
    tenant = models.ForeignKey(
        "tenants.Tenant", null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios"
    )
    region = models.ForeignKey(
        "tenants.Region", null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios"
    )
    version_sesion = models.PositiveIntegerField(default=0)
    secreto_totp = models.CharField(max_length=64, blank=True)
    segundo_factor_habilitado = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UsuarioManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(rol=Rol.ADMIN_PLATAFORMA, tenant__isnull=True, region__isnull=True)
                    | Q(rol=Rol.USUARIO_TENANT, tenant__isnull=False, region__isnull=True)
                    | Q(rol=Rol.RESPONSABLE_ALMACEN, tenant__isnull=True, region__isnull=False)
                ),
                name="usuario_alcance_coherente",
            ),
            models.UniqueConstraint(
                fields=["tenant"],
                condition=Q(rol=Rol.USUARIO_TENANT),
                name="un_usuario_tenant_por_tenant",
            ),
        ]
```

- La restricción `un_usuario_tenant_por_tenant` garantiza una sola cuenta por tenant, incluso si se intenta crear otra desde fuera de la interfaz.
- La cuenta del tenant no tiene subcuentas ni roles internos.
- Las cuentas de Administrador de plataforma y de Responsable de almacén no tienen tenant.

```python
class Invitacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="invitaciones")
    token_hash = models.CharField(max_length=64, unique=True)
    correo = models.EmailField()
    expira_en = models.DateTimeField()
    enviada_en = models.DateTimeField(null=True, blank=True)
    usada_en = models.DateTimeField(null=True, blank=True)
    revocada_en = models.DateTimeField(null=True, blank=True)
    ultimo_error = models.TextField(blank=True)
    creada_por = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="+")
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["usuario", "usada_en", "revocada_en"], name="invitacion_vigente"),
        ]
```

- `token_hash` guarda el hash del token; el token original solo viaja en el correo.
- Una cuenta nueva se crea con `is_active=False` hasta aceptar la invitación.
- `version_sesion` se incrementa al cambiar rol, desactivar la cuenta o suspender el tenant.

### App `auditoria`

```python
class RegistroCambio(models.Model):
    entidad = models.CharField(max_length=50)      # Region, Almacen, Tenant, Usuario, Invitacion
    entidad_id = models.BigIntegerField()
    campo = models.CharField(max_length=50)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    fecha = models.DateTimeField(auto_now_add=True)
```

- Solo inserción. No se actualizan ni se borran filas.
- Nunca se guardan contraseñas, tokens ni secretos de segundo factor.
- Los valores anteriores y nuevos se guardan como texto.

## Migraciones
- `tenants/migrations/0001_initial.py`: `Region`, `Almacen` y `Tenant`, con índices y restricciones.
- `acceso/migrations/0001_initial.py`: `Usuario` e `Invitacion`, con la restricción de una cuenta por tenant.
- `auditoria/migrations/0001_initial.py`: `RegistroCambio`, si la app no existe.
- `AUTH_USER_MODEL = "acceso.Usuario"` debe configurarse **antes** de la primera migración.
- No se crean credenciales ni administradores por migración.
- Comando de arranque `crear_admin_plataforma`: crea la primera cuenta de Administrador de plataforma con rol explícito, sin superusuario de Django ni de base de datos.
- Ninguna migración modifica datos de tenants existentes.

## Servicios (lógica de negocio)
Viven en `tenants/services.py` y `acceso/services.py`, no en las vistas.

### Regiones y tenants
- `crear_region(datos, actor)`:
  - Verifica que el actor sea Administrador de plataforma.
  - Valida código único, nombre, Centro, Almacén y buzón.
  - En `transaction.atomic`, crea la región, su almacén y la auditoría.
- `actualizar_region(region, datos, actor)`:
  - Solo Administrador de plataforma.
  - Audita cada campo modificado.
- `crear_tenant(datos, actor)`:
  - Solo Administrador de plataforma.
  - Verifica región activa y código único.
  - En `transaction.atomic`, crea el tenant y la auditoría.
- `suspender_tenant(tenant, actor)`:
  - Solo Administrador de plataforma.
  - Cambia el estado a Suspendido, invalida las sesiones de su cuenta y audita.
  - No modifica datos ni stock.
- `activar_tenant(tenant, actor)`:
  - Solo Administrador de plataforma.
  - Cambia el estado a Activo y audita.

### Cuentas
- Toda cuenta nueva se crea con contraseña inutilizable (`set_unusable_password`) y `is_active=False` hasta aceptar la invitación.
- `crear_cuenta_tenant(tenant, correo, actor)`:
  - Solo Administrador de plataforma.
  - Verifica correo único y que el tenant no tenga ya una cuenta, activa o desactivada.
  - Crea la cuenta inactiva con rol `USUARIO_TENANT` y su tenant.
  - Genera y envía la invitación.
  - Audita el alta.
  - Si el tenant ya tiene cuenta, devuelve “El tenant ya tiene una cuenta”; no crea subcuentas.
- `crear_cuenta_almacen(region, correo, actor)`:
  - Solo Administrador de plataforma.
  - Crea la cuenta inactiva con rol `RESPONSABLE_ALMACEN`, sin tenant.
  - Genera la invitación y audita.
- `cambiar_rol(usuario, nuevo_rol, actor)`:
  - Solo Administrador de plataforma.
  - Rechaza el cambio de rol de una cuenta de tenant; esa cuenta solo se desactiva o reactiva.
  - Valida que el nuevo rol sea compatible con el alcance.
  - Incrementa `version_sesion` y audita el rol anterior y el nuevo.
- `desactivar_cuenta(usuario, actor)`:
  - Valida alcance del actor.
  - Marca `is_active=False`, incrementa `version_sesion` y audita.
- `reactivar_cuenta(usuario, actor)`:
  - Solo Administrador de plataforma.
  - Reactiva, incrementa `version_sesion` y audita.
- `verificar_alcance(actor, objetivo)`:
  - Administrador de plataforma: cualquier cuenta administrativa.
  - Cuenta del tenant: no administra cuentas.
  - Responsable de almacén: no administra cuentas de tenant.
  - Un usuario común no administra cuentas.

### Invitaciones y autenticación
- `enviar_invitacion(usuario, actor)`:
  - Revoca invitaciones pendientes anteriores.
  - Genera un token aleatorio, guarda solo su hash y fija `expira_en = ahora + 72 h`.
  - Envía el correo mediante una tarea con reintentos.
  - Registra `enviada_en` o `ultimo_error`.
- `aceptar_invitacion(token, password)`:
  - Busca por hash, verifica vigencia, que no esté usada ni revocada.
  - Valida la política de contraseña.
  - Activa la cuenta, guarda la contraseña, marca la invitación como usada y audita.
- `iniciar_sesion(correo, password)`:
  - Rechaza cuentas inactivas y tenants suspendidos.
  - Si el rol exige segundo factor, deja la sesión en estado pendiente.
- `verificar_segundo_factor(usuario, codigo)`:
  - Valida el código TOTP.
  - Solo entonces abre la sesión definitiva.
- `renovar_version_sesion(usuario)`:
  - Incrementa el contador para invalidar sesiones abiertas.

## Permisos y middleware
- `ContextoUsuarioMiddleware`:
  - Se ejecuta después de la autenticación.
  - Rechaza cuentas inactivas, tenants suspendidos y versiones de sesión desactualizadas.
  - Verifica que la cuenta del tenant esté activa antes de operar.
  - Publica `request.usuario`, `request.rol`, `request.tenant` y `request.region`.
  - Para `USUARIO_TENANT`, `request.tenant = usuario.tenant`.
  - Para `RESPONSABLE_ALMACEN`, `request.region = usuario.region`.
  - Para Administrador de plataforma, no hay tenant ni región.
- Decoradores:
  - `@requiere_rol(*roles)`
  - `@requiere_tenant`
  - `@requiere_region`
- Los servicios vuelven a validar el alcance; nunca se confía solo en la vista.
- `UsuarioManager.para_tenant(tenant)` y `para_region(region)` para consultas.
- No se acepta `tenant_id` ni `region_id` desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado de aplicación.

## Autenticación y segundo factor
- Inicio de sesión con correo y contraseña.
- Cuentas nuevas: `is_active=False` hasta aceptar la invitación.
- Invitación:
  - Token aleatorio de alta entropía.
  - Solo se guarda el hash.
  - Vence a las 72 horas.
  - Un solo uso.
  - Reenviar invalida la anterior.
- Segundo factor:
  - Obligatorio para Administrador de plataforma y Responsable de almacén.
  - TOTP con secreto por usuario.
  - El secreto se guarda cifrado o en un campo protegido; nunca en texto plano en la auditoría.
  - Sin segundo factor válido no se abre la sesión.
- Revocación:
  - `version_sesion` se incrementa al cambiar rol, desactivar cuenta o suspender tenant.
  - El middleware compara la versión de la sesión con la de la base de datos.
  - Si no coincide, cierra la sesión.
- Recuperación de contraseña y de segundo factor: fuera de alcance.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/login/` | GET / POST | Inicio de sesión con correo y contraseña |
| `/login/2fa/` | GET / POST | Verificación del segundo factor |
| `/logout/` | POST | Cierre de sesión |
| `/invitacion/<token>/` | GET / POST | Definir contraseña desde la invitación |
| `/plataforma/regiones/` | GET | Listado de regiones |
| `/plataforma/regiones/nueva/` | GET / POST | Alta de región y almacén |
| `/plataforma/regiones/<id>/editar/` | GET / POST | Edición de región y almacén |
| `/plataforma/tenants/` | GET | Listado de tenants |
| `/plataforma/tenants/nuevo/` | GET / POST | Alta de tenant |
| `/plataforma/tenants/<id>/` | GET | Detalle del tenant y su cuenta |
| `/plataforma/tenants/<id>/cuenta/nueva/` | GET / POST | Crear la cuenta única del tenant |
| `/plataforma/tenants/<id>/suspender/` | POST | Suspender tenant |
| `/plataforma/cuentas/` | GET | Listado de cuentas |
| `/plataforma/cuentas/<id>/desactivar/` | POST | Desactivar cuenta |
| `/plataforma/cuentas/<id>/reactivar/` | POST | Reactivar cuenta |
| `/plataforma/cuentas/<id>/rol/` | POST | Cambiar rol administrativo |
| `/auditoria/acceso/` | GET | Consulta de altas, cambios y desactivaciones |

### Pantallas
- **Administrador de plataforma:** regiones, tenants, cuenta única del tenant, cuentas de almacén y auditoría de acceso.
- **Cuenta del tenant:** todas las funciones del tenant, sin pantalla de gestión de usuarios.
- **Responsable de almacén:** solo su perfil y su región; no administra cuentas.
- **Invitación:** formulario de contraseña con token.
- **Segundo factor:** verificación y configuración inicial.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Código de región único | Servicio y restricción única | “El código de región ya existe” |
| Código de tenant único | Servicio y restricción única | “El código de tenant ya existe” |
| Tenant con región | Formulario, servicio y FK obligatoria | “El tenant debe pertenecer a una región” |
| Región inmutable | Formulario y servicio | “La región del tenant no se puede cambiar” |
| Una cuenta por tenant | Servicio y restricción única | “El tenant ya tiene una cuenta” |
| Correo único | Formulario, servicio y restricción única | “El correo ya está registrado” |
| Alcance coherente | Servicio y `CheckConstraint` | “El alcance de la cuenta no es válido” |
| Rol permitido | Servicio | “No puedes asignar ese rol” |
| Rol de cuenta del tenant inmutable | Servicio | “La cuenta del tenant no cambia de rol” |
| Invitación vigente | Servicio | “La invitación venció o ya fue usada” |
| Segundo factor | Servicio de autenticación | “Debes completar el segundo factor” |
| Cuenta activa | Middleware y servicio | “La cuenta está desactivada” |
| Tenant activo | Middleware y servicio | “El tenant está suspendido” |
| Permiso de administración | Servicio y decorador | “No tienes permiso para administrar esta cuenta” |
| Buzón válido | Formulario | “El buzón no es válido” |
| Centro y Almacén obligatorios | Formulario y `CheckConstraint` | “Centro y Almacén son obligatorios” |

## Transacciones y concurrencia
- El alta de región y almacén se ejecuta en una sola transacción.
- El alta de tenant y su auditoría se ejecutan en una sola transacción.
- El alta de cuenta, la invitación y la auditoría se ejecutan en una sola transacción; el envío de correo se hace después del commit.
- Las restricciones únicas de la base de datos resuelven dos altas simultáneas con el mismo código o correo.
- La restricción de una cuenta por tenant resuelve dos altas simultáneas de cuenta para el mismo tenant.
- El cambio de rol, la desactivación y la suspensión se ejecutan en transacción e incrementan `version_sesion` para invalidar sesiones.
- Los reenvíos de invitación revocan la anterior dentro de la misma transacción.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_crear_region_con_almacen_valido`
- `test_codigo_de_region_duplicado_se_rechaza`
- `test_tenant_sin_region_se_rechaza`
- `test_region_de_tenant_no_se_puede_cambiar`
- `test_tenant_sin_cuenta_activa_no_opera`
- `test_admin_plataforma_crea_cuenta_unica_de_tenant_y_envia_invitacion`
- `test_segunda_cuenta_de_tenant_se_rechaza`
- `test_tenant_no_puede_crear_subcuentas`
- `test_cuenta_de_tenant_puede_cargar_y_aprobar_conciliacion`
- `test_invitacion_vencida_usada_o_revocada_se_rechaza`
- `test_reenvio_de_invitacion_invalida_la_anterior`
- `test_usuario_de_tenant_no_ve_datos_de_otro_tenant`
- `test_responsable_almacen_no_ve_otra_region`
- `test_admin_plataforma_no_opera_inventario_ni_aprueba_conciliacion`
- `test_desactivar_cuenta_invalida_sesion_y_conserva_historial`
- `test_suspender_tenant_bloquea_operaciones_y_conserva_datos`
- `test_admin_y_almacen_requieren_segundo_factor`
- `test_cambio_de_rol_audita_valor_anterior_y_nuevo`
- `test_cuenta_de_tenant_no_cambia_de_rol`
- `test_correo_duplicado_se_rechaza`
- `test_cuenta_con_tenant_y_region_se_rechaza`
- `test_no_se_eliminan_regiones_tenants_ni_cuentas`
- `test_altas_simultaneas_con_mismo_codigo_fallan_por_restriccion_unica`
- `test_reactivacion_de_cuenta_de_tenant_restaura_operacion`

Además, pruebas de base de datos:
- Insertar una cuenta con tenant y región directamente debe fallar.
- Insertar dos regiones o tenants con el mismo código directamente debe fallar.
- Insertar dos cuentas con el mismo correo directamente debe fallar.
- Insertar dos cuentas de tenant para el mismo tenant directamente debe fallar.

## Decisiones y riesgos
- **Modelo de usuario personalizado:** debe definirse antes de la primera migración. Si el proyecto ya tuviera un usuario estándar, se requiere una migración compleja; en este repositorio todavía no hay código, así que se crea desde cero.
- **Una sola cuenta por tenant:** se refuerza con una restricción única condicional. No existen subcuentas ni roles Operador/Aprobador/Responsable del tenant.
- **Sin separación de funciones internas:** la misma cuenta del tenant carga y aprueba sus conciliaciones. Es una decisión de negocio confirmada; la auditoría registra qué cuenta hizo cada acción.
- **Credencial compartida:** si varias personas del tenant usan la misma cuenta, comparten usuario y contraseña. Se recomienda una contraseña fuerte y auditoría; una funcionalidad futura podría permitir cuentas adicionales con el mismo alcance.
- **RF-05, RF-51, RF-55 y RES-18:** se interpretan como alta centralizada. ACT-02 crea la cuenta única del tenant y las cuentas de Almacén; el tenant no crea cuentas.
- **Región inmutable:** se asume que un tenant no cambia de región. Si el negocio lo requiere, se define un flujo de traslado con validación de stock y auditoría.
- **Invitación por correo:** el envío puede fallar. Se registra el error y se permite reenviar; el alta no depende del éxito inmediato del correo.
- **Segundo factor:** se implementa con TOTP. La recuperación de códigos queda fuera de alcance y se resuelve desactivando la cuenta y creando otra.
- **Revocación inmediata:** se usa `version_sesion` porque la cookie de sesión de Django no invalida por sí sola las sesiones abiertas.
- **Suspensión de tenant:** bloquea el acceso y las operaciones, pero no borra ni modifica datos. El stock se conserva.
- **Sin eliminación:** no se borran regiones, tenants ni cuentas; se desactivan o suspenden. Esto preserva la trazabilidad.
- **Concurrencia:** las restricciones únicas de la base de datos son la fuente de verdad ante altas simultáneas.

## Complexity Tracking

> Sin violaciones a la constitución. La complejidad añadida está cubierta por el stack y las
> ADR vigentes: modelo de usuario personalizado (ADR-019) y versión de sesión para revocación
> inmediata (ADR-008, ADR-019). Las dos dependencias adicionales (`pyotp` y `cryptography`)
> se justifican en `research.md`.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Ninguna | — | — |

## Artefactos de diseño

| Artefacto | Contenido |
|---|---|
| `research.md` | Decisiones técnicas y alternativas: usuario personalizado, TOTP, invitaciones, revocación de sesión, RLS, correo asíncrono y concurrencia |
| `data-model.md` | Entidades, campos, relaciones, restricciones, índices y transiciones de estado |
| `contracts/http-endpoints.md` | Contrato de las rutas, roles, peticiones, respuestas y errores |
| `contracts/auditoria-registro.md` | Contrato del registro de auditoría y datos que nunca se almacenan |
| `quickstart.md` | Escenarios ejecutables de validación extremo a extremo |
