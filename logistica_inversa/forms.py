"""Formularios de logística inversa."""

from datetime import date

from django import forms
from django.urls import reverse

from series.models import EstadoSerie, Serie
from tecnicos.models import Tecnico

from .models import CausaBaja


class DevolucionForm(forms.Form):
    tecnico = forms.ModelChoiceField(queryset=Tecnico.objects.none())
    fecha = forms.DateField(initial=date.today)
    series = forms.ModelMultipleChoiceField(
        queryset=Serie.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, tenant=None, tecnico=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].queryset = Tecnico.objects.none()
        self.fields["series"].queryset = Serie.objects.none()
        if tenant is None:
            return

        self.fields["tecnico"].queryset = (
            Tecnico.objects.filter(
                tenant=tenant,
                series__estado=EstadoSerie.ASIGNADA,
            )
            .distinct()
            .order_by("nif")
        )
        self.fields["tecnico"].empty_label = "Selecciona un técnico"
        self.fields["fecha"].widget = forms.DateInput(
            attrs={"type": "date"}
        )
        self.fields["tecnico"].widget.attrs.update(
            {
                "hx-get": reverse("series_tecnico_devolucion"),
                "hx-target": "#series-tecnico",
                "hx-trigger": "change",
                "hx-include": "this",
            }
        )
        tecnico_id = tecnico
        if tecnico_id in (None, ""):
            tecnico_id = self.data.get("tecnico")
        tecnico_obj = (
            Tecnico.objects.filter(pk=tecnico_id, tenant=tenant).first()
            if tecnico_id
            else None
        )
        if tecnico_obj is not None:
            self.fields["series"].queryset = (
                Serie.objects.filter(
                    tenant=tenant,
                    estado=EstadoSerie.ASIGNADA,
                    tecnico=tecnico_obj,
                )
                .select_related("material")
                .order_by("material__codigo", "numero")
            )

    def clean(self):
        datos = super().clean()
        tecnico = datos.get("tecnico")
        series = datos.get("series")
        if tecnico and series:
            ajenas = [
                serie.numero
                for serie in series
                if serie.tecnico_id != tecnico.pk
            ]
            if ajenas:
                raise forms.ValidationError(
                    "Hay series que no pertenecen al técnico seleccionado: "
                    + ", ".join(ajenas)
                )
        return datos

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > date.today():
            raise forms.ValidationError(
                "La fecha de devolución no es válida"
            )
        return fecha


class BajaEquipoForm(forms.Form):
    tecnico = forms.ModelChoiceField(queryset=Tecnico.objects.none())
    series = forms.ModelMultipleChoiceField(
        queryset=Serie.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    causa = forms.ChoiceField(choices=CausaBaja.choices)
    observaciones = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, tenant=None, tecnico=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tecnico"].queryset = Tecnico.objects.none()
        self.fields["series"].queryset = Serie.objects.none()
        if tenant is None:
            return
        self.fields["tecnico"].queryset = (
            Tecnico.objects.filter(
                tenant=tenant,
                series__estado=EstadoSerie.ASIGNADA,
            )
            .distinct()
            .order_by("nif")
        )
        self.fields["tecnico"].empty_label = "Selecciona un técnico"
        self.fields["tecnico"].widget.attrs.update(
            {
                "hx-get": reverse("series_tecnico_baja"),
                "hx-target": "#series-tecnico",
                "hx-trigger": "change",
                "hx-include": "this",
            }
        )
        tecnico_id = tecnico
        if tecnico_id in (None, ""):
            tecnico_id = self.data.get("tecnico")
        tecnico_obj = (
            Tecnico.objects.filter(pk=tecnico_id, tenant=tenant).first()
            if tecnico_id
            else None
        )
        if tecnico_obj is not None:
            self.fields["series"].queryset = (
                Serie.objects.filter(
                    tenant=tenant,
                    estado=EstadoSerie.ASIGNADA,
                    tecnico=tecnico_obj,
                )
                .select_related("material")
                .order_by("material__codigo", "numero")
            )

    def clean(self):
        datos = super().clean()
        tecnico = datos.get("tecnico")
        series = datos.get("series")
        if tecnico and series:
            ajenas = [
                serie.numero
                for serie in series
                if serie.tecnico_id != tecnico.pk
            ]
            if ajenas:
                raise forms.ValidationError(
                    "Hay series que no pertenecen al técnico seleccionado: "
                    + ", ".join(ajenas)
                )
        return datos
