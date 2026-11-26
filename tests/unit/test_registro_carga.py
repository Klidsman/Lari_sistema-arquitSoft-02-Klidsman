"""Normalización de la lista de órdenes de carga masiva."""

from registro_materiales.services import procesar_lista


def test_procesar_lista_normaliza_y_deduplica():
    texto = "  ABC1  \n\nabc1\n  XYZ9\n\n"
    lista = procesar_lista(texto)
    assert lista.ordenes == ["ABC1", "XYZ9"]
    assert lista.rechazadas == []


def test_procesar_lista_rechaza_espacios_internos_y_separadores():
    lista = procesar_lista("AB 1\nAB,1\nAB;1\nOK1")
    assert lista.ordenes == ["OK1"]
    assert len(lista.rechazadas) == 3


def test_procesar_lista_normaliza_mayusculas_e_ignora_vacias():
    lista = procesar_lista("\n   \nAbC9\n")
    assert lista.ordenes == ["ABC9"]
    assert lista.rechazadas == []


def test_procesar_lista_acepta_guiones_simples():
    lista = procesar_lista("FE-1133926298\nfe-1133926298\n")
    assert lista.ordenes == ["FE-1133926298"]
    assert lista.rechazadas == []


def test_procesar_lista_rechaza_caracteres_invalidos_y_guiones_consecutivos():
    lista = procesar_lista("FE--1133926298\nFE$1133926298\nFE-1133926298")
    assert lista.ordenes == ["FE-1133926298"]
    assert len(lista.rechazadas) == 2
