"""Formularios de recojos."""

from django import forms
from django.forms import formset_factory


class RecojoForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre del recojo",
        max_length=100,
        error_messages={
            "required": "El nombre es obligatorio",
            "max_length": "El nombre no puede superar los 100 caracteres",
        },
    )
    fecha = forms.DateField(
        label="Fecha",
        error_messages={
            "required": "La fecha es obligatoria",
            "invalid": "La fecha no es válida",
        },
    )


class LineaRecojoForm(forms.Form):
    material_id = forms.CharField(required=False)
    material_codigo = forms.CharField(required=False)
    series = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    cantidad = forms.CharField(required=False)

    def clean_series(self):
        from series.services import extraer_numeros, normalizar_numero

        valor = self.cleaned_data.get("series") or ""
        return "\n".join(
            normalizar_numero(numero)
            for numero in extraer_numeros(valor)
        )


LineaRecojoFormSet = formset_factory(
    LineaRecojoForm,
    extra=3,
    can_delete=False,
)
