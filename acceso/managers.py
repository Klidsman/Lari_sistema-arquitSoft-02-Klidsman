"""Manager del usuario del sistema."""

from django.contrib.auth.base_user import BaseUserManager


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El correo es obligatorio")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", False)

        usuario = self.model(email=email, **extra_fields)
        if password is None:
            usuario.set_unusable_password()
        else:
            usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("rol", "ADMIN_PLATAFORMA")
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("El superusuario debe tener is_staff=True")
        if not extra_fields.get("is_superuser"):
            raise ValueError("El superusuario debe tener is_superuser=True")

        return self.create_user(email, password, **extra_fields)

    def para_tenant(self, tenant):
        return self.filter(
            rol="USUARIO_TENANT",
            tenant=tenant,
        )

    def para_region(self, region):
        return self.filter(
            rol="RESPONSABLE_ALMACEN",
            region=region,
        )
