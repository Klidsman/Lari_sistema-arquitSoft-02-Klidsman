"""Formularios de técnicos."""

from django import forms

from .services import (
    ValidacionTecnico,
    normalizar_nif,
    validar_nif,
    validar_nombre,
)


class TecnicoForm(forms.Form):
    # Se permite un margen para normalizar espacios externos antes de validar.
    nif = forms.CharField(
        label="NIF",
        max_length=20,
        error_messages={
            "required": "El NIF debe tener el formato LAXXXX",
            "max_length": "El NIF debe tener el formato LAXXXX",
        },
    )
    nombre = forms.CharField(
        label="Nombre",
        max_length=100,
        error_messages={
            "required": "El nombre es obligatorio",
            "max_length": "El nombre no puede superar los 100 caracteres",
        },
    )

    def clean_nif(self):
        nif = normalizar_nif(self.cleaned_data.get("nif"))
        try:
            return validar_nif(nif)
        except ValidacionTecnico as exc:
            raise forms.ValidationError(str(exc)) from exc

    def clean_nombre(self):
        try:
            return validar_nombre(self.cleaned_data.get("nombre"))
        except ValidacionTecnico as exc:
            raise forms.ValidationError(str(exc)) from exc


class TecnicoEdicionForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        max_length=100,
        error_messages={
            "required": "El nombre es obligatorio",
            "max_length": "El nombre no puede superar los 100 caracteres",
        },
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if instance is not None:
            self.initial.setdefault("nombre", instance.nombre)

    def clean_nombre(self):
        try:
            return validar_nombre(self.cleaned_data.get("nombre"))
        except ValidacionTecnico as exc:
            raise forms.ValidationError(str(exc)) from exc
