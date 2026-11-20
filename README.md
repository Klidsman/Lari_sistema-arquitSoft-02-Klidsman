# Sistema de despacho por mensajería interna y conciliación de stcok para el control de materiales en subcontratistas de Lari contratistas
# Nombre:
CASTAÑEDA MALLQUI, Klidsman Junior

# Descripción
Sistema web de control de inventario y custodia de equipos de telecomunicaciones para una empresa subcontratista que opera con una contrata principal. Permite gestionar el almacén central, despachar equipos y materiales a las cuadrillas de técnicos, y conciliar diariamente lo asignado contra lo reportado como instalado.

# Curso:

Arquitectura de Software

## Puesta en marcha

Requisitos: Python 3.12+, PostgreSQL 16+ y Redis.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# PostgreSQL y Redis (ejemplo con Docker)
docker run --name lari-postgres -e POSTGRES_USER=lari_app `
  -e POSTGRES_PASSWORD=lari_app -e POSTGRES_DB=lari -p 5434:5432 -d postgres:16
docker run --name lari-redis -p 6379:6379 -d redis:7
```

Crea `.env` con, al menos:

```text
SECRET_KEY=cambia-esta-clave
DEBUG=True
DATABASE_URL=postgresql://lari_app:lari_app@localhost:5434/lari
REDIS_URL=redis://localhost:6379/0
TOTP_ENCRYPTION_KEY=<clave Fernet de 32 bytes en base64>
BASE_URL=http://localhost:8000
```

Genera la clave TOTP con:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Aplica migraciones y crea la primera cuenta administradora:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py crear_admin_plataforma --email admin@lari.local
.\.venv\Scripts\python.exe manage.py runserver
.\.venv\Scripts\celery.exe -A config worker -l info
```

El comando imprime la URL `/invitacion/<token>/` para definir la contraseña. No se crea
superusuario de Django.

## Pruebas

Las pruebas usan PostgreSQL (nunca SQLite):

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest --cov=tenants --cov=acceso --cov=auditoria
```

Para más detalle del flujo y los escenarios manuales consulta
`05-especificaciones/001-tenants-y-acceso/quickstart.md`.