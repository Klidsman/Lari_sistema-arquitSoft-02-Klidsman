# 01 - Actores

Actores que interactúan con el sistema.
## Actores principales (usuarios del sistema)

| Actor | Rol en el sistema | Responsabilidades principales |
|---|---|---|
| **ACT-01** | Tenant (usuario del subcontratista) | registra recojos, crea asignaciones y traspasos, carga reportes, aprueba o rechaza conciliaciones y gestiona técnicos |
| **ACT-02** | Administrador de plataforma (superusuario) | Global: crea regiones, almacenes, tenants. Gestiona el catálogo compartido |
| **ACT-03** | Almacén | Región: confirma o rechaza solicitudes de asignación y traspasos de su región, envia reportes de materiales respecto a su región |
| **ACT-04** | Técnico (LAxxxx) | Tenant: recibe materiales |



## Roles dentro del tenant (ACT-01)

Son permisos dentro del tenant, no actores separados.

| Rol | Puede | No puede |
|---|---|---|
| tenant | Registrar recojos, crear asignaciones y traspasos, cargar reportes, Aprobar o rechazar conciliaciones completas, Dar de alta y gestionar técnicos | Su alcance está limitado exclusivamente a sus propios datos, No puede modificar la configuración global de la plataforma ni acceder a datos de otros tenants o del almacén central. |




