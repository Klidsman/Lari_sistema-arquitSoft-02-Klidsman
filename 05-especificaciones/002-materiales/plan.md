# Plan técnico: 002 Módulo de materiales

## Referencias
- Spec: `05-especificaciones/002-materiales/spec.md`
- Reglas: `03-reglas-de-dominio/catalogo-de-materiales.md`, `auditoria.md`
- Arquitectura: `02-arquitectura-software/estilo-arquitectonico.md`
- Stack: constitución, sección 4

## Módulos afectados
- App Django `catalogo`: modelo `Material`, servicios de alta y edición,
  formularios, vistas y búsqueda.
- App Django `auditoria`: modelo `RegistroCambio`, compartido por todos los
  módulos (si aún no existe, se crea aquí).

## Modelo de datos

```python
class Material(models.Model):
    codigo = models.CharField(max_length=11, unique=True)
    descripcion = models.CharField(max_length=100)
    lote = models.CharField(max_length=50, blank=True)
    es_seriado = models.BooleanField()
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name="+")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(codigo__regex=r"^[0-9]{11}$"),
                name="material_codigo_11_digitos",
            ),
        ]
```

- Sin `tenant_id`: el catálogo es compartido.
- `unique=True` crea el índice único global sobre `codigo`.
- La restricción `CheckConstraint` impide códigos inválidos aunque algo
  salte la validación de la aplicación.

```python
class RegistroCambio(models.Model):
    # Tabla de auditoría compartida (ver auditoria.md)
    entidad = models.CharField(max_length=50)      # "Material"
    entidad_id = models.BigIntegerField()
    campo = models.CharField(max_length=50)
    valor_anterior = models.TextField(blank=True)
    valor_nuevo = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    fecha = models.DateTimeField(auto_now_add=True)
```

- Solo inserción: el servicio nunca actualiza ni borra filas. Los permisos
  de la base de datos se configuran para que la aplicación solo pueda insertar.

## Servicios (lógica de negocio)
Viven en `catalogo/services.py`, no en las vistas.

- `crear_material(datos, usuario)`
  - Normaliza: quita espacios, colapsa espacios internos, lote en mayúsculas.
  - Valida formato y longitud.
  - En `transaction.atomic`: crea el material y el registro de alta.
  - Si la base de datos rechaza el código duplicado (`IntegrityError`),
    devuelve "El material ya existe".
- `actualizar_material(material, cambios, usuario)`
  - Valida permiso: creador o administrador de plataforma. Si no, lanza `PermisoDenegado`.
  - Rechaza cambios en código.
  - Si cambia el tipo, llama a `puede_cambiar_tipo(material)`.
  - En `transaction.atomic`: aplica cambios y registra un `RegistroCambio`
    por cada campo modificado.
- `puede_cambiar_tipo(material)`
  - Hoy: devuelve `True` si no hay movimientos.
  - Desde la spec 004: consulta la tabla de inventario. Por eso el método
    se define ahora, aunque la regla completa se active después.

## Permisos
- Crear: cualquier usuario con permiso `catalogo.add_material`.
- Editar descripción y lote: creador (`creado_por == usuario`) o
  permiso `catalogo.administrar_catalogo_global`.
- Asignar el permiso global solo al rol Administrador de plataforma.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/materiales/` | GET | Listado paginado con búsqueda |
| `/materiales/buscar/?q=` | GET | Fragmento HTMX con resultados (lo usan 005, 006 y 009) |
| `/materiales/nuevo/` | GET / POST | Formulario de alta |
| `/materiales/<id>/editar/` | GET / POST | Edición de descripción y lote |

- El formulario de alta desactiva el botón Guardar al primer clic (HTMX
  `hx-disabled-elt`) y además depende de la restricción única.
- El fragmento de búsqueda devuelve código, descripción, lote y tipo, que
  los formularios de asignación usan para autocompletar.
- El campo código es de solo lectura en el formulario de edición.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| 11 dígitos | Formulario y `CheckConstraint` | "El código debe tener 11 dígitos" |
| Código único | Servicio y restricción única | "El material ya existe" |
| Descripción no vacía | Formulario | "La descripción es obligatoria" |
| Tipo inmutable con movimientos | Servicio | "El tipo no se puede cambiar: el material tiene movimientos" |
| Permiso de edición | Servicio (nunca solo la vista) | "No tienes permiso para editar este material" |

## Pruebas
Un caso por criterio de aceptación. Los nombres salen directo de la spec.

- `test_crear_material_con_codigo_nuevo_registra_creador_y_fecha`
- `test_codigo_duplicado_se_rechaza_sin_revelar_tenant`
- `test_codigo_con_longitud_incorrecta_o_letras_se_rechaza`
- `test_material_sin_lote_se_guarda_con_lote_vacio`
- `test_lote_visible_para_otro_tenant_en_busqueda`
- `test_editar_descripcion_registra_valor_anterior_y_nuevo`
- `test_usuario_sin_permiso_no_puede_editar_descripcion_ni_lote`
- `test_codigo_no_es_editable`
- `test_cambio_de_tipo_rechazado_si_hay_movimientos`
- `test_descripcion_solo_espacios_se_rechaza`
- `test_doble_envio_no_crea_duplicado`
- `test_busqueda_por_descripcion_devuelve_material`

Además, una prueba de la restricción en base de datos: insertar un código
de 10 dígitos directamente debe fallar.

## Decisiones y riesgos
- **Lote en mayúsculas:** decisión tomada aquí, pendiente de confirmar. Si
  Lari envía lotes con minúsculas, cambiar la regla en la spec primero.
- **Auditoría en tabla compartida:** se usa `RegistroCambio` para evitar un
  sistema de auditoría por módulo. Se documenta en `auditoria.md`.
- **Riesgo de catálogo compartido:** cualquier usuario crea materiales. Un
  error de descripción afecta a todos. Mitigación: auditoría y restricción de
  edición. Revisar si hace falta validación del administrador (mejora pendiente).
- **Doble clic:** se resuelve con la restricción única, no con bloqueos de
  aplicación. Así funciona también con dos usuarios creando el mismo código.