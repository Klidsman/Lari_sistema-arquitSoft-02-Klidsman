"""Contrato de nombres de servicios de traspasos (009)."""

from traspasos import services


def test_servicios_del_contrato_existen():
    for nombre in (
        "crear_solicitud_traspaso",
        "actualizar_lineas_borrador",
        "enviar_solicitud_traspaso",
        "confirmar_traspaso",
        "rechazar_traspaso",
        "cancelar_traspaso",
        "validar_estructura_tecnicos",
        "tecnicos_implicados",
        "stock_tecnico_para_traspaso",
        "verificar_hash_excel",
    ):
        assert callable(getattr(services, nombre))


def test_verificar_hash_excel_acepta_contenido():
    class _Solicitud:
        excel_hash = "0" * 64

    assert callable(services.verificar_hash_excel)
    try:
        services.verificar_hash_excel(_Solicitud(), b"contenido")
    except services.ArchivoAlterado:
        pass
    else:  # pragma: no cover - debería lanzar
        raise AssertionError("El hash alterado debió bloquear la descarga")
