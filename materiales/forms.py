"""Formularios del catálogo de materiales."""

from django import forms

from .services import (
    PATRON_CODIGO,
    normalizar_codigo,
    normalizar_descripcion,
    normalizar_lote,
)

TIPOS = [
    ("SERIADO", "Seriado"),
    ("NO_SERIADO", "No seriado"),
]


class _BaseMaterialForm(forms.Form):
    descripcion = forms.CharField(
        label="Descripción",
        max_length=100,
        error_messages={
            "required": "La descripción es obligatoria",
            "max_length": "La descripción no puede superar los 100 caracteres",
        },
    )
    lote = forms.CharField(
        label="Lote",
        max_length=50,
        required=False,
        error_messages={
            "max_length": "El lote no puede superar los 50 caracteres",
        },
    )

    def clean_descripcion(self):
        descripcion = normalizar_descripcion(self.cleaned_data.get("descripcion"))
        if not descripcion:
            raise forms.ValidationError("La descripción es obligatoria")
        if len(descripcion) > 100:
            raise forms.ValidationError(
                "La descripción no puede superar los 100 caracteres"
            )
        return descripcion

    def clean_lote(self):
        lote = normalizar_lote(self.cleaned_data.get("lote"))
        if len(lote) > 50:
            raise forms.ValidationError(
                "El lote no puede superar los 50 caracteres"
            )
        return lote


class MaterialForm(_BaseMaterialForm):
    field_order = ["codigo", "descripcion", "lote", "tipo"]

    codigo = forms.CharField(
        label="Código",
        max_length=11,
        error_messages={
            "required": "El código debe tener 11 dígitos",
            "max_length": "El código debe tener 11 dígitos",
        },
    )
    tipo = forms.ChoiceField(
        label="Tipo",
        choices=TIPOS,
        error_messages={
            "required": "El tipo es obligatorio",
            "invalid_choice": "El tipo es obligatorio",
        },
    )

    def clean_codigo(self):
        codigo = normalizar_codigo(self.cleaned_data.get("codigo"))
        if not PATRON_CODIGO.match(codigo):
            raise forms.ValidationError("El código debe tener 11 dígitos")
        return codigo

    def clean(self):
        datos = super().clean()
        tipo = datos.get("tipo")
        if tipo:
            datos["es_seriado"] = tipo == "SERIADO"
        return datos


class MaterialEdicionForm(_BaseMaterialForm):
    field_order = ["descripcion", "lote", "tipo"]

    tipo = forms.ChoiceField(
        label="Tipo",
        choices=TIPOS,
        required=False,
        error_messages={"invalid_choice": "El tipo es obligatorio"},
    )

    def __init__(self, *args, instance=None, permitir_tipo=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if instance is not None:
            self.initial.setdefault("descripcion", instance.descripcion)
            self.initial.setdefault("lote", instance.lote)
            self.initial.setdefault("tipo", instance.tipo)
        if not permitir_tipo:
            self.fields["tipo"].disabled = True

    def clean(self):
        datos = super().clean()
        tipo = datos.get("tipo")
        if not tipo and self.instance is not None:
            tipo = self.instance.tipo
            datos["tipo"] = tipo
        if tipo:
            datos["es_seriado"] = tipo == "SERIADO"
        return datos
