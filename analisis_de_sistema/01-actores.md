# 01 - Actores

Actores que interactúan con el sistema, derivados de los requerimientos brutos (RF-01 a RF-27).

## Actores principales (usuarios del sistema)

| Actor | Rol en el sistema | Responsabilidades principales |
|---|---|---|
| **Administrador** | Rol `Administrador` | Acceso total: configuración, gestión de catálogos, auditorías, logs, creación de credenciales de Subcontratistas y Almaceneros. |
| **Subcontratista** | Rol `Subcontratista` | Registra materiales, crea órdenes de despacho, asigna órdenes a sus técnicos, sube cortes diarios de la contrata, consulta reportes. |
| **Almacenero** | Rol `Almacenero` | Gestiona la bandeja de despachos, descarga formatos, confirma asignaciones/rechazos, envía reportes de stock en Excel a subcontratistas. |

## Actores registrados en el padrón (no autenticados)

| Actor | Descripción |
|---|---|
| **Técnico de campo** | Persona registrada con nombres, apellidos, código de trabajador (LA), zona y estado operativo (Activo, Suspendido, De Baja). Custodio de equipos asignados. |

## Actores externos

| Actor | Descripción |
|---|---|
| **Contrata principal** | Entidad externa que provee materiales, recibe devoluciones y emite el reporte diario de stock que se importa al sistema. |
| **Cliente final** | Destinatario de la instalación; origen de equipos retirados por avería o migración. |

## Notas

- El Técnico de campo no se autentica directamente al sistema; su actividad se registra a través del Subcontratista y del Almacenero.
- La Contrata principal no usa la aplicación, pero sus documentos (guías de remisión, reportes de stock, paradas) son entradas críticas del sistema.
