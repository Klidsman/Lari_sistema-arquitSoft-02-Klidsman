"""Formularios de logística inversa."""

from datetime import date

from django import forms

from series.models import EstadoSerie, Serie
from tecnicos.models import Tecnico

from .models import CausaBaja


class DevolucionForm(forms.Form):
    tecnico = forms.ModelChoiceField(queryset=Tecnico.objects.none())
    fecha = forms.DateField(initial=date.today)
    series = forms.ModelMultipleChoiceField(queryset=Serie.objects.none())
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant is not None:
            self.fields["tecnico"].queryset = Tecnico.objects.filter(
                tenant=tenant, activo=True
            ).order_by("nif")
            self.fields["series"].queryset = (
                Serie.objects.filter(
                    tenant=tenant, estado=EstadoSerie.ASIGNADA
                )
                .select_related("material", "tecnico")
                .order_by("numero")
            )

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > date.today():
            raise forms.ValidationError(
                "La fecha de devolución no es válida"
            )
        return fecha


class BajaEquipoForm(forms.Form):
    serie = forms.CharField(max_length=12)
    causa = forms.ChoiceField(choices=CausaBaja.choices)
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def clean_serie(self):
        return self.cleaned_data["serie"].strip().upper()
