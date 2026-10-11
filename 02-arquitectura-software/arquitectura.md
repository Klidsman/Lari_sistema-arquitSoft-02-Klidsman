# Arquitectura del Sistema

Monolito modular en capas con frontend SPA y base de datos PostgreSQL.

```mermaid
flowchart TB
    subgraph SPA["Frontend SPA (Single Page Application)"]
        V1["Vistas por rol<br/>(Administrador / Subcontratista / Almacenero)"]
        V2["Notificaciones en tiempo real<br/>(WebSocket/SSE: sonoras y visuales)"]
        V3["Bandeja de despachos / Reportes"]
    end

    subgraph Monolito["Monolito Modular — Backend"]
        subgraph API["Capa de API / Controladores"]
            C1["Auth & RBAC<br/>(JWT, expiración configurable)"]
            C2["Pedidos, Despachos, Confirmaciones"]
            C3["Conciliación diaria"]
            C4["Devoluciones / Logs / Reportes"]
        end

        subgraph Dominio["Capa de Dominio (Módulos)"]
            M1["Seguridad y Padrón de Técnicos"]
            M2["Catálogo y Almacén"]
            M3["Despacho y Custodia"]
            M4["Mensajería y Confirmación"]
            M5["Conciliación por Diferencias"]
            M6["Logística Inversa"]
            M7["Auditoría y Reportes"]
        end

        subgraph Infra["Capa de Infraestructura"]
            R1["Repositorios (EF/ORM)"]
            R2["Generador de Excel .xlsx"]
            R3["Hash SHA-256 / almacenamiento inmutable"]
            R4["Importador de reportes<br/>(Excel / CSV / texto)"]
        end
    end

    subgraph Persistencia["Persistencia"]
        PG[("PostgreSQL<br/>(datos, bitácora inmutable, estados)")]
        FS["Almacenamiento local seguro<br/>(Excels de despacho firmados)"]
    end

    SPA -->|REST/JSON| API
    V2 <-->|WebSocket/SSE| API
    API --> Dominio
    Dominio --> Infra
    R1 --> PG
    R3 --> FS
    M7 --> PG
    M5 --> R4
```

## Notas

- El frontend es una SPA desacoplada que consume la API REST del monolito.
- El backend es un único despliegue con módulos de dominio separados.
- PostgreSQL es la única base de datos; los Excels firmados se guardan en disco.
- Las notificaciones en tiempo real usan canal push (WebSocket/SSE) entre Almacenero y Subcontratista.
