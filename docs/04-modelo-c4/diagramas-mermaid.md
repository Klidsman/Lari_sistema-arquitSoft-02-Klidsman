# Diagramas Mermaid: monolito modular, componentes y arquitectura

Estos diagramas describen la **implementación real** del repositorio: Django + HTMX, cookie de sesión, PostgreSQL, Celery/Redis y `MEDIA_ROOT`. No representan la SPA/REST/JWT que todavía aparece en `docs/02-arquitectura-software/arquitectura.md`; prevalecen ADR-008 y ADR-015.

> Para visualizarlos: pega cada bloque en <https://mermaid.live>, usa la extensión Mermaid de VS Code o abre el archivo en GitHub.

## 1. Monolito modular

Un solo despliegue Django, una sola base PostgreSQL y módulos de dominio con dependencias unidireccionales. La presentación habla con servicios; los servicios concentran las reglas; los modelos y la infraestructura quedan debajo. `auditoria`, `series` y `stock` actúan como núcleo compartido.

```mermaid
flowchart TB
    subgraph PRESENTACION["Presentación"]
        TPL["Plantillas Django + HTMX"]
        VISTAS["Vistas y formularios"]
    end

    subgraph APLICACION["Aplicación y dominio"]
        direction TB

        subgraph NUCLEO["Núcleo transversal"]
            ACCESO["acceso<br/>sesión y cuentas"]
            TENANTS["tenants<br/>regiones y almacenes"]
            AUDITORIA["auditoria<br/>registro inmutable"]
        end

        subgraph CATALOGO["Catálogo y padrón"]
            MATERIALES["materiales<br/>catálogo global"]
            TECNICOS["tecnicos<br/>padrón del tenant"]
            SERIES["series<br/>serie individual"]
        end

        subgraph INVENTARIO["Inventario"]
            STOCK["stock<br/>general y por técnico"]
            STOCK_INICIAL["stock_inicial<br/>carga inicial"]
        end

        subgraph OPERACIONES["Operaciones"]
            RECOJOS["recojos"]
            ASIGNACIONES["asignaciones<br/>solicitud, envío y almacén"]
            TRASPASOS["traspasos"]
            CONCILIACIONES["conciliaciones"]
            LOGISTICA["logistica_inversa"]
            REGISTRO["registro_materiales"]
            REPORTES["reportes"]
        end
    end

    subgraph INFRAESTRUCTURA["Infraestructura"]
        ORM["ORM Django"]
        EXCEL["openpyxl<br/>Excel y actas"]
        CELERY["Celery"]
        REDIS["Redis<br/>broker y eventos"]
        SMTP["SMTP"]
    end

    PG[("PostgreSQL 16+<br/>RLS como respaldo")]
    MEDIA[("MEDIA_ROOT<br/>Excel y actas")]

    TPL --> VISTAS
    VISTAS --> ACCESO
    VISTAS --> TENANTS
    VISTAS --> CATALOGO
    VISTAS --> INVENTARIO
    VISTAS --> OPERACIONES

    OPERACIONES --> CATALOGO
    OPERACIONES --> INVENTARIO
    OPERACIONES --> NUCLEO
    INVENTARIO --> CATALOGO
    CATALOGO --> NUCLEO

    APLICACION --> ORM
    ORM --> PG
    OPERACIONES --> EXCEL
    EXCEL --> MEDIA
    OPERACIONES --> CELERY
    CELERY --> REDIS
    CELERY --> SMTP
    CELERY --> PG
    CELERY --> MEDIA
    AUDITORIA --> PG
```

### Mapa de dependencias entre apps

```mermaid
flowchart LR
    CONFIG["config<br/>settings, URLs, Celery"]

    ACCESO["acceso"]
    TENANTS["tenants"]
    AUDITORIA["auditoria"]

    MATERIALES["materiales"]
    TECNICOS["tecnicos"]
    SERIES["series"]
    STOCK["stock"]

    STOCK_INICIAL["stock_inicial"]
    RECOJOS["recojos"]
    ASIGNACIONES["asignaciones"]
    TRASPASOS["traspasos"]
    CONCILIACIONES["conciliaciones"]
    LOGISTICA["logistica_inversa"]
    REPORTES["reportes"]
    REGISTRO["registro_materiales"]

    CONFIG --> ACCESO
    CONFIG --> TENANTS

    ACCESO --> TENANTS
    ACCESO --> AUDITORIA
    TENANTS --> AUDITORIA

    MATERIALES --> AUDITORIA
    TECNICOS --> ACCESO
    TECNICOS --> AUDITORIA
    SERIES --> MATERIALES
    SERIES --> TENANTS
    SERIES --> AUDITORIA

    STOCK --> TENANTS
    STOCK --> MATERIALES
    STOCK --> TECNICOS
    STOCK --> AUDITORIA

    STOCK_INICIAL --> STOCK
    STOCK_INICIAL --> SERIES
    STOCK_INICIAL --> TECNICOS
    STOCK_INICIAL --> AUDITORIA

    RECOJOS --> STOCK
    RECOJOS --> SERIES
    RECOJOS --> MATERIALES
    RECOJOS --> AUDITORIA

    ASIGNACIONES --> STOCK
    ASIGNACIONES --> SERIES
    ASIGNACIONES --> TECNICOS
    ASIGNACIONES --> AUDITORIA

    TRASPASOS --> STOCK
    TRASPASOS --> SERIES
    TRASPASOS --> TECNICOS
    TRASPASOS --> AUDITORIA

    CONCILIACIONES --> STOCK
    CONCILIACIONES --> SERIES
    CONCILIACIONES --> TECNICOS
    CONCILIACIONES --> AUDITORIA

    LOGISTICA --> STOCK
    LOGISTICA --> SERIES
    LOGISTICA --> TECNICOS
    LOGISTICA --> AUDITORIA

    REPORTES --> ASIGNACIONES
    REPORTES --> CONCILIACIONES
    REPORTES --> LOGISTICA
    REPORTES --> AUDITORIA

    REGISTRO --> MATERIALES
    REGISTRO --> TECNICOS
    REGISTRO --> STOCK
    REGISTRO --> AUDITORIA
```

## 2. Diagrama de componentes

Componentes dentro del contenedor web y su comunicación con los contenedores de datos. La sesión se transporta con cookie de Django; las notificaciones del almacén usan SSE sobre Redis.

```mermaid
flowchart LR
    NAV["Navegador<br/>HTML + HTMX + CSS"]

    subgraph WEB["Contenedor web: Django (gunicorn/WSGI)"]
        URLS["URLs y middleware<br/>ContextoUsuarioMiddleware"]
        VISTAS["Vistas"]
        FORMULARIOS["Formularios"]
        SERVICIOS["Servicios de dominio<br/>services.py"]
        MODELOS["Modelos y ORM"]
        PLANTILLAS["Plantillas + parciales HTMX"]
        AUDITORIA["Auditoría<br/>registrar_cambio"]
        TAREAS["Tareas Celery<br/>programar_envio_solicitud<br/>enviar_excel_solicitud"]
    end

    PG[("PostgreSQL 16+<br/>RLS")]
    REDIS[("Redis 7<br/>broker / SSE")]
    WORKER["Worker Celery"]
    SMTP["SMTP"]
    MEDIA[("MEDIA_ROOT<br/>Excel y actas")]

    NAV -->|"HTTPS + cookie de sesión"| URLS
    URLS --> VISTAS
    VISTAS --> FORMULARIOS
    VISTAS --> SERVICIOS
    VISTAS --> PLANTILLAS
    PLANTILLAS -->|"HTML / fragmento HTMX"| NAV

    FORMULARIOS --> SERVICIOS
    SERVICIOS --> MODELOS
    SERVICIOS --> AUDITORIA
    SERVICIOS --> TAREAS
    SERVICIOS --> MEDIA
    MODELOS --> PG
    AUDITORIA --> PG

    TAREAS --> REDIS
    REDIS --> WORKER
    WORKER --> PG
    WORKER --> MEDIA
    WORKER --> SMTP
    WORKER --> REDIS

    REDIS -->|"eventos"| VISTAS
    VISTAS -->|"text/event-stream"| NAV
```

## 3. Diagrama de arquitectura

Contenedores de despliegue. Nginx sirve estáticos y protege la aplicación; la web y el worker comparten PostgreSQL, Redis y el volumen de documentos. El detalle de despliegue aún no está fijado en el repositorio, así que este diagrama muestra la topología objetivo, no una receta de infraestructura.

```mermaid
flowchart TB
    USUARIO["Usuario<br/>Administrador de plataforma<br/>Responsable de almacén<br/>Cuenta de tenant"]

    subgraph BORDE["Borde"]
        NGINX["Nginx<br/>TLS + proxy inverso"]
        STATIC[("staticfiles<br/>collectstatic")]
    end

    subgraph APLICACION["Aplicación"]
        WEB["Web Django<br/>gunicorn + WSGI"]
        WORKER["Worker Celery"]
    end

    subgraph DATOS["Datos y servicios"]
        PG[("PostgreSQL 16+<br/>RLS")]
        REDIS[("Redis 7<br/>broker y eventos")]
        MEDIA[("Volumen media<br/>Excel y actas")]
        SMTP["Servidor SMTP"]
    end

    USUARIO -->|"HTTPS"| NGINX
    NGINX -->|"proxy /"| WEB
    NGINX -->|"/static/"| STATIC
    NGINX -->|"/media/"| MEDIA

    WEB --> PG
    WEB --> REDIS
    WEB --> MEDIA
    WEB --> SMTP

    WORKER --> PG
    WORKER --> REDIS
    WORKER --> MEDIA
    WORKER --> SMTP

    REDIS -->|"eventos SSE"| WEB
    REDIS -->|"tareas"| WORKER
```

## Notas de lectura

- **Un solo despliegue web**: no hay microservicios; los módulos son apps Django y se comunican por servicios, no por red.
- **Una sola base**: PostgreSQL concentra datos operativos, stock, series, auditoría y RLS.
- **Worker separado**: Celery ejecuta correos, reintentos y procesos de fondo; comparte código, base y `MEDIA_ROOT` con la web.
- **Documentos**: los Excel de asignación, traspaso, conciliación, stock inicial y las actas viven en `MEDIA_ROOT`; su hash SHA-256 se guarda en base para verificar integridad.
- **Sesión**: cookie de Django, no JWT. El tenant y la región salen de `request.usuario`, nunca del cliente.
- **Tiempo real**: SSE del almacén sobre Redis/pub-sub; no WebSocket ni Django Channels.
- **Auditoría**: toda operación de escritura relevante registra `RegistroCambio` en la misma transacción; el historial es de solo inserción.
