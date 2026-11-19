"""Formularios de stock inicial."""

from django import forms


class CargaExcelForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo Excel",
        error_messages={"required": "Debes seleccionar un archivo Excel"},
        widget=forms.FileInput(attrs={"accept": ".xlsx"}),
    )
