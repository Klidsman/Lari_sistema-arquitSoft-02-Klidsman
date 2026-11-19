"""Contrato de nombres de servicios de traspasos (009)."""

from traspasos import services


def test_alias_de_servicios_coinciden_con_el_contrato():
    assert (
        services.crear_solicitud_traspaso
        is services.crear_borrador_traspaso
    )
    assert (
        services.actualizar_lineas_borrador
        is services.actualizar_borrador_traspaso
    )
    assert (
        services.enviar_solicitud_traspaso is services.enviar_traspaso
    )


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
