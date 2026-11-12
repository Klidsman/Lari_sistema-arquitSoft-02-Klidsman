# Investigación y decisiones técnicas: 001 Tenants, regiones y acceso

**Fase**: 0 | **Fecha**: 2026-11-11 | **Spec**: `05-especificaciones/001-tenants-y-acceso/spec.md`

Este documento resuelve las incógnitas del contexto técnico antes del diseño de datos y
contratos. No queda ningún `NEEDS CLARIFICATION` pendiente.

---

## 1. Modelo de usuario personalizado

**Decision**: crear `acceso.Usuario` como `AbstractUser` con `username = None`,
`USERNAME_FIELD = "email"` y `AUTH_USER_MODEL = "acceso.Usuario"` configurado antes de la
primera migración.

**Rationale**: el correo es el identificador de inicio de sesión y el alcance (tenant o
región) forma parte de la identidad. Cambiar `AUTH_USER_MODEL` después de existir migraciones
es costoso y propenso a errores. El repositorio aún no tiene código de aplicación, por lo que
el costo es cero.

**Alternatives considered**:
- `User` estándar con un `Profile` asociado: obliga a un join en cada autenticación y permite
  usuarios sin alcance; no impide estados incoherentes a nivel de base de datos.
- Un usuario por rol (tablas separadas): duplica autenticación y complica la sesión única.

---

## 2. Un solo modelo con rol y alcance

**Decision**: un campo `rol` (`ADMIN_PLATAFORMA`, `USUARIO_TENANT`, `RESPONSABLE_ALMACEN`) y
dos FK opcionales (`tenant`, `region`), reforzados con un `CheckConstraint`
(`usuario_alcance_coherente`) y un `UniqueConstraint` condicional
(`un_usuario_tenant_por_tenant`).

**Rationale**: ADR-019 confirma un usuario único con alcance. La restricción de base de datos
impide combinaciones inválidas aunque se salte la capa de aplicación, y la unicidad
condicional garantiza una sola cuenta de tenant incluso ante altas concurrentes o inserciones
directas.

**Alternatives considered**:
- Tablas de permisos por rol: más flexible, pero la spec prohíbe roles internos y
  funcionalidades "por si acaso".
- Validación solo en formularios: no cumple RNF-03 ni el principio de permisos en backend.

---

## 3. Aislamiento multitenant y RLS

**Decision**: el tenant y la región se derivan siempre de `request.usuario` mediante
`ContextoUsuarioMiddleware`; los servicios reciben y revalidan el actor. En PostgreSQL se
habilitan políticas RLS sobre las tablas operativas con una variable de sesión
(`app.tenant_id`, `app.region_id`) fijada por el middleware y por el worker. En desarrollo y
pruebas se usa el mismo motor PostgreSQL; no se usa SQLite.

**Rationale**: el principio I es no negociable y ADR-006 pide RLS como respaldo. Usar SQLite
en pruebas ocultaría diferencias de restricciones condicionales, RLS y concurrencia.

**Alternatives considered**:
- Solo filtrado en el ORM: un filtro olvidado expone datos entre tenants.
- Una base por tenant: descartada por ADR-002 (costo operativo para ~100 tenants).

**Nota de implementación**: el rol de aplicación no es superusuario ni `BYPASSRLS`; las
migraciones usan un rol distinto. Las pruebas que necesiten insertar datos inválidos usan el
rol de prueba sin RLS o desactivan la política solo dentro de la transacción de prueba.

---

## 4. Autenticación de dos factores (TOTP)

**Decision**: usar `pyotp` para generar y verificar códigos TOTP, y `cryptography`
(`Fernet`) para cifrar el secreto en `Usuario.secreto_totp` con una clave tomada de variables
de entorno (`TOTP_ENCRYPTION_KEY`). La provisión se muestra como URI `otpauth://` y QR
generado en el servidor.

**Rationale**: `pyotp` es pequeño, sin dependencias pesadas y suficiente para TOTP. Cifrar el
secreto cumple la regla de no almacenar secretos en claro y evita filtrarlos en auditoría. No
se requiere un framework completo de OTP para tres roles y un solo factor adicional.

**Alternatives considered**:
- `django-otp`: robusto, pero agrega su propio modelo de dispositivos y duplica el campo
  `secreto_totp` ya definido en el plan; mayor superficie para una necesidad acotada.
- TOTP en texto plano: incumple la constitución y la regla de auditoría.

**Rotación de clave**: `Fernet` permite `MultiFernet` para rotar claves sin invalidar todos
los secretos; se documenta en configuración de producción.

---

## 5. Flujo de sesión y revocación inmediata

**Decision**: autenticación con cookie de sesión de Django. Al superar correo y contraseña,
si el rol exige segundo factor, la sesión queda en estado `pendiente_2fa` y no se marca como
autenticada hasta verificar el TOTP. Cada sesión guarda `version_sesion`; el middleware la
compara con la de la base y cierra la sesión si difieren. `version_sesion` se incrementa al
cambiar rol, desactivar la cuenta o suspender/activar el tenant.

**Rationale**: ADR-008 elige cookie de sesión para una interfaz HTMX, pero la cookie de
Django por sí sola no invalida sesiones abiertas. La versión de sesión da revocación inmediata
sin infraestructura adicional.

**Alternatives considered**:
- JWT: un token vigente seguiría funcionando tras desactivar la cuenta (descartado en
  ADR-008).
- Borrar filas de `django_session` por usuario: requiere recorrer sesiones y no cubre réplicas
  ni workers; la versión es O(1) y determinista.

---

## 6. Invitaciones por correo

**Decision**: generar un token con `secrets.token_urlsafe(32)`, guardar solo su hash SHA-256
en `Invitacion.token_hash` (64 caracteres hex) y enviar el token original en el enlace. La
invitación vence a las 72 horas, es de un solo uso y el reenvío revoca las pendientes dentro
de la misma transacción. El envío se ejecuta con Celery después del commit
(`transaction.on_commit`) y registra `enviada_en` o `ultimo_error` con reintentos.

**Rationale**: guardar el hash limita el daño si se filtra la base. SHA-256 es suficiente
porque el token es aleatorio de alta entropía (no una contraseña humana) y permite búsqueda
indexada por igualdad. El envío asíncrono evita que una caída de SMTP bloquee el alta, y
`on_commit` impide enviar correos de transacciones revertidas.

**Alternatives considered**:
- Guardar el token en claro: incumple la regla de no almacenar tokens.
- `make_password` de Django: produce hashes no indexables; obligaría a comparar todas las
  invitaciones.
- Enviar el correo dentro de la transacción: puede enviarse un enlace de un alta que luego
  falla.

---

## 7. Contraseñas y política de seguridad

**Decision**: usar los validadores de Django (`UserAttributeSimilarityValidator`,
`MinimumLengthValidator` con mínimo 12, `CommonPasswordValidator`,
`NumericPasswordValidator`) y `set_password`; las cuentas nuevas nacen con
`set_unusable_password()` e `is_active=False`.

**Rationale**: la spec propone mínimo 12 caracteres y prohíbe que el administrador conozca la
contraseña. Los validadores son configurables y no agregan dependencias.

**Alternatives considered**: política propia con expresiones regulares; se rechaza por
duplicar funcionalidad ya probada del framework.

---

## 8. Correo electrónico

**Decision**: backend SMTP configurable por variables de entorno; en desarrollo se usa el
backend de consola. El remitente y el dominio del enlace se configuran por entorno.

**Rationale**: cumple RNF-22 (fallo controlado del correo) y permite validar el flujo sin un
servidor real. No se agrega un proveedor transaccional en esta spec.

**Alternatives considered**: proveedor SaaS desde el inicio; se pospone, no es necesario para
la validación académica y agrega dependencia externa.

---

## 9. Auditoría inmutable

**Decision**: `auditoria.RegistroCambio` se escribe solo con `INSERT`, dentro de la misma
transacción que el cambio. La app no expone `update` ni `delete`; en PostgreSQL se revocan
`UPDATE` y `DELETE` al rol de aplicación. Los valores se serializan como texto legible y
nunca se registran contraseñas, tokens ni secretos TOTP.

**Rationale**: principio VI y regla `auditoria.md`. La base de datos refuerza la inmutabilidad
frente a errores de código.

**Alternatives considered**:
- `django-simple-history`: guarda versiones completas y agrega dependencia; la spec exige un
  registro por campo con valor anterior y nuevo.
- Triggers de base de datos para toda tabla: más complejo y difícil de probar; la escritura
  explícita en el servicio es suficiente y trazable.

---

## 10. Integridad, concurrencia y transacciones

**Decision**: cada alta o cambio se ejecuta en `transaction.atomic`; las restricciones únicas
de la base son la fuente de verdad. Los servicios capturan `IntegrityError` y lo traducen a
mensajes de dominio (`El código de región ya existe`, `El tenant ya tiene una cuenta`,
`El correo ya está registrado`). La suspensión y el cambio de rol bloquean la fila del usuario
(`select_for_update`) para incrementar `version_sesion` de forma consistente.

**Rationale**: cumple el principio V y los casos borde de altas simultáneas. Los mensajes
uniformes evitan filtrar información entre tenants.

**Alternatives considered**:
- "Comprobar y luego insertar" sin restricción: sufre condiciones de carrera.
- Bloqueos pesimistas globales: innecesarios y reducen concurrencia.

---

## 11. Inmutabilidad de la región del tenant

**Decision**: `Tenant.region` es obligatoria en modelo y base de datos; el formulario de
edición no incluye el campo y el servicio rechaza cualquier intento de cambiarla comparando
el valor recibido con el actual.

**Rationale**: la spec y las reglas de dominio confirman que la región no cambia en esta
versión. La validación en dos capas evita que una petición forzada lo consiga.

**Alternatives considered**: permitir el cambio con auditoría; queda fuera de alcance y
requeriría validar stock.

---

## 12. Interfaz y HTMX

**Decision**: vistas Django server-rendered con plantillas y HTMX para actualizaciones
parciales (listados, formularios y mensajes). No se crea una API REST separada en esta spec.

**Rationale**: ADR-008 y ADR-015 eligen HTMX y cookie de sesión. Una API REST adicional no
aporta valor y ampliaría la superficie de permisos.

**Alternatives considered**: SPA con API REST/JWT; contradice las ADR vigentes y agrega
complejidad.

---

## 13. Pruebas

**Decision**: `pytest` + `pytest-django` con base PostgreSQL. Un archivo de pruebas por
criterio de aceptación agrupado por área (regiones, tenants, cuentas, invitaciones, sesión,
aislamiento, auditoría). Las pruebas de contrato verifican rutas, métodos, roles y mensajes;
las de integración verifican restricciones directamente en la base.

**Rationale**: la puerta de calidad exige al menos una prueba por criterio de aceptación. Usar
PostgreSQL permite probar RLS, `CheckConstraint` condicionales y concurrencia real.

**Alternatives considered**: SQLite para velocidad; se rechaza porque no reproduce el
comportamiento de restricciones y RLS.

---

## 14. Configuración y secretos

**Decision**: settings por entorno (`base`, `dev`, `prod`, `test`); secretos
(`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `EMAIL_*`, `TOTP_ENCRYPTION_KEY`) por variables
de entorno. `.env` solo en desarrollo y excluido del repositorio.

**Rationale**: evita secretos en el código y permite despliegues reproducibles.

**Alternatives considered**: secretos en `settings.py`; descartado por seguridad.

---

## Resumen de dependencias adicionales

| Dependencia | Motivo | Alternativa descartada |
|---|---|---|
| `pyotp` | Generar y verificar TOTP | `django-otp` (duplica el modelo de secreto) |
| `cryptography` | Cifrar el secreto TOTP con `Fernet` | Guardar el secreto en claro (prohibido) |

El resto del stack (`Django`, `Celery`, `Redis`, `HTMX`, `pytest`) ya está fijado por la
constitución y ADR-015. No se requieren más dependencias.

## Incógnitas resueltas

| Incógnita del contexto técnico | Resolución |
|---|---|
| Modelo de usuario | Personalizado, email como `USERNAME_FIELD` (§1) |
| Segundo factor | TOTP con `pyotp`, secreto cifrado (§4) |
| Revocación de sesión | `version_sesion` validada por middleware (§5) |
| Invitaciones | Token aleatorio, hash SHA-256, 72 h, un solo uso (§6) |
| Correo | Celery tras commit, SMTP configurable (§6, §8) |
| Aislamiento | Sesión + servicios + RLS (§3) |
| Inmutabilidad de auditoría | Solo inserción + permisos de base (§9) |
| Concurrencia | Restricciones únicas + `IntegrityError` (§10) |
| Pruebas | pytest-django sobre PostgreSQL (§13) |
