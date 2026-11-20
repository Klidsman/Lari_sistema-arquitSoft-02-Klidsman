# Guía: CI con GitHub Actions

Esta guía explica cómo activar integración continua para el proyecto Lari usando GitHub Actions.
El CI valida que el proyecto arranque, que las migraciones estén completas y que toda la suite de
pruebas pase sobre **PostgreSQL real** y **Redis**, tal como exige la constitución del proyecto.

## 1. Objetivo

En cada `push` y cada `pull request`, GitHub debe:

1. Instalar Python 3.12 y las dependencias.
2. Levantar PostgreSQL 16 y Redis 7 como servicios.
3. Ejecutar `manage.py check`.
4. Verificar que no falten migraciones.
5. Aplicar las migraciones desde cero.
6. Ejecutar toda la suite de pruebas.

No se usa SQLite en ningún paso.

## 2. Estado actual del repositorio

- Python: 3.12.
- Django: 5.2.
- PostgreSQL: 16.
- Redis: 7.
- Suite actual: 623 pruebas.
- Configuración de pruebas: `config/settings/test.py`.
- Dependencias: `requirements.txt` y `requirements-dev.txt`.
- No existe todavía `.github/workflows/`.

## 3. Crear la carpeta y el archivo

Desde la raíz del repositorio:

```powershell
New-Item -ItemType Directory -Force .github/workflows
```

Crea el archivo `.github/workflows/ci.yml` con este contenido:

```yaml
name: CI

on:
  push:
    branches: [main, especificaciones]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  tests:
    name: Django + PostgreSQL + Redis
    runs-on: ubuntu-latest
    timeout-minutes: 20

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: lari_app
          POSTGRES_PASSWORD: lari_app
          POSTGRES_DB: lari
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U lari_app -d lari"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 12

      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 12

    env:
      DJANGO_SETTINGS_MODULE: config.settings.test
      SECRET_KEY: ci-solo-pruebas
      DEBUG: "False"
      DATABASE_URL: postgresql://lari_app:lari_app@localhost:5432/lari
      TEST_DATABASE_NAME: test_lari
      REDIS_URL: redis://localhost:6379/0
      EMAIL_BACKEND: django.core.mail.backends.locmem.EmailBackend
      TOTP_ENCRYPTION_KEY: MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: |
            requirements.txt
            requirements-dev.txt

      - name: Instalar dependencias
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Comprobar configuración
        run: python manage.py check

      - name: Comprobar migraciones pendientes
        run: python manage.py makemigrations --check --dry-run

      - name: Aplicar migraciones
        run: python manage.py migrate --noinput

      - name: Verificar que no queden migraciones sin aplicar
        run: python manage.py migrate --check

      - name: Ejecutar pruebas
        run: python -m pytest -q
```

## 4. Por qué estas variables

| Variable | Uso |
|---|---|
| `DJANGO_SETTINGS_MODULE=config.settings.test` | Usa la configuración de pruebas y su base `test_lari` |
| `DATABASE_URL` | Conexión al servicio PostgreSQL del job |
| `TEST_DATABASE_NAME` | Nombre de la base temporal que crea pytest-django |
| `REDIS_URL` | Broker de Celery y notificaciones |
| `EMAIL_BACKEND` | Correo en memoria; no se envía nada real |
| `SECRET_KEY` | Valor ficticio solo para CI |
| `TOTP_ENCRYPTION_KEY` | Clave Fernet válida de pruebas |
| `DEBUG=False` | Evita páginas de error de desarrollo |

`manage.py` usa `config.settings.dev` por defecto, pero respeta `DJANGO_SETTINGS_MODULE` si ya está
definido. En CI siempre se define.

## 4.1 Dependencias reproducibles

Las dependencias directas viven en:

```text
requirements.in
requirements-dev.in
```

Los archivos instalables son generados por `pip-tools` y contienen versiones exactas de todas las
dependencias, incluidas las transitivas:

```text
requirements.txt
requirements-dev.txt
```

No edites los archivos generados a mano. Para cambiar una dependencia, edita el `.in` y vuelve a
compilar:

```powershell
.\.venv\Scripts\python.exe -m pip install "pip-tools>=7.4,<8.0"

.\.venv\Scripts\pip-compile.exe --no-emit-index-url --no-emit-trusted-host `
  --output-file=requirements.txt requirements.in

.\.venv\Scripts\pip-compile.exe --no-emit-index-url --no-emit-trusted-host `
  --output-file=requirements-dev.txt requirements-dev.in
```

Para actualizar una sola dependencia:

```powershell
.\.venv\Scripts\pip-compile.exe --upgrade-package pyotp `
  --no-emit-index-url --no-emit-trusted-host `
  --output-file=requirements.txt requirements.in
```

Para actualizar todas:

```powershell
.\.venv\Scripts\pip-compile.exe --upgrade `
  --no-emit-index-url --no-emit-trusted-host `
  --output-file=requirements.txt requirements.in
```

Después de regenerar:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

El CI instala `requirements-dev.txt`, por lo que usa exactamente las mismas versiones que el lock.
Si quieres además fijar hashes, genera el lock en Ubuntu con `--generate-hashes`; no mezcles locks
generados en Windows y Linux para paquetes con binarios.

## 5. Por qué PostgreSQL y Redis son servicios

- **PostgreSQL**: las pruebas validan restricciones, `select_for_update`, RLS y transacciones. La
  constitución prohíbe SQLite, incluso en pruebas.
- **Redis**: Celery y las notificaciones. `config/settings/test.py` deja Celery en modo *eager*,
  pero se levanta Redis para evitar fallos si alguna prueba lo usa directamente.

El usuario `lari_app` de la imagen oficial de PostgreSQL se crea como superusuario. Eso permite
crear la base `test_lari` y aplicar migraciones. En producción el rol de aplicación **no** debe ser
superusuario.

## 6. Activar el CI en GitHub

1. Crea `.github/workflows/ci.yml` con el contenido anterior.
2. Haz commit y push:

   ```powershell
   git add .github/workflows/ci.yml
   git commit -m "ci: agregar workflow de GitHub Actions"
   git push
   ```

3. Abre GitHub → pestaña **Actions**.
4. Verifica que el job **Django + PostgreSQL + Redis** aparezca y termine en verde.
5. Abre un pull request de prueba para confirmar que también se ejecuta en PR.

## 7. Proteger la rama principal

En GitHub:

1. **Settings → Branches → Add branch protection rule**.
2. Patrón: `main` (y `especificaciones` si se usa como rama de integración).
3. Activa **Require a pull request before merging**.
4. Activa **Require status checks to pass before merging**.
5. Selecciona el check **Django + PostgreSQL + Redis**.
6. Activa **Require branches to be up to date before merging**.
7. Guarda.

Con esto, ningún cambio entra a la rama protegida si la suite falla.

## 8. Verificación local equivalente

Antes de subir un cambio, reproduce el CI en local:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.test"
$env:DATABASE_URL = "postgresql://lari_app:lari_app@localhost:5434/lari"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:TEST_DATABASE_NAME = "test_lari"
$env:SECRET_KEY = "local-solo-pruebas"
$env:TOTP_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="

.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py migrate --check
.\.venv\Scripts\python.exe -m pytest -q
```

En local PostgreSQL está en el puerto `5434`; en GitHub Actions se usa `5432` porque es el puerto
interno del servicio del job.

## 9. Opcional: lint y formato con Ruff

Cuando el equipo quiera añadir lint:

1. Agrega Ruff a `requirements-dev.txt`:

   ```text
   ruff>=0.9,<1.0
   ```

2. Añade estos pasos al workflow, después de instalar dependencias:

   ```yaml
      - name: Revisar estilo
        run: ruff check .

      - name: Revisar formato
        run: ruff format --check .
   ```

3. Ejecuta `ruff check . --fix` y `ruff format .` una sola vez en local y revisa el diff antes de
   activar el paso como obligatorio.

## 10. Opcional: cobertura

El proyecto ya tiene `pytest-cov`, pero `pyproject.toml` solo mide `tenants`, `acceso` y
`auditoria`. Antes de publicar cobertura, amplía la lista:

```toml
[tool.coverage.run]
source = [
  "acceso", "tenants", "auditoria", "materiales", "tecnicos", "series",
  "stock", "recojos", "stock_inicial", "asignaciones", "traspasos",
  "conciliaciones", "logistica_inversa", "registro_materiales", "reportes",
]
```

Luego añade al workflow:

```yaml
      - name: Ejecutar pruebas con cobertura
        run: python -m pytest -q --cov --cov-report=xml

      - name: Publicar cobertura
        uses: actions/upload-artifact@v4
        with:
          name: cobertura
          path: coverage.xml
```

No hagas obligatorio un porcentaje mínimo hasta que la cobertura real esté estabilizada.

## 11. Opcional: auditoría de dependencias

```yaml
      - name: Auditar dependencias
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt
```

Si el equipo decide que sea obligatorio, fija la versión de `pip-audit` en
`requirements-dev.txt`.

## 12. Problemas frecuentes

### `permission denied to create database`

El usuario de PostgreSQL no tiene permiso para crear `test_lari`. Con la imagen oficial y
`POSTGRES_USER=lari_app`, el usuario es superusuario y no ocurre. Si usas otro usuario, otorga
`CREATEDB`:

```sql
ALTER ROLE lari_app CREATEDB;
```

### `password authentication failed for user "lari_app"`

`DATABASE_URL` no coincide con las credenciales del servicio. Revisa usuario, contraseña, host y
puerto.

### `django.db.utils.OperationalError: could not connect`

El servicio PostgreSQL aún no está listo. Mantén el `healthcheck` con `pg_isready` y sus reintentos.

### `Redis connection refused`

Revisa que el servicio `redis` esté en el job y que `REDIS_URL` apunte a `localhost:6379`.

### `Your models have changes that are not yet reflected in a migration`

Ejecuta en local:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations
```

Revisa la migración, pruébala y haz commit.

### `Secrets must be at least 112 bits after decoding`

No es un problema de `TOTP_ENCRYPTION_KEY`. Es `pyotp` 2.12 o superior validando el **secreto
Base32 de las pruebas**. Un secreto de ejemplo como `JBSWY3DPEHPK3PXP` tiene 80 bits y ya no es
aceptado. Usa al menos 32 caracteres Base32 (160 bits), por ejemplo:

```text
JBSWY3DPEHPK3PXPJBSWY3DPJBSWY3DP
```

Ese valor ya está aplicado en las pruebas de TOTP y 2FA.

### `InvalidToken` o error con `TOTP_ENCRYPTION_KEY`

La clave debe ser una clave Fernet válida. Genera una nueva:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

En CI usa un valor fijo de pruebas, nunca una clave real.

### Las pruebas pasan en Windows pero fallan en Ubuntu

Revisa:

- Rutas con mayúsculas/minúsculas.
- Separadores `/` y `\`.
- Codificación UTF-8.
- Diferencias de zona horaria.
- Pruebas que dependen de archivos locales no versionados.

### `FATAL: database "test_lari" already exists`

En GitHub cada job parte de un entorno limpio, así que no debería ocurrir. En local puedes usar
`pytest --create-db` o eliminar la base de pruebas.

## 13. Seguridad

- El CI de pruebas **no necesita secretos**: todos los valores son ficticios.
- No subas `.env`, claves TOTP reales ni credenciales de producción.
- Un workflow de despliegue debe ser distinto y usar **Environments** y **Secrets** de GitHub.
- El rol de PostgreSQL de producción no debe ser superusuario ni tener `BYPASSRLS`.

## 14. Checklist de activación

- [ ] Existe `.github/workflows/ci.yml`.
- [ ] El workflow se ejecuta en `push` y `pull_request`.
- [ ] PostgreSQL 16 y Redis 7 levantan con healthcheck.
- [ ] `manage.py check` pasa.
- [ ] `makemigrations --check --dry-run` pasa.
- [ ] `migrate` y `migrate --check` pasan.
- [ ] `pytest -q` pasa completo.
- [ ] El check aparece en GitHub Actions y en el pull request.
- [ ] La rama principal exige el check antes de mergear.
- [ ] El equipo reproduce los mismos comandos en local antes de subir cambios.
