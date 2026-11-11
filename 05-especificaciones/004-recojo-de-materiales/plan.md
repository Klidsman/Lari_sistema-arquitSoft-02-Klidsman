# Plan técnico: 004 Recojo de Materiales

## Referencias
- Spec: `05-especificaciones/004-recojo-de-materiales/spec.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación), ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, HTMX y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `recojos`: modelo `Recojo`, `LineaRecojo`, servicios, formularios y vistas.
- App `materiales`: consulta del catálogo de materiales.
- App `series`: validación de existencia de series.
- App `stock`: incremento del stock general del tenant.
- App `auditoria`: modelo `RegistroCambio`, compartido.
- Middleware de contexto de tenant de la spec 001.
- No se modifican asignaciones, traspasos, conciliaciones ni técnicos.

## Modelo de datos

```python
class Recojo(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="recojos",
    )
    region = models.ForeignKey(
        "regiones.Region",
        on_delete=models.PROTECT,
        related_name="recojos",
    )
    fecha = models.DateField()
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recojos_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="recojo_tenant_fecha"),
            models.Index(fields=["region", "fecha"], name="recojo_region_fecha"),
        ]

    def __str__(self):
        return f"Recojo {self.id} - {self.tenant} - {self.fecha}"


class LineaRecojo(models.Model):
    recojo = models.ForeignKey(
        "Recojo",
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_recojo",
    )
    lote = models.CharField(max_length=50)
    serie = models.CharField(
        max_length=12,
        null=True,
        blank=True,
    )
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(serie__isnull=False) | Q(cantidad__gt=0),
                name="linea_recojo_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=~Q(serie__isnull=False) | Q(cantidad=1),
                name="linea_recojo_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(serie__regex=r"^[A-Z0-9]{12}$") | Q(serie__isnull=True),
                name="linea_recojo_serie_formato",
            ),
        ]
        indexes = [
            models.Index(fields=["recojo", "material"], name="linea_recojo_recojo_material"),
            models.Index(fields=["serie"], name="linea_recojo_serie"),
        ]

    def __str__(self):
        if self.serie:
            return f"{self.material.codigo} - {self.serie}"
        return f"{self.material.codigo} - {self.cantidad}"
```

- `Recojo` representa el registro completo del recojo con su fecha, tenant y región.
- `region` se deriva de `tenant.region` al crear el recojo y se guarda explícitamente para facilitar consultas por región.
- `LineaRecojo` representa cada línea del formulario (material, lote, serie o cantidad).
- Para materiales seriados: `serie` tiene valor, `cantidad=1`.
- Para materiales no seriados: `serie` es NULL, `cantidad>0`.
- La restricción `linea_recojo_serie_o_cantidad` exige que haya serie o cantidad (no ambas vacías).
- La restricción `linea_recojo_serie_cantidad_uno` exige que si hay serie, la cantidad sea 1.
- La restricción `linea_recojo_serie_formato` protege el formato de serie en la base de datos.
- El índice en `serie` acelera la validación de duplicados y existencia.

## Migraciones
- `recojos/migrations/0001_initial.py`: modelos `Recojo` y `LineaRecojo` con restricciones e índices.
- No se crean recojos por migración.
- No se modifican tablas de stock, series, asignaciones, traspasos ni conciliaciones.

## Servicios (lógica de negocio)
Viven en `recojos/services.py`, no en las vistas.

### Validación de alcance
- `validar_cuenta_tenant(actor, tenant)`:
  - Verifica que `actor.rol == "USUARIO_TENANT"`.
  - Verifica que `actor.tenant_id == tenant.id`.
  - Verifica que la cuenta esté activa y que el tenant esté activo.
  - Si no cumple, lanza `PermisoDenegado`.
- `validar_region_tenant(tenant, region)`:
  - Verifica que `tenant.region == region`.
  - Si no, lanza `RegionIncorrecta`.

### Normalización y validación de series
- `normalizar_serie(serie)`:
  - Elimina espacios al inicio y al final.
  - Convierte a mayúsculas.
  - No elimina espacios internos: la validación de formato los rechaza.
- `validar_formato_serie(serie)`:
  - Debe cumplir `^[A-Z0-9]{12}$`.
  - Si no, lanza `SerieInvalida` con "La serie debe tener 12 caracteres alfanuméricos".
- `validar_serie_no_existe(serie)`:
  - Consulta el índice de series en `LineaRecojo` y `series.Serie`.
  - Si existe, lanza `SerieYaExiste` con "La serie ya está registrada en el sistema".
- `validar_serie_no_duplicada(lista_series)`:
  - Verifica que no haya duplicados en la lista de series del mismo recojo.
  - Si hay duplicados, lanza `SerieDuplicada` con "La serie está duplicada en el recojo".

### Validación de materiales
- `validar_material_tenant(material, tenant)`:
  - Verifica que el material existe en el catálogo.
  - No valida tenant porque el catálogo es compartido.
- `obtener_datos_material(material)`:
  - Devuelve `codigo, descripcion, lote, tipo` del material.
  - El tipo indica si es seriado o no seriado.

### Validación previa al guardar
- `validar_recojo_previo(tenant, lineas)`:
  - Para cada línea:
    - Normaliza y valida formato de serie (si aplica).
    - Valida que la serie no exista en el sistema.
    - Valida que la serie no esté duplicada en el mismo recojo.
    - Valida que el material existe en el catálogo.
    - Valida que la cantidad sea > 0 para no seriados.
  - Si alguna validación falla, lanza la excepción correspondiente.
  - Esta validación es rápida y se ejecuta antes de mostrar la vista previa final.

### Creación de recojo
- `crear_recojo(tenant, lineas, actor)`:
  - `validar_cuenta_tenant(actor, tenant)`.
  - `validar_region_tenant(tenant, tenant.region)`.
  - `validar_recojo_previo(tenant, lineas)`.
  - En `transaction.atomic`:
    - Crea el `Recojo` con tenant, region y fecha.
    - Crea cada `LineaRecojo` con sus datos.
    - Para seriados: crea la `Serie` con tenant y región.
    - Incrementa el stock general del tenant (material y cantidad).
    - Registra auditoría del recojo.
  - Si falla alguna inserción, toda la transacción se revierte.
  - Devuelve el `Recojo` creado.

### Consultas
- `listar_recojos(tenant, fecha_desde=None, fecha_hasta=None)`:
  - Filtra siempre por `tenant`.
  - Opcionalmente filtra por rango de fechas.
  - Ordena por `fecha` descendente.
  - Devuelve un queryset paginado.
- `obtener_recojo(tenant, recojo_id)`:
  - Busca el recojo filtrando por `tenant`.
  - Si no existe o pertenece a otro tenant, lanza `NoEncontrado`.

## Permisos
- Crear: `recojos.add_recojo`.
- Ver: `recojos.view_recojo`.
- Listar: `recojos.list_recojo`.
- Todos se asignan al rol `USUARIO_TENANT`.
- El Administrador de plataforma y el Responsable de almacén no reciben estos permisos por defecto.
- Los servicios vuelven a validar rol, tenant y región; nunca se confía solo en la vista.
- No se acepta `tenant_id` desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/recojos/` | GET | Listado paginado con filtro por fecha |
| `/recojos/nuevo/` | GET / POST | Formulario de recojo |
| `/recojos/validar-series/` | POST | Validación en tiempo real de series pegadas o escaneadas |
| `/recojos/<id>/` | GET | Detalle del recojo |

### Pantallas
- **Listado:** Fecha, tenant, número de líneas, total series, total cantidad. Filtro por rango de fechas.
- **Formulario de recojo:**
  - Fecha (precompletada con hoy, editable).
  - Material (selector del catálogo, autocompletado).
  - Tipo de material (solo lectura, del catálogo).
  - Lote (solo lectura, del catálogo).
  - Para seriados: campo de texto para pegar series o escanear.
  - Para no seriados: campo numérico para cantidad.
  - Vista previa en tiempo real de series con estado (válida, inválida, duplicada, ya existe).
  - Botón "Agregar línea" para añadir más materiales.
  - Botón "Guardar" que solo se habilita si todas las validaciones pasan.
- **Detalle:** Datos del recojo, lista de líneas con sus series o cantidades.

### Validación en tiempo real
- El endpoint `/recojos/validar-series/` recibe:
  - Lista de series (texto separado por saltos de línea).
  - Material (para filtrar por tipo si es necesario).
- Devuelve JSON con:
  - Lista de series con estado: `{serie: "ABC123456789", estado: "valida"}`.
  - Estados posibles: `valida`, `invalida_formato`, `duplicada`, `ya_existe`.
- El frontend usa HTMX para actualizar la vista previa sin recargar la página.

## Integraciones
- **Stock (spec 005):** el recojo incrementa el stock general del tenant. La integración se hace a través del servicio de stock.
- **Series (transversal):** las series creadas en el recojo se registran en el módulo de series con tenant y región.
- **Catálogo de materiales (spec 002):** el selector de materiales consulta el catálogo compartido.
- **Conciliación (spec 010):** las series del recojo se comparan con el reporte de Lari.
- **Asignaciones (spec 006):** las series del recojo pasan a estar disponibles para asignación.

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Tenant de la sesión | Servicio y decorador | "No tienes permiso para registrar recojos" |
| Región del tenant | Servicio | "Solo puedes registrar recojos de tu región" |
| Serie formato 12 caracteres | Formulario, servicio y `CheckConstraint` | "La serie debe tener 12 caracteres alfanuméricos" |
| Serie única en sistema | Servicio y validación previa | "La serie ya está registrada en el sistema" |
| Serie no duplicada en recojo | Servicio y validación previa | "La serie está duplicada en el recojo" |
| Material existe en catálogo | Servicio | "El material no existe en el catálogo" |
| Cantidad > 0 para no seriados | Formulario y servicio | "La cantidad debe ser mayor a 0" |
| Serie o cantidad obligatoria | Formulario y `CheckConstraint` | "Debe indicar serie o cantidad" |
| Todo o nada | Servicio y transacción | "Si alguna serie es inválida, no se guarda el recojo" |

## Transacciones y concurrencia
- La creación del recojo, sus líneas, las series y el incremento de stock se ejecutan en una sola transacción.
- La validación previa se ejecuta antes de la transacción para fallar rápido.
- Si dos sesiones intentan registrar la misma serie simultáneamente:
  - La primera en validar_previo pasa.
  - La segunda detecta que la serie ya existe (porque la primera ya la guardó) y falla.
- No se usan bloqueos de aplicación; la restricción única de serie en la base de datos es la fuente de verdad.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_crear_recojo_valido_incrementa_stock_y_audita`
- `test_serie_normalizada_mayusculas_sin_espacios`
- `test_serie_con_formato_invalido_se_rechaza`
- `test_serie_duplicada_en_mismo_recojo_se_rechaza`
- `test_serie_ya_existente_en_sistema_se_rechaza`
- `test_recojo_con_serie_invalida_no_se_guarda_todo_o_nada`
- `test_material_no_seriado_con_cantidad_se_guarda`
- `test_material_seriado_con_cantidad_distinta_de_1_se_rechaza`
- `test_tenant_solo_puede_registrar_recojos_de_su_region`
- `test_tenant_de_otra_region_no_puede_registrar_recojo`
- `test_validacion_previa_devuelve_estados_correctos`
- `test_validacion_en_tiempo_real_htmx_actualiza_vista_previa`
- `test_recojo_con_varias_lineas_se_guarda_completo`
- `test_incremento_stock_general_por_material_seriado`
- `test_incremento_stock_general_por_material_no_seriado`
- `test_series_creadas_tienen_tenant_y_region_correctos`
- `test_lista_recojos_solo_muestra_del_tenant`
- `test_no_se_puede_crear_recojo_sin_lineas`

Además, pruebas de base de datos:
- Insertar una serie con formato inválido directamente debe fallar.
- Insertar dos líneas del mismo recojo con la misma serie debe fallar.
- Insertar una línea con serie y cantidad != 1 debe fallar.
- Insertar una línea sin serie ni cantidad debe fallar.

## Decisiones y riesgos
- **Recojo por formulario, no Excel:** por decisión de negocio (RF-16). Esto simplifica la validación y evita errores de formato.
- **Normalización de series:** se hace antes de cualquier validación para asegurar consistencia.
- **Validación previa separada de guardado:** permite mostrar errores al usuario antes de intentar la transacción.
- **Vista previa en tiempo real:** mejora la usabilidad al permitir corregir errores antes de guardar.
- **Región explícita en Recojo:** aunque se deriva de tenant, se guarda para facilitar consultas por región sin joins.
- **Todo o nada:** la transacción asegura que no se guardan recojos parciales. Si falla una línea, falla todo.
- **Índice en serie:** es crítico para rendimiento al validar existencia de series. Si el volumen crece, se evalúa particionamiento.
- **Concurrencia en series:** la validación previa + restricción única maneja el caso de dos usuarios intentando registrar la misma serie simultáneamente.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Scanner de código de barras:** el campo de texto acepta entrada por scanner (que funciona como teclado rápido). No se requiere lógica especial.
- **Integración con stock:** el recojo llama al servicio de stock para incrementar. Si el stock falla, toda la transacción se revierte.
