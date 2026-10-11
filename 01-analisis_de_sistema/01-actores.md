# 01 - Actores

Actores que interactúan con el sistema.
## Actores principales (usuarios del sistema)

| Actor | Rol en el sistema | Responsabilidades principales | Estado |
|---|---|---|---|
| **ACT-01** | Tenant (usuario del subcontratista) | Según su rol (ver tabla siguiente): registra recojos, crea asignaciones y traspasos, carga reportes, aprueba o rechaza conciliaciones, gestiona técnicos y usuarios de su tenant | Supuesto (actor) |
| **ACT-02** | Administrador de plataforma (superusuario) | Global: crea regiones, almacenes, tenants y las cuentas de Responsable del tenant y de Responsable de almacén. Gestiona el catálogo compartido | Supuesto (actor y alcance) |
| **ACT-03** | Almacén | Región: confirma o rechaza solicitudes y traspasos de su región | Supuesto (actor) |
| **ACT-04** | Técnico (LAxxxx) | Tenant: recibe materiales | Confirmado (actor pasivo, no genera HU) |

## Cuenta de Responsable de almacén (operadora de ACT-03)

Quien la opera en el sistema es la cuenta de **Responsable de almacén**, creada por ACT-02 (RF-53, RES-19). Esa cuenta no tiene rol de tenant y su alcance es una sola región.

## Roles dentro del tenant (ACT-01)

Son permisos dentro del tenant, no actores separados. Cada usuario del tenant tiene un solo rol. 

| Rol | Puede | No puede |
|---|---|---|
| Operador | Registrar recojos, crear asignaciones y traspasos, cargar reportes | Aprobar conciliaciones, crear usuarios |
| Aprobador | Aprobar o rechazar conciliaciones completas | Crear asignaciones, registrar recojos |
| Responsable del tenant | Crear técnicos y las cuentas de Operador y Aprobador de su tenant | Aprobar conciliaciones, operar inventario, crear cuentas de otros tenants, de Almacén o de plataforma |

## Sistema externo (no actor)

| Actor | Descripción |
|---|---|
| **Lari** | Envía reportes de conciliación en Excel por región y recibe por correo los Excel de asignación y traspaso. **No opera la plataforma.** *[Confirmado]* |
| **Contrata principal** | Entidad externa que provee materiales, recibe devoluciones y emite el reporte diario de stock que se importa al sistema. *(Fuente antigua; no considerada actor en v3.1; reportado como hueco)* |
| **Cliente final** | Destinatario de la instalación; origen de equipos retirados por avería o migración. *(Fuente antigua; no considerado actor en v3.1; reportado como hueco)* |

