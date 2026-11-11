# 01 - Actores

Actores que interactúan con el sistema.
## Actores principales (usuarios del sistema)

| Actor | Rol en el sistema | Responsabilidades principales |
|---|---|---|
| **ACT-01** | Tenant (cuenta única del subcontratista) | Cuenta única: registra recojos, crea asignaciones y traspasos, carga reportes, aprueba o rechaza conciliaciones y gestiona técnicos y materiales |
| **ACT-02** | Administrador de plataforma (superusuario) | Global: crea regiones, almacenes, tenants, la cuenta única de cada tenant y las cuentas de Responsable de almacén. Gestiona el catálogo compartido |
| **ACT-03** | Responsable de almacén | Región: confirma o rechaza solicitudes de asignación y traspasos de su región, envía reportes de materiales respecto a su región |
| **ACT-04** | Técnico (LAxxxx) | Tenant: recibe materiales |



## Cuenta única del tenant (ACT-01)

El tenant no se divide en subcuentas ni roles internos. Tiene una sola cuenta operativa con todas las funciones de su propio tenant.

| Puede | No puede |
|---|---|
| Registrar recojos, crear asignaciones y traspasos | Ver datos de otro tenant |
| Cargar reportes y aprobar o rechazar conciliaciones | Confirmar solicitudes como almacén |
| Gestionar técnicos y materiales de su tenant | Crear regiones, tenants, cuentas o subcuentas |
| Consultar sus reportes y su auditoría | Operar fuera de su región |

No existe separación entre operación y aprobación dentro del tenant: la misma cuenta puede cargar y aprobar una conciliación.




