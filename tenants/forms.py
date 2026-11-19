"""Formularios de regiones, almacenes y tenants."""

from django import forms

from .models import Region


class RegionForm(forms.Form):
    codigo = forms.CharField(
        label="Código",
        max_length=20,
        error_messages={"required": "El código de región es obligatorio"},
    )
    nombre = forms.CharField(
        label="Nombre",
        max_length=100,
        error_messages={"required": "El nombre es obligatorio"},
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if instance is not None:
            self.fields["codigo"].disabled = True
            self.initial.setdefault("codigo", instance.codigo)
            self.initial.setdefault("nombre", instance.nombre)

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not codigo:
            raise forms.ValidationError("El código de región es obligatorio")
        if len(codigo) > 20 or not codigo.isalnum():
            raise forms.ValidationError("El código de región no es válido")
        return codigo

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio")
        return nombre


class AlmacenForm(forms.Form):
    centro = forms.CharField(
        label="Centro",
        max_length=20,
        required=False,
    )
    almacen = forms.CharField(
        label="Almacén",
        max_length=20,
        required=False,
    )
    buzon = forms.EmailField(
        label="Buzón",
        error_messages={
            "invalid": "El buzón no es válido",
            "required": "El buzón no es válido",
        },
    )

    def __init__(self, *args, con_activa=False, **kwargs):
        super().__init__(*args, **kwargs)
        if con_activa:
            self.fields["activa"] = forms.BooleanField(
                label="Activa",
                required=False,
                initial=True,
            )

    def clean(self):
        datos = super().clean()
        centro = (datos.get("centro") or "").strip()
        almacen = (datos.get("almacen") or "").strip()
        if not centro or not almacen:
            raise forms.ValidationError("Centro y Almacén son obligatorios")
        datos["centro"] = centro
        datos["almacen"] = almacen
        return datos


class TenantForm(forms.Form):
    codigo = forms.CharField(
        label="Código",
        max_length=20,
        error_messages={"required": "El código de tenant es obligatorio"},
    )
    nombre = forms.CharField(
        label="Nombre",
        max_length=100,
        error_messages={"required": "El nombre es obligatorio"},
    )
    region = forms.ModelChoiceField(
        label="Región",
        queryset=Region.objects.none(),
        empty_label="Selecciona una región",
        error_messages={
            "required": "El tenant debe pertenecer a una región",
            "invalid_choice": "La región seleccionada no está disponible",
        },
    )

    def __init__(self, *args, incluir_region=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["region"].queryset = Region.objects.filter(
            activa=True
        ).order_by("codigo")
        if not incluir_region:
            del self.fields["region"]

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not codigo:
            raise forms.ValidationError("El código de tenant es obligatorio")
        if len(codigo) > 20 or not all(
            caracter.isalnum() or caracter in {"-", "_"} for caracter in codigo
        ):
            raise forms.ValidationError("El código de tenant no es válido")
        return codigo

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio")
        return nombre


class TenantEdicionForm(TenantForm):
    """Formulario de edición: la región no se expone."""

    def __init__(self, *args, **kwargs):
        kwargs["incluir_region"] = False
        super().__init__(*args, **kwargs)

