# AGENTS.md

## Qué es este repo

Repositorio **de especificación y diseño**, no de código: todavía no hay `manage.py`,
`requirements*.txt`, tests ni aplicación. Todo lo que existe son documentos en español y la
infraestructura de Spec Kit. No busques puntos de entrada de código; el trabajo actual es
escribir/ajustar specs, planes y tareas.

Orden de autoridad: `.specify/memory/constitution.md` → ADR en
`docs/01-analisis_de_sistema/07-decisiones_arquitectonicas.md` → `spec.md` → `plan.md`.
Si un documento contradice la constitución, se corrige el documento **antes** del código
(principio VIII, «documento primero»).

## Spec Kit en este repo

- Comandos disponibles en `.opencode/commands/speckit.*.md` (`/speckit.specify`, `plan`,
  `tasks`, `implement`, `analyze`, `checklist`, `clarify`, `converge`, `constitution`).
- Scripts en PowerShell: `.specify/scripts/powershell/*.ps1`.
- Las features viven en `05-especificaciones/NNN-nombre/`. `001` y `002` tienen diseño
  completo; `003`–`013` solo tienen `spec.md` y `plan.md`; solo `001` tiene `tasks.md`.
- **Gotcha crítico**: `.specify/feature.json` fija la feature activa
  (`05-especificaciones/001-tenants-y-acceso`). Los scripts la usan aunque pidas otra en el
  prompt. Para trabajar en otra feature, exporta el override antes de ejecutarlos:

  ```powershell
  $env:SPECIFY_FEATURE_DIRECTORY = "05-especificaciones/002-materiales"
  .specify/scripts/powershell/setup-plan.ps1 -Json
  ```

  Sin el override, `setup-plan.ps1` / `setup-tasks.ps1` resolverán 001. Verifica con
  `check-prerequisites.ps1 -Json`. El override **se persiste** en `.specify/feature.json`;
  para resolver rutas sin escribirlo, define `SPECIFY_FEATURE_NO_PERSIST=1`.
- Los scripts no comprueban la rama de git; las features no son ramas (rama actual:
  `especificaciones`).
- No existe `.specify/extensions.yml`: los hooks de extensión no aplican.

## Stack y arquitectura ya decididos (no los cambies sin ADR)

- Python 3.12+, Django LTS 5.x, PostgreSQL 16+ (con RLS como respaldo), Celery + Redis, HTMX,
  `openpyxl`, `pyotp` y `cryptography`. **Sin SQLite**, ni en pruebas.
- Monolito modular. `config/` (settings `base/dev/prod/test`, URLs, Celery), apps `tenants`,
  `acceso`, `auditoria`, `materiales` y las que agreguen las specs 003–013.
- La lógica de negocio va en `services.py` de cada app, nunca en vistas ni formularios.
- Interfaz, documentación y nombres de código (modelos, campos, rutas, mensajes) en español.
- Autenticación: `AUTH_USER_MODEL = "acceso.Usuario"`, login por email, una sola cuenta por
  tenant, sin subcuentas ni autoregistro. 2FA TOTP obligatorio para Administrador de
  plataforma y Responsable de almacén.
- Aislamiento multitenant: tenant y región se derivan **solo de la sesión**
  (`request.usuario`), nunca de `tenant_id`/`region_id` enviados por el cliente. Acceso ajeno
  se responde `404`. Única excepción: el catálogo de materiales es global, sin `tenant_id`.
- No se eliminan regiones, tenants, cuentas ni materiales; se desactivan o suspenden.
- Toda alta/cambio se audita en `auditoria.RegistroCambio`, en la misma transacción. Nunca se
  auditan contraseñas, tokens ni secretos TOTP.

## Reglas de trabajo

- No implementes nada que no esté en una spec aprobada; si falta una decisión, pregunta.
- Cada criterio de aceptación necesita al menos una prueba; no se avanza con pruebas en rojo.
- Las tareas de `tasks.md` siguen el formato `- [ ] TNNN [P?] [USn?] descripción con ruta`;
  un caso por criterio de aceptación, agrupadas por historia y con fase fundacional previa.
- Al implementar, el orden global está en `06-plan-implementacion/desglose-tareas.md`
  (001 → 002 → 003 → 004 → 008 → 005 → 006 → 007 → 009 → 010 → 011 → 013 → 012).
- Los comandos de ejecución de la aplicación aún no existen. Cuando se implemente 001, las
  instrucciones reales están en `05-especificaciones/001-tenants-y-acceso/quickstart.md`
  (venv, PostgreSQL, Redis, `.env`, `migrate`, `crear_admin_plataforma`, `celery worker`,
  `pytest`). No inventes un runner de tests antes de que exista.

## Inconsistencias conocidas (resolver en documentos, no en código)

- Spec 002 usa la app `materiales` (así la referencian 004–011), pero el plan de 013 usa
  `catalogo.Material` y el plan de 001 menciona `catalogo`. Corregir esos textos a
  `materiales` antes de implementar 013.
- `03-reglas-de-dominio/catalogo-de-materiales.md` está **vacío** (0 bytes); la spec 002 es la
  fuente vigente hasta completarlo.
- `06-plan-implementacion/desglose-tareas.md` dice «crear superusuario inicial», pero la
  constitución y el plan 001 lo prohíben: la primera cuenta se crea con
  `crear_admin_plataforma`, sin superusuario de Django.
- `docs/02-arquitectura-software/arquitectura.md` describe SPA/REST/JWT; prevalecen ADR-008 y
  ADR-015 (Django + HTMX + cookie de sesión).

## Mapa mínimo

- `05-especificaciones/NNN-*/spec.md` — qué; `plan.md` — cómo; `tasks.md` — ejecución.
- `05-especificaciones/001-tenants-y-acceso/` y `002-materiales/` — únicos diseños completos
  (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`).
- `03-reglas-de-dominio/` — reglas de negocio; `04-contratos/` — formatos Excel y actas.
- `docs/` — análisis, arquitectura, C4 y ADR.
