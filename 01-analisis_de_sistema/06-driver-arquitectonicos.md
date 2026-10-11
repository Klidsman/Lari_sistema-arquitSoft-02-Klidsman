# 06 - Drivers Arquitectónicos

Decisiones de arquitectura forzadas por los requisitos de negocio. Derivados de la sección 7 "Drivers Arquitectónicos" de `01-notas-de-descubrimiento.md` v3.1. Los IDs de driver siguen el formato DRV-.

| Driver | Requisito / Contexto | Implicación arquitectónica | RF / RNF / RES relacionados |
|---|---|---|---|
| **DRV-01** | Aislamiento multitenant con una excepción (catálogo compartido) | Modelo con tenant_id en las tablas operativas, aislamiento en varias capas, pruebas obligatorias | RNF-01, RNF-02, RNF-03, RNF-20, RES-11 |
| **DRV-02** | Consistencia transaccional del stock | Operaciones de stock atómicas; estructura modular con reglas de negocio en el núcleo | RNF-04, RNF-06 |
| **DRV-03** | Unicidad global de series sin revelar el tenant | Restricción única global; validación que devuelve siempre el mismo mensaje | RNF-05, RES-01 |
| **DRV-04** | Auditoría inmutable | Libro de movimientos de solo inserción; las correcciones son movimientos nuevos | RNF-07, RES-14 |
| **DRV-05** | Picos nocturnos de conciliación para 100 tenants | Procesos de trabajo separados de la web, con cola y límites de concurrencia por tenant | RNF-09, RNF-11 |
| **DRV-06** | Entrega fiable al almacén por correo | Registro del envío en la misma operación que la solicitud, y envío con reintentos | RNF-12, RES-09 |
| **DRV-07** | Jerarquía región → tenant → técnico | Parámetros por región (Centro, Almacén, buzón); permisos por región para Responsable de almacén; alta de cuentas centralizadas | RF-01, RF-02, RF-04, RF-53, RES-05 |
| **DRV-08** | Formatos externos fijos de Lari | Adaptadores de entrada y salida separados del dominio; contratos de Excel versionados | RNF-15, RNF-16, RES-03, RES-10 |
| **DRV-09** | Operación en campo y de digitación intensiva | Formularios con autocompletado y validación por fila; ingreso de series por pegado | RNF-17, RNF-18, RES-08 |
| **DRV-10** | Volumen y crecimiento de 100 tenants | Índices compuestos que empiezan por tenant; esquema compartido | RNF-11 |
| **DRV-11** | Administración centralizada de accesos y separación de funciones | Rol de plataforma separado del dominio operativo; flujo de invitación; auditoría de la administración | RF-51, RF-55, RF-58, RF-59, RNF-20, RNF-21, RES-18 |