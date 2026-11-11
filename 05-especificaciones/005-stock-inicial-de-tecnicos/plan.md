# Plan técnico: 005 Stock Inicial de Técnicos

## Referencias
- Spec: `05-especificaciones/005-stock-inicial-de-tecnicos/spec.md`
- Contrato: `04-contratos/excel-stock-inicial.md`
- Reglas: `03-reglas-de-dominio/stock.md`, `series.md`, `auditoria.md`
- ADR: ADR-012 (conciliación), ADR-013 (Excel)
- Stack: Django LTS, PostgreSQL, HTMX y pytest, según la sección final de la constitución.

## Módulos afectados
- App Django nueva `stock_inicial`: modelo `CargaStockInicial`, `LineaStockInicial`, servicios, formularios y vistas.
- App `tenants`: agregar campo `stock_inicial_cargado` al modelo `Tenant`.
- App `materiales`: consulta del catálogo de materiales.
- App `series`: validación de existencia de series.
- App `stock`: asignación directa al stock del técnico (no pasa por stock general).
- App `tecnicos`: validación de existencia de técnicos.
- App `auditoria`: modelo `RegistroCambio`, compartido.
- Middleware de contexto de tenant de la spec 001.
- No se modifican recojos, asignaciones, traspasos ni conciliaciones.

## Modelo de datos

```python
# Cambio en tenants.models.Tenant
class Tenant(models.Model):
    # ... campos existentes ...
    stock_inicial_cargado = models.BooleanField(default=False)
    fecha_stock_inicial = models.DateTimeField(null=True, blank=True)
    # ... resto del modelo ...


class CargaStockInicial(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="cargas_stock_inicial",
    )
    fecha = models.DateTimeField(auto_now_add=True)
    metodo = models.CharField(
        max_length=10,
        choices=[("EXCEL", "Excel"), ("FORMULARIO", "Formulario")],
    )
    archivo = models.CharField(max_length=255, null=True, blank=True)  # Nombre del archivo Excel
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cargas_stock_inicial_creadas",
    )

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "fecha"], name="carga_stock_tenant_fecha"),
        ]

    def __str__(self):
        return f"Carga {self.id} - {self.tenant} - {self.metodo}"


class LineaStockInicial(models.Model):
    carga = models.ForeignKey(
        "CargaStockInicial",
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    tecnico = models.ForeignKey(
        "tecnicos.Tecnico",
        on_delete=models.PROTECT,
        related_name="lineas_stock_inicial",
    )
    material = models.ForeignKey(
        "materiales.Material",
        on_delete=models.PROTECT,
        related_name="lineas_stock_inicial",
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
                name="linea_stock_serie_o_cantidad",
            ),
            models.CheckConstraint(
                condition=~Q(serie__isnull=False) | Q(cantidad=1),
                name="linea_stock_serie_cantidad_uno",
            ),
            models.CheckConstraint(
                condition=Q(serie__regex=r"^[A-Z0-9]{12}$") | Q(serie__isnull=True),
                name="linea_stock_serie_formato",
            ),
        ]
        indexes = [
            models.Index(fields=["carga", "tecnico"], name="linea_stock_carga_tecnico"),
            models.Index(fields=["serie"], name="linea_stock_serie"),
        ]

    def __str__(self):
        if self.serie:
            return f"{self.tecnico.nif} - {self.material.codigo} - {self.serie}"
        return f"{self.tecnico.nif} - {self.material.codigo} - {self.cantidad}"
```

- `Tenant.stock_inicial_cargado`: marca si el tenant ya cargó su stock inicial.
- `Tenant.fecha_stock_inicial`: fecha en que se cargó el stock inicial.
- `CargaStockInicial`: representa una carga de stock inicial (por Excel o formulario).
- `LineaStockInicial`: representa cada línea de la carga (técnico, material, serie o cantidad).
- Para materiales seriados: `serie` tiene valor, `cantidad=1`.
- Para materiales no seriados: `serie` es NULL, `cantidad>0`.
- Las restricciones son idénticas a las de `LineaRecojo` para mantener consistencia.
- El índice en `serie` acelera la validación de duplicados y existencia.

## Migraciones
- `tenants/migrations/XXXX_add_stock_inicial_fields.py`: agregar `stock_inicial_cargado` y `fecha_stock_inicial` a `Tenant`.
- `stock_inicial/migrations/0001_initial.py`: modelos `CargaStockInicial` y `LineaStockInicial` con restricciones e índices.
- No se crean cargas por migración.
- No se modifican tablas de stock, series, asignaciones, traspasos ni conciliaciones.

## Servicios (lógica de negocio)
Viven en `stock_inicial/services.py`, no en las vistas.

### Validación de estado
- `validar_puede_cargar_stock_inicial(tenant)`:
  - Verifica que `tenant.stock_inicial_cargado == False`.
  - Si ya está cargado, lanza `StockInicialYaCargado`.
- `validar_puede_editar_stock_inicial(tenant)`:
  - Verifica que `tenant.stock_inicial_cargado == True`.
  - Si no está cargado, lanza `StockInicialNoCargado`.
- `validar_cuenta_tenant(actor, tenant)`:
  - Verifica que `actor.rol == "USUARIO_TENANT"`.
  - Verifica que `actor.tenant_id == tenant.id`.
  - Verifica que la cuenta esté activa y que el tenant esté activo.
  - Si no cumple, lanza `PermisoDenegado`.

### Validación de técnicos
- `validar_tecnico_existe(tenant, nif)`:
  - Busca el técnico filtrando por `tenant` y `nif`.
  - Si no existe, lanza `TecnicoNoExiste`.

### Validación de materiales
- `validar_material_existe(codigo)`:
  - Consulta el catálogo de materiales.
  - Si no existe, lanza `MaterialNoExiste`.

### Validación de series (reutiliza lógica de recojos)
- `normalizar_serie(serie)`: igual que en recojos.
- `validar_formato_serie(serie)`: igual que en recojos.
- `validar_serie_no_existe(serie)`: igual que en recojos.
- `validar_serie_no_duplicada(lista_series)`: igual que en recojos.

### Procesamiento de Excel
- `leer_excel_stock_inicial(archivo)`:
  - Usa `openpyxl` para leer el archivo Excel.
  - Extrae las columnas: Material, Lote, Libre utilización, Número de serie, Nº ident.fis.1, Texto breve material.
  - Devuelve una lista de diccionarios con los datos de cada fila.
  - Si el formato es inválido, lanza `FormatoExcelInvalido`.

### Validación previa al cargar
- `validar_carga_previa(tenant, lineas)`:
  - Para cada línea:
    - Valida que el técnico exista en el tenant.
    - Valida que el material exista en el catálogo.
    - Normaliza y valida formato de serie (si aplica).
    - Valida que la serie no exista en el sistema.
    - Valida que la serie no esté duplicada en la misma carga.
    - Valida que la cantidad sea > 0 para no seriados.
  - Si alguna validación falla, lanza la excepción correspondiente con detalle de errores.
  - Devuelve la lista de líneas validadas.

### Carga de stock inicial
- `cargar_stock_inicial(tenant, lineas, metodo, archivo=None, actor=None)`:
  - `validar_puede_cargar_stock_inicial(tenant)`.
  - `validar_cuenta_tenant(actor, tenant)`.
  - `validar_carga_previa(tenant, lineas)`.
  - En `transaction.atomic`:
    - Crea la `CargaStockInicial` con tenant, método y archivo.
    - Crea cada `LineaStockInicial` con sus datos.
    - Para seriados: crea la `Serie` con tenant y región.
    - Asigna el stock directamente al técnico (no pasa por stock general).
    - Marca `tenant.stock_inicial_cargado = True`.
    - Marca `tenant.fecha_stock_inicial = timezone.now()`.
    - Registra auditoría de la carga.
  - Si falla alguna inserción, toda la transacción se revierte.
  - Devuelve la `CargaStockInicial` creada.

### Edición de stock inicial
- `agregar_linea_stock_inicial(carga, linea, actor)`:
  - `validar_puede_editar_stock_inicial(carga.tenant)`.
  - `validar_cuenta_tenant(actor, carga.tenant)`.
  - Valida que el técnico exista en el tenant.
  - Valida que el material exista en el catálogo.
  - Normaliza y valida formato de serie (si aplica).
  - Valida que la serie no exista en el sistema.
  - Valida que la serie no esté duplicada en la carga.
  - Valida que la cantidad sea > 0 para no seriados.
  - En `transaction.atomic`:
    - Crea la `LineaStockInicial`.
    - Para seriados: crea la `Serie` con tenant y región.
    - Asigna el stock al técnico.
    - Registra auditoría del cambio.
  - Devuelve la línea creada.

- `eliminar_linea_stock_inicial(linea, actor)`:
  - `validar_puede_editar_stock_inicial(linea.carga.tenant)`.
  - `validar_cuenta_tenant(actor, linea.carga.tenant)`.
  - En `transaction.atomic`:
    - Si es seriado: elimina la `Serie` del sistema.
    - Resta el stock del técnico.
    - Elimina la `LineaStockInicial`.
    - Registra auditoría del cambio (valor anterior, valor nuevo = eliminado).

- `modificar_cantidad_stock_inicial(linea, nueva_cantidad, actor)`:
  - `validar_puede_editar_stock_inicial(linea.carga.tenant)`.
  - `validar_cuenta_tenant(actor, linea.carga.tenant)`.
  - Valida que la línea sea de material no seriado.
  - Valida que la nueva cantidad sea > 0.
  - En `transaction.atomic`:
    - Ajusta el stock del técnico (diferencia entre nueva y anterior cantidad).
    - Actualiza `linea.cantidad = nueva_cantidad`.
    - Registra auditoría del cambio (valor anterior, valor nuevo).
  - Devuelve la línea actualizada.

### Reinicio (solo para implementación)
- `reiniciar_stock_inicial(tenant, actor)`:
  - Solo disponible para Administrador de plataforma.
  - Verifica que el usuario tenga permiso especial.
  - En `transaction.atomic`:
    - Marca `tenant.stock_inicial_cargado = False`.
    - Marca `tenant.fecha_stock_inicial = None`.
    - Borra todas las `CargaStockInicial` del tenant (en cascada borra las líneas).
    - Borra las series creadas por esa carga.
    - Ajusta el stock de los técnicos (resta lo cargado).
    - Registra auditoría del reinicio.
  - Esta operación es solo para correcciones durante la implementación inicial.

### Consultas
- `obtener_carga_stock_inicial(tenant)`:
  - Devuelve la carga de stock inicial del tenant (si existe).
  - Si no existe, lanza `NoEncontrado`.
- `listar_lineas_stock_inicial(tenant)`:
  - Devuelve todas las líneas de stock inicial del tenant.
  - Agrupadas por técnico.

## Permisos
- Cargar: `stock_inicial.add_cargastockinicial`.
- Ver: `stock_inicial.view_cargastockinicial`.
- Editar: `stock_inicial.change_cargastockinicial`.
- Reiniciar: `stock_inicial.reiniciar_stockinicial` (solo Admin plataforma).
- Cargar, Ver y Editar se asignan al rol `USUARIO_TENANT`.
- Reiniciar se asigna solo al rol `ADMIN_PLATAFORMA`.
- Los servicios vuelven a validar rol, tenant y estado; nunca se confía solo en la vista.
- No se acepta `tenant_id` desde formularios, URLs o archivos.
- Se recomienda RLS en PostgreSQL como respaldo del filtrado por tenant.

## Interfaz y endpoints

| Ruta | Método | Función |
|---|---|---|
| `/stock-inicial/` | GET | Pantalla de carga de stock inicial |
| `/stock-inicial/cargar-excel/` | POST | Carga por Excel |
| `/stock-inicial/cargar-formulario/` | POST | Carga por formulario |
| `/stock-inicial/validar-excel/` | POST | Validación previa de Excel |
| `/stock-inicial/<id>/` | GET | Detalle de la carga |
| `/stock-inicial/<id>/editar/` | GET / POST | Edición del stock inicial |
| `/stock-inicial/<id>/agregar-linea/` | POST | Agregar línea al stock inicial |
| `/stock-inicial/linea/<id>/eliminar/` | POST | Eliminar línea del stock inicial |
| `/stock-inicial/linea/<id>/modificar/` | POST | Modificar cantidad de línea |

### Pantallas
- **Pantalla principal:**
  - Muestra si el stock inicial ya está cargado.
  - Si no está cargado: dos opciones (Excel y formulario).
  - Si está cargado: muestra resumen de la carga y fecha.
- **Carga por Excel:**
  - Formulario para subir archivo Excel.
  - Botón "Validar" que verifica el formato y las filas antes de cargar.
  - Vista previa de errores si los hay.
  - Botón "Cargar" que solo se habilita si todo es válido.
  - Barra de progreso durante la carga.
- **Carga por formulario:**
  - Selector de técnico.
  - Selector de material.
  - Campo de series o cantidad (según tipo de material).
  - Botón "Agregar línea" para añadir más materiales.
  - Vista previa de líneas agregadas.
  - Botón "Guardar" que carga el stock inicial para ese técnico.
- **Detalle de carga:**
  - Datos de la carga (fecha, método, archivo).
  - Lista de líneas agrupadas por técnico.
  - Totales (técnicos, series, cantidades).
  - Botón "Editar" para modificar el stock inicial.
- **Edición de stock inicial:**
  - Lista de líneas actuales agrupadas por técnico.
  - Botón "Agregar línea" para añadir series o cantidades faltantes.
  - Botón "Eliminar" en cada línea para quitar series o cantidades incorrectas.
  - Botón "Modificar cantidad" en líneas no seriadas para ajustar cantidades.
  - Vista previa de cambios antes de guardar.
  - Botón "Guardar cambios" que aplica todas las modificaciones transaccionalmente.

### Validación en tiempo real
- El endpoint `/stock-inicial/validar-excel/` recibe:
  - Archivo Excel.
- Devuelve JSON con:
  - Estado: `valido` o `invalido`.
  - Lista de errores si los hay.
  - Resumen de filas si es válido.
- El frontend usa HTMX para mostrar el resultado sin recargar la página.

## Integraciones
- **Stock (transversal):** el stock inicial asigna directamente al técnico. La integración se hace a través del servicio de stock.
- **Series (transversal):** las series creadas en el stock inicial se registran en el módulo de series con tenant y región.
- **Catálogo de materiales (spec 002):** el selector de materiales consulta el catálogo compartido.
- **Técnicos (spec 003):** la validación de técnicos usa los servicios del módulo de técnicos.
- **Recojos (spec 004):** las validaciones de series se reutilizan del módulo de recojos.
- **Conciliación (spec 010):** las series del stock inicial se comparan con el reporte de Lari.
- **Asignaciones (spec 006):** las series del stock inicial pasan a estar disponibles para traspaso (no para asignación, ya que están en el técnico).

## Validaciones (dónde vive cada una)

| Regla | Dónde se valida | Mensaje |
|---|---|---|
| Stock inicial no cargado previamente | Servicio | "El stock inicial ya fue cargado para este tenant" |
| Tenant de la sesión | Servicio y decorador | "No tienes permiso para cargar stock inicial" |
| Técnico existe en tenant | Servicio | "El técnico no existe en este tenant" |
| Material existe en catálogo | Servicio | "El material no existe en el catálogo" |
| Serie formato 12 caracteres | Servicio (reutiliza recojos) | "La serie debe tener 12 caracteres alfanuméricos" |
| Serie única en sistema | Servicio (reutiliza recojos) | "La serie ya está registrada en el sistema" |
| Serie no duplicada en carga | Servicio (reutiliza recojos) | "La serie está duplicada en la carga" |
| Cantidad > 0 para no seriados | Servicio | "La cantidad debe ser mayor a 0" |
| Transaccionalidad | Servicio y transacción | "Si hay errores, no se carga nada" |

## Transacciones y concurrencia
- La carga del stock inicial, sus líneas, las series y la asignación a técnicos se ejecutan en una sola transacción.
- La validación previa se ejecuta antes de la transacción para fallar rápido.
- Si dos sesiones intentan cargar stock inicial para el mismo tenant simultáneamente:
  - La primera en validar previo pasa.
  - La segunda detecta que `stock_inicial_cargado` ya es True (porque la primera ya lo marcó) y falla.
- El reinicio del stock inicial también es transaccional y se usa solo en implementación.

## Pruebas
Un caso por criterio de aceptación. Nombres propuestos:

- `test_cargar_stock_inicial_por_excel_exitoso`
- `test_cargar_stock_inicial_por_formulario_exitoso`
- `test_tecnico_no_existe_rechaza_carga`
- `test_material_no_existe_rechaza_carga`
- `test_serie_duplicada_en_excel_rechaza_carga`
- `test_serie_ya_existe_en_sistema_rechaza_carga`
- `test_carga_unica_segunda_intento_rechazada`
- `test_asignacion_directa_al_tecnico`
- `test_auditoria_de_carga_registra_usuario_y_archivo`
- `test_transaccionalidad_error_en_una_fila_falla_todo`
- `test_validacion_previa_excel_devuelve_errores`
- `test_mark_tenant_como_stock_inicial_cargado`
- `test_reiniciar_stock_inicial_solo_admin_plataforma`
- `test_reiniciar_stock_inicial_borra_carga_y_series`
- `test_lista_lineas_stock_inicial_agrupada_por_tecnico`
- `test_agregar_linea_stock_inicial_crea_serie_y_asigna`
- `test_agregar_linea_stock_inicial_audita_cambio`
- `test_eliminar_linea_stock_inicial_elimina_serie_y_audita`
- `test_modificar_cantidad_stock_inicial_audita_cambio`
- `test_edicion_transaccional_error_falla_todo`
- `test_no_puede_editar_stock_inicial_no_cargado`

Además, pruebas de base de datos:
- Insertar una serie con formato inválido directamente debe fallar.
- Insertar dos líneas de la misma carga con la misma serie debe fallar.
- Insertar una línea con serie y cantidad != 1 debe fallar.
- Insertar una línea sin serie ni cantidad debe fallar.

## Decisiones y riesgos
- **Dos formas de carga:** se permite Excel y formulario para flexibilidad. El Excel es mejor para grandes volúmenes, el formulario para correcciones puntuales.
- **Asignación directa al técnico:** el stock inicial no pasa por el stock general. Esto es diferente al flujo normal (recojo → stock general → asignación), pero es necesario para la implementación inicial.
- **Formato idéntico a reporte de Lari:** facilita la migración ya que los tenants pueden usar el mismo formato que ya conocen.
- **Carga única:** el flag `stock_inicial_cargado` evita cargas accidentales posteriores. El reinicio solo está disponible para el Admin durante implementación.
- **Reutilización de validaciones:** las validaciones de series se reutilizan del módulo de recojos para mantener consistencia.
- **Índice en serie:** es crítico para rendimiento al validar existencia de series en grandes volúmenes.
- **Transaccionalidad:** asegura que no se cargan stock inicial parciales. Si falla una fila, falla todo.
- **Concurrencia:** el flag `stock_inicial_cargado` resuelve el caso de dos usuarios intentando cargar simultáneamente.
- **Auditoría compartida:** se usa `RegistroCambio` para evitar un sistema de auditoría por módulo.
- **Riesgo de reinicio:** el comando de reinicio es poderoso y solo debe usarse durante implementación. Se documenta claramente y se puede remover después.
- **Integración con stock:** el stock inicial llama al servicio de stock para asignar directamente al técnico. Si el stock falla, toda la transacción se revierte.
