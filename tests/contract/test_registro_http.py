"""Contrato de servicios y excepciones del registro de materiales."""

import inspect

from registro_materiales import exportacion, services


def test_excepciones_heredan_del_error_base():
    nombres = [
        "PermisoDenegado",
        "TecnicoNoExiste",
        "MaterialNoHabilitado",
        "MaterialInactivo",
        "CantidadInvalida",
        "NumeroOrdenInvalido",
        "PeriodoInvalido",
        "SaldoInsuficiente",
        "PeriodoCerrado",
        "CargaNoDeshacible",
        "CierreBloqueado",
        "BackupRequerido",
        "NoEncontrado",
        "MotivoRequerido",
    ]
    for nombre in nombres:
        clase = getattr(services, nombre)
        assert issubclass(clase, services.ErrorRegistro), nombre


def test_firmas_publicas_de_servicios():
    esperadas = {
        "previsualizar_carga": ["tenant", "tecnico", "periodo", "texto"],
        "confirmar_carga": [
            "tenant",
            "tecnico",
            "periodo",
            "texto",
            "actor",
        ],
        "deshacer_carga": ["carga", "actor", "motivo"],
        "guardar_uso": [
            "orden",
            "fecha_instalacion",
            "cantidades",
            "actor",
        ],
        "cerrar_mes": ["tenant", "periodo", "backup_ref", "actor"],
        "reabrir_mes": ["cierre", "motivo", "actor"],
    }
    for nombre, parametros in esperadas.items():
        firma = inspect.signature(getattr(services, nombre))
        assert list(firma.parameters) == parametros, nombre


def test_firmas_de_exportacion():
    for nombre in (
        "exportar_reporte_mensual",
        "exportar_detalle_ordenes",
    ):
        firma = inspect.signature(getattr(exportacion, nombre))
        assert list(firma.parameters) == ["tenant", "periodo", "formato"]
