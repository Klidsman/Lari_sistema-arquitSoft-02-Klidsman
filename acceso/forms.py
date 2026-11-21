"""Formularios de acceso."""

from django import forms

from tenants.models import Region


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Correo",
        error_messages={"invalid": "El correo no es válido"},
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
    )


class SegundoFactorForm(forms.Form):
    codigo = forms.RegexField(
        regex=r"^\d{6}$",
        label="Código de 6 dígitos",
        error_messages={
            "invalid": "Debes completar el segundo factor",
            "required": "Debes completar el segundo factor",
        },
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "pattern": "[0-9]*",
                "maxlength": "6",
                "autocomplete": "one-time-code",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        ),
    )


class ConfigurarTotpForm(SegundoFactorForm):
    pass


class CuentaTenantForm(forms.Form):
    email = forms.EmailField(
        label="Correo",
        error_messages={
            "invalid": "El correo no es válido",
            "required": "El correo no es válido",
        },
    )


class CuentaAlmacenForm(CuentaTenantForm):
    region = forms.ModelChoiceField(
        label="Región",
        queryset=Region.objects.none(),
        empty_label="Selecciona una región",
        error_messages={
            "required": "La región es obligatoria",
            "invalid_choice": "La región seleccionada no está disponible",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["region"].queryset = Region.objects.filter(
            activa=True
        ).order_by("codigo")


class InvitacionPasswordForm(forms.Form):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        min_length=12,
        error_messages={
            "required": "La contraseña es obligatoria",
            "min_length": "La contraseña debe tener al menos 12 caracteres",
        },
    )
    password_confirmacion = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput,
        error_messages={"required": "Debes confirmar la contraseña"},
    )

    def clean(self):
        datos = super().clean()
        password = datos.get("password")
        confirmacion = datos.get("password_confirmacion")
        if password and confirmacion and password != confirmacion:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return datos
