"""API pública del envío de asignaciones por correo (007).

La implementación vive en ``almacen_services`` para reutilizar la verificación
del Excel y el acceso al almacén; este módulo fija el punto de entrada que usan
las tareas y las vistas.
"""

from .almacen_services import (
    encolar_envio_solicitud,
    envio_definitivo_fallido,
    programar_envio_solicitud,
    procesar_envio_solicitud,
    registrar_fallo_programacion,
)

__all__ = [
    "encolar_envio_solicitud",
    "envio_definitivo_fallido",
    "programar_envio_solicitud",
    "procesar_envio_solicitud",
    "registrar_fallo_programacion",
]
