"""Formulario de carga del reporte de conciliación."""

from django import forms


class ReporteConciliacionForm(forms.Form):
    archivo = forms.FileField(label="Reporte de Lari (.xlsx)")

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        nombre = getattr(archivo, "name", "") or ""
        if not nombre.lower().endswith(".xlsx"):
            raise forms.ValidationError(
                "El archivo debe ser un Excel .xlsx válido"
            )
        return archivo
