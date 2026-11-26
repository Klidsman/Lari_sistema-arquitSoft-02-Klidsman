# Arquitectura del Sistema

Monolito modular en Django con renderizado en servidor, HTMX y PostgreSQL.

```mermaid
flowchart TB
    subgraph Cliente["Navegador"]
        V1["Vistas HTML por rol<br/>(Administrador / Tenant / Almacén)"]
        V2["HTMX: fragmentos, polling y SSE"]
    end

    subgraph Monolito["Monolito Modular — Django"]
        subgraph Aplicacion["Capa de aplicación"]
            C1["Acceso y sesión<br/>(cookie)"]
            C2["Vistas y formularios<br/>(renderizado en servidor)"]
            C3["Servicios de dominio<br/>(services.py)"]
            C4["Tareas Celery<br/>(correo, reintentos)"]
            C5["SSE / polling<br/>(bandeja del almacén)"]
        end

        subgraph Dominio["Módulos de dominio"]
            M1["Tenants y acceso"]
            M2["Materiales y técnicos"]
            M3["Series, stock y asignaciones"]
            M4["Recojos, traspasos y devoluciones"]
            M5["Logística inversa"]
            M6["Registro de materiales y reportes"]
        end
    end

    subgraph Persistencia["Persistencia"]
        PG[("PostgreSQL<br/>(datos, auditoría, estados)")]
        RD[("Redis<br/>(broker Celery, notificaciones)")]
        FS["MEDIA_ROOT<br/>(Excels y actas)"]
    end

    V1 -->|HTTP HTML| C2
    V2 <-->|HTMX / SSE| C5
    C3 --> M1
    C3 --> M2
    C3 --> M3
    C3 --> M4
    C3 --> M5
    C3 --> M6
    C4 <--> RD
    C5 <--> RD
    M3 --> PG
    M4 --> PG
    M5 --> PG
    M6 --> PG
    C3 --> FS
```

## Notas

- La interfaz es HTML renderizado por Django y potenciado con HTMX. No hay SPA, API REST ni JWT.
- La sesión se mantiene con cookie de Django; los roles y el alcance por tenant/región se validan en
  los servicios, no en el cliente.
- El backend es un único despliegue con módulos de dominio separados y lógica de negocio en
  `services.py`.
- PostgreSQL es la única base de datos. Redis se usa para Celery y para las notificaciones de la
  bandeja del almacén.
- Los Excel y actas se generan con `openpyxl`, se guardan bajo `MEDIA_ROOT` y se verifican con hash
  SHA-256.
- Las notificaciones del almacén usan SSE y polling de respaldo; no hay WebSocket ni Channels.
