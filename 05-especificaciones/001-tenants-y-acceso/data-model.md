# Modelo de datos: 001 Tenants, regiones y acceso

**Fase**: 1 | **Fecha**: 2026-11-11 | **Spec**: `05-especificaciones/001-tenants-y-acceso/spec.md`

Este documento describe las entidades, campos, relaciones, restricciones y transiciones de
estado. El detalle de implementación (métodos y firmas) vive en `plan.md`; los contratos HTTP
viven en `contracts/`.

## Diagrama de relaciones

```mermaid
erDiagram
    REGION ||--|| ALMACEN : "tiene un almacén central"
    REGION ||--o{ TENANT : "agrupa"
    REGION ||--o{ USUARIO : "alcance de almacén"
    TENANT ||--o| USUARIO : "una sola cuenta operativa"
    USUARIO ||--o{ INVITACION : "recibe"
    USUARIO ||--o{ REGISTRO_CAMBIO : "autor de la acción"

    REGION {
        bigint id PK
        varchar codigo UK
        varchar nombre
        boolean activa
        bigint creado_por FK
        datetime creado_en
        bigint actualizado_por FK
        datetime actualizado_en
    }
    ALMACEN {
        bigint id PK
        bigint region_id FK UK
        varchar centro
        varchar codigo_almacen
        varchar buzon
        boolean activo
        bigint creado_por FK
        datetime creado_en
        bigint actualizado_por FK
        datetime actualizado_en
    }
    TENANT {
        bigint id PK
        varchar codigo UK
        varchar nombre
        bigint region_id FK
        varchar estado
        bigint creado_por FK
        datetime creado_en
        bigint actualizado_por FK
        datetime actualizado_en
    }
    USUARIO {
        bigint id PK
        varchar email UK
        varchar password
        varchar rol
        bigint tenant_id FK "nullable, único por rol"
        bigint region_id FK "nullable"
        boolean is_active
        int version_sesion
        varchar secreto_totp
        boolean segundo_factor_habilitado
        datetime date_joined
        datetime last_login
    }
    INVITACION {
        bigint id PK
        bigint usuario_id FK
        varchar token_hash UK
        varchar correo
        datetime expira_en
        datetime enviada_en
        datetime usada_en
        datetime revocada_en
        text ultimo_error
        bigint creada_por FK
        datetime creada_en
    }
    REGISTRO_CAMBIO {
        bigint id PK
        bigint tenant_id FK "nullable; nulo para acciones globales"
        varchar entidad
        bigint entidad_id
        varchar campo
        text valor_anterior
        text valor_nuevo
        bigint usuario_id FK
        datetime fecha
    }
```

## Clasificación de tablas

| Tabla | Tipo | Aislamiento |
|---|---|---|
| `tenants.Region` | Global administrativa | Solo Administrador de plataforma |
| `tenants.Almacen` | Global administrativa | Ligada 1:1 a una región |
| `tenants.Tenant` | Operativa | Filtrada por el tenant de la sesión |
| `acceso.Usuario` | Global de identidad | El usuario ve su propia cuenta; el Administrador administra |
| `acceso.Invitacion` | Identidad | Ligada al usuario y su alcance |
| `auditoria.RegistroCambio` | Global de auditoría | Consulta según alcance de la entidad auditada |

## Entidades

### Region (`tenants.Region`)

Agrupación de tenants que comparten un almacén central.

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `codigo` | `CharField(20)` | No | Único global; 1–20 caracteres alfanuméricos; no vacío |
| `nombre` | `CharField(100)` | No | No vacío |
| `activa` | `BooleanField` | No | Por defecto `True`; una región inactiva no admite tenants nuevos |
| `creado_por` | FK `Usuario` | No | `PROTECT`, `related_name="+"` |
| `creado_en` | `DateTimeField` | No | `auto_now_add` |
| `actualizado_por` | FK `Usuario` | Sí | `PROTECT`, `related_name="+"` |
| `actualizado_en` | `DateTimeField` | No | `auto_now` |

**Restricciones**
- `unique(codigo)`.
- `CheckConstraint(region_codigo_obligatorio)`: `codigo <> ''`.

**Relaciones**
- 1:1 con `Almacen` (obligatorio para operar).
- 1:N con `Tenant`.
- 1:N con `Usuario` de rol `RESPONSABLE_ALMACEN`.

**Validaciones de servicio**: código único, nombre obligatorio, buzón válido, Centro y
Almacén obligatorios. Toda alta y cambio se audita campo por campo.

---

### Almacen (`tenants.Almacen`)

Almacén central de una región.

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `region` | `OneToOneField(Region)` | No | `PROTECT`, `related_name="almacen"` |
| `centro` | `CharField(20)` | No | Parámetro configurable; precargado `PR05` |
| `codigo_almacen` | `CharField(20)` | No | Parámetro configurable; precargado `BE03` |
| `buzon` | `EmailField` | No | Correo válido |
| `activo` | `BooleanField` | No | Por defecto `True` |
| `creado_por` / `creado_en` / `actualizado_por` / `actualizado_en` | Auditoría básica | — | Igual que `Region` |

**Restricciones**
- `unique(region)` por la relación 1:1.
- `CheckConstraint(almacen_parametros_obligatorios)`: `centro <> '' AND codigo_almacen <> ''`.

**Validaciones**: buzón con formato válido; Centro y Almacén obligatorios. Se crea y edita en
la misma transacción que su región.

---

### Tenant (`tenants.Tenant`)

Subcontratista que opera sobre una sola región.

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `codigo` | `CharField(20)` | No | Único global; 1–20 caracteres alfanuméricos |
| `nombre` | `CharField(100)` | No | No vacío |
| `region` | FK `Region` | No | `PROTECT`, `related_name="tenants"`; inmutable tras el alta |
| `estado` | `CharField(10)` | No | `ACTIVO` o `SUSPENDIDO`; por defecto `ACTIVO` |
| `creado_por` / `creado_en` / `actualizado_por` / `actualizado_en` | Auditoría básica | — | Igual que `Region` |

**Restricciones**
- `unique(codigo)`.
- `CheckConstraint(tenant_codigo_obligatorio)`: `codigo <> ''`.
- `CheckConstraint(tenant_estado_valido)`: `estado IN ('ACTIVO', 'SUSPENDIDO')`.
- `Index(region, estado)`.

**Relaciones**
- N:1 con `Region` (obligatoria).
- 1:0..1 con `Usuario` de rol `USUARIO_TENANT` (unicidad condicional).

**Transiciones de estado**

```text
ACTIVO ── suspender_tenant (Admin) ──▶ SUSPENDIDO
SUSPENDIDO ── activar_tenant (Admin) ──▶ ACTIVO
```

- La suspensión bloquea el acceso y las operaciones, conserva datos y stock e incrementa
  `version_sesion` de la cuenta del tenant.
- Un tenant queda creado en `ACTIVO`, pero **no opera** hasta que su cuenta esté activa.
- No existe transición a eliminado.

**Reglas de negocio**
- La región se define al crear y no se puede cambiar.
- Un tenant no opera sin una cuenta activa (`tiene_cuenta_activa()`).
- No se elimina; solo se suspende.

---

### Usuario (`acceso.Usuario`)

Identidad de acceso con un rol y un alcance.

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `email` | `EmailField` | No | Único global; `USERNAME_FIELD` |
| `password` | `CharField(128)` | No | Hash de Django; inutilizable hasta aceptar invitación |
| `rol` | `CharField(30)` | No | `ADMIN_PLATAFORMA`, `USUARIO_TENANT`, `RESPONSABLE_ALMACEN` |
| `tenant` | FK `Tenant` | Sí | `PROTECT`, `related_name="usuarios"`; solo para `USUARIO_TENANT` |
| `region` | FK `Region` | Sí | `PROTECT`, `related_name="usuarios"`; solo para `RESPONSABLE_ALMACEN` |
| `is_active` | `BooleanField` | No | `False` hasta aceptar la invitación |
| `version_sesion` | `PositiveIntegerField` | No | Por defecto `0`; se incrementa al revocar sesiones |
| `secreto_totp` | `CharField(64)` | Sí | Secreto TOTP cifrado; nunca en auditoría |
| `segundo_factor_habilitado` | `BooleanField` | No | Por defecto `False` |
| `date_joined` | `DateTimeField` | No | Heredado de `AbstractUser` |
| `last_login` | `DateTimeField` | Sí | Heredado de `AbstractUser` |

**Restricciones**
- `unique(email)`.
- `CheckConstraint(usuario_alcance_coherente)`:
  - `ADMIN_PLATAFORMA` ⇒ `tenant IS NULL AND region IS NULL`.
  - `USUARIO_TENANT` ⇒ `tenant IS NOT NULL AND region IS NULL`.
  - `RESPONSABLE_ALMACEN` ⇒ `tenant IS NULL AND region IS NOT NULL`.
- `UniqueConstraint(tenant)` con condición `rol = 'USUARIO_TENANT'`
  (`un_usuario_tenant_por_tenant`).

**Transiciones de estado**

```text
inactiva (is_active=False) ── aceptar_invitacion ──▶ activa (is_active=True)
activa ── desactivar_cuenta (Admin) ──▶ inactiva
inactiva ── reactivar_cuenta (Admin) ──▶ activa
```

- Cambiar de rol, desactivar o suspender el tenant incrementa `version_sesion`.
- La cuenta del tenant no cambia de rol; solo se desactiva o reactiva.
- No existe eliminación de cuentas.

**Reglas de negocio**
- El correo es único y es el identificador de inicio de sesión.
- Una cuenta pertenece a un tenant, a una región o a ninguno, nunca a ambos.
- La cuenta del tenant es única por tenant.
- Segundo factor obligatorio para `ADMIN_PLATAFORMA` y `RESPONSABLE_ALMACEN`.
- El Administrador de plataforma no tiene tenant ni región y no opera inventario.

---

### Invitacion (`acceso.Invitacion`)

Invitación de un solo uso para definir la contraseña.

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `usuario` | FK `Usuario` | No | `CASCADE`, `related_name="invitaciones"` |
| `token_hash` | `CharField(64)` | No | Único; SHA-256 hex del token |
| `correo` | `EmailField` | No | Copia del correo al momento del envío |
| `expira_en` | `DateTimeField` | No | `ahora + 72 h` |
| `enviada_en` | `DateTimeField` | Sí | Se completa al enviar |
| `usada_en` | `DateTimeField` | Sí | Se completa al aceptar |
| `revocada_en` | `DateTimeField` | Sí | Se completa al reenviar o revocar |
| `ultimo_error` | `TextField` | Sí | Error de envío, sin datos sensibles |
| `creada_por` | FK `Usuario` | No | `PROTECT`, `related_name="+"` |
| `creada_en` | `DateTimeField` | No | `auto_now_add` |

**Restricciones**
- `unique(token_hash)`.
- `Index(usuario, usada_en, revocada_en)` (`invitacion_vigente`).

**Transiciones de estado**

```text
creada ── enviar ──▶ enviada
enviada ── aceptar_invitacion ──▶ usada
enviada ── reenviar / revocar ──▶ revocada
enviada ── vencer (expira_en < ahora) ──▶ vencida (estado derivado)
enviada ── fallo de correo ──▶ pendiente con ultimo_error (reintentable)
```

- Una invitación usada, revocada o vencida no permite definir contraseña.
- Reenviar invalida las invitaciones pendientes anteriores.
- No se envía a un correo que ya pertenece a otra cuenta.

---

### RegistroCambio (`auditoria.RegistroCambio`)

Libro de auditoría de solo inserción.

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| `id` | `BigAutoField` | No | Clave primaria |
| `tenant` | FK `Tenant` | Sí | `PROTECT`, `related_name="registros_cambio"`; nulo para acciones globales de plataforma |
| `entidad` | `CharField(50)` | No | Nombre de la entidad auditada (`Region`, `Tenant`, `SolicitudAsignacion`, `Serie`, `Conciliacion`, etc.) |
| `entidad_id` | `BigIntegerField` | No | Identificador de la entidad auditada |
| `campo` | `CharField(50)` | No | Campo modificado o `alta` / `suspension` / `desactivacion` |
| `valor_anterior` | `TextField` | Sí | Texto legible; vacío en altas |
| `valor_nuevo` | `TextField` | Sí | Texto legible |
| `usuario` | FK `Usuario` | No | `PROTECT`, `related_name="+"`; autor de la acción |
| `fecha` | `DateTimeField` | No | `auto_now_add` |

**Reglas**
- Solo `INSERT`; nunca `UPDATE` ni `DELETE`.
- Se escribe en la misma transacción que el cambio; si el cambio falla, no se audita.
- Un registro por campo modificado.
- Nunca almacena contraseñas, tokens de invitación ni secretos TOTP.
- `tenant` se puebla desde la entidad auditada o el actor; si la acción es global (por ejemplo,
  administración de regiones), queda nulo.
- Índice recomendado: `(entidad, entidad_id)`, `(usuario, fecha)` y `(tenant, fecha)`.

---

## Reglas de validación y su ubicación

| Regla | Modelo/BD | Servicio | Formulario | Mensaje |
|---|---|---|---|---|
| Código de región único | `unique` | Sí | Sí | El código de región ya existe |
| Código de tenant único | `unique` | Sí | Sí | El código de tenant ya existe |
| Tenant con región | FK `NOT NULL` | Sí | Sí | El tenant debe pertenecer a una región |
| Región inmutable | FK sin campo editable | Sí | Campo ausente | La región del tenant no se puede cambiar |
| Una cuenta por tenant | `UniqueConstraint` condicional | Sí | — | El tenant ya tiene una cuenta |
| Correo único | `unique` | Sí | Sí | El correo ya está registrado |
| Alcance coherente | `CheckConstraint` | Sí | Sí | El alcance de la cuenta no es válido |
| Rol permitido | Choices | Sí | Sí | No puedes asignar ese rol |
| Rol de tenant inmutable | Choices | Sí | — | La cuenta del tenant no cambia de rol |
| Invitación vigente | Índice | Sí | — | La invitación venció o ya fue usada |
| Segundo factor | — | Servicio de autenticación | Sí | Debes completar el segundo factor |
| Cuenta activa | `is_active` | Middleware y servicio | — | La cuenta está desactivada |
| Tenant activo | `estado` | Middleware y servicio | — | El tenant está suspendido |
| Buzón válido | `EmailField` | Sí | Sí | El buzón no es válido |
| Centro y Almacén obligatorios | `CheckConstraint` | Sí | Sí | Centro y Almacén son obligatorios |

## Trazabilidad con la spec

| Entidad | Criterios de aceptación / reglas |
|---|---|
| `Region` / `Almacen` | Alta auditada, código único, buzón válido, Centro/Almacén obligatorios, sin eliminación |
| `Tenant` | Región obligatoria e inmutable, sin cuenta activa no opera, suspensión conserva datos |
| `Usuario` | Correo único, alcance coherente, una cuenta por tenant, sin rol para tenant, desactivación inmediata |
| `Invitacion` | Un solo uso, 72 h, reenvío invalida, correo ya registrado se rechaza |
| `RegistroCambio` | Toda alta, cambio de rol y desactivación con usuario, fecha, valor anterior y nuevo |
